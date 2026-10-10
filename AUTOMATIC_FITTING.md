# Automatic temperature fitting

1. Select valid left and right calibration files and temperatures.
2. Use **Select Folder for T-fit** to choose the acquisition folder.
3. Enable **Automatic Fitting**. The status line shows whether the program is
   watching, fitted a file, skipped a file, or encountered a problem.

The watcher monitors the selected folder and its subfolders. New `.spe` and
`.SPE` files are detected, including files renamed from temporary filenames.
Files that already exist when automatic mode starts are not automatically fit.

The program checks once per second. It waits until a new file's size and
modification time have stayed unchanged for at least one second before reading
it. If reading or fitting fails, it retries up to five times for that unchanged
file version. If writing resumes later, the changed version is tried again.
Duplicate filesystem notifications do not cause duplicate fits.

Successful fits update the selected spectrum path, temperature labels, and
plots. All Tk and plotting work stays on the main thread. Both calibration files
must exist; otherwise the new spectrum is skipped with a visible status message.

Turning automatic mode off stops its observer and cancels its timer immediately.
Choosing another folder while automatic mode is enabled switches the watch to
that folder. Closing the window or choosing **Main > Exit** stops the watcher.

Regression checks (includes real filesystem events and temperature fits):

```powershell
python -B -m unittest test_automatic_fitting test_calibration_selection test_debug_mode -v
```
