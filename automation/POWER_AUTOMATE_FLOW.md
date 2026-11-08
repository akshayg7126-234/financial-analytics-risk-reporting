# Power Automate flow: monthly board pack (build this in the real tool)

`refresh_and_email.py` does the same job in Python and is tested. The brief asks for **Power Automate**, so recreate it there:

**Trigger:** Recurrence - monthly, day 3, 08:00.

1. **Run script / refresh data.** Pick one:
   - *Excel Online (Business) > Run script* on the workbook stored in OneDrive/SharePoint (refresh Power Query / data connections), **or**
   - *HTTP* action calling the pipeline if you host `run_all.py` (Azure Function / GitHub Action).
2. **Delay** 2 minutes (let the refresh finish).
3. **Export the report to PDF:** *Power BI > Export to file* (if you rebuild the dashboard there), or *OneDrive > Convert file* (Excel report sheet -> PDF), or reuse the `Board_Pack_<month>.pdf` produced by the pipeline and read it with *OneDrive > Get file content*.
4. **Send an email (V2)** (Outlook): To = board distribution list; Subject = `Monthly board pack - @{formatDateTime(utcNow(),'MMMM yyyy')}`; Attachments = PDF from step 3.
5. **Configure run after / error handling:** add a parallel branch on *has failed* that emails you the error.

**Test:** use "Test > Manually", send to yourself first, screenshot the successful run for the final presentation.
