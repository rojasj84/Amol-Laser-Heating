# EPL laser heating control

Tk application for the existing laser, AGILIS motor, and Denkovi relay controls,
with temperature fitting from camera-exported spectra. The spectrometer/camera
currently exports files outside this application; the application reads them.

## Run

```powershell
python main.py --debug
python main.py
python main.py --debug --config config/default.json
```

Debug mode simulates instrument commands and still fits actual local files.
`main_debug.bat` launches this checkout. `main.bat` is the older laboratory
launcher with absolute paths to other installations and a separate camera
program; it has been retained as laboratory configuration.

Dependencies are listed in `requirements.txt`, pinned to the environment used
for validation (Windows, Python 3.13.12). Tk comes with the Windows Python
installation. For a new environment:

```powershell
python -m pip install -r requirements.txt
```

## Where to work

| Change | File or package |
| --- | --- |
| Dark palette, typography, shared control styles | `theme.py` |
| Camera dimensions, default ROIs, calibration paths, connections | `config/default.json` |
| New camera export format | `laser_heating/readers.py` |
| Capture, ROI, spectrum, and result types | `laser_heating/models.py` |
| Extract spectra and coordinate fitting | `laser_heating/analysis.py` |
| Existing Planck equations and fit | `TemperatureFit/TemperatureFitting.py` |
| Startup, menus, windows, shared connection settings | `laser_heating/application.py` |
| Plotting and frame navigation | `laser_heating/ui/plots.py` |
| ROI editing | `laser_heating/ui/roi.py` |
| Manual loading and automatic folder fitting | `laser_heating/ui/files.py` |
| Camera tab: exposure, acquire, background, flatfield | `laser_heating/ui/camera.py` |
| PICAM driver, LightField automation and simulated camera back ends | `laser_heating/camera.py` |
| Reference SPE, `.lfe` settings, SPE writing | `laser_heating/spe.py` |
| Calibration fields and optical filter controls | `laser_heating/ui/calibration.py` |
| Calibration CSV lookup and filename resolution | `import_calibration.py` |
| Existing physical instrument commands | `agilis_control.py`, `denkovi_serial.py`, `laser_communication.py` |

`main.py` is the launcher. `acton_pixis.py` keeps the original class imports
working while implementation lives in the package. `deprecated/` and the
vendored `T-rax-develop/` tree are not part of application startup.

## Camera tab (direct PIXIS control)

The **Camera** tab talks to the PIXIS through its PICAM driver, with
LightField **closed** (only one program can own the camera). It needs the PICAM
runtime that LightField installs and the `pylablib-lightweight` package. The
camera is opened by **Connect** or by the first camera action, not at program
start.

The driver knows nothing about the spectrograph, so wavelengths come from a
**reference SPE**: any LightField spectrum saved at the current grating
position. Its wavelength axis and its readout regions (the two 35-row bands in
the bundled files) are reused for every capture. The default reference is the
left calibration file; **Wavelength ref.** picks another, and the line below
the button names the one in use. **If the grating is moved, save one spectrum
from LightField and select it as the new reference**, otherwise the fitted
temperatures will be wrong. The app reads one sensor rectangle covering all
regions and cuts the regions out, so saved images have the same layout as
LightField's.

| Control | Behavior |
| --- | --- |
| Exposure + unit (µs / ms / s), **Set** | Value is shown as `%.2f` and sent to the camera. Changing the unit reinterprets the number. |
| **Load LF Exp. Setup file** | Reads a `.lfe` file and applies what the driver understands: exposure, readout regions, ADC speed, gain and quality. The status line lists what was applied or refused. Spectrograph, online-correction and file-naming settings are ignored. |
| **Wavelength ref.** | Chooses the reference SPE described above. |
| **Acquire Spectrum** | Captures with the exposure shown and fits it like a manually selected file. |
| Background **Collect / Save / Load / Clear** | The mean background frame is subtracted from every measurement. Block the light before collecting. |
| Flatfield **Left / Right**, **Ref T (K)**, **Collect / Save / Load** | The capture becomes that side's calibration file and Ref T its calibration temperature. |

Captures go to the "Folder for T-fit" as `spectrum_*`, `background_*` and
`flatfield_<side>_*` with a timestamp; automatic fitting ignores them.

A flatfield from this tab is raw, so the active background is subtracted from
it as well. Calibration files chosen on the Calibration tab or by the filter
table are used exactly as saved (the bundled ones are already
background-subtracted LightField exports). Selecting a filter state replaces a
flatfield with the table's file for that state. The background must have the
same image size and wavelength grid as the capture; otherwise it is rejected
and the previous fit stays on screen.

Errors open a "Camera message" window with the full text, driver details and a
**Copy text** button; they are also listed in the Communications Monitor.

Captures are raw 16-bit counts written as SPE 3.0 with the reference's
wavelength calibration. Unlike the bundled LightField exports they have no
cosmic-ray removal, and background is removed only by the Background controls
here.

`camera_control` in the JSON profile sets the starting exposure, the readout
timeout beyond the exposure, and optionally `reference_file`, `camera_serial`
and `picam_dll_folder` (if `picam.dll` is not in the default Princeton
Instruments folder). `"backend": "lightfield"` selects the earlier LightField
automation link instead, which needs `pythonnet` and a running LightField.

## Another camera or ROI

Copy `config/default.json` to a new profile. Set `camera.width` and
`camera.height` to the dimensions of the **saved image**, after hardware
cropping/binning. Supply left and right ROIs with zero-based pixel coordinates
and exclusive end bounds, matching NumPy slices.

Paths in a profile resolve relative to the JSON file. In the ROI editor, drag
the corner/edge handles to resize, or drag inside a rectangle to move it. Hovering shows the available action. The coordinate
fields update while dragging; fitting changes only after **Apply & Close**.
Click a side title to select which ROI to edit when they overlap.

Runtime ROI edits can be saved in the ROI editor's separate JSON format; they do not overwrite the
application profile. Runtime connection edits also do not overwrite it.

Supported readers:

- `spe`: current Princeton Instruments SPE adapter.
- `npz`: generic NumPy archive containing `frames` and `wavelengths_nm`, with
  optional `exposure_seconds`. Frames have shape `(frame, row, column)` or
  `(row, column)` for a single frame. Wavelengths have one value per column,
  in nanometers, positive and strictly increasing.

Example generic export:

```python
np.savez("capture.npz", frames=images, wavelengths_nm=wavelengths,
         exposure_seconds=0.1)
```

For a different camera, set `calibration.left_file`, `calibration.right_file`,
and `initial_measurement` to compatible captures. Set
`calibration.use_filter_table` to `false` when selecting calibrations manually;
this keeps the current optical-state tables from replacing those paths. The
physical relay controls still operate. For automatic state-based selection,
provide that setup's calibration root and tables.

To add a vendor format, implement `CameraReader.read(path) -> CameraData` and
its `extensions` tuple, then register it in `ReaderRegistry.defaults()` and
use its name in the profile. A custom registry can also be passed to
`HeatingApplication` for embedding. Fitting and plotting do not need vendor
SDK imports. Direct SDK acquisition is a future integration described in
`ARCHITECTURE.md`.

## Verify

```powershell
python -B -m unittest test_modular_architecture test_calibration_selection test_debug_mode test_automatic_fitting test_roi_dragging -v
```

Tests exercise real Tk widgets and watchdog events, so they require a Windows
desktop session. Pure analysis tests can run separately:

```powershell
python -B -m unittest test_modular_architecture.AnalysisTests -v
```

See `ARCHITECTURE.md` for the structural assessment and next steps,
`DEBUG_MODE.md` for offline operation, and `AUTOMATIC_FITTING.md` for watcher
behavior.
