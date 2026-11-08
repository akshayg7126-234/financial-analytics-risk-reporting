-- P&L: one row per month, signed so that Net income = SUM of the lines.
-- Tax is 25% of pre-tax profit (assumption, see docs/METRICS.md).
CREATE VIEW v_pnl AS
WITH m AS (
  SELECT period,
    SUM(CASE WHEN category='Revenue' THEN actual END)            AS revenue,
    SUM(CASE WHEN category='Cost of funds' THEN actual END)      AS cost_of_funds,
    SUM(CASE WHEN category='Credit costs' THEN actual END)       AS credit_costs,
    SUM(CASE WHEN category='Operating expense' THEN actual END)  AS opex,
    SUM(CASE WHEN category='Revenue' THEN budget END)            AS revenue_b,
    SUM(CASE WHEN category<>'Revenue' THEN budget END)           AS cost_b
  FROM gl_monthly GROUP BY period)
SELECT period, revenue, cost_of_funds, credit_costs, opex,
       revenue - cost_of_funds                                   AS net_interest_revenue,
       revenue - cost_of_funds - credit_costs - opex             AS pre_tax_profit,
       0.25 * (revenue - cost_of_funds - credit_costs - opex)    AS tax,
       0.75 * (revenue - cost_of_funds - credit_costs - opex)    AS net_income,
       revenue_b - cost_b                                        AS pre_tax_profit_budget
FROM m;

-- Balance sheet pivoted wide; check column must be 0.
CREATE VIEW v_balance_sheet AS
SELECT period,
  SUM(CASE WHEN line='Cash' THEN amount END)                         AS cash,
  SUM(CASE WHEN line='Loans receivable (gross)' THEN amount END)     AS loans_gross,
  SUM(CASE WHEN line='Allowance for credit losses' THEN amount END)  AS allowance,
  SUM(CASE WHEN line='Fixed assets (net)' THEN amount END)           AS fixed_assets,
  SUM(CASE WHEN grp='Assets' THEN amount END)                        AS total_assets,
  SUM(CASE WHEN grp='Liabilities' THEN amount END)                   AS total_liabilities,
  SUM(CASE WHEN grp='Equity' THEN amount END)                        AS total_equity,
  ROUND(SUM(CASE WHEN grp='Assets' THEN amount END)
      - SUM(CASE WHEN grp<>'Assets' THEN amount END), 2)             AS balance_check
FROM balance_sheet GROUP BY period;

-- Budget vs actual per account with variance sign convention:
-- favourable = positive (revenue above budget, or cost below budget).
CREATE VIEW v_budget_variance AS
SELECT period, account, category, actual, budget,
  CASE WHEN category='Revenue' THEN actual-budget ELSE budget-actual END            AS variance_fav,
  ROUND(100.0*(CASE WHEN category='Revenue' THEN actual-budget ELSE budget-actual END)/NULLIF(budget,0),2) AS variance_pct
FROM gl_monthly;

-- Interest-income variance split into VOLUME and RATE effects (sums exactly to total).
--   volume = (actual avg balance - budget avg balance) x budget yield / 12
--   rate   = (actual yield - budget yield) x actual avg balance / 12
-- Budget balance is backed out from budget interest income and the planned yield (14.05%).
CREATE VIEW v_interest_pvm AS
SELECT p.period,
  g.actual AS actual_income, g.budget AS budget_income,
  p.gross_receivable AS actual_balance,
  g.budget*12/0.1405 AS budget_balance,
  (p.gross_receivable - g.budget*12/0.1405) * 0.1405/12 AS volume_effect,
  (g.actual*12/p.gross_receivable - 0.1405) * p.gross_receivable/12 AS rate_effect
FROM portfolio_monthly p JOIN gl_monthly g ON g.period=p.period AND g.account='Interest income';

-- Credit quality by grade (bad rate = share of loans that defaulted).
CREATE VIEW v_grade_performance AS
SELECT grade, COUNT(*) AS loans, ROUND(SUM(loan_amnt)) AS originated,
  ROUND(AVG(int_rate),2) AS avg_rate, ROUND(100.0*AVG(default_flag),2) AS default_rate_pct
FROM loans GROUP BY grade ORDER BY grade;

-- Window-function example: rolling 3-month net income + month-on-month change
CREATE VIEW v_pnl_trend AS
SELECT period, net_income,
  AVG(net_income) OVER (ORDER BY period ROWS BETWEEN 2 PRECEDING AND CURRENT ROW) AS ni_3m_avg,
  net_income - LAG(net_income) OVER (ORDER BY period) AS ni_mom_change
FROM v_pnl;
