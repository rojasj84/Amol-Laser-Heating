"""Exercise real Windows watchdog events and the Tk queue, away from instruments."""
from pathlib import Path
import tempfile
import threading
import time
from types import SimpleNamespace
import tkinter as tk
import unittest
from unittest.mock import patch

from watchdog.events import FileCreatedEvent

from acton_pixis import CalibrationFileSelection, DataFileHandling, PlotGraphs
from import_calibration import CALIBRATION_ROOT
from TemperatureFit.SpeFile import SpeFile
from laser_heating.readers import SpeReader


class AutomaticFittingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.folder = Path(self.temp.name)
        self.root = tk.Tk()
        self.root.withdraw()
        self.errors = []
        self.root.report_callback_exception = lambda exc, value, trace: self.errors.append(value)
        self.left = CALIBRATION_ROOT / '15xMag' / 'L_2255K_15x_wI.spe'
        self.right = CALIBRATION_ROOT / '15xMag' / 'R_2255K_15x_wI.spe'
        self.payload = self.left.read_bytes()
        self.calibration = CalibrationFileSelection(self.root, 0, 0, self.left, self.right, self.folder)
        self.fits = []
        self.plots = SimpleNamespace(update_graphs=self.record_fit, set_capture=self.set_capture, load_capture=SpeReader().read, file_extensions=(".spe",))
        self.panel = DataFileHandling(self.root, self.plots, self.calibration, 0, 0, self.folder)
        self.panel.AUTOFIT_POLL_MS = 40
        self.panel.AUTOFIT_SETTLE_SECONDS = 0.08
        self.panel.AUTOFIT_MAX_READ_RETRIES = 2
        self.observers = []
        self.gui_thread = threading.get_ident()

    def tearDown(self):
        if self.panel.winfo_exists():
            self.panel.stop_automatic_fitting()
        for observer in self.observers:
            observer.stop()
            observer.join(timeout=2)
            self.assertFalse(observer.is_alive())
        self.root.destroy()
        self.temp.cleanup()
        self.assertEqual(self.errors, [])

    def set_capture(self, measurement, left, right, left_temperature, right_temperature):
        self.plots.data_file = measurement
        self.plots.left_calibration_file, self.plots.right_calibration_file = left, right
        self.plots.left_calibration_temperature, self.plots.right_calibration_temperature = left_temperature, right_temperature
        self.plots.current_frame_index = 0
        self.plots.update_graphs()

    def record_fit(self):
        self.assertEqual(threading.get_ident(), self.gui_thread)
        self.fits.append(Path(self.plots.data_file.source).name)

    def start(self):
        self.panel.automatic_fitting_button_state.set(1)
        self.panel.automatic_file_fitting()
        if self.panel.my_observer is not None:
            self.observers.append(self.panel.my_observer)

    def wait(self, condition, timeout=3):
        end = time.monotonic() + timeout
        while time.monotonic() < end:
            self.root.update()
            if condition():
                return
            time.sleep(0.01)
        self.fail('Timed out waiting for the watcher: ' + str(self.fits))

    def pump(self, seconds):
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            self.root.update()
            time.sleep(0.01)

    def test_complete_file_is_fitted_once_on_gui_thread(self):
        (self.folder / 'existing.spe').write_bytes(self.payload)
        self.start()
        path = self.folder / 'new.spe'
        path.write_bytes(self.payload)
        for _ in range(5):
            self.panel.file_created(FileCreatedEvent(str(path)))
        self.wait(lambda: 'new.spe' in self.fits)
        self.pump(0.2)
        self.assertEqual(self.fits, ['new.spe'])
        self.assertEqual(self.panel.selected_lightfield_spectra.get('1.0', tk.END).strip(), str(path))

    def test_renamed_uppercase_spe_in_subfolder_is_fitted(self):
        subfolder = self.folder / 'nested'
        subfolder.mkdir()
        self.start()
        staging = subfolder / 'capture.tmp'
        staging.write_bytes(self.payload)
        staging.rename(subfolder / 'capture.SPE')
        self.wait(lambda: self.fits == ['capture.SPE'])

    def test_slow_file_recovers_after_retry_limit_and_seven_second_pause(self):
        self.start()
        path = self.folder / 'slow.spe'
        path.write_bytes(self.payload[:100])
        self.wait(lambda: str(path) in self.panel._failed_spe_files)
        self.pump(7.1)
        self.assertEqual(self.fits, [])
        path.write_bytes(self.payload)
        self.wait(lambda: self.fits == ['slow.spe'])
        self.assertNotIn(str(path), self.panel._failed_spe_files)

    def test_continuously_growing_file_waits_for_readiness(self):
        self.start()
        path = self.folder / 'growing.spe'
        with path.open('wb') as file:
            for chunk in (self.payload[:100], self.payload[100:10000], self.payload[10000:]):
                file.write(chunk)
                file.flush()
                self.pump(0.05)
                self.assertEqual(self.fits, [])
        self.wait(lambda: self.fits == ['growing.spe'])

    def test_burst_and_fallback_scan_do_not_lose_files(self):
        self.start()
        # Suppress events to exercise the reconciliation scan independently.
        with patch.object(self.panel, 'file_created'):
            for index in range(3):
                (self.folder / f'burst{index}.spe').write_bytes(self.payload)
            self.wait(lambda: len(self.fits) == 3)
        self.assertEqual(set(self.fits), {'burst0.spe', 'burst1.spe', 'burst2.spe'})

    def test_stop_is_immediate_and_restart_leaves_only_one_observer(self):
        self.start()
        previous_generation = self.panel._watch_generation
        first = self.panel.my_observer
        self.panel.automatic_fitting_button_state.set(0)
        self.panel.automatic_file_fitting()
        self.assertFalse(first.is_alive())
        self.assertIsNone(self.panel._autofit_after_id)
        (self.folder / 'while_stopped.spe').write_bytes(self.payload)
        self.pump(0.15)
        self.assertEqual(self.fits, [])
        self.start()
        self.panel.file_created(FileCreatedEvent(str(self.folder / 'old_session.spe')), previous_generation)
        self.pump(0.1)
        self.assertNotIn(str(self.folder / 'old_session.spe'), self.panel._pending_spe_files)
        self.assertEqual(sum(observer.is_alive() for observer in self.observers), 1)
        (self.folder / 'after_restart.spe').write_bytes(self.payload)
        self.wait(lambda: self.fits == ['after_restart.spe'])

    def test_invalid_folder_does_not_leave_automatic_mode_enabled(self):
        self.panel.selected_folder_to_save_tfit.delete('1.0', tk.END)
        self.panel.selected_folder_to_save_tfit.insert(tk.END, str(self.folder / 'absent'))
        self.start()
        self.assertEqual(self.panel.automatic_fitting_button_state.get(), 0)
        self.assertIsNone(self.panel.my_observer)
        self.assertIsNone(self.panel._autofit_after_id)

    def test_folder_dialog_switches_the_active_watch(self):
        self.start()
        old = self.panel.my_observer
        new_folder = self.folder / 'other'
        new_folder.mkdir()
        with patch('laser_heating.ui.files.filedialog.askdirectory', return_value=str(new_folder)):
            self.panel.data_file_open_dialog(2)
        self.observers.append(self.panel.my_observer)
        self.assertFalse(old.is_alive())
        self.assertEqual(self.panel.folder_path, str(new_folder))
        (self.folder / 'outside.spe').write_bytes(self.payload)
        (new_folder / 'inside.spe').write_bytes(self.payload)
        self.wait(lambda: self.fits == ['inside.spe'])

    def test_destroy_stops_observer_and_cancels_timer(self):
        self.start()
        observer = self.panel.my_observer
        self.panel.destroy()
        self.assertFalse(observer.is_alive())
        self.pump(0.15)

    def test_missing_calibration_skips_fit_with_visible_status(self):
        self.calibration.update_left_calibration_file(None)
        self.start()
        path = self.folder / 'no_calibration.spe'
        path.write_bytes(self.payload)
        self.wait(lambda: str(path) in self.panel._processed_spe_files)
        self.assertEqual(self.fits, [])
        self.assertIn('calibration missing', self.panel.autofit_status.cget('text'))

    def test_reader_closes_handle_when_partial_file_read_fails(self):
        path = self.folder / 'partial.spe'
        path.write_bytes(self.payload[:100])
        real_open = open
        handles = []

        def tracked_open(*args, **kwargs):
            handle = real_open(*args, **kwargs)
            handles.append(handle)
            return handle

        with patch('builtins.open', side_effect=tracked_open):
            with self.assertRaises(Exception):
                SpeFile(path)
        self.assertTrue(handles)
        self.assertTrue(all(handle.closed for handle in handles))

    def test_new_file_runs_actual_temperature_fit_and_redraw(self):
        self.plots = PlotGraphs(self.root, 0, 0, str(self.left), str(self.right), str(self.left))
        self.panel.plots = self.plots
        widget_count = len(self.plots.winfo_children())
        canvas = self.plots.graph_canvas
        original_update = self.plots.update_graphs

        def fitted_update():
            original_update()
            self.record_fit()

        self.plots.update_graphs = fitted_update
        self.start()
        (self.folder / 'actual_fit.spe').write_bytes(self.payload)
        self.wait(lambda: self.fits == ['actual_fit.spe'])
        self.assertIn('T=', self.plots.left_temperature_label.cget('text'))
        self.assertIn('T=', self.plots.right_temperature_label.cget('text'))
        (self.folder / 'second_fit.spe').write_bytes(self.payload)
        self.wait(lambda: self.fits == ['actual_fit.spe', 'second_fit.spe'])
        self.assertIs(self.plots.graph_canvas, canvas)
        self.assertEqual(len(self.plots.winfo_children()), widget_count)

    def test_failed_observer_start_resets_checkbox_and_timer(self):
        with patch('laser_heating.ui.files.Observer') as factory:
            factory.return_value.start.side_effect = OSError('cannot watch folder')
            self.start()
        self.assertEqual(self.panel.automatic_fitting_button_state.get(), 0)
        self.assertIsNone(self.panel.my_observer)
        self.assertIsNone(self.panel._autofit_after_id)
        self.assertIn('Could not watch', self.panel.autofit_status.cget('text'))


if __name__ == '__main__':
    unittest.main()
