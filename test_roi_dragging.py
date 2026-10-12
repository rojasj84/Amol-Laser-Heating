"""Exercise the actual ROI editor's matplotlib mouse event bindings."""
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import tkinter as tk
import unittest
from unittest.mock import Mock, patch

from matplotlib.backend_bases import MouseEvent
import numpy as np

from laser_heating.models import CameraData, RegionOfInterest
from laser_heating.ui.roi import ROISelectionWindow


class ROIMouseEditingTests(unittest.TestCase):
    def setUp(self):
        self.root = tk.Tk()
        self.root.withdraw()
        self.errors = []
        self.root.report_callback_exception = lambda exc, value, trace: self.errors.append(value)
        self.plots = SimpleNamespace(data_file=CameraData(np.ones((20, 96)), np.linspace(500, 900, 96), 'test.npz'),
                                     current_frame_index=0, left_roi=RegionOfInterest(10, 80, 2, 9),
                                     right_roi=RegionOfInterest(10, 80, 12, 19), update_graphs=Mock())
        self.editor = ROISelectionWindow(self.root, self.plots)
        self.editor.withdraw()
        self.editor.canvas.draw()
        self.dragger = self.editor.drag_controller

    def tearDown(self):
        self.root.destroy()
        self.assertEqual(self.errors, [])

    def event(self, name, x, y, button=None, screen_offset=(0, 0)):
        screen = self.editor.ax.transData.transform((x, y)) + screen_offset
        event = MouseEvent(name, self.editor.canvas, *screen, button=button)
        self.editor.canvas.callbacks.process(name, event)
        return event

    def drag(self, origin, end, button=1, screen_offset=(0, 0)):
        self.event('button_press_event', *origin, button=button, screen_offset=screen_offset)
        self.event('motion_notify_event', *end, button=button, screen_offset=screen_offset)
        self.event('button_release_event', *end, button=button, screen_offset=screen_offset)

    def test_all_four_corner_handles_resize_correct_fields(self):
        cases = (((10, 2), (14, 3), RegionOfInterest(14, 80, 3, 9)),
                 ((80, 2), (86, 1), RegionOfInterest(10, 86, 1, 9)),
                 ((80, 9), (86, 10), RegionOfInterest(10, 86, 2, 10)),
                 ((10, 9), (14, 10), RegionOfInterest(14, 80, 2, 10)))
        for origin, end, expected in cases:
            with self.subTest(origin=origin):
                self.editor._on_roi_drag('left', RegionOfInterest(10, 80, 2, 9))
                self.drag(origin, end)
                self.assertEqual(self.editor._roi_from_fields('left'), expected)
                self.assertEqual(self.dragger.rois['left'], expected)
        self.plots.update_graphs.assert_not_called()

    def test_edge_drag_changes_one_bound_without_changing_other_axis(self):
        # Pick away from the midpoint handle to exercise the edge hit test.
        self.drag((30, 9), (30, 11))
        self.assertEqual(self.editor._roi_from_fields('left'), RegionOfInterest(10, 80, 2, 11))
        self.drag((80, 6), (90, 6))
        self.assertEqual(self.editor._roi_from_fields('left'), RegionOfInterest(10, 90, 2, 11))

    def test_right_rectangle_drag_does_not_change_left(self):
        left = self.editor._roi_from_fields('left')
        self.drag((80, 12), (88, 11))
        self.assertEqual(self.editor._roi_from_fields('right'), RegionOfInterest(10, 88, 11, 19))
        self.assertEqual(self.editor._roi_from_fields('left'), left)
        self.assertEqual(self.dragger.active_side, 'right')

    def test_drag_inside_moves_rectangle_and_preserves_size(self):
        self.drag((30, 5), (35, 7))
        self.assertEqual(self.editor._roi_from_fields('left'), RegionOfInterest(15, 85, 4, 11))

    def test_drag_beyond_image_clamps_resize_and_move(self):
        self.drag((80, 9), (200, 40))
        self.assertEqual(self.editor._roi_from_fields('left'), RegionOfInterest(10, 96, 2, 20))
        self.editor._on_roi_drag('left', RegionOfInterest(10, 80, 2, 9))
        self.drag((30, 5), (-100, -50))
        self.assertEqual(self.editor._roi_from_fields('left'), RegionOfInterest(0, 70, 0, 7))
        self.drag((30, 3), (200, 50))
        self.assertEqual(self.editor._roi_from_fields('left'), RegionOfInterest(26, 96, 13, 20))

    def test_crossing_opposite_corner_keeps_at_least_one_pixel(self):
        self.drag((10, 2), (100, 15))
        roi = self.editor._roi_from_fields('left')
        self.assertEqual(roi, RegionOfInterest(79, 80, 8, 9))
        roi.validate(96, 20)

    def test_picking_near_handle_does_not_jump_rectangle(self):
        original = self.editor._roi_from_fields('left')
        # Handle pick tolerance uses display pixels rather than camera pixels.
        self.event('button_press_event', 10, 2, button=1, screen_offset=(-4, 4))
        self.event('motion_notify_event', 10, 2, button=1, screen_offset=(-4, 4))
        self.assertEqual(self.editor._roi_from_fields('left'), original)
        self.event('motion_notify_event', 15, 3, button=1, screen_offset=(-4, 4))
        self.event('button_release_event', 15, 3, button=1)
        self.assertEqual(self.editor._roi_from_fields('left'), RegionOfInterest(15, 80, 3, 9))

    def test_mouse_release_outside_axes_ends_drag(self):
        self.event('button_press_event', 80, 9, button=1)
        self.event('motion_notify_event', 200, 40, button=1)
        self.event('button_release_event', 200, 40, button=1)
        before = self.editor._roi_from_fields('left')
        self.event('motion_notify_event', 40, 5)
        self.assertEqual(self.editor._roi_from_fields('left'), before)
        self.assertIsNone(self.dragger._drag)

    def test_hover_feedback_and_exit_reset(self):
        self.event('motion_notify_event', 10, 2)
        self.assertEqual(self.editor.canvas.get_tk_widget().cget('cursor'), 'top_left_corner')
        self.assertIn('Left ROI', self.editor.mouse_hint.cget('text'))
        self.event('motion_notify_event', 30, 5)
        self.assertEqual(self.editor.canvas.get_tk_widget().cget('cursor'), 'fleur')
        self.event('motion_notify_event', -20, -5)
        self.assertEqual(self.editor.canvas.get_tk_widget().cget('cursor'), 'arrow')

    def test_numeric_edits_update_handles_and_invalid_text_is_ignored(self):
        self.editor.left_x_start_var.set('15')
        self.assertEqual(self.dragger.rois['left'].x_start, 15)
        self.assertEqual(self.dragger.handles['left'].get_xdata()[0], 15)
        self.editor.left_x_start_var.set('')
        self.assertNotIn('left', self.dragger.rois)
        self.assertFalse(self.editor.left_rect.get_visible())
        self.editor.left_x_start_var.set('15')
        self.assertTrue(self.editor.left_rect.get_visible())

    def test_selected_side_can_be_dragged_when_rectangles_overlap(self):
        self.editor._on_roi_drag('right', self.editor._roi_from_fields('left'))
        self.dragger.select_side('right')
        self.drag((80, 9), (86, 10))
        self.assertEqual(self.editor._roi_from_fields('right'), RegionOfInterest(10, 86, 2, 10))
        self.assertEqual(self.editor._roi_from_fields('left'), RegionOfInterest(10, 80, 2, 9))

    def test_click_outside_and_right_button_leave_rois_unchanged(self):
        original = dict(self.dragger.rois)
        self.drag((10, 2), (20, 5), button=3)
        self.drag((2, 10), (7, 11))
        self.assertEqual(self.dragger.rois, original)

    def test_changes_are_previewed_then_applied_once(self):
        original = self.plots.left_roi
        self.drag((80, 9), (86, 10))
        self.assertEqual(self.plots.left_roi, original)
        self.plots.update_graphs.assert_not_called()
        self.editor.apply_and_close()
        self.assertEqual(self.plots.left_roi, RegionOfInterest(10, 86, 2, 10))
        self.plots.update_graphs.assert_called_once_with()

    def test_cancel_discards_preview_and_disconnects_events(self):
        original = self.plots.left_roi
        self.drag((80, 9), (86, 10))
        self.editor.destroy()
        self.assertEqual(self.plots.left_roi, original)
        self.assertEqual(self.dragger._connections, [])
        self.plots.update_graphs.assert_not_called()

    def test_mouse_edited_bounds_are_saved_and_loaded(self):
        self.drag((80, 9), (86, 10))
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'roi.json'
            with patch('laser_heating.ui.roi.filedialog.asksaveasfilename', return_value=str(path)):
                self.editor.save_config()
            saved = json.loads(path.read_text())
            self.assertEqual((saved['left_x_end'], saved['left_y_end']), (86, 10))
            self.editor._on_roi_drag('left', RegionOfInterest(10, 80, 2, 9))
            with patch('laser_heating.ui.roi.filedialog.askopenfilename', return_value=str(path)):
                self.editor.load_config()
            self.assertEqual(self.dragger.rois['left'], RegionOfInterest(10, 86, 2, 10))

    def test_original_wide_camera_handles_use_same_pixel_hit_tolerance(self):
        self.editor.destroy()
        self.plots.data_file = CameraData(np.ones((70, 1340)), np.linspace(500, 900, 1340), 'wide.spe')
        self.plots.left_roi, self.plots.right_roi = RegionOfInterest(1, 1339, 0, 34), RegionOfInterest(1, 1339, 35, 69)
        self.editor = ROISelectionWindow(self.root, self.plots)
        self.editor.withdraw()
        self.editor.canvas.draw()
        self.dragger = self.editor.drag_controller
        self.drag((1, 0), (51, 3), screen_offset=(-4, 4))
        roi = self.editor._roi_from_fields('left')
        # Display-coordinate integer rounding is about 3 detector columns here.
        self.assertLessEqual(abs(roi.x_start-51), 3)
        self.assertEqual((roi.y_start, roi.x_end, roi.y_end), (3, 1339, 34))
        roi.validate(1340, 70)


if __name__ == '__main__':
    unittest.main()
