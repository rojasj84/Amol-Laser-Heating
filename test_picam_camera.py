"""PICAM driver back end: reference SPE, SPE writing, .lfe settings, and the Camera tab."""
from dataclasses import replace
import gc
from pathlib import Path
import tempfile
import time
import tkinter as tk
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import numpy as np

import hardware_mode
from laser_heating import spe
from laser_heating.application import HeatingApplication
from laser_heating.camera import CameraError, PicamDriverCamera, _open_picam_device
from laser_heating.config import APP_ROOT, ApplicationConfig
from laser_heating.readers import SpeReader
from laser_heating.spe import CameraSetup, SensorRegion

DEFAULT_CONFIG = APP_ROOT / "config" / "default.json"
CALIBRATION = APP_ROOT / "TemperatureFit" / "T_Calib_20250314" / "15xMag"
LEFT, RIGHT = CALIBRATION / "L_2255K_15x_wI.spe", CALIBRATION / "R_2255K_15x_wI.spe"
BANDS = (SensorRegion(0, 1340, 1, 75, 35, 1), SensorRegion(0, 1340, 1, 290, 35, 1))

LFE = """<?xml version="1.0" encoding="utf-8"?>
<Experiment xmlns="http://www.princetoninstruments.com/experiment/2009" version="11">
  <System><Cameras count="1"><Camera deviceID="2" model="PIXIS: 400B"/></Cameras></System>
  <Devices><Cameras count="1"><Camera deviceID="2">
    <ShutterTiming><ExposureTime type="Double">50</ExposureTime></ShutterTiming>
    <ReadoutControl><RegionsOfInterest>
      <Selection type="RegionsOfInterestSelection">{selection}</Selection>
      <CustomRegions type="RegionsOfInterest" count="2">
        <RegionOfInterest id="0" x="0" width="1340" xBinning="1" y="80" height="30" yBinning="1"/>
        <RegionOfInterest id="1" x="0" width="1340" xBinning="1" y="295" height="40" yBinning="1"/>
      </CustomRegions>
      <BinnedSensor><XBinning type="Int32">2</XBinning><YBinning type="Int32">4</YBinning></BinnedSensor>
      <Result count="1"><RegionOfInterest id="0" x="0" width="10" xBinning="1" y="0" height="10" yBinning="1"/></Result>
    </RegionsOfInterest></ReadoutControl>
    <Adc><Speed type="Double">0.1</Speed><AnalogGain type="AdcAnalogGain">High</AnalogGain>
         <Quality type="AdcQuality">LowNoise</Quality></Adc>
    <Experiment><Acquisition><FramesToStore type="Int64">1</FramesToStore></Acquisition></Experiment>
  </Camera></Cameras>
  <Spectrometers><Spectrometer><Grating><CenterWavelength type="Double">650</CenterWavelength></Grating></Spectrometer></Spectrometers>
  </Devices>
</Experiment>"""


class FakePicamDevice:
    """The part of pylablib's PicamCamera that the back end uses."""

    DARK = 100

    def __init__(self, sensor=(1340, 400)):
        self.sensor = sensor
        self.roi = (0, sensor[0], 0, sensor[1], 1, 1)
        self.exposure = 0.1
        self.attributes = {}
        self.closed = False
        self.dark = False
        self.snap_timeouts = []
        left = np.clip(SpeReader().read(LEFT).frame(0), 0, None)
        right = np.clip(SpeReader().read(RIGHT).frame(0), 0, None)
        self.scene = np.zeros((sensor[1], sensor[0]))
        self.scene[75:110] = left[0:35]
        self.scene[290:325] = right[35:70]

    def get_detector_size(self):
        return self.sensor

    def set_roi(self, hstart=0, hend=None, vstart=0, vend=None, hbin=1, vbin=1):
        self.roi = (hstart, hend, vstart, vend, hbin, vbin)
        return self.roi

    def get_exposure(self):
        return self.exposure

    def set_exposure(self, exposure):
        self.exposure = exposure
        return exposure

    def set_attribute_value(self, name, value, truncate=True, error_on_missing=True):
        allowed = {"ADC Speed": (0.1, 2.0), "ADC Analog Gain": ("Low", "Medium", "High"),
                   "ADC Quality": ("Low Noise", "High Capacity")}
        if value not in allowed[name]:
            raise ValueError(f"{value!r} is not valid for {name}")
        self.attributes[name] = value

    def get_device_info(self):
        return SimpleNamespace(model="PIXIS: 400B", serial_number="2807060001")

    def snap(self, timeout=5.0):
        self.snap_timeouts.append(timeout)
        x0, x1, y0, y1, _, _ = self.roi
        frame = np.full((y1 - y0, x1 - x0), float(self.DARK))
        if not self.dark:
            frame += self.scene[y0:y1, x0:x1]
        return np.clip(np.rint(frame), 0, 65535).astype(np.uint16)

    def close(self):
        self.closed = True


class SpeHelperTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.folder = Path(self.temp.name)
        self.reference = spe.read_reference(LEFT)

    def tearDown(self):
        self.temp.cleanup()

    def test_reference_supplies_wavelengths_regions_and_camera_settings(self):
        reference = self.reference
        self.assertEqual((reference.sensor_width, reference.sensor_height), (1340, 400))
        self.assertEqual(reference.setup, CameraSetup(2.0, BANDS, 2.0, "Medium", "LowNoise"))
        np.testing.assert_array_equal(reference.wavelengths_for(BANDS), SpeReader().read(LEFT).wavelengths_nm)
        self.assertEqual(spe.readout_window(BANDS), (0, 1340, 75, 325))

    def test_files_without_a_wavelength_footer_are_rejected(self):
        short = self.folder / "short.spe"
        short.write_bytes(b"not an spe file")
        old = self.folder / "old.spe"
        old.write_bytes(bytes(spe.HEADER_BYTES) + bytes(100))
        for path, reason in ((short, "too short"), (old, "no SPE 3.0 footer"), (self.folder / "missing.spe", "missing")):
            with self.assertRaisesRegex(ValueError, "cannot be used as a wavelength reference") as caught:
                spe.read_reference(path)
            self.assertIn(reason, str(caught.exception))

    def test_written_spe_is_read_back_by_the_existing_reader(self):
        image = (np.arange(70 * 1340).reshape(70, 1340) % 60000).astype(np.uint16)
        path = spe.write_spe(self.folder / "capture.spe", np.stack((image, image + 1)),
                             self.reference.sensor_wavelengths_nm, BANDS, (1340, 400), 0.25, "PIXIS: 400B")
        self.assertEqual([item.name for item in self.folder.iterdir()], ["capture.spe"])
        data = SpeReader().read(path)
        self.assertEqual((data.frames.shape, data.frames.dtype), ((2, 70, 1340), np.uint16))
        np.testing.assert_array_equal(data.frames[1], image + 1)
        np.testing.assert_array_equal(data.wavelengths_nm, SpeReader().read(LEFT).wavelengths_nm)
        self.assertAlmostEqual(data.exposure_seconds, 0.25)
        # A capture written by the app can itself serve as the next reference.
        again = spe.read_reference(path)
        self.assertEqual(again.setup, CameraSetup(0.25, BANDS))
        np.testing.assert_array_equal(again.sensor_wavelengths_nm, self.reference.sensor_wavelengths_nm)
        single = spe.write_spe(self.folder / "single.spe", image.astype(float) - 5.5,
                               self.reference.sensor_wavelengths_nm, BANDS, (1340, 400), 1.0)
        self.assertEqual(SpeReader().read(single).frames.dtype, np.float32)
        with self.assertRaisesRegex(ValueError, "Frame size"):
            spe.write_spe(self.folder / "bad.spe", image[:60], self.reference.sensor_wavelengths_nm,
                          BANDS, (1340, 400), 1.0)

    def test_regions_are_cut_from_the_readout_window_and_binned_by_summing(self):
        window = np.arange(250 * 1340, dtype=np.uint32).reshape(250, 1340)
        image = spe.assemble_image(window, BANDS)
        np.testing.assert_array_equal(image[:35], window[:35])
        np.testing.assert_array_equal(image[35:], window[215:250])
        binned = (SensorRegion(0, 8, 2, 0, 4, 4), SensorRegion(0, 8, 2, 6, 2, 1))
        small = np.ones((8, 8), dtype=np.uint16) * 60000
        result = spe.assemble_image(small, binned)
        self.assertEqual(result.shape, (3, 4))
        np.testing.assert_array_equal(result[0], 480000)  # no 16-bit overflow
        np.testing.assert_array_equal(result[1:], 120000)
        np.testing.assert_allclose(spe.region_wavelengths(np.arange(10.0), binned), [0.5, 2.5, 4.5, 6.5])
        with self.assertRaisesRegex(ValueError, "expected 1340x250"):
            spe.assemble_image(window[:249], BANDS)

    def test_invalid_regions_are_rejected(self):
        cases = (((), "No readout region"),
                 ((SensorRegion(0, 1340, 1, 380, 35, 1),), "exceeds"),
                 ((BANDS[0], SensorRegion(10, 1330, 1, 290, 35, 1)), "same columns"),
                 ((BANDS[1], BANDS[0]), "top to bottom"),
                 ((BANDS[0], SensorRegion(0, 1340, 1, 100, 35, 1)), "overlapping"))
        for regions, message in cases:
            with self.assertRaisesRegex(ValueError, message):
                spe.validate_regions(regions, 1340, 400)
        with self.assertRaises(ValueError):
            SensorRegion(0, 1340, 3, 0, 35, 1)

    def test_lightfield_experiment_file_settings(self):
        path = self.folder / "Heating.lfe"
        path.write_text(LFE.format(selection="CustomRegions"), encoding="utf-8")
        regions = (SensorRegion(0, 1340, 1, 80, 30, 1), SensorRegion(0, 1340, 1, 295, 40, 1))
        self.assertEqual(spe.read_experiment_file(path, (1340, 400)), CameraSetup(0.05, regions, 0.1, "High", "LowNoise"))
        path.write_text(LFE.format(selection="FullSensor"), encoding="utf-8")
        self.assertEqual(spe.read_experiment_file(path, (1340, 400)).regions, (SensorRegion(0, 1340, 1, 0, 400, 1),))
        path.write_text(LFE.format(selection="BinnedSensor"), encoding="utf-8")
        self.assertEqual(spe.read_experiment_file(path, (1340, 400)).regions, (SensorRegion(0, 1340, 2, 0, 400, 4),))
        path.write_text("<Experiment><Devices/></Experiment>", encoding="utf-8")
        self.assertEqual(spe.read_experiment_file(path, (1340, 400)), CameraSetup())
        path.write_text("not xml", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "Could not read Heating.lfe"):
            spe.read_experiment_file(path)


class PicamDriverCameraTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.folder = Path(self.temp.name)
        self.device = FakePicamDevice()
        self.camera = PicamDriverCamera(LEFT, timeout_seconds=7, device_factory=lambda: self.device)

    def tearDown(self):
        self.temp.cleanup()

    def test_connect_sets_one_window_over_both_bands_and_close_releases_camera(self):
        self.assertFalse(self.camera.connected)
        self.assertEqual(self.camera.reference_name, LEFT.name)
        with self.assertRaisesRegex(CameraError, "not connected"):
            self.camera.acquire(self.folder, "a")
        self.camera.connect()
        self.camera.connect()
        self.assertEqual(self.device.roi, (0, 1340, 75, 325, 1, 1))
        self.camera.close()
        self.camera.close()
        self.assertTrue(self.device.closed)
        self.assertFalse(self.camera.connected)

    def test_capture_is_saved_as_spe_matching_lightfield_layout(self):
        self.camera.connect()
        self.camera.set_exposure_seconds(0.5)
        path = self.camera.acquire(self.folder / "run", "spectrum_1", "spectrum")
        self.assertEqual(path, self.folder / "run" / "spectrum_1.spe")
        self.assertEqual(self.device.snap_timeouts, [7.5])
        data, calibration = SpeReader().read(path), SpeReader().read(LEFT)
        self.assertEqual((data.frames.shape, data.frames.dtype), ((1, 70, 1340), np.uint16))
        np.testing.assert_array_equal(data.wavelengths_nm, calibration.wavelengths_nm)
        self.assertAlmostEqual(data.exposure_seconds, 0.5)
        expected = np.clip(calibration.frame(0)[0:35], 0, None) + FakePicamDevice.DARK
        np.testing.assert_allclose(data.frame(0)[0:35], np.rint(expected))
        self.assertLess(abs(data.frame(0)[35:70].mean() - 100 - SpeReader().read(RIGHT).frame(0)[35:70].mean()), 2)
        self.assertEqual(spe.read_reference(path).setup.regions, BANDS)
        with self.assertRaisesRegex(CameraError, "already exists"):
            self.camera.acquire(self.folder / "run", "spectrum_1")
        for bad in (0, -1, float("inf")):
            with self.assertRaises(CameraError):
                self.camera.set_exposure_seconds(bad)
        self.assertEqual(self.device.exposure, 0.5)

    def test_experiment_file_applies_what_the_driver_understands(self):
        self.camera.connect()
        path = self.folder / "Heating.lfe"
        path.write_text(LFE.format(selection="CustomRegions"), encoding="utf-8")
        self.assertEqual(self.camera.load_experiment(path), "Heating")
        self.assertEqual(self.device.roi, (0, 1340, 80, 335, 1, 1))
        self.assertAlmostEqual(self.camera.get_exposure_seconds(), 0.05)
        self.assertEqual(self.device.attributes, {"ADC Speed": 0.1, "ADC Analog Gain": "High",
                                                  "ADC Quality": "Low Noise"})
        self.assertEqual(self.camera.experiment_note, "Applied 2 regions, exposure, ADC speed, gain, ADC quality")
        data = SpeReader().read(self.camera.acquire(self.folder, "after"))
        self.assertEqual(data.frames.shape, (1, 70, 1340))
        # A value this camera does not offer is reported, not fatal.
        path.write_text(LFE.format(selection="CustomRegions").replace(">0.1<", ">4<"), encoding="utf-8")
        self.camera.load_experiment(path)
        self.assertEqual(self.camera.experiment_note,
                         "Applied 2 regions, exposure, gain, ADC quality; camera refused ADC speed")
        path.write_text("<Experiment/>", encoding="utf-8")
        with self.assertRaisesRegex(CameraError, "no camera settings"):
            self.camera.load_experiment(path)

    def test_reference_can_be_replaced_and_bad_ones_keep_the_current_setup(self):
        self.camera.connect()
        other = spe.write_spe(self.folder / "other.spe", np.zeros((40, 1340), dtype=np.uint16),
                              spe.read_reference(LEFT).sensor_wavelengths_nm + 10.0,
                              (SensorRegion(0, 1340, 1, 100, 40, 1),), (1340, 400), 1.0)
        self.assertEqual(self.camera.set_reference(other), "other.spe")
        self.assertEqual(self.device.roi, (0, 1340, 100, 140, 1, 1))
        data = SpeReader().read(self.camera.acquire(self.folder, "shifted"))
        self.assertEqual(data.frames.shape, (1, 40, 1340))
        np.testing.assert_allclose(data.wavelengths_nm, SpeReader().read(LEFT).wavelengths_nm + 10.0)
        wrong_sensor = spe.write_spe(self.folder / "wrong.spe", np.zeros((10, 1024), dtype=np.uint16),
                                     np.linspace(400, 900, 1024), (SensorRegion(0, 1024, 1, 0, 10, 1),), (1024, 256), 1.0)
        with self.assertRaisesRegex(CameraError, "1024x256 sensor, but this camera is 1340x400"):
            self.camera.set_reference(wrong_sensor)
        with self.assertRaisesRegex(CameraError, "wavelength reference"):
            self.camera.set_reference(self.folder / "missing.spe")
        self.assertEqual(self.camera.reference_name, "other.spe")
        self.assertEqual(self.device.roi, (0, 1340, 100, 140, 1, 1))

    def test_driver_problems_become_camera_errors(self):
        strict = FakePicamDevice()
        strict.set_roi = lambda *window: (0, 1340, 72, 328, 1, 1)
        camera = PicamDriverCamera(LEFT, device_factory=lambda: strict)
        with self.assertRaisesRegex(CameraError, "did not accept the readout region"):
            camera.connect()
        self.assertFalse(camera.connected)
        self.assertTrue(strict.closed)
        self.camera.connect()
        self.device.snap = lambda timeout: (_ for _ in ()).throw(RuntimeError("readout timed out"))
        with self.assertRaisesRegex(CameraError, "Camera driver: readout timed out"):
            self.camera.acquire(self.folder, "a")
        self.assertEqual(list(self.folder.iterdir()), [])
        with self.assertRaisesRegex(CameraError, "wavelength reference"):
            PicamDriverCamera(self.folder / "missing.spe", device_factory=lambda: self.device).connect()

    def test_missing_driver_package_is_a_clear_error(self):
        with patch.dict("sys.modules", {"pylablib": None}):
            with self.assertRaisesRegex(CameraError, "pylablib-lightweight"):
                _open_picam_device()


class PicamCameraTabTests(unittest.TestCase):
    """The Camera tab driving the PICAM back end against a stand-in device."""

    def setUp(self):
        # Tk objects left by earlier tests must be collected on this thread, not later on
        # the camera worker thread (these tests pump events without running mainloop).
        gc.collect()
        self.temp = tempfile.TemporaryDirectory()
        self.folder = Path(self.temp.name)
        config = replace(ApplicationConfig.load(DEFAULT_CONFIG), acquisition_folder=self.folder)
        hardware_mode.configure(debug=True)  # relays, motors and lasers stay simulated
        self.patches = [patch("serial.Serial", side_effect=AssertionError("Serial I/O in debug")),
                        patch("socket.socket", side_effect=AssertionError("Network I/O in debug")),
                        patch("serial.tools.list_ports.comports", side_effect=AssertionError("Port scan in debug"))]
        for mock in self.patches:
            mock.start()
        self.device = FakePicamDevice()
        self.camera = PicamDriverCamera(LEFT, device_factory=lambda: self.device)
        self.root = tk.Tk()
        self.root.withdraw()
        self.errors = []
        self.root.report_callback_exception = lambda exc, error, trace: self.errors.append(error)
        self.app = HeatingApplication(self.root, config, camera=self.camera)
        for window in self.app.windows.values():
            window.withdraw()
        self.view = self.app.temperature
        self.plots = self.view.Temperature_graphs
        self.panel = self.view.CameraControl
        self.panel.POLL_MS = 5

    def tearDown(self):
        self.root.destroy()
        for mock in reversed(self.patches):
            mock.stop()
        self.temp.cleanup()
        self.assertEqual(self.errors, [])
        self.assertTrue(self.device.closed or not self.camera.connected)

    def wait(self):
        deadline = time.monotonic() + 10
        self.root.update()
        while self.panel.busy:
            self.assertLess(time.monotonic(), deadline, "camera job did not finish")
            self.root.update()
            time.sleep(0.002)

    def test_background_flatfield_and_spectrum_through_the_driver(self):
        self.assertIs(self.panel.camera, self.camera)
        self.assertTrue(self.panel.has_reference)
        self.assertEqual(self.panel.experiment_label.cget("text"), f"Ref: {LEFT.name}")
        self.device.dark = True
        self.panel.collect_background_button.invoke()
        self.wait()
        self.assertEqual(self.panel.background_path.suffix, ".spe")
        self.assertIn("Connected: PICAM driver", self.panel.connection_label.cget("text"))
        self.device.dark = False
        self.panel.acquire_button.invoke()
        self.wait()
        self.assertIn("Fitted spectrum_", self.panel.status_label.cget("text"))
        self.assertEqual(self.plots.data_file.source.suffix, ".spe")
        # The stand-in shows the 2255 K lamp; with the dark level removed it fits as the lamp.
        for result in (self.plots.left_result, self.plots.right_result):
            self.assertAlmostEqual(result.temperature_kelvin, 2255, delta=3)
        self.panel.reference_temperature.set("2255")
        self.panel.side_buttons["right"].invoke()
        self.panel.collect_flatfield_button.invoke()
        self.wait()
        flatfield = self.panel.flatfield_paths["right"]
        self.assertEqual(flatfield.suffix, ".spe")
        selection = self.view.CalibrationFileSelect
        self.assertEqual(selection.right_file_location.get("1.0", tk.END).strip(), str(flatfield))
        self.assertEqual(self.plots.calibration_needs_background, {"left": False, "right": True})
        self.assertAlmostEqual(self.plots.right_result.temperature_kelvin, 2255, delta=1)
        self.assertEqual(len(list(self.folder.glob("*.spe"))), 3)

    def test_reference_and_experiment_controls(self):
        other = spe.write_spe(self.folder / "other.spe", np.zeros((70, 1340), dtype=np.uint16),
                              spe.read_reference(LEFT).sensor_wavelengths_nm, BANDS, (1340, 400), 1.0)
        with patch("laser_heating.ui.camera.filedialog.askopenfilename", return_value=str(other)):
            self.panel.reference_button.invoke()
        self.wait()
        self.assertEqual(self.panel.experiment_label.cget("text"), "Ref: other.spe")
        self.assertEqual(self.panel.status_label.cget("text"), "Wavelengths from other.spe")
        with patch("laser_heating.ui.camera.filedialog.askopenfilename", return_value=str(self.folder / "none.spe")):
            self.panel.reference_button.invoke()
        self.wait()
        self.assertIn("cannot be used as a wavelength reference", self.panel.status_label.cget("text"))
        self.assertEqual(self.panel.experiment_label.cget("text"), "Ref: other.spe")

        experiment = self.folder / "Heating.lfe"
        experiment.write_text(LFE.format(selection="CustomRegions"), encoding="utf-8")
        with patch("laser_heating.ui.camera.filedialog.askopenfilename", return_value=str(experiment)):
            self.panel.load_experiment_button.invoke()
        self.wait()
        self.assertEqual(self.panel.experiment_label.cget("text"), "Ref: other.spe  ·  Exp: Heating")
        self.assertIn("Applied 2 regions, exposure", self.panel.status_label.cget("text"))
        self.assertEqual((self.panel.exposure_value.get(), self.panel.exposure_unit.get()), ("50.00", "ms"))


if __name__ == "__main__":
    unittest.main()
