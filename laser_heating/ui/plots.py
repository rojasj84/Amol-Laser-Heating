"""Temperature result display and frame navigation."""
import tkinter as tk
import numpy as np
from matplotlib import pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import theme
from laser_heating.analysis import fit_temperature, subtract_background
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

        # A separate header keeps readouts and navigation outside the plot canvas.
        self.plot_header = tk.Frame(self, bg=theme.PANEL_BG)
        self.plot_header.place(x=0, y=0, width=928, height=64)
        tk.Label(self.plot_header, text="LEFT TEMPERATURE", font=(theme.FONT_FAMILY, 9, "bold"),
                 fg=theme.LEFT_FG, bg=theme.PANEL_BG, anchor="w").place(x=18, y=6, width=285, height=18)
        tk.Label(self.plot_header, text="RIGHT TEMPERATURE", font=(theme.FONT_FAMILY, 9, "bold"),
                 fg=theme.RIGHT_FG, bg=theme.PANEL_BG, anchor="w").place(x=625, y=6, width=285, height=18)
        self.left_temperature_label = tk.Label(self.plot_header, text="", font=(theme.FONT_FAMILY, 14, "bold"),
                                               fg=theme.FG, bg=theme.PANEL_BG, anchor="w")
        self.left_temperature_label.place(x=18, y=26, width=285, height=29)
        self.right_temperature_label = tk.Label(self.plot_header, text="", font=(theme.FONT_FAMILY, 14, "bold"),
                                                fg=theme.FG, bg=theme.PANEL_BG, anchor="w")
        self.right_temperature_label.place(x=625, y=26, width=285, height=29)
        tk.Frame(self.plot_header, bg=theme.BORDER).place(x=0, y=63, width=928, height=1)

        self.frame_controls = tk.Frame(self.plot_header, bg=theme.PANEL_BG)
        self.frame_controls.place(relx=0.5, rely=0.5, anchor="center", width=232, height=36)
        self.btn_prev_frame = tk.Button(self.frame_controls, text="‹", command=self.prev_frame)
        self.btn_prev_frame.place(x=0, y=0, width=36, height=36)
        self.frame_status_label = tk.Label(self.frame_controls, text="Frame: 1 / 1",
                                           font=theme.FONT_BODY, fg=theme.FG_MUTED, bg=theme.PANEL_BG)
        self.frame_status_label.place(x=40, y=0, width=150, height=36)
        self.btn_next_frame = tk.Button(self.frame_controls, text="›", command=self.next_frame)
        self.btn_next_frame.place(x=196, y=0, width=36, height=36)
        theme.style_button(self.btn_prev_frame)
        theme.style_button(self.btn_next_frame)

        self.fig, self.axis = plt.subplots(2, 2, figsize=(9.28, 5.7), layout="constrained")
        self.fig.patch.set_facecolor(theme.PANEL_BG)
        self.graph_canvas = FigureCanvasTkAgg(self.fig, master=self)
        self.graph_canvas.get_tk_widget().place(x=0, y=65, width=928, height=573)
        self.left_roi = self.camera_profile.left_roi
        self.right_roi = self.camera_profile.right_roi
        self.current_frame_index = 0
        # Background is subtracted from every measurement. A calibration is
        # only subtracted when it is a raw flatfield collected through the
        # Camera tab; exported calibration files are used as saved.
        self.background = None
        self.calibration_needs_background = {"left": False, "right": False}

        self.left_calibration_temperature = calibration_temperature
        self.right_calibration_temperature = calibration_temperature
        self.left_calibration_file = self.load_capture(left_calibration_file)
        self.right_calibration_file = self.load_capture(right_calibration_file)
        self.data_file = self.load_capture(default_fit_file)
        self.update_graphs()

    def destroy(self):
        plt.close(self.fig)
        super().destroy()

    def set_capture(self, measurement, left_calibration, right_calibration, left_temperature, right_temperature,
                    calibration_needs_background=None):
        """Replace the displayed capture only if both sides can be fitted."""
        names = ("data_file", "left_calibration_file", "right_calibration_file",
                 "left_calibration_temperature", "right_calibration_temperature", "current_frame_index",
                 "calibration_needs_background")
        previous = {name: getattr(self, name) for name in names}
        self.data_file = measurement
        self.left_calibration_file, self.right_calibration_file = left_calibration, right_calibration
        self.left_calibration_temperature, self.right_calibration_temperature = left_temperature, right_temperature
        self.current_frame_index = 0
        flags = calibration_needs_background or {}
        self.calibration_needs_background = {side: bool(flags.get(side, False)) for side in ("left", "right")}
        try:
            self.update_graphs()
        except Exception:
            for name, value in previous.items():
                setattr(self, name, value)
            raise

    def set_background(self, background):
        """Use, replace, or clear (None) the background; keep the old one if the fit fails."""
        previous = self.background
        self.background = background
        try:
            self.update_graphs()
        except Exception:
            self.background = previous
            raise

    def _without_background(self, capture, apply=True):
        if self.background is None or not apply:
            return capture
        return subtract_background(capture, self.background)

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
        # The profile's reader is preferred; captures made by the Camera tab
        # may use another registered format (the simulated camera writes NPZ).
        capture = self.readers.read_by_suffix(path, self.camera_profile.reader)
        self.camera_profile.validate_data(capture)
        return capture

    def update_graphs(self):
        self.current_frame_index = min(self.current_frame_index, self.data_file.frame_count - 1)
        measurement = self._without_background(self.data_file)
        left_calibration = self._without_background(self.left_calibration_file,
                                                    self.calibration_needs_background["left"])
        right_calibration = self._without_background(self.right_calibration_file,
                                                     self.calibration_needs_background["right"])
        left = fit_temperature(measurement, left_calibration, self.left_roi,
                               self.left_calibration_temperature, self.current_frame_index)
        right = fit_temperature(measurement, right_calibration, self.right_roi,
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
        for column, result in enumerate((left, right)):
            side = "Left" if column == 0 else "Right"
            color = theme.LEFT_FG if column == 0 else theme.RIGHT_FG
            self.axis[0, column].plot(result.wavelengths_nm, result.corrected_counts,
                                      color=color, linewidth=1.3)
            self.axis[0, column].plot(result.wavelengths_nm, result.fitted_counts,
                                      color=theme.FIT_COLOR, linewidth=1.6, linestyle="--")
            self.axis[0, column].set_title(f"{side} fit", loc="left", pad=10)
            self.axis[1, column].plot(result.wavelengths_nm, result.raw_counts,
                                      color=color, linewidth=1.3)
            self.axis[1, column].set_title(f"{side} raw spectrum", loc="left", pad=10)
            self.axis[1, column].set_xlabel("Wavelength (nm)")
            for row in range(2):
                axis = self.axis[row, column]
                axis.set_ylabel("Counts")
                theme.style_plot_axis(axis)
        self.graph_canvas.draw()
        self.left_temperature_label.config(text=self._temperature_label(left))
        self.right_temperature_label.config(text=self._temperature_label(right))

    @staticmethod
    def _temperature_label(result):
        if not np.isfinite(result.temperature_kelvin):
            return "Temperature fit unavailable"
        uncertainty = str(round(result.uncertainty_kelvin)) if np.isfinite(result.uncertainty_kelvin) else "?"
        return f"T= {round(result.temperature_kelvin)} ± {uncertainty} K"
