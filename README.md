# Financial Analytics & Risk Reporting System

Automated finance reports (P&L, budget vs actual, balance sheet), a credit-risk scorecard, an interactive dashboard and a monthly board pack, built end to end on a synthetic lending company.

## What is in the box

| Output | File | What it is |
|---|---|---|
| Excel workbook | `outputs/Financial_Analytics_Workbook.xlsx` | P&L, balance sheet, budget vs actual (pick a month), credit risk, scorecard, metric definitions. 922 live formulas over 4 Excel Tables (PivotTable / Power Pivot ready) |
| Interactive dashboard | `outputs/Financial_Risk_Dashboard.html` | Single offline file. Filters (month, grade, purpose), tooltips, table views, light/dark. Stand-in for Qlik Sense |
| Board pack | `outputs/Board_Pack_2026-10.pdf` | 3-page monthly PDF |
| Credit scorecard | `src/credit_scorecard.py`, `outputs/scorecard_points.csv` | WoE + logistic regression, points, 5 risk bands |
| SQL | `sql/` | Schema + views for P&L, balance sheet, variance, volume/rate split, window functions |
| Automation | `automation/` | `refresh_and_email.py` (tested dry-run) + Power Automate recipe |
| Qlik | `qlik/load_script.qvs` | Load script + measures to rebuild the dashboard in Qlik Sense (untested) |
| Docs | `docs/` | Architecture, data, metrics, test results, presentation script, reflection template |

## Run it

```bash
pip install -r requirements.txt
python run_all.py            # rebuilds data, DB, model, Excel, dashboard, PDF, diagram
python -m pytest tests -q    # 13 tests
python automation/refresh_and_email.py   # dry run; --send with SMTP_* env vars to really email
```
Open `outputs/Financial_Risk_Dashboard.html` in any browser. After `run_all.py`, open the Excel file once so formulas calculate.

## Headline results (synthetic data)

- 24,447 loans, 8.6% default rate, $341M originated; gross loans $203M at Oct 2026.
- Oct 2026: revenue $2.99M, net income $339K, cost-to-income 43.6%. FY2025 net income $254K (four loss months), YTD 2026 $2.36M.
- Interest income is $212K (8.9%) above budget in Oct 2026: volume -$11K, **rate +$223K** (yield 15.4% vs 14.05% planned).
- Scorecard (30% hold-out): AUC 0.710, Gini 0.420, KS 0.313, predicted default rate 8.60% vs actual 8.60%. Default rate rises from 2.3% (band A) to 19.3% (band E).

## Honest limitations

- **Data is synthetic.** The loan tape imitates Lending Club fields; the model rediscovers the rules used to generate it, so real-data results would differ (see `docs/DATA.md` for swapping in Kaggle data).
- **Cash is the balancing item** on the balance sheet, so the balance check proves arithmetic, not an independent cash ledger.
- **Qlik Sense, Power Pivot and Power Automate were not available here.** Equivalents are provided; recreate them in the real tools (steps in `docs/RECREATE_IN_REQUIRED_TOOLS.md`).
- Scorecard is fit on one random split, not out-of-time, and ignores reject inference.
