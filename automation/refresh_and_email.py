"""Monthly refresh + email of the board pack (stand-in for the Power Automate flow).

  python automation/refresh_and_email.py                 # DRY RUN: rebuilds and writes outputs/email_preview.eml
  python automation/refresh_and_email.py --send          # really sends (set SMTP_HOST, SMTP_USER, SMTP_PASS, MAIL_TO, MAIL_FROM)
"""
import os, sys, smtplib, subprocess
from email.message import EmailMessage
from pathlib import Path
R = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(R / "src"))

def main(send=False):
    for s in ["generate_data", "build_db", "credit_scorecard", "build_excel", "build_dashboard"]:
        subprocess.run([sys.executable, str(R / "src" / f"{s}.py")], check=True, stdout=subprocess.DEVNULL)
    import build_pdf
    pdf = Path(build_pdf.build())
    msg = EmailMessage()
    msg["Subject"] = f"Monthly board pack - {pdf.stem.split('_')[-1]}"
    msg["From"] = os.getenv("MAIL_FROM", "finance-reports@example.com"); msg["To"] = os.getenv("MAIL_TO", "board@example.com")
    msg.set_content("Hello,\n\nPlease find attached this month's board pack (P&L, budget vs actual, balance sheet, credit risk).\n"
                    "Metric definitions are in the Excel workbook's Definitions sheet.\n\nRegards,\nFinance Analytics (automated)")
    msg.add_attachment(pdf.read_bytes(), maintype="application", subtype="pdf", filename=pdf.name)
    if send:
        with smtplib.SMTP(os.environ["SMTP_HOST"], int(os.getenv("SMTP_PORT", 587))) as s:
            s.starttls(); s.login(os.environ["SMTP_USER"], os.environ["SMTP_PASS"]); s.send_message(msg)
        print("sent to", msg["To"])
    else:
        (R / "outputs/email_preview.eml").write_bytes(bytes(msg)); print("dry run: wrote outputs/email_preview.eml with", pdf.name, "attached")
if __name__ == "__main__": main("--send" in sys.argv)
