# Personal Finance Tracker

Una dashboard locale per registrare e analizzare entrate e spese personali, costruita con Python, Streamlit e SQLite.

## Funzioni

- riepilogo giornaliero e mensile di entrate, uscite e saldo;
- diari separati per più persone;
- creazione rapida di un nuovo diario personale;
- inserimento di entrate e uscite con data, ora, categoria e nota;
- movimenti separati per ogni diario;
- eliminazione dei movimenti;
- database SQLite locale: i dati restano sul computer.

## Avvio

Richiede Python 3.10 o successivo.

```bash
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

Streamlit aprirà automaticamente la dashboard nel browser. In alternativa, visita `http://localhost:8501`.

## Struttura

- `app.py`: dashboard e gestione dei movimenti;
- `finance.db`: database SQLite locale, creato automaticamente e non pubblicato;
- `analysis.py`: esempio di analisi SQL da terminale;
- `create_db.py`: creazione sicura di un database vuoto;
- `requirements.txt`: dipendenze Python.

## Privacy

Il progetto non invia dati finanziari a servizi esterni. Non pubblicare `finance.db` se contiene movimenti reali; per un uso personale è consigliabile aggiungerlo a `.gitignore`.
