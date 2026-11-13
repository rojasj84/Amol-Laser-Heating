"""Compose the temperature view from its independent panels."""
import tkinter as tk
import numpy as np
import theme
from laser_heating.models import CameraData
from laser_heating.camera import create_camera
from laser_heating.config import ApplicationConfig
from .camera import CameraControlPanel
from .calibration import CalibrationFileSelection, TransmissionFilterSelection
from .files import DataFileHandling
from .plots import PlotGraphs
from .roi import ROISelectionWindow

class LogoDisplay(tk.Frame):
    def __init__(self,container,x_position, y_position):
        super().__init__(container)

        #Frame visual configuration
        self.configure(width=1260,height=40,background=theme.PANEL_BG, highlightbackground=theme.BORDER, highlightthickness=1)

        #Frame position information
        self.place(x = x_position, y = y_position)

        #Set logo
        self.logotext = tk.Label(self, text="High Temperature", font=theme.FONT_TITLE, anchor="w", padx=14, background=theme.PANEL_BG)
        self.logotext.place(x = 5, y = 0, width=1250, height=35)


class TemperaturePanel(tk.Frame):
    def __init__(self, container, x_position, y_position, left_denkovi_com_port, right_denkovi_com_port, config=None, readers=None, camera=None):
        super().__init__(container)

        #Frame visual configuration
        self.configure(width=1280,height=1000)

        #Frame position information
        self.place(x = x_position, y = y_position)

        self.config_data = config or ApplicationConfig()
        settings = self.config_data.calibration
        self.right_calibration_file = settings.right_file
        self.left_calibration_file = settings.left_file
        self.autofit_folderpath = self.config_data.acquisition_folder
        default_fit_file = self.config_data.initial_measurement or settings.right_file

        self.Logo = LogoDisplay(self, 10,10)
        self.Logo.logotext.config(text=f"Temperature analysis  ·  {self.config_data.camera.name}")
        self.CalibrationFileSelect = CalibrationFileSelection(self, 10, 100, self.left_calibration_file, self.right_calibration_file, self.autofit_folderpath)
        self.TransmissionFilter = TransmissionFilterSelection (self, 340, 60, left_denkovi_com_port, right_denkovi_com_port, calibration_file_select=self.CalibrationFileSelect, calibration_settings=settings)
        self.TransmissionFilter.place(x = 340, y = 60)

        self.Temperature_graphs = PlotGraphs(self, 340, 320, self.left_calibration_file, self.right_calibration_file, default_fit_file, self.config_data.camera, readers, settings.temperature_kelvin)
        for field in (self.CalibrationFileSelect.set_left_temperature, self.CalibrationFileSelect.set_right_temperature):
            field.delete("1.0", tk.END)
            field.insert(tk.END, str(settings.temperature_kelvin))
        self.DataFileSelect = DataFileHandling(self, self.Temperature_graphs, self.CalibrationFileSelect, 10, 100, self.autofit_folderpath)

        plots = self.Temperature_graphs
        def simulated_lamp():
            # Each calibration file holds the lamp in its own side's rows only.
            left, right = plots.load_capture(settings.left_file), plots.load_capture(settings.right_file)
            frame = np.clip(left.frame(0), 0, None) + np.clip(right.frame(0), 0, None)
            return CameraData(frame, left.wavelengths_nm, left.source, left.exposure_seconds)

        self.camera = camera or create_camera(self.config_data.camera_control, simulated_lamp,
                                              settings.temperature_kelvin)
        self.CameraControl = CameraControlPanel(self, self.camera, plots, self.CalibrationFileSelect,
                                                self.DataFileSelect, 10, 100,
                                                self.config_data.camera_control.exposure_seconds)

        self.DataFileSelect_placedata = self.DataFileSelect.place_info()
        self.CalibrationFileSelect_placedata = self.CalibrationFileSelect.place_info()
        self.CameraControl_placedata = self.CameraControl.place_info()
        self.CameraControl.place_forget()

        #Buttons for showing the correct file handling window
        self.show_calibration_selection_window = tk.Button(self, text="Calibration", command=lambda: self.select_file_handling(1))
        self.show_calibration_selection_window.place(x = 10, y = 60, width = 106, height = 30)
        self.show_data_selection_window = tk.Button(self, text="Temperature Fit", command=lambda: self.select_file_handling(2))
        self.show_data_selection_window.place(x = 117, y = 60, width = 106, height = 30)
        self.show_camera_control_window = tk.Button(self, text="Camera", command=lambda: self.select_file_handling(3))
        self.show_camera_control_window.place(x = 224, y = 60, width = 106, height = 30)
        self.show_data_selection_window.config(state="disabled")

        # ROI Settings Button
        self.btn_roi_settings = tk.Button(self, text="ROI Settings", command=self.open_roi_settings, font=('Helvetica', 12, 'bold'))
        self.btn_roi_settings.place(x=10, y=480, width=320, height=40)
        theme.style_button(self.btn_roi_settings, kind="primary")
        self._style_tabs(2)
        theme.modernize_widgets(self)

    def open_roi_settings(self):
        ROISelectionWindow(self, self.Temperature_graphs)

    def _tabs(self):
        return {1: (self.show_calibration_selection_window, self.CalibrationFileSelect, self.CalibrationFileSelect_placedata),
                2: (self.show_data_selection_window, self.DataFileSelect, self.DataFileSelect_placedata),
                3: (self.show_camera_control_window, self.CameraControl, self.CameraControl_placedata)}

    def _style_tabs(self, selected_window):
        for number, (button, _, _) in self._tabs().items():
            theme.style_button(button, kind="primary" if number == selected_window else "secondary")
            button.configure(padx=2)

    def select_file_handling(self, selected_window):
        if selected_window not in self._tabs():
            return
        self._style_tabs(selected_window)
        for number, (button, panel, placement) in self._tabs().items():
            if number == selected_window:
                panel.place(placement)
                panel.lift()
                button.config(state="disabled")
            else:
                panel.place_forget()
                button.config(state="normal")



# Compatibility for the original public entry point.
InitiateActonTfit = TemperaturePanel
