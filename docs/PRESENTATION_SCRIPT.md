# 10-minute presentation script (matches the 10 slides in docs/Project_Presentation.pptx)

Speak in your own words; these are talking points. Know the "why" behind each number.

1. **Title (0:30)** - "I built an automated finance and credit-risk reporting system for a lending company, using synthetic data."
2. **Problem (1:00)** - Finance teams build P&L, budget variance and risk reports by hand, slowly, with inconsistent definitions. Goal: one pipeline that produces trustworthy reports every month.
3. **Architecture (1:00)** - Data -> SQL views -> credit model -> Excel / dashboard / PDF -> automated email. One command rebuilds it.
4. **Data (0:45)** - Synthetic loan tape (24k loans) and a ledger derived from it, so interest income and losses reconcile. Say it is synthetic and can be swapped for Lending Club.
5. **Finance reports (1:30)** - Show P&L and balance sheet in Excel. Net income $339K in Oct; four loss months in 2025 and improvement since. Open the Budget vs Actual sheet, change the month in B3.
6. **Variance drivers (1:15)** - Interest income $212K over budget: volume -$11K, rate +$223K, because yield was 15.4% vs 14.05% planned. "Rate, not volume" is the insight.
7. **Credit scorecard (1:30)** - WoE bins -> logistic regression -> points. FICO is the strongest predictor (IV 0.51). AUC 0.71, calibrated (8.60% predicted vs actual). Default rate 2.3% in band A to 19.3% in band E.
8. **Dashboard demo (1:00)** - Open the HTML, filter grade E and small business, click a month bar, show a tooltip.
9. **Testing & automation (0:45)** - 13 tests; Excel matches SQL to the dollar; monthly email flow (dry run; Power Automate recipe).
10. **Challenges, limits, next steps (0:45)** - Challenges: cash plug on balance sheet, loss months hidden by a chart bug I found and fixed, off-by-one row references caught by recalculation. Limits: synthetic data, random not out-of-time split. Next: real data, Qlik/Power Automate versions, out-of-time validation, monitoring PSI.

**Likely questions**: What is WoE/IV? Why is AUC 0.71 acceptable (application scorecards are typically 0.65-0.80)? Why exclude grade? (It is the lender's own output, would leak pricing.) What is PDO? How does variance sign work?
