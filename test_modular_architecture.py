"""Camera-independent analysis and its integration with the existing application."""
from dataclasses import replace
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import tkinter as tk
import unittest
from unittest.mock import patch

import numpy as np
from matplotlib import pyplot as plt

import hardware_mode
from laser_heating.analysis import extract_spectrum, fit_temperature
from laser_heating.application import HeatingApplication
from laser_heating.config import APP_ROOT, ApplicationConfig, CalibrationSettings, CameraProfile
from laser_heating.models import CameraData, RegionOfInterest
from laser_heating.readers import ReaderRegistry, SpeReader
from laser_heating.ui.roi import ROISelectionWindow
from TemperatureFit.SpeFile import SpeFile
from TemperatureFit.TemperatureFitting import Temperature_Measurement


class AnalysisTests(unittest.TestCase):
    def setUp(self):
        self.wavelengths = np.linspace(500, 900, 96)
        self.capture = CameraData(np.arange(2*20*96).reshape(2, 20, 96), self.wavelengths, Path('camera.npz'))
        self.roi = RegionOfInterest(2, 94, 3, 9)

    def test_roi_extracts_selected_frame_and_exclusive_bounds(self):
        spectrum = extract_spectrum(self.capture, self.roi, 1)
        np.testing.assert_array_equal(spectrum.counts, self.capture.frames[1, 3:9, 2:94].sum(axis=0))
        np.testing.assert_array_equal(spectrum.wavelengths_nm, self.wavelengths[2:94])

    def test_invalid_roi_is_rejected_instead_of_silently_clipped(self):
        for roi in (RegionOfInterest(-1, 4, 0, 3), RegionOfInterest(0, 97, 0, 3),
                    RegionOfInterest(4, 4, 0, 3), RegionOfInterest(0, 4, 0, 21),
                    RegionOfInterest(0, 4, 5, 2), RegionOfInterest(0.5, 4, 0, 3)):
            with self.subTest(roi=roi), self.assertRaises(ValueError):
                extract_spectrum(self.capture, roi)

    def test_frame_index_validation(self):
        for index in (-1, 2, 0.5, True):
            with self.subTest(index=index), self.assertRaises(ValueError):
                self.capture.frame(index)

    def test_single_frame_is_normalized(self):
        data = CameraData(np.ones((20, 96)), self.wavelengths, 'single.npz')
        self.assertEqual(data.frames.shape, (1, 20, 96))
        self.assertEqual((data.frame_count, data.width, data.height), (1, 96, 20))

    def test_invalid_camera_data_is_rejected(self):
        for frames, wavelengths in ((np.ones((20, 96)), self.wavelengths[:-1]),
                                    (np.ones((0, 20, 96)), self.wavelengths),
                                    (np.ones(96), self.wavelengths),
                                    (np.full((20, 96), 'x'), self.wavelengths),
                                    (np.ones((20, 96), dtype=complex), self.wavelengths),
                                    (np.ones((20, 96)), self.wavelengths[::-1]),
                                    (np.ones((20, 96)), np.full(96, np.nan))):
            with self.subTest(shape=frames.shape), self.assertRaises(ValueError):
                CameraData(frames, wavelengths, 'invalid.npz')

    def test_mismatched_calibration_grid_is_rejected(self):
        calibration = CameraData(self.capture.frames, self.wavelengths+0.5, 'calibration.npz')
        with self.assertRaisesRegex(ValueError, 'wavelength grids differ'):
            fit_temperature(self.capture, calibration, self.roi, 2255)

    def test_invalid_calibration_temperature_is_rejected(self):
        for temperature in (0, -1, np.nan, np.inf):
            with self.subTest(temperature=temperature), self.assertRaises(ValueError):
                fit_temperature(self.capture, self.capture, self.roi, temperature)

    def test_existing_left_and_right_fit_results_match_original_equations(self):
        settings = CalibrationSettings()
        measurement = SpeReader().read(settings.right_file)
        old_measurement = SpeFile(str(settings.right_file))
        profile = CameraProfile()
        for file, roi in ((settings.left_file, profile.left_roi), (settings.right_file, profile.right_roi)):
            calibration = SpeReader().read(file)
            old_calibration = SpeFile(str(file))
            old_fit = Temperature_Measurement(1500, 0.5, 2255,
                old_measurement.x_calibration[roi.x_start:roi.x_end],
                np.sum(old_calibration.img[roi.y_start:roi.y_end, roi.x_start:roi.x_end], axis=0),
                np.sum(old_measurement.img[roi.y_start:roi.y_end, roi.x_start:roi.x_end], axis=0))
            new_fit = fit_temperature(measurement, calibration, roi, 2255)
            np.testing.assert_allclose([new_fit.temperature_kelvin, new_fit.uncertainty_kelvin, new_fit.emissivity],
                                       [old_fit.fit_T, old_fit.sigT, old_fit.fit_Eps], rtol=1e-12, atol=1e-12)
            np.testing.assert_allclose(new_fit.corrected_counts, old_fit.unknown_graybody_spectrum, rtol=1e-12)
            np.testing.assert_allclose(new_fit.fitted_counts, old_fit.gray_body_spectrum, rtol=1e-12)

    def test_analysis_import_does_not_load_gui_or_hardware(self):
        code = "import sys; import laser_heating.analysis; assert not any(name in sys.modules for name in ('tkinter', 'matplotlib', 'serial', 'hardware_mode'))"
        result = subprocess.run([sys.executable, '-B', '-c', code], cwd=APP_ROOT, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)


class ReaderAndConfigTests(unittest.TestCase):
    def test_spe_single_and_multi_frame_formats_are_normalized(self):
        single = SpeReader().read(CalibrationSettings().left_file)
        multi = SpeReader().read(APP_ROOT / 'T-rax-develop/tests/test_files/temperature_fitting/test_measurement_multiple.spe')
        self.assertEqual(single.frames.shape, (1, 70, 1340))
        self.assertEqual(multi.frames.shape, (10, 255, 1024))
        self.assertEqual(multi.wavelengths_nm.shape, (1024,))

    def test_npz_reader_and_optional_exposure(self):
        with tempfile.TemporaryDirectory() as directory:
            file = Path(directory) / 'capture.npz'
            frames, wavelengths = np.ones((2, 20, 96)), np.linspace(500, 900, 96)
            np.savez(file, frames=frames, wavelengths_nm=wavelengths, exposure_seconds=0.1)
            data = ReaderRegistry.defaults().read(file, 'npz')
            self.assertEqual(data.exposure_seconds, 0.1)
            np.testing.assert_array_equal(data.frames, frames)
            np.savez(file, frames=frames[0], wavelengths_nm=wavelengths)
            self.assertIsNone(ReaderRegistry.defaults().read(file, 'npz').exposure_seconds)

    def test_custom_reader_does_not_need_plot_or_fit_changes(self):
        class VendorReader:
            extensions = ('.vendor',)
            def read(self, path):
                return CameraData(np.ones((20, 96)), np.linspace(500, 900, 96), path)
        registry = ReaderRegistry()
        registry.register('vendor', VendorReader())
        data = registry.read('new-camera.vendor', 'vendor')
        self.assertEqual(extract_spectrum(data, RegionOfInterest(0, 96, 0, 10)).counts[0], 10)
        with self.assertRaises(ValueError):
            registry.register('vendor', VendorReader())
        with self.assertRaises(ValueError):
            registry.read('wrong.spe', 'vendor')
        with self.assertRaises(ValueError):
            registry.get('unknown')

    def test_default_json_matches_current_instrument_configuration(self):
        configured = ApplicationConfig.load(APP_ROOT / 'config/default.json')
        self.assertEqual(configured.camera, CameraProfile())
        self.assertEqual(configured.calibration, CalibrationSettings())
        self.assertEqual(configured.acquisition_folder, APP_ROOT / 'TemperatureFit')

    def test_config_paths_are_relative_to_json_instead_of_working_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'profile.json'
            path.write_text(json.dumps({'schema_version': 1, 'acquisition_folder': 'captures',
                'calibration': {'left_file': 'calibration/left.npz', 'use_filter_table': False},
                'initial_measurement': 'captures/initial.npz'}), encoding='utf-8')
            config = ApplicationConfig.load(path)
            self.assertEqual(config.acquisition_folder, path.parent / 'captures')
            self.assertEqual(config.calibration.left_file, path.parent / 'calibration/left.npz')
            self.assertEqual(config.initial_measurement, path.parent / 'captures/initial.npz')

    def test_profile_rejects_wrong_image_size_and_bad_roi(self):
        profile = CameraProfile()
        with self.assertRaisesRegex(ValueError, 'expects 1340x70'):
            profile.validate_data(CameraData(np.ones((20, 96)), np.linspace(500, 900, 96), 'other.npz'))
        with self.assertRaises(ValueError):
            replace(profile, width=96)
        with self.assertRaises(ValueError):
            replace(profile, height=0)

    def test_config_rejects_bad_schema_and_calibration_settings(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'profile.json'
            for raw in ([], {'schema_version': 2}, {'schema_version': 1, 'calibration': {'temperature_kelvin': -3}},
                        {'schema_version': 1, 'calibration': {'use_filter_table': 'false'}}):
                path.write_text(json.dumps(raw), encoding='utf-8')
                with self.subTest(raw=raw), self.assertRaises(ValueError):
                    ApplicationConfig.load(path)


class GenericCameraApplicationTests(unittest.TestCase):
    """Exercise a different camera through the real GUI and real folder watcher."""
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.folder = Path(self.temp.name)
        self.wavelengths = np.linspace(500, 900, 96)
        self.base = Temperature_Measurement.f_Planck(None, self.wavelengths, 2100, 1)
        self.base = self.base / self.base.max() * 2000 + 20
        self.image = np.broadcast_to(self.base, (20, 96)).copy()
        self.left = self.folder / 'left.npz'
        self.right = self.folder / 'right.npz'
        self.initial = self.folder / 'initial.npz'
        for file in (self.left, self.right):
            np.savez(file, frames=self.image, wavelengths_nm=self.wavelengths)
        ratio = (Temperature_Measurement.f_Planck(None, self.wavelengths, 2300, 1) /
                 Temperature_Measurement.f_Planck(None, self.wavelengths, 2100, 1))
        np.savez(self.initial, frames=np.stack((self.image, self.image*ratio)), wavelengths_nm=self.wavelengths)
        self.profile = CameraProfile('Generic test camera', 'npz', 96, 20,
                                     RegionOfInterest(1, 95, 0, 9), RegionOfInterest(1, 95, 10, 20))
        self.config = ApplicationConfig(camera=self.profile, calibration=CalibrationSettings(
            left_file=self.left, right_file=self.right, temperature_kelvin=2100, use_filter_table=False),
            acquisition_folder=self.folder, initial_measurement=self.initial)
        hardware_mode.configure(debug=True)
        self.patches = [patch('serial.Serial', side_effect=AssertionError('Serial I/O in debug')),
                        patch('socket.socket', side_effect=AssertionError('Network I/O in debug')),
                        patch('serial.tools.list_ports.comports', side_effect=AssertionError('Port scan in debug'))]
        for mock in self.patches:
            mock.start()
        self.root = tk.Tk()
        self.root.withdraw()
        self.errors = []
        self.root.report_callback_exception = lambda exc, error, trace: self.errors.append(error)
        self.app = HeatingApplication(self.root, self.config)
        for window in self.app.windows.values():
            window.withdraw()
        self.plots = self.app.temperature.Temperature_graphs
        self.panel = self.app.temperature.DataFileSelect
        self.panel.AUTOFIT_POLL_MS = 40
        self.panel.AUTOFIT_SETTLE_SECONDS = 0.08

    def tearDown(self):
        self.root.destroy()
        for mock in reversed(self.patches):
            mock.stop()
        self.temp.cleanup()
        self.assertEqual(self.errors, [])

    def test_generic_camera_profile_and_custom_temperature_fit_on_startup(self):
        self.assertEqual(self.plots.data_file.frames.shape, (2, 20, 96))
        self.assertEqual(self.plots.file_extensions, ('.npz',))
        self.assertAlmostEqual(self.plots.left_result.temperature_kelvin, 2100, places=4)
        self.assertAlmostEqual(self.plots.right_result.temperature_kelvin, 2100, places=4)
        selection = self.app.temperature.CalibrationFileSelect
        self.assertEqual(selection.left_file_location.get('1.0', tk.END).strip(), str(self.left))
        self.assertIn('OK', selection.left_status_label.cget('text'))
        self.app.temperature.TransmissionFilter.left_700_filter_selection.invoke()
        self.assertEqual(selection.left_file_location.get('1.0', tk.END).strip(), str(self.left))

    def test_multiframe_navigation_uses_new_camera_and_keeps_one_canvas(self):
        canvas = self.plots.graph_canvas
        self.plots.next_frame()
        self.assertEqual(self.plots.current_frame_index, 1)
        self.assertAlmostEqual(self.plots.left_result.temperature_kelvin, 2300, places=4)
        self.assertEqual(self.plots.frame_status_label.cget('text'), 'Frame: 2 / 2')
        self.plots.next_frame()
        self.assertEqual(self.plots.current_frame_index, 1)
        self.plots.prev_frame()
        self.assertAlmostEqual(self.plots.left_result.temperature_kelvin, 2100, places=4)
        self.assertIs(self.plots.graph_canvas, canvas)

    def test_navigation_and_readouts_do_not_overlap_or_clip_the_plot(self):
        from tkinter import font as tkfont

        def bounds_in_plot(widget):
            x, y = 0, 0
            current = widget
            while current is not self.plots:
                x += current.winfo_x()
                y += current.winfo_y()
                current = current.master
            return x, y, x+widget.winfo_width(), y+widget.winfo_height()

        for frame in (0, 1):
            self.plots.current_frame_index = frame
            self.plots.update_graphs()
            self.root.update_idletasks()
            canvas = self.plots.graph_canvas.get_tk_widget()
            _, canvas_top, _, _ = bounds_in_plot(canvas)
            for name in ("left_temperature_label", "right_temperature_label",
                         "frame_status_label", "btn_prev_frame", "btn_next_frame"):
                widget = getattr(self.plots, name)
                self.assertLessEqual(bounds_in_plot(widget)[3], canvas_top, name)
                font = tkfont.Font(root=widget, font=widget.cget("font"))
                self.assertLessEqual(font.measure(widget.cget("text")), widget.winfo_width(), name)

    def test_automatic_mode_fits_new_generic_camera_file(self):
        self.panel.automatic_fitting_button_state.set(1)
        self.panel.automatic_file_fitting()
        path = self.folder / 'new-camera.npz'
        np.savez(path, frames=self.image*1.5, wavelengths_nm=self.wavelengths)
        end = time.monotonic()+5
        while time.monotonic() < end:
            self.root.update()
            if self.plots.data_file.source == path:
                break
            time.sleep(0.01)
        self.assertEqual(self.plots.data_file.source, path)
        self.assertAlmostEqual(self.plots.right_result.temperature_kelvin, 2100, places=4)
        self.assertEqual(self.plots.data_file.frame_count, 1)
        self.panel.stop_automatic_fitting()

    def test_invalid_manual_capture_keeps_previous_result(self):
        previous_data, previous_result = self.plots.data_file, self.plots.left_result
        path = self.folder / 'wrong-grid.npz'
        np.savez(path, frames=self.image, wavelengths_nm=self.wavelengths+2)
        with patch('laser_heating.ui.files.filedialog.askopenfilename', return_value=str(path)):
            self.panel.data_file_open_dialog(1)
        self.assertIs(self.plots.data_file, previous_data)
        self.assertIs(self.plots.left_result, previous_result)
        self.assertIn('wavelength grids differ', self.panel.autofit_status.cget('text'))

    def test_roi_editor_limits_and_invalid_application_use_real_dimensions(self):
        editor = ROISelectionWindow(self.root, self.plots)
        editor.withdraw()
        self.assertEqual((editor.image_width, editor.image_height), (96, 20))
        original = self.plots.left_roi
        editor.left_x_end_var.set('97')
        editor.apply_and_close()
        self.assertTrue(editor.winfo_exists())
        self.assertEqual(self.plots.left_roi, original)
        self.assertIn('96-pixel', editor.error_label.cget('text'))
        editor.left_x_end_var.set('90')
        editor.apply_and_close()
        self.assertFalse(editor.winfo_exists())
        self.assertEqual(self.plots.left_roi.x_end, 90)

    def test_roi_config_from_another_camera_is_rejected(self):
        editor = ROISelectionWindow(self.root, self.plots)
        editor.withdraw()
        path = self.folder / 'other-roi.json'
        path.write_text(json.dumps({'camera_width': 1340, 'camera_height': 70}), encoding='utf-8')
        with patch('laser_heating.ui.roi.filedialog.askopenfilename', return_value=str(path)):
            editor.load_config()
        self.assertIn('different camera image size', editor.error_label.cget('text'))
        editor.destroy()

    def test_connection_changes_update_filters_and_all_motor_widgets(self):
        settings = replace(self.config.hardware, agilis_port='COM25', left_relay_port='COM26',
                           right_relay_port='COM27', left_laser_ip='10.0.0.1', right_laser_ip='10.0.0.2')
        self.app.set_connections(settings)
        filters = self.app.temperature.TransmissionFilter
        self.assertEqual((filters.left_denkovi_com_port, filters.right_denkovi_com_port), ('COM26', 'COM27'))
        relays = self.app.panels['festo']
        self.assertEqual(relays.LeftSideControls.left_side_comport, 'COM26')
        self.assertEqual(relays.RightSideControls.right_side_comport, 'COM27')
        motors = self.app.panels['piezo']
        axes = []
        def collect(widget):
            if type(widget).__name__ == 'AxisControl':
                axes.append(widget)
            for child in widget.winfo_children():
                collect(child)
        collect(motors)
        self.assertEqual(len(axes), 12)
        self.assertTrue(all(axis.agilis_comport == 'COM25' for axis in axes))
        self.assertEqual((motors.left_laser_ip, motors.right_laser_ip), ('10.0.0.1', '10.0.0.2'))
        self.app.open_window('connections').withdraw()
        self.app.open_window('laser').withdraw()
        self.app.set_connections(replace(settings, left_laser_ip='10.0.0.3'))
        self.app.windows['laser'].withdraw()

    def test_window_reopening_uses_current_configuration_and_figures_close(self):
        first = self.app.windows['piezo']
        first.destroy()
        settings = replace(self.config.hardware, agilis_port='COM25')
        self.app.set_connections(settings)
        second = self.app.open_window('piezo')
        second.withdraw()
        self.assertIsNot(first, second)
        self.assertEqual(self.app.panels['piezo'].agilis_comport, 'COM25')
        figure_number = self.plots.fig.number
        self.app.temperature.destroy()
        self.assertNotIn(figure_number, plt.get_fignums())


if __name__ == '__main__':
    unittest.main()
