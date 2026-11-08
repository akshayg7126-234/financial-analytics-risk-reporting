"""Embed the data into the dashboard template -> one self-contained HTML file (works offline)."""
import json, sqlite3, pandas as pd
from pathlib import Path
R = Path(__file__).resolve().parent.parent
con = sqlite3.connect(R / "data/finance.db")
pnl = pd.read_sql("select * from v_pnl order by period", con)
gl = pd.read_sql("select * from gl_monthly", con); pf = pd.read_sql("select * from portfolio_monthly order by period", con)
ln = pd.read_csv(R / "data/loans_scored.csv"); M = json.load(open(R / "outputs/model_metrics.json"))
months = list(pnl.period)
accts = [(a, gl[gl.account == a].category.iloc[0] if gl[gl.account == a].category.iloc[0] == "Revenue" else "Cost") for a in
         ["Interest income", "Fee income", "Interest expense", "Credit loss provision", "Salaries", "Marketing", "Technology", "Rent", "Professional fees", "Depreciation"]]
ai = {a[0]: i for i, a in enumerate(accts)}; mi = {m: i for i, m in enumerate(months)}
glr = [[mi[r.period], ai[r.account], round(r.actual, 2), round(r.budget, 2)] for r in gl.itertuples()]
grades = sorted(ln.grade.unique()); purposes = sorted(ln.purpose.unique())
bands = ["A - Very low risk", "B - Low risk", "C - Medium risk", "D - High risk", "E - Very high risk"]
ln["g"] = ln.grade.map({g: i for i, g in enumerate(grades)}); ln["p"] = ln.purpose.map({g: i for i, g in enumerate(purposes)})
ln["b"] = ln.risk_band.map({g: i for i, g in enumerate(bands)}); ln["m"] = ln.issue_month.map(mi).fillna(-1).astype(int)
# loans issued in 2024 (before the reporting window) are folded into month index 0
ln.loc[ln.m < 0, "m"] = 0
cube = ln.groupby(["g", "p", "b", "m"]).agg(n=("loan_id", "size"), e=("loan_amnt", "sum"), d=("default_flag", "sum")).reset_index()
data = dict(months=months, accts=accts, gl=glr, grades=grades, purposes=purposes, bands=bands, bYld=0.1405, auc=round(M["auc_test"], 3),
            pnl=dict(rev=pnl.revenue.round(0).tolist(), cof=pnl.cost_of_funds.round(0).tolist(), opex=pnl.opex.round(0).tolist(), ni=pnl.net_income.round(0).tolist()),
            pf=dict(bal=pf.gross_receivable.round(0).tolist()), cube=cube.values.astype(int).tolist())
html = (R / "src/dashboard_template.html").read_text().replace("__DATA__", json.dumps(data, separators=(",", ":")))
(R / "outputs/Financial_Risk_Dashboard.html").write_text(html)
print("dashboard bytes:", len(html))
