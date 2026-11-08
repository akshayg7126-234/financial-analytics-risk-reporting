"""Generate a synthetic loan tape + finance ledger (reproducible, seed=42).

Why synthetic: the brief allows 'synthetic company ledgers' as a data option.
The loan tape mimics Lending Club fields so a real Kaggle file can be swapped in
(see docs/DATA.md). The finance ledger is DERIVED from the loan tape so that
interest income, charge-offs and receivables reconcile to the loans.
"""
import numpy as np, pandas as pd
from pathlib import Path

rng = np.random.default_rng(42)
OUT = Path(__file__).resolve().parent.parent / "data"
START, END = pd.Period("2024-01", "M"), pd.Period("2026-10", "M")   # loan issue window
FIN_START = pd.Period("2025-01", "M")                              # reporting window start
months = pd.period_range(START, END, freq="M")

# ---------- loan tape ----------
rows = []
for i, m in enumerate(months):
    n = int(rng.normal(600 * (1 + 0.012 * i), 25))
    rows.append(pd.DataFrame({"issue_month": [m] * n}))
loans = pd.concat(rows, ignore_index=True)
N = len(loans)
loans.insert(0, "loan_id", np.arange(100000, 100000 + N))

loans["annual_inc"] = np.round(rng.lognormal(11.05, 0.45, N), -2).clip(18000, 400000)
loans["fico"] = np.clip(rng.normal(690, 45, N), 580, 830).round().astype(int)
loans["dti"] = np.clip(rng.normal(18, 8, N), 0, 45).round(1)
loans["revol_util"] = np.clip(rng.normal(48, 24, N), 0, 100).round(1)
loans["delinq_2yrs"] = rng.poisson(0.25, N).clip(0, 6)
loans["inq_last_6m"] = rng.poisson(0.8, N).clip(0, 8)
loans["emp_length"] = rng.choice([0, 1, 2, 3, 5, 8, 10], N, p=[.1, .1, .1, .12, .18, .15, .25])
loans["home_ownership"] = rng.choice(["RENT", "MORTGAGE", "OWN"], N, p=[.45, .42, .13])
loans["purpose"] = rng.choice(["debt_consolidation", "credit_card", "home_improvement", "major_purchase",
                               "small_business", "medical", "other"], N, p=[.42, .22, .09, .07, .06, .05, .09])
loans["term"] = rng.choice([36, 60], N, p=[.72, .28])
loans["loan_amnt"] = (np.clip(rng.lognormal(9.4, 0.55, N), 1000, 40000) / 250).round() * 250

# latent default risk (the 'true' data-generating process; the scorecard must rediscover it)
z = (-2.95
     - 0.017 * (loans.fico - 690)
     + 0.035 * (loans.dti - 18)
     + 0.010 * (loans.revol_util - 48)
     + 0.35 * loans.delinq_2yrs
     + 0.12 * loans.inq_last_6m
     - 0.0000045 * (loans.annual_inc - 70000)
     + 0.30 * (loans.term == 60)
     + 0.45 * (loans.purpose == "small_business")
     + 0.20 * (loans.purpose == "medical")
     + 0.12 * (loans.home_ownership == "RENT")
     - 0.03 * loans.emp_length
     + rng.normal(0, 0.35, N))
p_def = 1 / (1 + np.exp(-z))
loans["default_flag"] = (rng.random(N) < p_def).astype(int)

# grade + rate assigned by a lender-style rule (noisy proxy of risk, NOT the model output)
score = -(loans.fico - 690) / 45 + (loans.dti - 18) / 8 + rng.normal(0, 0.6, N)
loans["grade"] = pd.cut(score, [-99, -1.4, -0.7, -0.1, 0.5, 1.1, 1.8, 99], labels=list("ABCDEFG")).astype(str)
base = {"A": 7.5, "B": 10.0, "C": 12.8, "D": 15.9, "E": 19.0, "F": 22.5, "G": 25.5}
loans["int_rate"] = (loans.grade.map(base) + rng.normal(0, 0.5, N)).round(2)

# default timing (months on book) for defaulted loans
loans["default_age"] = np.where(loans.default_flag == 1,
                                np.minimum(rng.integers(4, 26, N), loans.term - 1), 0)

# ---------- monthly portfolio roll-forward ----------
mi = loans.issue_month.map(lambda p: p.ordinal).values
def balance_at(period):
    age = period.ordinal - mi
    live = (age >= 0)
    bal = loans.loan_amnt.values * np.clip(1 - age / loans.term.values, 0, 1)
    charged = (loans.default_flag.values == 1) & (age >= loans.default_age.values)
    bal = np.where(live & ~charged, bal, 0.0)
    return bal, charged & live, age

fin_months = pd.period_range(FIN_START, END, freq="M")
pf = []
for m in fin_months:
    bal, _, age = balance_at(m)
    prev_bal, _, _ = balance_at(m - 1)
    new = (age == 0)
    co_mask = (loans.default_flag.values == 1) & (age == loans.default_age.values) & (age > 0)
    interest = float((bal * loans.int_rate.values / 100 / 12).sum())
    pf.append(dict(period=str(m), originations=float(loans.loan_amnt.values[new].sum()),
                   new_loans=int(new.sum()), gross_receivable=float(bal.sum()),
                   interest_income=interest, charge_offs=float(prev_bal[co_mask].sum())))
pf = pd.DataFrame(pf)
pf["avg_receivable"] = (pf.gross_receivable + pf.gross_receivable.shift(1).fillna(pf.gross_receivable)) / 2
pf["yield_annual"] = pf.interest_income * 12 / pf.avg_receivable

# ---------- finance ledger (actual vs budget) ----------
t = np.arange(len(pf))
fee = pf.originations * 0.035                                   # origination fee 3.5%
funding_debt = pf.gross_receivable * 0.80
interest_exp = funding_debt * 0.068 / 12
allow = pf.gross_receivable * 0.045
provision = pf.charge_offs + allow.diff().fillna(0)
salaries = 310000 * (1 + 0.006 * t) * rng.normal(1, 0.01, len(pf))
marketing = pf.originations * 0.028 * rng.normal(1, 0.06, len(pf))
tech = 95000 * (1 + 0.004 * t) * rng.normal(1, 0.03, len(pf))
rent = np.full(len(pf), 42000.0)
prof = 38000 * rng.normal(1, 0.15, len(pf))
dep = 18000 + 120 * t

actual = pd.DataFrame({
    "Interest income": pf.interest_income, "Fee income": fee,
    "Interest expense": interest_exp, "Credit loss provision": provision,
    "Salaries": salaries, "Marketing": marketing, "Technology": tech,
    "Rent": rent, "Professional fees": prof, "Depreciation": dep})
# --- budget: built from PLANNED volume and PLANNED yield (so variance has real drivers) ---
b_orig = 600 * 15500 * (1 + 0.010 * t)                         # planned originations $
b_bal = pf.gross_receivable * (1 + 0.03 * np.sin(t / 3) - 0.015)  # planned avg receivable
b_yield = 0.1405
budget = pd.DataFrame({
    "Interest income": b_bal * b_yield / 12,
    "Fee income": b_orig * 0.035,
    "Interest expense": b_bal * 0.80 * 0.066 / 12,
    "Credit loss provision": b_bal * 0.0042,                    # planned ~0.42%/month loss charge
    "Salaries": 310000 * (1 + 0.005 * t),
    "Marketing": b_orig * 0.030,
    "Technology": 95000 * (1 + 0.003 * t),
    "Rent": np.full(len(pf), 42000.0),
    "Professional fees": np.full(len(pf), 38000.0),
    "Depreciation": 18000 + 100 * t})
cat = {"Interest income": "Revenue", "Fee income": "Revenue", "Interest expense": "Cost of funds",
       "Credit loss provision": "Credit costs", "Salaries": "Operating expense", "Marketing": "Operating expense",
       "Technology": "Operating expense", "Rent": "Operating expense", "Professional fees": "Operating expense",
       "Depreciation": "Operating expense"}
gl = []
for k, name in enumerate(actual.columns):
    for j, per in enumerate(pf.period):
        gl.append((per, name, cat[name], round(float(actual[name][j]), 2), round(float(budget[name][j]), 2)))
gl = pd.DataFrame(gl, columns=["period", "account", "category", "actual", "budget"])

# ---------- balance sheet (cash is the balancing item: documented simplification) ----------
bs_rows = []
share_cap, re0 = 40_000_000.0, 0.0
ni_cum = 0.0
for j, per in enumerate(pf.period):
    g = gl[gl.period == per]
    rev = g[g.category == "Revenue"].actual.sum()
    exp = g[g.category != "Revenue"].actual.sum()
    pre = rev - exp
    ni = pre * (1 - 0.25)
    ni_cum += ni
    gross = pf.gross_receivable[j]; al = allow[j]
    debt = funding_debt[j]; ap = 0.9 * (marketing[j] + prof[j] + tech[j]); accr = 0.5 * salaries[j]
    fa = 1_000_000 - dep[:j + 1].sum()        # opening net fixed assets $1.0M less cumulative depreciation
    equity = share_cap + re0 + ni_cum
    liab = debt + ap + accr
    noncash = gross - al + fa
    cash = liab + equity - noncash
    for line, grp, amt in [("Cash", "Assets", cash), ("Loans receivable (gross)", "Assets", gross),
                           ("Allowance for credit losses", "Assets", -al), ("Fixed assets (net)", "Assets", fa),
                           ("Borrowings", "Liabilities", debt), ("Accounts payable", "Liabilities", ap),
                           ("Accrued expenses", "Liabilities", accr),
                           ("Share capital", "Equity", share_cap), ("Retained earnings", "Equity", re0 + ni_cum)]:
        bs_rows.append((per, grp, line, round(float(amt), 2)))
bs = pd.DataFrame(bs_rows, columns=["period", "grp", "line", "amount"])

loans["issue_month"] = loans.issue_month.astype(str)
loans.to_csv(OUT / "loans.csv", index=False)
gl.to_csv(OUT / "gl_monthly.csv", index=False)
bs.to_csv(OUT / "balance_sheet.csv", index=False)
pf.round(4).to_csv(OUT / "portfolio_monthly.csv", index=False)
print(f"loans={N:,}  default_rate={loans.default_flag.mean():.2%}  periods={len(pf)}")
print("min cash:", bs[bs.line == 'Cash'].amount.min().round(0))
