"""Build the Excel workbook. Every report cell is a formula over the Data_* sheets,
so replacing the data (or changing an assumption) recalculates the whole workbook."""
import json, pandas as pd
from pathlib import Path
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter as L
from openpyxl.worksheet.table import Table, TableStyleInfo
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.comments import Comment

R = Path(__file__).resolve().parent.parent
gl = pd.read_csv(R / "data/gl_monthly.csv"); bs = pd.read_csv(R / "data/balance_sheet.csv")
pf = pd.read_csv(R / "data/portfolio_monthly.csv"); ln = pd.read_csv(R / "data/loans_scored.csv")
card = pd.read_csv(R / "outputs/scorecard_points.csv"); iv = pd.read_csv(R / "outputs/information_value.csv")
M = json.load(open(R / "outputs/model_metrics.json"))
for d, c in [(gl, "period"), (bs, "period"), (pf, "period"), (ln, "issue_month")]:
    d[c] = pd.to_datetime(d[c] + "-01")

F = "Arial"
f_norm, f_bold = Font(name=F, size=10), Font(name=F, size=10, bold=True)
f_in = Font(name=F, size=10, color="0000FF"); f_link = Font(name=F, size=10, color="008000")
f_title = Font(name=F, size=14, bold=True, color="1F3864"); f_hdr = Font(name=F, size=10, bold=True, color="FFFFFF")
fill_hdr = PatternFill("solid", fgColor="1F3864"); fill_sub = PatternFill("solid", fgColor="D9E1F2")
fill_in = PatternFill("solid", fgColor="FFFF00"); fill_tot = PatternFill("solid", fgColor="F2F2F2")
thin = Side(style="thin", color="999999"); top = Border(top=thin)
USD = '#,##0;(#,##0);"-"'; PCT = '0.0%;(0.0%);"-"'; DT = "mmm-yy"

wb = Workbook()
def put(ws, ref, v, font=f_norm, fmt=None, fill=None, bold=False, align=None):
    c = ws[ref]; c.value = v; c.font = Font(name=F, size=font.size, bold=bold or font.bold, color=font.color)
    if fmt: c.number_format = fmt
    if fill: c.fill = fill
    if align: c.alignment = align
    return c
def header(ws, row, labels, c0=1):
    for i, t in enumerate(labels):
        c = ws.cell(row=row, column=c0 + i, value=t); c.font = f_hdr; c.fill = fill_hdr
        c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

# ---------- Assumptions ----------
a = wb.active; a.title = "Assumptions"; a.sheet_view.showGridLines = False
put(a, "A1", "Financial Analytics & Risk Reporting - Assumptions", f_title)
put(a, "A2", "Blue text on yellow = input you can change. Everything else in the workbook is a formula.", f_norm)
rows = [("Tax rate on pre-tax profit", 0.25, PCT, "Assumption for the synthetic company."),
        ("Budgeted portfolio yield (annual)", 0.1405, '0.00%', "Planning assumption used in the budget; drives the volume/rate split."),
        ("Reporting currency", "USD", None, "All figures in US dollars."),
        ("Data source", "Synthetic loan tape (24,447 loans) + derived ledger", None, "See docs/DATA.md. Swap in Lending Club data to use real loans.")]
header(a, 4, ["Assumption", "Value", "Note"])
for i, (k, v, fm, n) in enumerate(rows):
    r = 5 + i; put(a, f"A{r}", k); put(a, f"B{r}", v, f_in, fm, fill_in); put(a, f"C{r}", n)
a["A11"] = "Sheet guide"; a["A11"].font = f_bold
guide = [("P&L", "Monthly income statement, FY2025 and YTD-2026 totals, key ratios"),
         ("Balance Sheet", "Monthly balance sheet with a balance check (must be 0)"),
         ("Budget vs Actual", "Pick a month in B3: month and YTD variance, volume/rate drivers of interest income"),
         ("Credit Risk", "Risk-band performance (COUNTIFS/SUMIFS over Data_Loans) and model quality metrics"),
         ("Scorecard", "Points per bin and Information Value per predictor"),
         ("Definitions", "Every metric defined"), ("Data_*", "Source tables (Excel Tables) - ready for PivotTable / Power Pivot")]
for i, (k, v) in enumerate(guide):
    put(a, f"A{12+i}", k, f_bold); put(a, f"B{12+i}", v)
a.column_dimensions["A"].width = 38; a.column_dimensions["B"].width = 44; a.column_dimensions["C"].width = 70
TAX, BYLD = "Assumptions!$B$5", "Assumptions!$B$6"

# ---------- Data sheets (as Excel Tables) ----------
def data_sheet(name, df, fmts):
    ws = wb.create_sheet(name)
    header(ws, 1, list(df.columns))
    for i, row in enumerate(df.itertuples(index=False), start=2):
        for j, v in enumerate(row, start=1):
            c = ws.cell(row=i, column=j, value=(v.to_pydatetime() if hasattr(v, "to_pydatetime") else v))
            c.font = f_norm
            if df.columns[j - 1] in fmts: c.number_format = fmts[df.columns[j - 1]]
    t = Table(displayName=name.replace("_", ""), ref=f"A1:{L(df.shape[1])}{len(df)+1}")
    t.tableStyleInfo = TableStyleInfo(name="TableStyleLight9", showRowStripes=True); ws.add_table(t)
    for j in range(1, df.shape[1] + 1): ws.column_dimensions[L(j)].width = 18
    ws.freeze_panes = "A2"; return ws
g = data_sheet("Data_GL", gl, {"period": DT, "actual": USD, "budget": USD}); NG = len(gl) + 1
b = data_sheet("Data_BS", bs, {"period": DT, "amount": USD}); NB = len(bs) + 1
p = data_sheet("Data_Portfolio", pf, {"period": DT, "originations": USD, "gross_receivable": USD, "interest_income": USD,
                                      "charge_offs": USD, "avg_receivable": USD, "yield_annual": "0.0%"}); NP = len(pf) + 1
lcols = ["loan_id", "issue_month", "loan_amnt", "grade", "int_rate", "fico", "dti", "score", "risk_band", "default_flag", "sample"]
l = data_sheet("Data_Loans", ln[lcols], {"issue_month": DT, "loan_amnt": USD}); NL = len(ln) + 1
GLr = lambda col: f"Data_GL!${col}$2:${col}${NG}"
BSr = lambda col: f"Data_BS!${col}$2:${col}${NB}"
PFr = lambda col: f"Data_Portfolio!${col}$2:${col}${NP}"
LNr = lambda col: f"Data_Loans!${col}$2:${col}${NL}"

periods = list(pf.period); nP = len(periods)               # 22 months, Jan-25..Oct-26
c0 = 2; cols = [L(c0 + i) for i in range(nP)]; cFY, cYTD = L(c0 + nP), L(c0 + nP + 1)
fy_first, fy_last = cols[0], cols[11]; ytd_first, ytd_last = cols[12], cols[-1]

# ---------- P&L ----------
w = wb.create_sheet("P&L", 1); w.sheet_view.showGridLines = False
put(w, "A1", "Profit & Loss (USD)", f_title); put(w, "A2", "Source: Data_GL via SUMIFS. FY2025 = Jan-Dec 2025; YTD 2026 = Jan-Oct 2026.")
header(w, 4, ["USD"] + [""] * nP + ["FY2025", "YTD 2026"])
for i, d in enumerate(periods):
    c = w[f"{cols[i]}4"]; c.value = d.to_pydatetime(); c.number_format = DT
lines = [("Interest income", "acc"), ("Fee income", "acc"), ("Total revenue", "sum:5:6"), ("Interest expense", "acc"),
         ("Net interest revenue", "f:{c}7-{c}8"), ("Credit loss provision", "acc"),
         ("Salaries", "acc"), ("Marketing", "acc"), ("Technology", "acc"), ("Rent", "acc"), ("Professional fees", "acc"),
         ("Depreciation", "acc"), ("Total operating expenses", "sum:11:16"),
         ("Pre-tax profit", "f:{c}9-{c}10-{c}17"), ("Tax", "f:" + TAX + "*{c}18"), ("Net income", "f:{c}18-{c}19")]
rowof = {}
for k, (name, kind) in enumerate(lines):
    r = 5 + k; rowof[name] = r; bold = not kind == "acc"
    put(w, f"A{r}", name, f_norm, bold=bold)
    for c in cols:
        if kind == "acc": v = f'=SUMIFS({GLr("D")},{GLr("A")},{c}$4,{GLr("B")},$A{r})'
        elif kind.startswith("sum"): _, s, e = kind.split(":"); v = f"=SUM({c}{s}:{c}{e})"
        else: v = "=" + kind[2:].format(c=c)
        put(w, f"{c}{r}", v, f_norm, USD, bold=bold)
    for cc, a_, z_ in [(cFY, fy_first, fy_last), (cYTD, ytd_first, ytd_last)]:
        if kind == "acc" or kind.startswith("sum") or kind.startswith("f:"):
            v = f"=SUM({a_}{r}:{z_}{r})"
        put(w, f"{cc}{r}", v, f_norm, USD, bold=bold)
    if bold:
        for c in ["A"] + cols + [cFY, cYTD]: w[f"{c}{r}"].fill = fill_tot; w[f"{c}{r}"].border = top
w["A5"].value = "Interest income"
# ratios
r0 = 23; put(w, f"A{r0-1}", "Key ratios", f_bold)
rat = [("Net margin (net income / revenue)", "={c}20/{c}7", PCT),
       ("Cost-to-income (opex / (revenue - interest expense))", "={c}17/{c}9", PCT),
       ("Credit cost rate (annualised provision / gross loans)", None, '0.00%'),
       ("Gross loans receivable (month-end)", None, USD)]
put(w, f"A{r0}", rat[0][0]); put(w, f"A{r0+1}", rat[1][0]); put(w, f"A{r0+2}", rat[2][0]); put(w, f"A{r0+3}", rat[3][0])
for c in cols:
    put(w, f"{c}{r0}", rat[0][1].format(c=c), f_norm, PCT); put(w, f"{c}{r0+1}", rat[1][1].format(c=c), f_norm, PCT)
    put(w, f"{c}{r0+3}", f'=SUMIFS({BSr("D")},{BSr("A")},{c}$4,{BSr("C")},"Loans receivable (gross)")', f_link, USD)
    put(w, f"{c}{r0+2}", f"=IFERROR({c}10*12/{c}{r0+3},0)", f_norm, '0.00%')
for cc in (cFY, cYTD):
    put(w, f"{cc}{r0}", f"=IFERROR({cc}20/{cc}7,0)", f_norm, PCT); put(w, f"{cc}{r0+1}", f"=IFERROR({cc}17/{cc}9,0)", f_norm, PCT)
w.column_dimensions["A"].width = 52
for c in cols + [cFY, cYTD]: w.column_dimensions[c].width = 13
w.freeze_panes = "B5"

# ---------- Balance sheet ----------
s = wb.create_sheet("Balance Sheet", 2); s.sheet_view.showGridLines = False
put(s, "A1", "Balance Sheet (USD)", f_title)
put(s, "A2", "Note: cash is the balancing item (synthetic data simplification), so the check proves the arithmetic, not an independent cash ledger.")
header(s, 4, ["USD"] + [""] * nP)
for i, d in enumerate(periods): s[f"{cols[i]}4"].value = d.to_pydatetime(); s[f"{cols[i]}4"].number_format = DT
bl = [("Cash", "Assets"), ("Loans receivable (gross)", "Assets"), ("Allowance for credit losses", "Assets"), ("Fixed assets (net)", "Assets"),
      ("Total assets", "T:5:8"), ("Borrowings", "Liabilities"), ("Accounts payable", "Liabilities"), ("Accrued expenses", "Liabilities"),
      ("Total liabilities", "T:10:12"), ("Share capital", "Equity"), ("Retained earnings", "Equity"), ("Total equity", "T:14:15"),
      ("Total liabilities + equity", "X"), ("Balance check (must be 0)", "C")]
for k, (name, kind) in enumerate(bl):
    r = 5 + k; tot = kind[0] in "TXC"; put(s, f"A{r}", name, f_norm, bold=tot)
    for c in cols:
        if kind[0] == "T": _, x, y = kind.split(":"); v = f"=SUM({c}{x}:{c}{y})"
        elif kind == "X": v = f"={c}13+{c}16"
        elif kind == "C": v = f"=ROUND({c}9-{c}17,0)"
        else: v = f'=SUMIFS({BSr("D")},{BSr("A")},{c}$4,{BSr("C")},$A{r})'
        put(s, f"{c}{r}", v, f_link if kind in ("Assets", "Liabilities", "Equity") else f_norm, USD, bold=tot)
        if tot: s[f"{c}{r}"].fill = fill_tot
    if tot: s[f"A{r}"].fill = fill_tot
s.column_dimensions["A"].width = 34
for c in cols: s.column_dimensions[c].width = 13
s.freeze_panes = "B5"

# ---------- Budget vs Actual ----------
v = wb.create_sheet("Budget vs Actual", 3); v.sheet_view.showGridLines = False
put(v, "A1", "Budget vs Actual", f_title)
put(v, "A3", "Select month  >>", f_bold); put(v, "B3", periods[-1].to_pydatetime(), f_in, DT, fill_in)
dv = DataValidation(type="list", formula1=f"='P&L'!${cols[0]}$4:${cols[-1]}$4", allow_blank=False); v.add_data_validation(dv); dv.add("B3")
put(v, "C3", "Sign convention: variance is FAVOURABLE (+) when revenue beats budget or cost is below budget.")
header(v, 5, ["Account", "Type", "Actual (month)", "Budget (month)", "Variance", "Var %", "Actual YTD", "Budget YTD", "Variance YTD", "Var % YTD"])
accts = [("Interest income", "Revenue"), ("Fee income", "Revenue"), ("Interest expense", "Cost"), ("Credit loss provision", "Cost"),
         ("Salaries", "Cost"), ("Marketing", "Cost"), ("Technology", "Cost"), ("Rent", "Cost"), ("Professional fees", "Cost"), ("Depreciation", "Cost")]
for k, (ac, ty) in enumerate(accts):
    r = 6 + k; put(v, f"A{r}", ac); put(v, f"B{r}", ty)
    put(v, f"C{r}", f'=SUMIFS({GLr("D")},{GLr("A")},$B$3,{GLr("B")},$A{r})', f_norm, USD)
    put(v, f"D{r}", f'=SUMIFS({GLr("E")},{GLr("A")},$B$3,{GLr("B")},$A{r})', f_norm, USD)
    put(v, f"G{r}", f'=SUMIFS({GLr("D")},{GLr("A")},">="&DATE(YEAR($B$3),1,1),{GLr("A")},"<="&$B$3,{GLr("B")},$A{r})', f_norm, USD)
    put(v, f"H{r}", f'=SUMIFS({GLr("E")},{GLr("A")},">="&DATE(YEAR($B$3),1,1),{GLr("A")},"<="&$B$3,{GLr("B")},$A{r})', f_norm, USD)
    for x, y, z, q in [("C", "D", "E", "F"), ("G", "H", "I", "J")]:
        put(v, f"{z}{r}", f'=IF($B{r}="Revenue",{x}{r}-{y}{r},{y}{r}-{x}{r})', f_norm, USD)
        put(v, f"{q}{r}", f"=IFERROR({z}{r}/{y}{r},0)", f_norm, PCT)
r = 16; put(v, f"A{r}", "Pre-tax profit", f_norm, bold=True)
for x in "CDGH": put(v, f"{x}{r}", f"=SUMIFS({x}6:{x}15,$B$6:$B$15,\"Revenue\")-SUMIFS({x}6:{x}15,$B$6:$B$15,\"Cost\")", f_norm, USD, bold=True)
for x, y, z, q in [("C", "D", "E", "F"), ("G", "H", "I", "J")]:
    put(v, f"{z}{r}", f"={x}{r}-{y}{r}", f_norm, USD, bold=True); put(v, f"{q}{r}", f"=IFERROR({z}{r}/ABS({y}{r}),0)", f_norm, PCT, bold=True)
for c in "ABCDEFGHIJ": v[f"{c}{r}"].fill = fill_tot
# PVM
put(v, "A19", "Why is interest income off budget?  Volume vs rate (month)", f_bold)
header(v, 20, ["Driver", "", "USD", "How it is calculated"])
pv = [("Actual average receivable", f'=SUMIFS({PFr("D")},{PFr("A")},$B$3)', USD, "Gross loans receivable at month-end (Data_Portfolio)"),
      ("Budget receivable (implied)", f"=D6*12/{BYLD}", USD, "Budget interest income x 12 / budgeted yield"),
      ("Actual yield (annual)", "=C6*12/C21", '0.00%', "Actual interest income x 12 / actual receivable"),
      ("Budget yield (annual)", f"={BYLD}", '0.00%', "Assumptions!B6"),
      ("Volume effect", f"=(C21-C22)*C24/12", USD, "(Actual balance - budget balance) x budget yield / 12"),
      ("Rate effect", f"=(C23-C24)*C21/12", USD, "(Actual yield - budget yield) x actual balance / 12"),
      ("Total interest income variance", "=C25+C26", USD, "Volume + rate"),
      ("Check vs table (must be 0)", "=ROUND(C27-E6,0)", USD, "Equals the variance in the table above")]
for k, (n, fm, nf, note) in enumerate(pv):
    r = 21 + k; put(v, f"A{r}", n, f_norm, bold=n.startswith("Total")); put(v, f"C{r}", fm, f_norm, nf, bold=n.startswith("Total")); put(v, f"D{r}", note)
v.column_dimensions["A"].width = 32; v.column_dimensions["B"].width = 10
for c in "CDEFGHIJ": v.column_dimensions[c].width = 16

# ---------- Credit Risk ----------
cr = wb.create_sheet("Credit Risk", 4); cr.sheet_view.showGridLines = False
put(cr, "A1", "Credit Risk - scorecard performance by risk band", f_title)
put(cr, "A2", "Live formulas over Data_Loans. Default rate = loans that defaulted / loans in band.")
header(cr, 4, ["Risk band", "Loans", "% of loans", "Exposure (USD)", "Avg score", "Default rate", "Avg interest rate", "Loss-adjusted spread"])
bands = ["A - Very low risk", "B - Low risk", "C - Medium risk", "D - High risk", "E - Very high risk"]
for k, bd in enumerate(bands):
    r = 5 + k; put(cr, f"A{r}", bd)
    put(cr, f"B{r}", f'=COUNTIFS({LNr("I")},$A{r})', f_norm, "#,##0")
    put(cr, f"C{r}", f"=B{r}/$B$10", f_norm, PCT)
    put(cr, f"D{r}", f'=SUMIFS({LNr("C")},{LNr("I")},$A{r})', f_norm, USD)
    put(cr, f"E{r}", f'=AVERAGEIFS({LNr("H")},{LNr("I")},$A{r})', f_norm, "0")
    put(cr, f"F{r}", f'=SUMIFS({LNr("J")},{LNr("I")},$A{r})/B{r}', f_norm, PCT)
    put(cr, f"G{r}", f'=AVERAGEIFS({LNr("E")},{LNr("I")},$A{r})/100', f_norm, PCT)
    put(cr, f"H{r}", f"=G{r}-F{r}*0.6", f_norm, PCT)
put(cr, "A10", "Total portfolio", f_norm, bold=True)
put(cr, "B10", "=SUM(B5:B9)", f_norm, "#,##0", bold=True); put(cr, "C10", "=SUM(C5:C9)", f_norm, PCT, bold=True)
put(cr, "D10", "=SUM(D5:D9)", f_norm, USD, bold=True); put(cr, "E10", f'=AVERAGE({LNr("H")})', f_norm, "0", bold=True)
put(cr, "F10", f'=SUM({LNr("J")})/B10', f_norm, PCT, bold=True); put(cr, "G10", f'=AVERAGE({LNr("E")})/100', f_norm, PCT, bold=True)
put(cr, "H10", "=G10-F10*0.6", f_norm, PCT, bold=True)
for c in "ABCDEFGH": cr[f"{c}10"].fill = fill_tot
put(cr, "A11", "Loss-adjusted spread = average rate - default rate x 60% loss-given-default (LGD 60% is an assumption).", f_norm)
put(cr, "A13", "Model quality (computed in Python on the 30% hold-out test set)", f_bold)
header(cr, 14, ["Metric", "Value", "Meaning"])
mm = [("AUC (test)", M["auc_test"], "0.5 = random, 1.0 = perfect. 0.70-0.80 is typical for application scorecards."),
      ("Gini (test)", M["gini_test"], "Equals 2 x AUC - 1"),
      ("KS statistic (test)", M["ks_test"], "Max separation between good and bad score distributions."),
      ("AUC (train)", M["auc_train"], "Close to test AUC => not overfit."),
      ("Predicted default rate (test)", M["calibration_test"]["mean_predicted"], "Mean model probability"),
      ("Actual default rate (test)", M["calibration_test"]["mean_actual"], "Observed - calibration check"),
      ("Brier score (test)", M["brier_test"], "Mean squared probability error; lower is better")]
for k, (n, val, meaning) in enumerate(mm):
    r = 15 + k; put(cr, f"A{r}", n); put(cr, f"B{r}", val, f_in, "0.000"); put(cr, f"C{r}", meaning)
cr.column_dimensions["A"].width = 36
for c in "BCDEFGH": cr.column_dimensions[c].width = 17

# ---------- Scorecard ----------
sc = wb.create_sheet("Scorecard", 5); sc.sheet_view.showGridLines = False
put(sc, "A1", "Scorecard points", f_title)
put(sc, "A2", f"Score = sum of points across features. Base {M['base_score']} points = {M['base_odds']}:1 good:bad odds; +{M['pdo']} points doubles the odds (PDO).")
header(sc, 4, ["Feature", "Bin", "Loans (train)", "Default rate", "WoE", "Points"])
for k, row in enumerate(card.itertuples(index=False)):
    r = 5 + k
    put(sc, f"A{r}", row.feature); put(sc, f"B{r}", str(row.bin)); put(sc, f"C{r}", int(row.n), f_norm, "#,##0")
    put(sc, f"D{r}", float(row.bad_rate), f_norm, PCT); put(sc, f"E{r}", float(row.woe), f_norm, "0.000"); put(sc, f"F{r}", int(row.points), f_in, "0")
r = 7 + len(card); put(sc, f"A{r}", "Information Value (predictive power) by feature", f_bold); header(sc, r + 1, ["Feature", "IV", "Strength", "Used in model?"])
for k, row in enumerate(iv.itertuples(index=False)):
    rr = r + 2 + k; put(sc, f"A{rr}", row.feature); put(sc, f"B{rr}", float(row.iv), f_norm, "0.000"); put(sc, f"C{rr}", str(row.strength))
    put(sc, f"D{rr}", "Yes" if row.feature in M["features_kept"] else "No (IV < 0.02)")
sc.column_dimensions["A"].width = 18; sc.column_dimensions["B"].width = 26
for c in "CDEF": sc.column_dimensions[c].width = 15

# ---------- Definitions ----------
d = wb.create_sheet("Definitions", 6); d.sheet_view.showGridLines = False
put(d, "A1", "Metric definitions", f_title); header(d, 3, ["Metric", "Definition / formula", "Where used"])
defs = json.load(open(R / "docs/metric_definitions.json"))
for k, (m_, df_, wh) in enumerate(defs):
    put(d, f"A{4+k}", m_, f_bold); put(d, f"B{4+k}", df_, f_norm, align=Alignment(wrap_text=True, vertical="top")); put(d, f"C{4+k}", wh)
d.column_dimensions["A"].width = 34; d.column_dimensions["B"].width = 95; d.column_dimensions["C"].width = 26

order = ["Assumptions", "P&L", "Balance Sheet", "Budget vs Actual", "Credit Risk", "Scorecard", "Definitions", "Data_GL", "Data_BS", "Data_Portfolio", "Data_Loans"]
wb._sheets = [wb[n] for n in order]
wb.save(R / "outputs/Financial_Analytics_Workbook.xlsx"); print("saved")
