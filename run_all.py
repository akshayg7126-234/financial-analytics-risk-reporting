"""One command rebuilds everything: python run_all.py"""
import subprocess, sys
steps = ["src/generate_data.py", "src/build_db.py", "src/credit_scorecard.py", "src/build_excel.py",
         "src/build_dashboard.py", "src/build_pdf.py", "src/make_architecture.py"]
for s in steps:
    print(f"\n=== {s}"); subprocess.run([sys.executable, s], check=True)
print("\nDone. Outputs in /outputs. Open the Excel file once in Excel so formulas calculate and cache.")
