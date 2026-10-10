"""Temperature result display and frame navigation."""
import tkinter as tk
import numpy as np
from matplotlib import pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import theme
from laser_heating.analysis import fit_temperature
from laser_heating.config import CameraProfile
from laser_heating.readers import ReaderRegistry

plt.style.use("dark_background")

class PlotGraphs(tk.Frame):
    def __init__(self, container, x_position, y_position, left_calibration_file, right_calibration_file, default_fit_file, camera_profile=None, readers=None, calibration_temperature=2255):
        super().__init__(container)
        self.camera_profile = camera_profile or CameraProfile()
        self.readers = readers or ReaderRegistry.defaults()
        self.file_extensions = self.readers.get(self.camera_profile.reader).extensions

        #Frame visual configuration
        self.configure(width=930,height=640,background=theme.PANEL_BG, highlightbackground=theme.BORDER, highlightthickness=1)

        #Frame position information
        self.x_position = x_position
        self.y_position = y_position
        self.place(x = self.x_position, y = self.y_position)

        self.wavelengths = np.arange(1, 101)
        self.left_fit = np.arange(1, 101)
        self.right_fit = np.arange(1, 101)
        self.left_raw = np.arange(1, 101)
        self.right_raw = np.arange(1, 101)

        self.fig, self.axis = plt.subplots(2, 2)
        self.fig.patch.set_facecolor(theme.PANEL_BG)
        for row in self.axis:
            for single_axis in row:
                single_axis.set_facecolor(theme.PANEL_BG)
        plt.tight_layout()
        self.axis[0, 0].plot(self.wavelengths, self.left_fit)
        self.axis[0, 0].set_title('LEFT FIT')

        self.axis[0, 1].plot(self.wavelengths, self.right_fit, 'tab:orange')
        self.axis[0, 1].set_title('RIGHT FIT')
        self.axis[1, 0].plot(self.wavelengths, self.left_raw, 'tab:green')
        self.axis[1, 0].set_title('LEFT RAW')
        self.axis[1, 1].plot(self.wavelengths, self.right_raw, 'tab:red')
        self.axis[1, 1].set_title('RIGHT RAW')

        self.graph_canvas = FigureCanvasTkAgg(self.fig, master=self)
        self.graph_canvas.draw()
        self.graph_canvas.get_tk_widget().place(x = 0, y = 0, width=928,height=638)

        self.left_temperature_label = tk.Label(self, text="", font=('Helvetica', 15), background=theme.PANEL_BG, anchor="w")
        self.left_temperature_label.place(x=77, y=30, width=230, height=30)
        self.right_temperature_label = tk.Label(self, text="", font=('Helvetica', 15), background=theme.PANEL_BG, anchor="w")
        self.right_temperature_label.place(x=530, y=30, width=230, height=30)

        self.left_roi = self.camera_profile.left_roi
        self.right_roi = self.camera_profile.right_roi

        self.current_frame_index = 0

        # Frame navigator controls
        self.btn_prev_frame = tk.Button(self, text="<", font=('Helvetica', 12, 'bold'), command=self.prev_frame)
        self.btn_prev_frame.place(x=320, y=30, width=30, height=30)

        self.frame_status_label = tk.Label(self, text="Frame: 1 / 1", font=('Helvetica', 12), background=theme.PANEL_BG)
        self.frame_status_label.place(x=360, y=30, width=120, height=30)

        self.btn_next_frame = tk.Button(self, text=">", font=('Helvetica', 12, 'bold'), command=self.next_frame)
        self.btn_next_frame.place(x=490, y=30, width=30, height=30)

        self.left_calibration_temperature = calibration_temperature
        self.right_calibration_temperature = calibration_temperature
        self.left_calibration_file = self.load_capture(left_calibration_file)
        self.right_calibration_file = self.load_capture(right_calibration_file)
        self.data_file = self.load_capture(default_fit_file)
        self.update_graphs()

    def destroy(self):
        plt.close(self.fig)
        super().destroy()

    def set_capture(self, measurement, left_calibration, right_calibration, left_temperature, right_temperature):
        """Replace the displayed capture only if both sides can be fitted."""
        names = ("data_file", "left_calibration_file", "right_calibration_file",
                 "left_calibration_temperature", "right_calibration_temperature", "current_frame_index")
        previous = {name: getattr(self, name) for name in names}
        self.data_file = measurement
        self.left_calibration_file, self.right_calibration_file = left_calibration, right_calibration
        self.left_calibration_temperature, self.right_calibration_temperature = left_temperature, right_temperature
        self.current_frame_index = 0
        try:
            self.update_graphs()
        except Exception:
            for name, value in previous.items():
                setattr(self, name, value)
            raise

    def prev_frame(self):
        if hasattr(self, 'data_file') and self.data_file.frame_count > 1:
            if self.current_frame_index > 0:
                self.current_frame_index -= 1
                self.update_graphs()

    def next_frame(self):
        if hasattr(self, 'data_file') and self.data_file.frame_count > 1:
            if self.current_frame_index < self.data_file.frame_count - 1:
                self.current_frame_index += 1
                self.update_graphs()


    def load_capture(self, path):
        capture = self.readers.read(path, self.camera_profile.reader)
        self.camera_profile.validate_data(capture)
        return capture

    def update_graphs(self):
        self.current_frame_index = min(self.current_frame_index, self.data_file.frame_count - 1)
        left = fit_temperature(self.data_file, self.left_calibration_file, self.left_roi,
                               self.left_calibration_temperature, self.current_frame_index)
        right = fit_temperature(self.data_file, self.right_calibration_file, self.right_roi,
                                self.right_calibration_temperature, self.current_frame_index)
        self.frame_status_label.config(text=f"Frame: {self.current_frame_index + 1} / {self.data_file.frame_count}")
        self.btn_prev_frame.config(state="normal" if self.current_frame_index > 0 else "disabled")
        self.btn_next_frame.config(state="normal" if self.current_frame_index < self.data_file.frame_count - 1 else "disabled")
        self.left_result, self.right_result = left, right
        # Keep named arrays available for plots, export, and existing callers.
        for side, result in (("left", left), ("right", right)):
            setattr(self, f"{side}_wavelengths", result.wavelengths_nm)
            setattr(self, f"{side}_raw", result.raw_counts)
            setattr(self, f"{side}_corrected", result.corrected_counts)
            setattr(self, f"{side}_fit", result.fitted_counts)
        for row in self.axis:
            for axis in row:
                axis.clear()
                axis.set_facecolor(theme.PANEL_BG)
        for column, result in enumerate((left, right)):
            label = "LEFT" if column == 0 else "RIGHT"
            self.axis[0, column].plot(result.wavelengths_nm, result.corrected_counts,
                                      result.wavelengths_nm, result.fitted_counts)
            self.axis[0, column].set_title(f"{label} FIT")
            self.axis[1, column].plot(result.wavelengths_nm, result.raw_counts)
            self.axis[1, column].set_title(f"{label} RAW")
        self.graph_canvas.draw()
        self.left_temperature_label.config(text=self._temperature_label(left))
        self.right_temperature_label.config(text=self._temperature_label(right))

    @staticmethod
    def _temperature_label(result):
        if not np.isfinite(result.temperature_kelvin):
            return "Temperature fit unavailable"
        uncertainty = str(round(result.uncertainty_kelvin)) if np.isfinite(result.uncertainty_kelvin) else "?"
        return f"T= {round(result.temperature_kelvin)} +/- {uncertainty} K"
