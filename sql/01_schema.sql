-- Tables are loaded from /data/*.csv by src/build_db.py
CREATE TABLE loans (loan_id INTEGER PRIMARY KEY, issue_month TEXT, annual_inc REAL, fico INTEGER, dti REAL,
  revol_util REAL, delinq_2yrs INTEGER, inq_last_6m INTEGER, emp_length INTEGER, home_ownership TEXT,
  purpose TEXT, term INTEGER, loan_amnt REAL, default_flag INTEGER, grade TEXT, int_rate REAL, default_age INTEGER);
CREATE TABLE gl_monthly (period TEXT, account TEXT, category TEXT, actual REAL, budget REAL);
CREATE TABLE balance_sheet (period TEXT, grp TEXT, line TEXT, amount REAL);
CREATE TABLE portfolio_monthly (period TEXT, originations REAL, new_loans INTEGER, gross_receivable REAL,
  interest_income REAL, charge_offs REAL, avg_receivable REAL, yield_annual REAL);
