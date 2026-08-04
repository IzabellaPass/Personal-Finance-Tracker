import sqlite3
from calendar import monthrange
from datetime import date, datetime, time
from html import escape
from pathlib import Path

import pandas as pd
import streamlit as st


DB_PATH = Path(__file__).with_name("finance.db")
EXPENSE_CATEGORIES = ["Spesa", "Casa", "Trasporti", "Salute", "Svago", "Shopping", "Altro"]
INCOME_CATEGORIES = ["Stipendio", "Freelance", "Rimborso", "Regalo", "Altro"]


def connect() -> sqlite3.Connection:
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database() -> None:
    with connect() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS diaries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL COLLATE NOCASE UNIQUE,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        connection.execute(
            "INSERT OR IGNORE INTO diaries(name) VALUES ('Il mio diario')"
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                type TEXT NOT NULL CHECK (type IN ('income', 'expense')),
                category TEXT NOT NULL,
                amount REAL NOT NULL CHECK (amount > 0),
                description TEXT DEFAULT '',
                transaction_time TEXT DEFAULT ''
            )
            """
        )
        columns = {row["name"] for row in connection.execute("PRAGMA table_info(transactions)")}
        if "description" not in columns:
            connection.execute("ALTER TABLE transactions ADD COLUMN description TEXT DEFAULT ''")
        if "transaction_time" not in columns:
            connection.execute("ALTER TABLE transactions ADD COLUMN transaction_time TEXT DEFAULT ''")
        if "diary_id" not in columns:
            connection.execute("ALTER TABLE transactions ADD COLUMN diary_id INTEGER")
        default_diary_id = connection.execute(
            "SELECT id FROM diaries ORDER BY id LIMIT 1"
        ).fetchone()[0]
        connection.execute(
            "UPDATE transactions SET diary_id = ? WHERE diary_id IS NULL",
            (default_diary_id,),
        )


def list_diaries() -> list[sqlite3.Row]:
    with connect() as connection:
        return connection.execute(
            "SELECT id, name FROM diaries ORDER BY id"
        ).fetchall()


def create_diary(name: str) -> int:
    clean_name = name.strip()
    if not clean_name:
        raise ValueError("Inserisci un nome.")
    with connect() as connection:
        cursor = connection.execute("INSERT INTO diaries(name) VALUES (?)", (clean_name,))
        return int(cursor.lastrowid)


def load_period(diary_id: int, start: str, end: str) -> pd.DataFrame:
    with connect() as connection:
        return pd.read_sql_query(
            """
            SELECT id, date, type, category, amount,
                   COALESCE(description, '') AS description,
                   COALESCE(transaction_time, '') AS transaction_time
            FROM transactions
            WHERE diary_id = ? AND date BETWEEN ? AND ?
            ORDER BY date DESC, id DESC
            """,
            connection,
            params=(diary_id, start, end),
        )


def save_transaction(
    diary_id: int,
    selected_day: date,
    transaction_type: str,
    category: str,
    amount: float,
    description: str,
    transaction_time: time,
) -> None:
    with connect() as connection:
        connection.execute(
            """
            INSERT INTO transactions(
                diary_id, date, type, category, amount, description, transaction_time
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                diary_id,
                selected_day.isoformat(),
                transaction_type,
                category,
                amount,
                description.strip(),
                transaction_time.strftime("%H:%M"),
            ),
        )


def remove_transaction(transaction_id: int, diary_id: int) -> None:
    with connect() as connection:
        connection.execute(
            "DELETE FROM transactions WHERE id = ? AND diary_id = ?",
            (transaction_id, diary_id),
        )


def euro(value: float, signed: bool = False) -> str:
    prefix = "+" if signed and value > 0 else ""
    formatted = f"{abs(value):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    sign = "−" if value < 0 else prefix
    return f"{sign}€ {formatted}"


def totals(frame: pd.DataFrame) -> tuple[float, float, float]:
    if frame.empty:
        return 0.0, 0.0, 0.0
    income = float(frame.loc[frame["type"] == "income", "amount"].sum())
    expenses = float(frame.loc[frame["type"] == "expense", "amount"].sum())
    return income, expenses, income - expenses


def show_metrics(frame: pd.DataFrame, balance_label: str) -> None:
    income, expenses, balance = totals(frame)
    col_1, col_2, col_3 = st.columns(3)
    col_1.metric("Entrate", euro(income))
    col_2.metric("Spese", euro(expenses))
    col_3.metric(balance_label, euro(balance, signed=True))


def show_entries(frame: pd.DataFrame, show_date: bool = False) -> None:
    if frame.empty:
        st.markdown(
            '<div class="empty">Ancora nessun movimento.</div>',
            unsafe_allow_html=True,
        )
        return

    for row in frame.itertuples():
        is_income = row.type == "income"
        category = escape(str(row.category))
        readable_date = pd.to_datetime(row.date).strftime("%d/%m/%Y")
        readable_time = row.transaction_time.strip() or "ora non indicata"
        detail = escape(row.description.strip() or ("Entrata" if is_income else "Spesa"))
        note = f"{readable_date} · {escape(readable_time)} · {detail}"
        amount = row.amount if is_income else -row.amount
        amount_class = "entry-income" if is_income else "entry-expense"
        st.markdown(
            f"""
            <div class="entry">
                <div>
                    <div class="entry-title">{category}</div>
                    <div class="entry-note">{note}</div>
                </div>
                <div class="{amount_class}">{euro(amount, signed=True)}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


st.set_page_config(page_title="Il mio diario", page_icon="€", layout="centered")

st.markdown(
    """
    <style>
        :root {
            --text: #12372f;
            --muted: #526b64;
            --green: #23745d;
            --green-light: #e6f3ee;
            --red: #a33f36;
            --background: #f4f8f6;
            --card: #ffffff;
            --border: #cbdcd5;
        }
        .stApp { background: var(--background); color: var(--text); }
        .block-container { max-width: 860px; padding-top: 2rem; padding-bottom: 4rem; }
        h1, h2, h3, p, label, [data-testid="stWidgetLabel"] * {
            color: var(--text) !important;
        }
        body, span, div { border-color: var(--border); }
        h1 { font-size: 2.25rem !important; margin-bottom: .15rem !important; letter-spacing: -.04em; }
        h2, h3 { font-size: 1.2rem !important; }
        .intro { color: var(--muted) !important; margin: 0 0 1.4rem; }
        [data-testid="stMetric"], [data-testid="stForm"] {
            background: var(--card);
            border: 1px solid var(--border);
            border-radius: 18px;
            box-shadow: 0 8px 28px rgba(35, 116, 93, .06);
        }
        [data-testid="stMetric"] { padding: 14px 16px; }
        [data-testid="stMetricLabel"] *, [data-testid="stMetricValue"] {
            color: var(--text) !important;
        }
        [data-testid="stForm"] { padding: 1.2rem; }
        [data-testid="stVerticalBlockBorderWrapper"] {
            background: rgba(255, 255, 255, .78);
            border: 1px solid var(--border) !important;
            border-radius: 20px;
            box-shadow: 0 10px 35px rgba(35, 116, 93, .06);
        }
        div[data-baseweb="input"], div[data-baseweb="select"] > div {
            background: white !important;
            border-color: var(--border) !important;
        }
        input { color: var(--text) !important; }
        [data-testid="stNumberInputContainer"],
        [data-testid="stSelectbox"] [role="group"],
        [data-testid="stTextInputRootElement"] > div,
        [data-testid="stTimeInput"] [data-baseweb="select"] > div {
            background: white !important;
            color: var(--text) !important;
            border-color: var(--border) !important;
        }
        [data-testid="stTimeInputTimeDisplay"] {
            color: var(--text) !important;
            opacity: 1 !important;
        }
        [data-testid="stTimeInput"] svg { fill: var(--green) !important; }
        [data-testid="stTextInputRootElement"] [data-baseweb="base-input"],
        [data-testid="stTextInputRootElement"] input {
            background: white !important;
            color: #2f745f !important;
        }
        [data-testid="stTextInputRootElement"] [data-baseweb="base-input"] {
            border: 1px solid var(--border) !important;
            box-shadow: none !important;
        }
        [data-testid="stTextInputRootElement"] [data-baseweb="base-input"]:focus-within {
            border-color: var(--green) !important;
            box-shadow: 0 0 0 2px var(--green-light) !important;
        }
        [data-testid="stTextInputRootElement"] input::placeholder {
            color: #75988c !important;
            opacity: 1 !important;
        }
        [data-testid="stTextInput"] [data-testid="stWidgetLabel"] p {
            color: #2f745f !important;
        }
        [data-testid="stNumberInputStepDown"],
        [data-testid="stNumberInputStepUp"],
        [data-testid="stSelectbox"] button {
            background: var(--green-light) !important;
            color: var(--text) !important;
        }
        [data-testid="stButtonGroup"] button {
            background: white !important;
            border-color: var(--border) !important;
            color: var(--text) !important;
        }
        [data-testid="stButtonGroup"] button p {
            color: var(--text) !important;
        }
        [data-testid="stButtonGroup"] button[aria-checked="true"] {
            background: var(--green) !important;
            border-color: var(--green) !important;
        }
        [data-testid="stButtonGroup"] button[aria-checked="true"] p {
            color: white !important;
        }
        .stButton button, [data-testid="stFormSubmitButton"] button {
            border-radius: 10px;
            border: 1px solid var(--green);
            color: var(--green);
            background: white;
        }
        [data-testid="stFormSubmitButton"] button {
            background: var(--green);
            color: white !important;
        }
        [data-testid="stFormSubmitButton"] button p { color: white !important; }
        [data-testid="stPopoverButton"] {
            background: var(--green) !important;
            border: 1px solid var(--green) !important;
            color: white !important;
        }
        [data-testid="stPopoverButton"] * { color: white !important; }
        [data-testid="stPopoverBody"] {
            background: white !important;
            border: 1px solid var(--border) !important;
        }
        [data-testid="stPopoverBody"] * { color: var(--text) !important; }
        [data-testid="stPopoverBody"] [data-testid="stFormSubmitButton"] * {
            color: white !important;
        }
        [data-testid="stToast"] {
            background: var(--green-light) !important;
            color: var(--text) !important;
        }
        [data-testid="stToast"] * { color: var(--text) !important; }
        button[role="tab"] p { color: var(--text) !important; font-weight: 650; }
        button[role="tab"][aria-selected="true"] { border-bottom-color: var(--green) !important; }
        .entry {
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 1rem;
            background: var(--card);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 14px 17px;
            margin-bottom: 7px;
            box-shadow: 0 5px 18px rgba(35, 116, 93, .04);
        }
        .entry-title { color: var(--text); font-weight: 700; }
        .entry-note { color: #3f7667; font-size: .88rem; margin-top: 2px; }
        .entry-income { color: var(--green); font-weight: 750; white-space: nowrap; }
        .entry-expense { color: var(--red); font-weight: 750; white-space: nowrap; }
        .empty {
            color: var(--muted);
            background: white;
            border: 1px dashed var(--border);
            border-radius: 12px;
            padding: 2rem 1rem;
            text-align: center;
        }
        #MainMenu, footer { visibility: hidden; }
        .diary-kicker {
            color: var(--green);
            font-size: .78rem;
            font-weight: 750;
            letter-spacing: .09em;
            text-transform: uppercase;
            margin-bottom: .2rem;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

initialize_database()

if "selected_day" not in st.session_state:
    st.session_state.selected_day = date.today()

diaries = list_diaries()
diary_ids = [int(diary["id"]) for diary in diaries]
diary_names = {int(diary["id"]): str(diary["name"]) for diary in diaries}
active_diary_id = st.session_state.get("active_diary_id", diary_ids[0])
if active_diary_id not in diary_ids:
    active_diary_id = diary_ids[0]

st.markdown('<div class="diary-kicker">Finanze personali</div>', unsafe_allow_html=True)
st.title("Diari di famiglia")
st.markdown(
    '<p class="intro">Ogni persona ha il proprio spazio, semplice e separato.</p>',
    unsafe_allow_html=True,
)

with st.container(border=True):
    diary_col, add_col = st.columns([3, 1])
    with diary_col:
        selected_diary_id = st.selectbox(
            "Diario attivo",
            diary_ids,
            index=diary_ids.index(active_diary_id),
            format_func=lambda diary_id: diary_names[diary_id],
        )
        st.session_state.active_diary_id = selected_diary_id
    with add_col:
        st.write("")
        with st.popover("＋ Nuovo diario", width="stretch"):
            with st.form("create_diary_form", clear_on_submit=True):
                new_diary_name = st.text_input(
                    "Nome della persona",
                    placeholder="Es. Marco",
                )
                create_submitted = st.form_submit_button(
                    "Crea diario", width="stretch"
                )
            if create_submitted:
                try:
                    new_diary_id = create_diary(new_diary_name)
                except sqlite3.IntegrityError:
                    st.error("Esiste già un diario con questo nome.")
                except ValueError as error:
                    st.error(str(error))
                else:
                    st.session_state.active_diary_id = new_diary_id
                    st.toast(f"Diario di {new_diary_name.strip()} creato")
                    st.rerun()

st.subheader(diary_names[selected_diary_id])

day_tab, month_tab = st.tabs(["Giorno", "Mese"])

with day_tab:
    selected_day = st.date_input("Data", format="DD/MM/YYYY", key="selected_day")

    daily = load_period(
        selected_diary_id, selected_day.isoformat(), selected_day.isoformat()
    )
    show_metrics(daily, "Saldo")

    st.subheader("Nuovo movimento")
    with st.form("quick_entry", clear_on_submit=True):
        type_col, amount_col, time_col = st.columns(3)
        with type_col:
            type_label = st.segmented_control(
                "Tipo", ["Spesa", "Entrata"], default="Spesa", width="stretch"
            )
        with amount_col:
            amount = st.number_input("Importo (€)", min_value=0.01, step=1.0, format="%.2f")
        with time_col:
            transaction_time = st.time_input(
                "Ora",
                value=datetime.now().time().replace(second=0, microsecond=0),
                step=300,
            )

        transaction_type = "income" if type_label == "Entrata" else "expense"
        categories = INCOME_CATEGORIES if transaction_type == "income" else EXPENSE_CATEGORIES
        category_col, note_col = st.columns(2)
        with category_col:
            category = st.selectbox("Categoria", categories)
        with note_col:
            description = st.text_input("Nota", placeholder="Facoltativa")

        submitted = st.form_submit_button("Salva movimento", width="stretch")

    if submitted:
        save_transaction(
            selected_diary_id,
            selected_day,
            transaction_type,
            category,
            amount,
            description,
            transaction_time,
        )
        st.toast("Movimento salvato")
        st.rerun()

    st.subheader("Movimenti del giorno")
    show_entries(daily)

    if not daily.empty:
        with st.expander("Elimina un movimento"):
            labels = {int(row.id): f"{row.category} · {euro(row.amount)}" for row in daily.itertuples()}
            selected_id = st.selectbox(
                "Movimento", list(labels), format_func=lambda item_id: labels[item_id]
            )
            if st.button("Elimina", type="secondary"):
                remove_transaction(selected_id, selected_diary_id)
                st.toast("Movimento eliminato")
                st.rerun()

with month_tab:
    month_start = selected_day.replace(day=1)
    month_end = selected_day.replace(
        day=monthrange(selected_day.year, selected_day.month)[1]
    )
    monthly = load_period(
        selected_diary_id, month_start.isoformat(), month_end.isoformat()
    )

    month_name = selected_day.strftime("%m/%Y")
    st.subheader(f"Riepilogo {month_name}")
    st.caption("Il mese segue la data scelta nella sezione Giorno.")
    show_metrics(monthly, "Saldo mensile")

    st.subheader("Movimenti del mese")
    show_entries(monthly, show_date=True)
