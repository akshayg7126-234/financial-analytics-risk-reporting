# Recreating the pieces in the required tools (do this part yourself, ~half a day)

The brief lists Advanced Excel (Power Pivot), SQL, Python, Qlik Sense, Power Automate. SQL and Python are done here. For the rest:

**Power Pivot (Excel):** open the workbook > Data > *Manage Data Model* / Power Pivot > add `DataGL`, `DataPortfolio`, `DataLoans` tables > relate GL and Portfolio on period (use a Date table) > Insert PivotTable from the Data Model: rows = account, columns = month, values = actual & budget. Add DAX measures: `Revenue := CALCULATE(SUM(DataGL[actual]), DataGL[category]="Revenue")`, `Default rate := DIVIDE(SUM(DataLoans[default_flag]), COUNTROWS(DataLoans))`.

**Qlik Sense:** free trial on Qlik Cloud. Upload CSVs from `data/`, paste `qlik/load_script.qvs`, build 3 sheets (Overview, Budget vs Actual, Credit risk) mirroring the HTML dashboard. Compare numbers with the HTML to validate.

**Power Automate:** follow `automation/POWER_AUTOMATE_FLOW.md`; screenshot a successful run.

Say clearly in your presentation which parts you built in which tool; mentors prefer honesty plus a working version.
