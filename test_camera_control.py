"""Camera control: services, background subtraction, and the real Camera tab in debug mode."""
from dataclasses import replace
import gc
import json
from pathlib import Path
import tempfile
import time
import tkinter as tk
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import numpy as np

import comms_monitor
import hardware_mode
from laser_heating.analysis import fit_temperature, subtract_background
from laser_heating.application import HeatingApplication
from laser_heating.camera import CameraError, LightFieldCamera, PicamDriverCamera, SimulatedCamera, create_camera
from laser_heating.config import APP_ROOT, ApplicationConfig, CameraControlSettings
from laser_heating.models import CameraData
from laser_heating.readers import ReaderRegistry

DEFAULT_CONFIG = APP_ROOT / "config" / "default.json"


def capture(frames, width=6, source="capture.npz"):
    return CameraData(np.asarray(frames, dtype=float), np.linspace(500, 900, width), Path(source))


class BackgroundSubtractionTests(unittest.TestCase):
    def test_mean_background_frame_is_subtracted_from_every_frame(self):
        data = capture(np.stack((np.full((2, 6), 50.0), np.full((2, 6), 80.0))))
        background = capture(np.stack((np.full((2, 6), 8.0), np.full((2, 6), 12.0))))
        result = subtract_background(data, background)
        np.testing.assert_allclose(result.frames[0], 40.0)
        np.testing.assert_allclose(result.frames[1], 70.0)
        self.assertEqual(result.source, data.source)
        np.testing.assert_allclose(data.frames[0], 50.0)  # input is not modified

    def test_integer_counts_can_go_negative_without_wrapping(self):
        data = CameraData(np.full((2, 6), 5, dtype=np.uint16), np.linspace(500, 900, 6), Path("a.npz"))
        background = CameraData(np.full((2, 6), 9, dtype=np.uint16), np.linspace(500, 900, 6), Path("b.npz"))
        np.testing.assert_allclose(subtract_background(data, background).frames, -4.0)

    def test_wrong_size_or_wavelength_grid_is_rejected(self):
        data = capture(np.ones((2, 6)))
        with self.assertRaisesRegex(ValueError, "pixels"):
            subtract_background(data, capture(np.ones((3, 6))))
        shifted = CameraData(np.ones((2, 6)), np.linspace(510, 910, 6), Path("b.npz"))
        with self.assertRaisesRegex(ValueError, "wavelength"):
            subtract_background(data, shifted)


class ReaderAndConfigTests(unittest.TestCase):
    def test_read_by_suffix_prefers_profile_reader_and_falls_back(self):
        registry = ReaderRegistry.defaults()
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "capture.npz"
            np.savez(path, frames=np.ones((2, 6)), wavelengths_nm=np.linspace(500, 900, 6))
            self.assertEqual(registry.read_by_suffix(path, "spe").frames.shape, (1, 2, 6))
            with self.assertRaisesRegex(ValueError, "No camera reader"):
                registry.read_by_suffix(Path(folder) / "capture.txt", "spe")

    def test_camera_control_settings_load_and_validate(self):
        self.assertEqual(ApplicationConfig.load(DEFAULT_CONFIG).camera_control,
                         CameraControlSettings("picam", 0.1, 30))
        self.assertEqual(CameraControlSettings(backend="lightfield").backend, "lightfield")
        raw = json.loads(DEFAULT_CONFIG.read_text(encoding="utf-8"))
        del raw["camera_control"]  # profiles written before this feature
        for key in ("root", "left_table", "right_table", "left_file", "right_file"):
            raw["calibration"][key] = str((DEFAULT_CONFIG.parent / raw["calibration"][key]).resolve())
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "old.json"
            path.write_text(json.dumps(raw), encoding="utf-8")
            self.assertEqual(ApplicationConfig.load(path).camera_control, CameraControlSettings())
        for bad in ({"backend": "epics"}, {"exposure_seconds": 0}, {"acquire_timeout_seconds": True},
                    {"camera_serial": 2807060001}):
            with self.assertRaises(ValueError):
                CameraControlSettings(**bad)


class SimulatedCameraTests(unittest.TestCase):
    def setUp(self):
        hardware_mode.configure(debug=True)
        self.temp = tempfile.TemporaryDirectory()
        self.folder = Path(self.temp.name)
        self.template = capture(np.full((4, 6), 1000.0))
        self.camera = SimulatedCamera(lambda: self.template, 2255, exposure_seconds=0.1, seed=1)

    def tearDown(self):
        self.temp.cleanup()

    def test_requires_connection(self):
        with self.assertRaisesRegex(CameraError, "not connected"):
            self.camera.acquire(self.folder, "a")

    def test_captures_are_valid_and_follow_kind_and_exposure(self):
        self.camera.connect()
        registry = ReaderRegistry.defaults()
        dark = registry.read_by_suffix(self.camera.acquire(self.folder, "dark", "background"))
        flat = registry.read_by_suffix(self.camera.acquire(self.folder, "flat", "flatfield"))
        self.assertEqual((dark.height, dark.width), (4, 6))
        self.assertAlmostEqual(dark.exposure_seconds, 0.1)
        self.assertLess(abs(dark.frames.mean() - SimulatedCamera.DARK_COUNTS), 3)
        self.assertLess(abs((flat.frames - dark.frames).mean() - 1000), 5)
        self.camera.set_exposure_seconds(0.2)
        double = registry.read_by_suffix(self.camera.acquire(self.folder, "flat2", "flatfield"))
        self.assertLess(abs((double.frames - dark.frames).mean() - 2000), 5)
        with self.assertRaisesRegex(CameraError, "already exists"):
            self.camera.acquire(self.folder, "flat2", "flatfield")
        with self.assertRaises(CameraError):
            self.camera.set_exposure_seconds(0)
        self.assertTrue(any("[DEBUG - SIMULATED]" in line and "PIXIS" in line
                            for line in comms_monitor.get_history()))

    def test_factory_uses_simulation_only_in_debug_mode(self):
        settings = CameraControlSettings()
        self.assertIsInstance(create_camera(settings, lambda: self.template, 2255), SimulatedCamera)
        hardware_mode.configure(debug=False)
        try:
            camera = create_camera(CameraControlSettings(backend="lightfield"), lambda: self.template, 2255)
            self.assertIsInstance(camera, LightFieldCamera)
            self.assertFalse(camera.connected)  # LightField is not started until asked
            camera = create_camera(settings, lambda: self.template, 2255, "calibration.spe")
            self.assertIsInstance(camera, PicamDriverCamera)
            self.assertFalse(camera.connected)  # the driver is not loaded until asked
            self.assertEqual(camera.reference_name, "calibration.spe")
            with self.assertRaisesRegex(ValueError, "reference_file"):
                create_camera(settings, lambda: self.template, 2255)
        finally:
            hardware_mode.configure(debug=True)


class FakeExperiment:
    """Stands in for LightField's IExperiment; writes the file when 'acquisition' ends."""

    def __init__(self, finish=True):
        self.values = {"exposure": 100.0, "frames": 1}
        self.finish = finish
        self.loaded = None
        self.stopped = False
        self.IsReadyToRun = True
        self._polls = 0
        self._acquiring = False

    def Exists(self, setting):
        return setting != "missing"

    def SetValue(self, setting, value):
        self.values[setting] = value

    def GetValue(self, setting):
        return self.values[setting]

    def GetSavedExperiments(self):
        return ["LaserHeating", "Ruby"]

    def Load(self, name):
        self.loaded = name
        self.values["exposure"] = 250.0

    def Acquire(self):
        self._acquiring = True
        self._polls = 0

    def Stop(self):
        self.stopped = True
        self._acquiring = False

    @property
    def IsRunning(self):
        if not self._acquiring:
            return False
        self._polls += 1
        if self.finish and self._polls >= 3:
            Path(self.values["directory"], self.values["base"] + ".spe").write_bytes(b"spe")
            self._acquiring = False
        return self._acquiring


class LightFieldCameraTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.folder = Path(self.temp.name)
        self.experiment = FakeExperiment()
        self.disposed = []
        self.session = SimpleNamespace(
            experiment=self.experiment, dispose=lambda: self.disposed.append(True),
            exposure_ms="exposure", directory="directory", base_name="base", attach_increment="increment",
            attach_date="date", attach_time="time", frames="frames")
        self.camera = LightFieldCamera(session_factory=lambda: self.session, timeout_seconds=0.2)
        self.camera.POLL_SECONDS = 0.001

    def tearDown(self):
        self.temp.cleanup()

    def test_not_connected_and_close(self):
        with self.assertRaisesRegex(CameraError, "not connected"):
            self.camera.get_exposure_seconds()
        self.camera.connect()
        self.camera.connect()
        self.assertTrue(self.camera.connected)
        self.camera.close()
        self.camera.close()
        self.assertEqual(self.disposed, [True])
        self.assertFalse(self.camera.connected)

    def test_exposure_is_exchanged_in_milliseconds(self):
        self.camera.connect()
        self.assertAlmostEqual(self.camera.get_exposure_seconds(), 0.1)
        self.camera.set_exposure_seconds(0.0025)
        self.assertAlmostEqual(self.experiment.values["exposure"], 2.5)
        for bad in (0, -1, float("nan")):
            with self.assertRaises(CameraError):
                self.camera.set_exposure_seconds(bad)
        self.assertAlmostEqual(self.experiment.values["exposure"], 2.5)

    def test_experiment_is_loaded_by_name_from_lightfield_folder(self):
        self.camera.connect()
        self.assertEqual(self.camera.load_experiment(r"C:\Users\lab\Documents\LightField\Experiments\Ruby.lfe"), "Ruby")
        self.assertEqual(self.experiment.loaded, "Ruby")
        self.assertAlmostEqual(self.camera.get_exposure_seconds(), 0.25)
        with self.assertRaisesRegex(CameraError, "Experiments folder"):
            self.camera.load_experiment(self.folder / "Elsewhere.lfe")
        self.assertEqual(self.experiment.loaded, "Ruby")

    def test_acquire_names_the_file_and_waits_for_it(self):
        self.camera.connect()
        path = self.camera.acquire(self.folder / "new", "background_1", "background")
        self.assertEqual(path, self.folder / "new" / "background_1.spe")
        self.assertTrue(path.is_file())
        values = self.experiment.values
        self.assertEqual((values["directory"], values["base"]), (str(self.folder / "new"), "background_1"))
        self.assertEqual((values["increment"], values["date"], values["time"]), (False, False, False))
        with self.assertRaisesRegex(CameraError, "already exists"):
            self.camera.acquire(self.folder / "new", "background_1")

    def test_timeout_stops_lightfield_and_not_ready_is_reported(self):
        self.experiment.finish = False
        self.camera.connect()
        started = time.monotonic()
        with self.assertRaisesRegex(CameraError, "Timed out"):
            self.camera.acquire(self.folder, "never")
        self.assertLess(time.monotonic() - started, 5)
        self.assertTrue(self.experiment.stopped)
        self.experiment.IsReadyToRun = False
        with self.assertRaisesRegex(CameraError, "not ready"):
            self.camera.acquire(self.folder, "blocked")

    def test_missing_lightfield_installation_is_a_clear_error(self):
        with patch.dict("os.environ", {}, clear=False) as environment:
            environment.pop("LIGHTFIELD_ROOT", None)
            with self.assertRaisesRegex(CameraError, "LightField is not installed"):
                LightFieldCamera().connect()


class CameraTabTests(unittest.TestCase):
    """The real application in debug mode with the bundled PIXIS calibration files."""

    def setUp(self):
        # Tk objects left by earlier tests must be collected on this thread, not later on
        # the camera worker thread (these tests pump events without running mainloop).
        gc.collect()
        self.temp = tempfile.TemporaryDirectory()
        self.folder = Path(self.temp.name)
        self.config = replace(ApplicationConfig.load(DEFAULT_CONFIG), acquisition_folder=self.folder)
        hardware_mode.configure(debug=True)
        self.patches = [patch("serial.Serial", side_effect=AssertionError("Serial I/O in debug")),
                        patch("socket.socket", side_effect=AssertionError("Network I/O in debug")),
                        patch("serial.tools.list_ports.comports", side_effect=AssertionError("Port scan in debug"))]
        for mock in self.patches:
            mock.start()
        self.root = tk.Tk()
        self.root.withdraw()
        self.errors = []
        self.root.report_callback_exception = lambda exc, error, trace: self.errors.append(error)
        self.app = HeatingApplication(self.root, self.config)
        for window in self.app.windows.values():
            window.withdraw()
        self.view = self.app.temperature
        self.plots = self.view.Temperature_graphs
        self.calibration = self.view.CalibrationFileSelect
        self.panel = self.view.CameraControl
        self.panel.POLL_MS = 5
        self.camera = self.panel.camera
        self.destroyed = False

    def tearDown(self):
        if not self.destroyed:
            self.root.destroy()
        for mock in reversed(self.patches):
            mock.stop()
        self.temp.cleanup()
        self.assertEqual(self.errors, [])

    def wait(self):
        deadline = time.monotonic() + 10
        self.root.update()
        while self.panel.busy:
            self.assertLess(time.monotonic(), deadline, "camera job did not finish")
            self.root.update()
            time.sleep(0.002)

    def status(self):
        return self.panel.status_label.cget("text")

    def field(self, widget):
        return widget.get("1.0", tk.END).strip()

    def test_camera_tab_is_third_tab_and_simulated_camera_starts_disconnected(self):
        self.assertIsInstance(self.camera, SimulatedCamera)
        self.assertFalse(self.camera.connected)
        self.assertEqual(self.panel.winfo_manager(), "")
        self.view.select_file_handling(3)
        self.assertEqual(self.panel.winfo_manager(), "place")
        self.assertEqual(self.view.DataFileSelect.winfo_manager(), "")
        self.assertEqual(str(self.view.show_camera_control_window.cget("state")), "disabled")
        self.view.select_file_handling(1)
        self.assertEqual(self.panel.winfo_manager(), "")
        self.assertEqual(self.calibration.winfo_manager(), "place")
        self.assertEqual(self.panel.exposure_value.get(), "100.00")
        self.assertEqual(self.panel.exposure_unit.get(), "ms")
        self.assertEqual(self.panel.reference_temperature.get(), "2255")

    def test_connect_then_exposure_in_each_unit(self):
        self.panel.connect_button.invoke()
        self.assertEqual(str(self.panel.acquire_button.cget("state")), "disabled")
        self.wait()
        self.assertTrue(self.camera.connected)
        self.assertIn("Connected", self.panel.connection_label.cget("text"))
        self.assertEqual(str(self.panel.acquire_button.cget("state")), "normal")
        for text, unit, seconds in (("250", "ms", 0.25), ("2", "s", 2.0), ("500.5", "µs", 500.5e-6)):
            self.panel.exposure_value.set(text)
            self.panel.exposure_unit.set(unit)
            self.panel.set_exposure_button.invoke()
            self.wait()
            self.assertAlmostEqual(self.camera.get_exposure_seconds(), seconds)
            self.assertEqual(self.panel.exposure_value.get(), f"{float(text):.2f}")
            self.assertEqual(self.panel.exposure_unit.get(), unit)
        for bad in ("", "abc", "0", "-3", "0.001", "inf", "nan"):
            self.panel.exposure_value.set(bad)
            self.panel.set_exposure_button.invoke()
            self.wait()
            self.assertIn("Exposure", self.status())
            self.assertAlmostEqual(self.camera.get_exposure_seconds(), 500.5e-6)

    def test_small_camera_exposure_is_shown_in_a_finer_unit(self):
        self.panel.exposure_unit.set("s")
        self.panel._show_exposure(0.005)
        self.assertEqual((self.panel.exposure_value.get(), self.panel.exposure_unit.get()), ("5.00", "ms"))
        self.panel._show_exposure(2.5)
        self.assertEqual((self.panel.exposure_value.get(), self.panel.exposure_unit.get()), ("2500.00", "ms"))

    def test_load_experiment_file(self):
        with patch("laser_heating.ui.camera.filedialog.askopenfilename", return_value="C:/x/Heating 15x.lfe"):
            self.panel.load_experiment_button.invoke()
        self.wait()
        self.assertEqual(self.panel.experiment_label.cget("text"), "Experiment: Heating 15x")
        with patch("laser_heating.ui.camera.filedialog.askopenfilename", return_value=""):
            self.panel.load_experiment_button.invoke()
        self.assertFalse(self.panel.busy)

    def test_acquire_background_and_fit(self):
        self.panel.acquire_button.invoke()
        self.wait()
        spectra = list(self.folder.glob("spectrum_*.npz"))
        self.assertEqual(len(spectra), 1)
        self.assertEqual(self.plots.data_file.source, spectra[0])
        self.assertIn("Fitted", self.status())
        without_background = self.plots.left_result.temperature_kelvin

        self.panel.collect_background_button.invoke()
        self.wait()
        self.assertIsNotNone(self.plots.background)
        self.assertEqual(self.panel.background_path.parent, self.folder)
        self.assertIn(self.panel.background_path.name, self.panel.background_label.cget("text"))
        # The simulated sample is 1800 K seen through the bundled 2255 K calibration.
        for result in (self.plots.left_result, self.plots.right_result):
            self.assertAlmostEqual(result.temperature_kelvin, SimulatedCamera.SAMPLE_TEMPERATURE, delta=10)
        self.assertGreater(abs(without_background - 1800), abs(self.plots.left_result.temperature_kelvin - 1800))
        # Exported calibration files are not background-subtracted.
        self.assertEqual(self.plots.calibration_needs_background, {"left": False, "right": False})

        saved = self.folder / "kept" / "dark.npz"
        saved.parent.mkdir()
        with patch("laser_heating.ui.camera.filedialog.asksaveasfilename", return_value=str(saved)):
            self.panel.save_background_button.invoke()
        self.assertEqual(saved.read_bytes(), self.panel.background_path.read_bytes())

        fitted = self.plots.left_result.temperature_kelvin
        self.panel.clear_background_button.invoke()
        self.assertIsNone(self.plots.background)
        self.assertAlmostEqual(self.plots.left_result.temperature_kelvin, without_background, places=6)
        with patch("laser_heating.ui.camera.filedialog.askopenfilename", return_value=str(saved)):
            self.panel.load_background_button.invoke()
        self.assertEqual(self.panel.background_path, saved)
        self.assertAlmostEqual(self.plots.left_result.temperature_kelvin, fitted, places=6)

    def test_bad_background_keeps_current_one(self):
        wrong = self.folder / "wrong.npz"
        np.savez(wrong, frames=np.ones((20, 96)), wavelengths_nm=np.linspace(500, 900, 96))
        before = self.plots.left_result.temperature_kelvin
        with patch("laser_heating.ui.camera.filedialog.askopenfilename", return_value=str(wrong)):
            self.panel.load_background_button.invoke()
        self.assertIsNone(self.plots.background)
        self.assertIsNone(self.panel.background_path)
        self.assertIn("1340x70", self.status())
        self.assertEqual(self.plots.left_result.temperature_kelvin, before)
        self.panel.save_background_button.invoke()
        self.assertIn("first", self.status())

    def test_flatfield_becomes_that_sides_calibration(self):
        right_before = self.field(self.calibration.right_file_location)
        self.panel.collect_background_button.invoke()
        self.wait()
        self.panel.reference_temperature.set("2300")
        self.panel.side_buttons["left"].invoke()
        self.panel.collect_flatfield_button.invoke()
        self.wait()
        flatfield = self.panel.flatfield_paths["left"]
        self.assertTrue(flatfield.name.startswith("flatfield_left_"))
        self.assertEqual(self.field(self.calibration.left_file_location), str(flatfield))
        self.assertEqual(self.field(self.calibration.set_left_temperature), "2300")
        self.assertEqual(self.field(self.calibration.right_file_location), right_before)
        self.assertEqual(self.field(self.calibration.set_right_temperature), "2255")
        self.assertEqual(self.plots.calibration_needs_background, {"left": True, "right": False})
        self.assertEqual(self.plots.left_calibration_temperature, 2300)
        self.assertIn(flatfield.name, self.panel.flatfield_label.cget("text"))
        self.assertIsNone(self.panel.flatfield_paths["right"])

        # A later measurement keeps using the raw flatfield with background removed.
        self.panel.acquire_button.invoke()
        self.wait()
        self.assertEqual(self.plots.calibration_needs_background, {"left": True, "right": False})
        expected = fit_temperature(subtract_background(self.plots.data_file, self.plots.background),
                                   subtract_background(self.plots.left_calibration_file, self.plots.background),
                                   self.plots.left_roi, 2300)
        self.assertAlmostEqual(self.plots.left_result.temperature_kelvin, expected.temperature_kelvin, places=6)
        # The simulated lamp equals the bundled calibration, so 1800 K at 2255 K reads higher at 2300 K.
        self.assertGreater(self.plots.left_result.temperature_kelvin, self.plots.right_result.temperature_kelvin)

        saved = self.folder / "left_flat.npz"
        with patch("laser_heating.ui.camera.filedialog.asksaveasfilename", return_value=str(saved)):
            self.panel.save_flatfield_button.invoke()
        self.assertTrue(saved.is_file())
        self.panel.side_buttons["right"].invoke()
        self.panel.reference_temperature.set("2200")
        with patch("laser_heating.ui.camera.filedialog.askopenfilename", return_value=str(saved)):
            self.panel.load_flatfield_button.invoke()
        self.assertEqual(self.field(self.calibration.right_file_location), str(saved))
        self.assertEqual(self.field(self.calibration.set_right_temperature), "2200")
        self.assertEqual(self.plots.calibration_needs_background, {"left": True, "right": True})

        # Choosing an exported calibration file again stops subtracting for that side.
        self.calibration.update_left_calibration_file(self.config.calibration.left_file)
        self.assertTrue(self.view.DataFileSelect.process_new_spe_file(str(self.plots.data_file.source)))
        self.assertEqual(self.plots.calibration_needs_background, {"left": False, "right": True})

    def test_invalid_reference_or_flatfield_changes_nothing(self):
        left_before = self.field(self.calibration.left_file_location)
        for bad in ("", "hot", "0", "-5"):
            self.panel.reference_temperature.set(bad)
            self.panel.collect_flatfield_button.invoke()
            self.assertFalse(self.panel.busy)
            self.assertIn("Ref T", self.status())
        self.assertEqual(list(self.folder.iterdir()), [])
        wrong = self.folder / "wrong.npz"
        np.savez(wrong, frames=np.ones((20, 96)), wavelengths_nm=np.linspace(500, 900, 96))
        self.panel.reference_temperature.set("2255")
        with patch("laser_heating.ui.camera.filedialog.askopenfilename", return_value=str(wrong)):
            self.panel.load_flatfield_button.invoke()
        self.assertEqual(self.field(self.calibration.left_file_location), left_before)
        self.assertIsNone(self.panel.flatfield_paths["left"])
        self.assertEqual(self.plots.calibration_needs_background, {"left": False, "right": False})
        self.assertIn("1340x70", self.status())
        self.panel.save_flatfield_button.invoke()
        self.assertIn("first", self.status())

    def test_camera_error_is_shown_and_controls_recover(self):
        with patch.object(self.camera, "acquire", side_effect=CameraError("shutter stuck")):
            self.panel.acquire_button.invoke()
            self.wait()
        self.assertEqual(self.status(), "shutter stuck")
        self.assertEqual(str(self.panel.acquire_button.cget("state")), "normal")
        # The whole message, with driver details, is readable and copyable in its own window.
        dialog = self.panel.error_dialog
        self.assertTrue(dialog.winfo_exists())
        shown = dialog.error_text.get("1.0", tk.END)
        self.assertTrue(shown.startswith("shutter stuck"))
        self.assertIn("Details for troubleshooting", shown)
        self.assertIn("CameraError: shutter stuck", shown)
        dialog.nametowidget(dialog.winfo_children()[0].winfo_children()[1]).invoke()  # Copy text
        self.assertIn("CameraError: shutter stuck", self.root.clipboard_get())
        long_message = "Exposure problem: " + "the camera refused this setting because " * 12
        self.panel._status(long_message, error=True)
        self.assertIs(self.panel.error_dialog, dialog)  # reused, not stacked
        self.assertEqual(dialog.error_text.get("1.0", tk.END).strip(), long_message.strip())
        self.assertGreaterEqual(dialog.winfo_reqwidth(), 420)
        dialog.destroy()
        self.panel.exposure_value.set("abc")
        self.panel.set_exposure_button.invoke()
        self.assertTrue(self.panel.error_dialog.winfo_exists())
        self.assertIn("Exposure time must be a number", self.panel.error_dialog.error_text.get("1.0", tk.END))
        self.panel.error_dialog.destroy()
        self.panel.exposure_value.set("100")
        self.panel.acquire_button.invoke()
        self.wait()
        self.assertIn("Fitted", self.status())

    def test_folder_watcher_leaves_camera_tab_captures_alone(self):
        files = self.view.DataFileSelect
        files.AUTOFIT_POLL_MS, files.AUTOFIT_SETTLE_SECONDS = 20, 0.05
        files.select_automatic_fit.invoke()
        self.assertIn("Watching", files.autofit_status.cget("text"))
        self.panel.collect_background_button.invoke()
        self.wait()
        background = self.panel.background_path
        for suffix in (".spe", "-raw.spe", ".npz"):
            self.assertIn(str(self.folder.resolve() / (background.stem + suffix)), files._processed_spe_files)
        files.stop_automatic_fitting()

    def test_closing_the_application_closes_the_camera(self):
        self.panel.connect_button.invoke()
        self.wait()
        worker = self.panel._worker
        self.root.destroy()
        self.destroyed = True
        self.assertFalse(self.camera.connected)
        self.assertFalse(worker.is_alive())


if __name__ == "__main__":
    unittest.main()
