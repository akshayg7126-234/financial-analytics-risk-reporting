"""Monthly board pack (PDF). Run: python src/build_pdf.py [YYYY-MM]  (default = latest month).
This is the file the monthly automation (automation/refresh_and_email.py) regenerates and emails."""
import sys, json, sqlite3, io, pandas as pd, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt
from pathlib import Path
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak, KeepTogether

R = Path(__file__).resolve().parent.parent
def money(v): a = abs(v); s = "-" if v < 0 else ""; return f"{s}${a/1e6:.2f}M" if a >= 1e6 else f"{s}${a/1e3:,.0f}K"
def build(month=None, out=None):
    con = sqlite3.connect(R / "data/finance.db")
    pnl = pd.read_sql("select * from v_pnl order by period", con).set_index("period")
    month = month or pnl.index[-1]; i = list(pnl.index).index(month); prev = pnl.index[i - 1] if i else None
    gl = pd.read_sql(f"select * from v_budget_variance where period='{month}'", con)
    ytd = pd.read_sql(f"select account,category,sum(actual) a,sum(budget) b from gl_monthly where period>='{month[:4]}-01' and period<='{month}' group by 1,2", con)
    bs = pd.read_sql(f"select * from v_balance_sheet where period='{month}'", con).iloc[0]
    pvm = pd.read_sql(f"select * from v_interest_pvm where period='{month}'", con).iloc[0]
    bands = pd.read_csv(R / "outputs/risk_bands.csv").sort_values("avg_score", ascending=False)
    M = json.load(open(R / "outputs/model_metrics.json"))
    pn = pd.read_sql("select * from v_pnl_trend order by period", con).set_index("period")
    r = pnl.loc[month]; bl, ac = "#2a78d6", "#eb6834"
    # charts
    def png(fig):
        b = io.BytesIO(); fig.savefig(b, format="png", dpi=170, bbox_inches="tight"); plt.close(fig); b.seek(0); return b
    fig, ax = plt.subplots(figsize=(7.2, 2.6)); h = pnl.iloc[:i + 1]
    ax.plot(h.index, h.revenue / 1e6, color=bl, lw=2, label="Revenue"); ax.plot(h.index, (h.revenue - h.pre_tax_profit) / 1e6, color=ac, lw=2, label="Total costs")
    ax.set_ylabel("USD millions"); ax.set_xticks(range(0, len(h), 3)); ax.set_xticklabels(h.index[::3], fontsize=8); ax.legend(frameon=False, fontsize=8)
    for s_ in ("top", "right"): ax.spines[s_].set_visible(False)
    c1 = png(fig)
    fig, ax = plt.subplots(figsize=(7.2, 2.4)); ni = h.net_income / 1e3
    ax.bar(h.index, ni, color=[bl if x >= 0 else ac for x in ni]); ax.axhline(0, color="#666", lw=.8)
    ax.set_ylabel("USD thousands"); ax.set_xticks(range(0, len(h), 3)); ax.set_xticklabels(h.index[::3], fontsize=8)
    for s_ in ("top", "right"): ax.spines[s_].set_visible(False)
    c2 = png(fig)
    fig, ax = plt.subplots(figsize=(7.2, 2.4)); lab = [b.split(" - ")[0] for b in bands.risk_band]
    ax.bar(lab, bands.actual_default_rate * 100, color=ac)
    for k, v in enumerate(bands.actual_default_rate * 100): ax.text(k, v + .3, f"{v:.1f}%", ha="center", fontsize=8)
    ax.set_ylabel("Default rate %"); ax.set_xlabel("Risk band (A = lowest risk)")
    for s_ in ("top", "right"): ax.spines[s_].set_visible(False)
    c3 = png(fig)

    st = getSampleStyleSheet(); H1 = ParagraphStyle("h1", parent=st["Title"], fontSize=20, textColor=colors.HexColor("#1F3864"), alignment=0)
    H2 = ParagraphStyle("h2", parent=st["Heading2"], textColor=colors.HexColor("#1F3864"), spaceBefore=8); B = ParagraphStyle("b", parent=st["Normal"], fontSize=9.5, leading=13)
    S = ParagraphStyle("s", parent=B, fontSize=8, textColor=colors.HexColor("#666666"))
    def tbl(data, widths, align_right=True, total_last=False):
        t = Table(data, colWidths=widths, repeatRows=1)
        sty = [("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F3864")), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white), ("FONTSIZE", (0, 0), (-1, -1), 8.5),
               ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"), ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F2F4F8")]),
               ("LINEBELOW", (0, 0), (-1, -1), .25, colors.HexColor("#CCCCCC")), ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]
        if align_right: sty.append(("ALIGN", (1, 0), (-1, -1), "RIGHT"))
        if total_last: sty += [("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"), ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#E4E8F0"))]
        t.setStyle(TableStyle(sty)); return t
    y, mo = month.split("-"); title = pd.Timestamp(f"{month}-01").strftime("%B %Y")
    doc = SimpleDocTemplate(str(out or R / f"outputs/Board_Pack_{month}.pdf"), pagesize=A4, leftMargin=16*mm, rightMargin=16*mm, topMargin=14*mm, bottomMargin=14*mm,
                            title=f"Monthly Board Pack {title}", author="Finance Analytics")
    E = []
    E += [Paragraph(f"Monthly Board Pack - {title}", H1), Paragraph("Financial Analytics &amp; Risk Reporting System · synthetic lending company · USD", S), Spacer(1, 6)]
    cti = r.opex / (r.revenue - r.cost_of_funds)
    k = [["Revenue", "Net income", "Cost-to-income", "Gross loans", "Portfolio default rate"],
         [money(r.revenue), money(r.net_income), f"{cti:.1%}", money(bs.loans_gross), f"{(M['overall_default_rate']):.2%}"]]
    kt = Table(k, colWidths=[35*mm]*5); kt.setStyle(TableStyle([("FONTSIZE", (0, 0), (-1, 0), 8), ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#555555")),
        ("FONTSIZE", (0, 1), (-1, 1), 14), ("FONTNAME", (0, 1), (-1, 1), "Helvetica-Bold"), ("BOX", (0, 0), (-1, -1), .5, colors.HexColor("#BBBBBB")),
        ("INNERGRID", (0, 0), (-1, -1), .25, colors.HexColor("#DDDDDD")), ("ALIGN", (0, 0), (-1, -1), "CENTER"), ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F7F8FA"))])); E += [kt]
    d_rev = (r.revenue / pnl.loc[prev].revenue - 1) if prev else 0; d_ni = r.net_income - pnl.loc[prev].net_income if prev else 0
    ii = gl[gl.account == "Interest income"].iloc[0]; big = gl.reindex(gl.variance_fav.abs().sort_values(ascending=False).index).head(3)
    bt = "; ".join(f"{x.account} {'favourable' if x.variance_fav >= 0 else 'unfavourable'} {money(abs(x.variance_fav))} ({x.variance_pct:+.1f}%)" for x in big.itertuples())
    E += [Paragraph("Headlines", H2), Paragraph(
        f"• Revenue was <b>{money(r.revenue)}</b> ({d_rev:+.1%} vs prior month) and net income <b>{money(r.net_income)}</b> ({'up' if d_ni >= 0 else 'down'} {money(abs(d_ni))} vs prior month).<br/>"
        f"• Largest budget variances this month: {bt}.<br/>"
        f"• Interest income is {money(abs(ii.variance_fav))} {'above' if ii.variance_fav >= 0 else 'below'} budget: volume effect {money(pvm.volume_effect)}, rate effect {money(pvm.rate_effect)} "
        f"(the book yields more than the 14.05% planned yield).<br/>"
        f"• The credit scorecard ranks risk well (test AUC {M['auc_test']:.2f}, Gini {M['gini_test']:.2f}, KS {M['ks_test']:.2f}); default rate climbs from "
        f"{bands.actual_default_rate.min():.1%} in band A to {bands.actual_default_rate.max():.1%} in band E.", B)]
    E += [Paragraph("Revenue vs total costs", H2), Image(c1, width=170*mm, height=170*mm*0.36), Paragraph("Net income by month", H2), Image(c2, width=170*mm, height=170*mm*0.33), PageBreak()]
    # P&L table
    lines = [("Interest income", None), ("Fee income", None), ("Total revenue", "revenue"), ("Interest expense", "cost_of_funds"), ("Net interest revenue", "net_interest_revenue"),
             ("Credit loss provision", "credit_costs"), ("Operating expenses", "opex"), ("Pre-tax profit", "pre_tax_profit"), ("Tax (25%)", "tax"), ("Net income", "net_income")]
    cur = pd.read_sql(f"select account,sum(case when period='{month}' then actual end) m, sum(actual) y from gl_monthly where period>='{y}-01' and period<='{month}' group by 1", con).set_index("account")
    ytdp = pnl.loc[f"{y}-01":month].sum()
    rows = [["USD", title, f"YTD {y}"]]
    for nme, key in lines:
        if key is None: rows.append([nme, f"{cur.loc[nme,'m']:,.0f}", f"{cur.loc[nme,'y']:,.0f}"])
        else: rows.append([nme, f"{r[key]:,.0f}", f"{ytdp[key]:,.0f}"])
    E += [Paragraph("Profit &amp; loss", H2), tbl(rows, [90*mm, 40*mm, 40*mm], total_last=True)]
    # BvA
    bv = [["Account", "Actual", "Budget", "Variance (fav +)", "Var %"]]
    for x in gl.itertuples(): bv.append([x.account, f"{x.actual:,.0f}", f"{x.budget:,.0f}", f"{x.variance_fav:,.0f}", f"{x.variance_pct:+.1f}%"])
    E += [Paragraph(f"Budget vs actual - {title}", H2), tbl(bv, [55*mm, 30*mm, 30*mm, 35*mm, 20*mm]),
          Paragraph("Variance is favourable (+) when revenue beats budget or a cost comes in under budget.", S)]
    # balance sheet
    bsr = [["Balance sheet", "USD"], ["Cash", f"{bs.cash:,.0f}"], ["Loans receivable (gross)", f"{bs.loans_gross:,.0f}"], ["Allowance for credit losses", f"{bs.allowance:,.0f}"],
           ["Fixed assets (net)", f"{bs.fixed_assets:,.0f}"], ["Total assets", f"{bs.total_assets:,.0f}"], ["Total liabilities", f"{bs.total_liabilities:,.0f}"], ["Total equity", f"{bs.total_equity:,.0f}"]]
    E += [Paragraph("Balance sheet summary", H2), tbl(bsr, [90*mm, 50*mm], total_last=False), Paragraph(f"Balance check (assets - liabilities - equity): {bs.balance_check:,.2f}", S), PageBreak()]
    # credit
    E += [Paragraph("Credit risk", H2), Image(c3, width=170*mm, height=170*mm*0.33)]
    cb = [["Risk band", "Loans", "Exposure", "Avg score", "Default rate", "Avg rate"]]
    for x in bands.itertuples(): cb.append([x.risk_band, f"{x.loans:,}", money(x.exposure), f"{x.avg_score:.0f}", f"{x.actual_default_rate:.1%}", f"{x.avg_rate:.1f}%"])
    E += [tbl(cb, [48*mm, 22*mm, 28*mm, 24*mm, 26*mm, 22*mm]), Spacer(1, 6),
          Paragraph(f"<b>Model quality (30% hold-out test set, {M['n_test']:,} loans):</b> AUC {M['auc_test']:.3f} (train {M['auc_train']:.3f}), Gini {M['gini_test']:.3f}, KS {M['ks_test']:.3f}. "
                    f"Predicted default rate {M['calibration_test']['mean_predicted']:.2%} vs actual {M['calibration_test']['mean_actual']:.2%}. "
                    f"Features used: {', '.join(M['features_kept'])}.", B),
          Paragraph("Definitions of every metric are in docs/METRICS.md and the Definitions sheet of the Excel workbook. Data is synthetic.", S)]
    doc.build(E); return doc.filename
if __name__ == "__main__": print(build(sys.argv[1] if len(sys.argv) > 1 else None))
