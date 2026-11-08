"""Run: python -m pytest tests -q   (needs outputs built: python run_all.py)"""
import json, sqlite3, pandas as pd, numpy as np, pytest
from pathlib import Path
R = Path(__file__).resolve().parent.parent
con = sqlite3.connect(R / "data/finance.db"); M = json.load(open(R / "outputs/model_metrics.json"))
loans = pd.read_csv(R / "data/loans_scored.csv")

def test_loan_ids_unique_and_no_nulls():
    assert loans.loan_id.is_unique
    assert loans[["fico", "dti", "loan_amnt", "default_flag", "score"]].notna().all().all()

def test_balance_sheet_balances():
    assert con.execute("select max(abs(balance_check)) from v_balance_sheet").fetchone()[0] < 0.05

def test_cash_never_negative():
    assert con.execute("select min(cash) from v_balance_sheet").fetchone()[0] > 0

def test_pnl_identity():
    d = pd.read_sql("select * from v_pnl", con)
    assert np.allclose(d.net_income, 0.75 * (d.revenue - d.cost_of_funds - d.credit_costs - d.opex))
    assert np.allclose(d.pre_tax_profit, d.revenue - d.cost_of_funds - d.credit_costs - d.opex)

def test_interest_income_reconciles_to_loan_tape():
    pf = pd.read_sql("select period, interest_income from portfolio_monthly", con).set_index("period").interest_income
    gl = pd.read_sql("select period, actual from gl_monthly where account='Interest income'", con).set_index("period").actual
    assert np.allclose(pf, gl, atol=0.01)

def test_volume_plus_rate_equals_variance():
    d = pd.read_sql("select * from v_interest_pvm", con)
    assert np.allclose(d.volume_effect + d.rate_effect, d.actual_income - d.budget_income, atol=0.01)

def test_variance_sign_convention():
    d = pd.read_sql("select * from v_budget_variance", con)
    rev, cost = d[d.category == "Revenue"], d[d.category != "Revenue"]
    assert np.allclose(rev.variance_fav, rev.actual - rev.budget) and np.allclose(cost.variance_fav, cost.budget - cost.actual)

def test_model_discriminates_and_not_overfit():
    assert M["auc_test"] > 0.65 and M["gini_test"] > 0.3 and M["ks_test"] > 0.25
    assert abs(M["auc_train"] - M["auc_test"]) < 0.03

def test_model_is_calibrated():
    assert abs(M["calibration_test"]["mean_predicted"] - M["calibration_test"]["mean_actual"]) < 0.005

def test_risk_bands_monotonic():
    assert M["bands_monotonic_test"]
    b = pd.read_csv(R / "outputs/risk_bands.csv").sort_values("avg_score", ascending=False)
    assert b.actual_default_rate.is_monotonic_increasing

def test_no_leakage_features():
    assert not {"grade", "int_rate", "default_age", "default_flag"} & set(M["features_kept"])

def test_scorecard_scaling_doubles_odds_per_pdo():
    # +PDO points must double good:bad odds: check model-implied log-odds slope
    t = loans[loans["sample"] == "test"].copy(); t["logit_good"] = -np.log(t.pd_model / (1 - t.pd_model))
    slope = np.polyfit(t.score, t.logit_good, 1)[0]
    assert abs(slope * M["pdo"] - np.log(2)) < 0.05

def test_excel_matches_sql_and_has_no_errors():
    import openpyxl
    wb = openpyxl.load_workbook(R / "outputs/Financial_Analytics_Workbook.xlsx", data_only=True)
    if wb["P&L"]["Y20"].value is None:
        pytest.skip("workbook has no cached values yet - open it once in Excel (or LibreOffice) and save, then re-run")
    ni_sql = con.execute("select sum(net_income) from v_pnl where period like '2026%'").fetchone()[0]
    assert abs(wb["P&L"]["Y20"].value - ni_sql) < 1
    assert all(wb["Balance Sheet"].cell(row=18, column=c).value == 0 for c in range(2, 24))
    for ws in wb.worksheets:
        if ws.title.startswith("Data_"): continue
        for row in ws.iter_rows():
            for c in row: assert not (isinstance(c.value, str) and c.value.startswith("#")), f"{ws.title}!{c.coordinate}"
