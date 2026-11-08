# Test results

Command: `python -m pytest tests -q` -> **13 passed**.

```
tests/test_all.py::test_loan_ids_unique_and_no_nulls PASSED              [  7%]
tests/test_all.py::test_balance_sheet_balances PASSED                    [ 15%]
tests/test_all.py::test_cash_never_negative PASSED                       [ 23%]
tests/test_all.py::test_pnl_identity PASSED                              [ 30%]
tests/test_all.py::test_interest_income_reconciles_to_loan_tape PASSED   [ 38%]
tests/test_all.py::test_volume_plus_rate_equals_variance PASSED          [ 46%]
tests/test_all.py::test_variance_sign_convention PASSED                  [ 53%]
tests/test_all.py::test_model_discriminates_and_not_overfit PASSED       [ 61%]
tests/test_all.py::test_model_is_calibrated PASSED                       [ 69%]
tests/test_all.py::test_risk_bands_monotonic PASSED                      [ 76%]
tests/test_all.py::test_no_leakage_features PASSED                       [ 84%]
tests/test_all.py::test_scorecard_scaling_doubles_odds_per_pdo PASSED    [ 92%]
tests/test_all.py::test_excel_matches_sql_and_has_no_errors PASSED       [100%]
============================== 13 passed in 1.96s ==============================
```

## Business-logic checks
| Check | Result |
|---|---|
| Balance sheet balances every month | max difference $0.02 (rounding) |
| Cash positive every month | min $11.2M |
| P&L identity (NI = 75% x (revenue - funding - provision - opex)) | exact |
| Interest income in ledger = loan-tape calculation | exact (to the cent) |
| Volume effect + rate effect = interest income variance | exact |
| Excel net income (YTD 2026 $2,360,882) = SQL | exact; 0 formula errors in 922 formulas |

## Model performance (30% hold-out, 7,335 loans)
| Metric | Value |
|---|---|
| AUC test / train | 0.710 / 0.718 (gap 0.008, no overfit) |
| Gini / KS | 0.420 / 0.313 |
| Predicted vs actual default rate | 8.60% vs 8.60% |
| Brier score | 0.0746 |
| Score scaling | +20 points doubles odds (verified by regression slope) |

## Default rate by risk band (all loans)
| Band | Loans | Default rate |
|---|---|---|
| A - very low risk | 4,743 | 2.3% |
| B - low | 4,696 | 4.5% |
| C - medium | 4,986 | 6.4% |
| D - high | 5,010 | 9.9% |
| E - very high | 5,012 | 19.3% |

## Not tested
Qlik Sense and Power Automate (not available here); real SMTP sending (dry run only); Excel PivotTables (not created by the script - add via Insert > PivotTable on the Data_* tables).
