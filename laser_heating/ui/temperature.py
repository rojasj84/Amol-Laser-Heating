"""Compose the temperature view from its independent panels."""
import tkinter as tk
import theme
from laser_heating.config import ApplicationConfig
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
        self.logotext = tk.Label(self, text="High Temperature", font=('Helvetica', 20), background=theme.PANEL_BG)
        self.logotext.place(x = 5, y = 0, width=1250, height=35)


class TemperaturePanel(tk.Frame):
    def __init__(self, container, x_position, y_position, left_denkovi_com_port, right_denkovi_com_port, config=None, readers=None):
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
        self.Logo.logotext.config(text=f"High T : {self.config_data.camera.name}")
        self.CalibrationFileSelect = CalibrationFileSelection(self, 10, 90, self.left_calibration_file, self.right_calibration_file, self.autofit_folderpath)
        self.TransmissionFilter = TransmissionFilterSelection (self, 340, 60, left_denkovi_com_port, right_denkovi_com_port, calibration_file_select=self.CalibrationFileSelect, calibration_settings=settings)
        self.TransmissionFilter.place(x = 340, y = 60)

        self.Temperature_graphs = PlotGraphs(self, 340, 320, self.left_calibration_file, self.right_calibration_file, default_fit_file, self.config_data.camera, readers, settings.temperature_kelvin)
        for field in (self.CalibrationFileSelect.set_left_temperature, self.CalibrationFileSelect.set_right_temperature):
            field.delete("1.0", tk.END)
            field.insert(tk.END, str(settings.temperature_kelvin))
        self.DataFileSelect = DataFileHandling(self, self.Temperature_graphs, self.CalibrationFileSelect, 10, 90, self.autofit_folderpath)

        self.DataFileSelect_placedata = self.DataFileSelect.place_info()
        self.CalibrationFileSelect_placedata = self.CalibrationFileSelect.place_info()

        self.show_data_selection_window = tk.Button(self, text="Temperature Fit", command=lambda: self.select_file_handling(2))
        self.show_data_selection_window.place(x = 170, y = 60, width = 160, height = 25)
        self.show_data_selection_window.config(state="disable")

        #Buttons for showing the correct file handling window
        self.show_calibration_selection_window = tk.Button(self, text="Calibration Selection", command=lambda: self.select_file_handling(1))
        self.show_calibration_selection_window.place(x = 10, y = 60, width = 160, height = 25)
        self.show_calibration_selection_window.config(state="active")

        # ROI Settings Button
        self.btn_roi_settings = tk.Button(self, text="ROI Settings", command=self.open_roi_settings, font=('Helvetica', 12, 'bold'))
        self.btn_roi_settings.place(x=10, y=470, width=320, height=40)

    def open_roi_settings(self):
        ROISelectionWindow(self, self.Temperature_graphs)

    def select_file_handling(self, selected_window):
        if selected_window == 1:
            self.DataFileSelect.place_forget()
            self.CalibrationFileSelect.place(self.CalibrationFileSelect_placedata)
            self.show_data_selection_window.config(state="active")
            self.show_calibration_selection_window.config(state="disabled")
        elif selected_window == 2:
            self.CalibrationFileSelect.place_forget()
            self.DataFileSelect.place(self.DataFileSelect_placedata)
            self.show_calibration_selection_window.config(state="active")
            self.show_data_selection_window.config(state="disabled")



# Compatibility for the original public entry point.
InitiateActonTfit = TemperaturePanel
