# Running without instruments

Double-click `main_debug.bat`, or run:

```powershell
python main.py --debug
```

Debug mode is selected at startup. The main window title and menu bar show
that instruments are simulated. Close the program and run `python main.py`
to return to normal hardware operation.

In debug mode:

- AGILIS motion commands, Denkovi relay commands, and laser commands (TCP and
  RS232) are logged without opening hardware connections or waiting for devices.
- The Communications Monitor labels every simulated command
  `[DEBUG - SIMULATED]`.
- Each relay board retains its own simulated 16-relay state, so toggling and
  reading controls work together. State resets when the program exits.
- The COM-port selector shows the configured ports without scanning devices.
- Calibration selection, local SPE-file analysis, plots, and the controls remain
  available. The bundled calibration files provide the initial plots.

- The Camera tab uses a simulated camera instead of the PICAM driver. It builds
  frames from the profile's two calibration files: a dark frame for
  Background, the lamp for Flatfield, and an 1800 K sample for Acquire
  Spectrum. Files are written as `.npz` in the folder for T-fit, and exposure
  scales the counts. `.lfe` loading only records the file name.

The usual Python dependencies are still required (`pylablib-lightweight` is not). Debug
mode does not simulate physical motion or laser power. Apart from the simulated
camera frames above, temperature fitting still uses actual local SPE files.

Normal mode remains the default and uses the existing hardware communication.
The existing `main.bat` retains its laboratory-specific launch commands; use
`main_debug.bat` for this checkout's offline launcher.
