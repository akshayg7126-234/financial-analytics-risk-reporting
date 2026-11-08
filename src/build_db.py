"""Load CSVs into SQLite and create the schema + views from /sql."""
import sqlite3, pandas as pd
from pathlib import Path
R = Path(__file__).resolve().parent.parent
def build():
    db = R / "data" / "finance.db"
    db.unlink(missing_ok=True)
    con = sqlite3.connect(db)
    con.executescript((R / "sql/01_schema.sql").read_text())
    for t, f in [("loans", "loans.csv"), ("gl_monthly", "gl_monthly.csv"),
                 ("balance_sheet", "balance_sheet.csv"), ("portfolio_monthly", "portfolio_monthly.csv")]:
        df = pd.read_csv(R / "data" / f)
        df = df[[c[1] for c in con.execute(f"PRAGMA table_info({t})")]]
        df.to_sql(t, con, if_exists="append", index=False)
    con.executescript((R / "sql/02_views.sql").read_text())
    con.commit()
    return con
if __name__ == "__main__":
    c = build()
    print(c.execute("SELECT COUNT(*) FROM loans").fetchone(), "loans loaded")
    for r in c.execute("SELECT period, round(net_income) FROM v_pnl ORDER BY 1 DESC LIMIT 3"): print(r)
    print("max |balance check|:", c.execute("SELECT MAX(ABS(balance_check)) FROM v_balance_sheet").fetchone()[0])
