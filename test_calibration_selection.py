import os
from pathlib import Path
import tempfile
import tkinter as tk
import unittest
from unittest.mock import patch

import hardware_mode
import import_calibration
from acton_pixis import CalibrationFileSelection, TransmissionFilterSelection
from TemperatureFit.SpeFile import SpeFile


class CalibrationPathTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.folder = self.root / '20xMag' / '20xL'
        self.folder.mkdir(parents=True)

    def file(self, name, folder=None):
        path = (folder or self.folder) / name
        path.write_bytes(b'test')
        return path.resolve()

    def resolve(self, name):
        return import_calibration.resolve_calibration_file(name, self.root)

    def test_missing_state_does_not_use_another_filter_or_raw_companion(self):
        self.file('L_2255K_20x_wI_T70T50.spe')
        self.file('L_2255K_20x_wI_T70-raw.spe')
        self.assertIsNone(self.resolve('L_2255K_20x_wI_T70'))
        self.assertIsNone(self.resolve('L_2255K_20x_wI'))
        self.assertIsNone(self.resolve(''))
        self.assertIsNone(self.resolve(None))

    def test_exposure_suffix_selects_processed_file(self):
        self.file('L_2255K_20x_woI_300ms-raw.spe')
        processed = self.file('L_2255K_20x_woI_300ms.spe')
        self.assertEqual(self.resolve('L_2255K_20x_woI'), processed)
        self.file('L_2255K_20x_woI_200ms.spe')
        self.assertIsNone(self.resolve('L_2255K_20x_woI'))

    def test_aliases_extensions_and_preferred_folder(self):
        preferred = self.file('L_2255K_20x_wI_T70T50.spe')
        self.file('L_2255K_20x_wI_T70T50.spe', self.folder.parent)
        self.assertEqual(self.resolve('L_2255K_20x_wI_T7050.spe'), preferred)
        alias = self.file('L_2255K_20x_wI_T7010.spe')
        self.assertEqual(self.resolve('L_2255K_20x_wI_T70T10'), alias)

    def test_misfiled_magnification_is_not_selected(self):
        wrong_folder = self.root / '15xMag'
        wrong_folder.mkdir()
        self.file('L_2255K_20x_woI_300ms.spe', wrong_folder)
        self.assertIsNone(self.resolve('L_2255K_20x_woI'))


class CalibrationGuiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.window = tk.Tk()
        cls.window.withdraw()

    @classmethod
    def tearDownClass(cls):
        cls.window.destroy()

    def setUp(self):
        hardware_mode.configure(debug=True)
        self.addCleanup(hardware_mode.configure)
        # Start with actual calibrations, then use the same callbacks as the UI.
        root = import_calibration.CALIBRATION_ROOT
        self.selection = CalibrationFileSelection(self.window, 0, 0,
            root / '15xMag' / 'L_2255K_15x_wI.spe',
            root / '15xMag' / 'R_2255K_15x_wI.spe', root)
        self.addCleanup(self.selection.destroy)
        self.controls = TransmissionFilterSelection(self.window, 0, 0, 'COM7', 'COM6', self.selection)
        self.addCleanup(self.controls.destroy)

    def test_all_64_states_display_the_correct_available_file(self):
        # Human filter ordering: none, T70, T50, T70+T50, T10,
        # T70+T10, T50+T10, all. Right-board relay ordering is reversed.
        values = {'left': (0, 1, 2, 3, 4, 5, 6, 7),
                  'right': (0, 4, 2, 6, 1, 5, 3, 7)}
        suffixes = ('', '_T70', '_T50', '_T70T50', '_T10', '_T70T10', '_T50T10', '_T70T50T10')
        counts = {}
        opened = set()
        with patch('serial.Serial', side_effect=AssertionError('serial I/O')), \
             patch('socket.socket', side_effect=AssertionError('network I/O')):
            for side in ('left', 'right'):
                available = 0
                for mag in (0, 1):
                    for iris in (1, 0):
                        for index, value in enumerate(values[side]):
                            with self.subTest(side=side, mag=mag, iris=iris, filter=index):
                                getattr(self.controls, f'filter_variable_{side}').set(value)
                                getattr(self.controls, f'iris_variable_{side}').set(iris)
                                getattr(self.controls, f'magnification_variable_{side}').set(mag)
                                self.controls.UpdateFestoStates()
                                displayed = getattr(self.selection, f'{side}_file_location').get('1.0', tk.END).strip()
                                exists = bool(iris or (index == 0 and (mag or side == 'right')))
                                if not exists:
                                    self.assertEqual(displayed, '')
                                    self.assertIn('Missing', getattr(self.selection, f'{side}_status_label').cget('text'))
                                    self.assertFalse(self.selection.has_valid_calibration())
                                    continue
                                available += 1
                                path = Path(displayed)
                                self.assertTrue(path.is_file())
                                self.assertNotIn('-raw', path.name)
                                magnification = '20x' if mag else '15x'
                                self.assertEqual(path.parent.name, magnification + ('L' if side == 'left' else 'R'))
                                expected = f'{side[0].upper()}_2255K_{magnification}_{"wI" if iris else "woI"}{suffixes[index]}'
                                if not iris:
                                    expected += '_200ms' if side == 'right' and not mag else '_300ms'
                                if side == 'right' and not mag and index == 5:
                                    expected = expected.replace('_T70T10', '_T7010')
                                self.assertEqual(path.stem, expected)
                                self.assertIn('OK', getattr(self.selection, f'{side}_status_label').cget('text'))
                                if path not in opened:
                                    data = SpeFile(str(path))
                                    self.assertGreater(data.img.size, 0)
                                    self.assertGreater(len(data.x_calibration), 0)
                                    opened.add(path)
                counts[side] = available
        self.assertEqual(counts, {'left': 17, 'right': 18})
        self.assertEqual(len(opened), 35)

    def test_blank_table_entry_clears_previously_valid_selection(self):
        for side in ('left', 'right'):
            getattr(self.controls, f'magnification_variable_{side}').set(1)
            getattr(self.controls, f'iris_variable_{side}').set(1)
            getattr(self.controls, f'filter_variable_{side}').set(0)
        self.controls.UpdateFestoStates()
        self.assertTrue(self.selection.has_valid_calibration())
        self.controls.iris_variable_left.set(0)
        self.controls.filter_variable_left.set(1)
        self.controls.UpdateFestoStates()
        self.assertEqual(self.selection.left_file_location.get('1.0', tk.END).strip(), '')
        self.assertFalse(self.selection.has_valid_calibration())
        self.controls.iris_variable_left.set(1)
        self.controls.UpdateFestoStates()
        self.assertTrue(self.selection.has_valid_calibration())

    def test_lookup_is_independent_of_working_directory(self):
        previous = Path.cwd()
        with tempfile.TemporaryDirectory() as folder:
            try:
                os.chdir(folder)
                path = self.controls.resolve_calibration_file_path('L_2255K_20x_wI_T7050')
                self.assertTrue(path.is_file())
                self.assertEqual(path.name, 'L_2255K_20x_wI_T70T50.spe')
            finally:
                os.chdir(previous)

    def test_manual_selection_refreshes_missing_status(self):
        left = import_calibration.resolve_calibration_file('L_2255K_15x_wI')
        right = import_calibration.resolve_calibration_file('R_2255K_15x_wI')
        with patch('laser_heating.ui.calibration.filedialog.askopenfilename', return_value=str(left)):
            self.selection.calibration_file_open_dialog(1)
        with patch('laser_heating.ui.calibration.filedialog.askopenfilename', return_value=str(right)):
            self.selection.calibration_file_open_dialog(2)
        self.assertTrue(self.selection.has_valid_calibration())
        self.assertIn('OK', self.selection.left_status_label.cget('text'))
        self.assertIn('OK', self.selection.right_status_label.cget('text'))


if __name__ == '__main__':
    unittest.main()
