# Metric definitions

Every number in the workbook, dashboard and board pack is defined here.

| Metric | Definition | Where used |
|---|---|---|
| Interest income | Interest earned in the month = sum over live loans of outstanding balance x annual rate / 12. Charged-off loans earn nothing. | P&L, dashboard |
| Fee income | Origination fee = 3.5% of loans originated in the month. | P&L |
| Total revenue | Interest income + fee income. | P&L |
| Interest expense | Funding cost = borrowings (80% of gross loans) x 6.8% / 12. | P&L |
| Net interest revenue | Total revenue - interest expense. | P&L |
| Credit loss provision | Charge-offs in the month + change in the allowance. Allowance = 4.5% of gross loans receivable. | P&L |
| Total operating expenses | Salaries + marketing + technology + rent + professional fees + depreciation. | P&L |
| Pre-tax profit | Net interest revenue - credit loss provision - operating expenses. | P&L |
| Net income | Pre-tax profit x (1 - tax rate). Tax rate is an input on the Assumptions sheet (25%). | P&L |
| Net margin | Net income / total revenue. | P&L |
| Cost-to-income ratio | Total operating expenses / (total revenue - interest expense). Lower is better. | P&L |
| Credit cost rate | Provision x 12 / gross loans receivable (annualised). | P&L |
| Gross loans receivable | Outstanding principal on loans that have not been charged off, straight-line amortised over the term. | Balance sheet |
| Allowance for credit losses | Reserve held against expected losses = 4.5% of gross loans; shown as a negative asset. | Balance sheet |
| Balance check | Total assets - (total liabilities + equity). Must be 0. Cash is the balancing item (synthetic simplification). | Balance sheet |
| Variance (favourable +) | Revenue lines: actual - budget. Cost lines: budget - actual. Positive always means better than budget. | Budget vs Actual |
| Variance % | Variance / budget. | Budget vs Actual |
| Volume effect | (Actual balance - budget balance) x budget yield / 12. Income gained or lost because the loan book was bigger/smaller than planned. | Budget vs Actual |
| Rate effect | (Actual yield - budget yield) x actual balance / 12. Income gained or lost because loans earned a higher/lower yield than planned. | Budget vs Actual |
| Default (bad) flag | 1 if the loan was charged off before maturity, else 0. 8.6% of the loan tape. | Scorecard |
| Default rate | Defaulted loans / total loans in the group. | Credit risk |
| WoE (weight of evidence) | ln(% of all good loans in the bin / % of all bad loans in the bin). Positive = safer than average. | Scorecard |
| IV (information value) | Sum over bins of (%good - %bad) x WoE. <0.02 useless, 0.02-0.1 weak, 0.1-0.3 medium, 0.3-0.5 strong, >0.5 very strong. | Scorecard |
| Credit score | Points sum. Base 600 at 30:1 odds; +20 points doubles the good:bad odds (PDO = 20). | Scorecard |
| Risk band | Score cut at the 20/40/60/80th percentiles of the training sample: A very low risk ... E very high risk. | Credit risk |
| AUC | Probability the model ranks a random bad loan riskier than a random good loan. 0.5 = coin flip. | Model quality |
| Gini | 2 x AUC - 1. | Model quality |
| KS statistic | Maximum gap between cumulative good and bad distributions across scores. Higher = better separation. | Model quality |
| Loss-adjusted spread | Average interest rate - default rate x LGD (60% assumed). A rough view of whether pricing pays for risk. | Credit risk |
