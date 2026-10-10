"""Compatibility entry point. New code uses laser_heating.ui modules directly."""
from laser_heating.ui.calibration import CalibrationFileSelection, TransmissionFilterSelection
from laser_heating.ui.files import DataFileHandling
from laser_heating.ui.plots import PlotGraphs
from laser_heating.ui.roi import ROISelectionWindow
from laser_heating.ui.temperature import InitiateActonTfit, LogoDisplay

if __name__ == "__main__":
    import tkinter as tk
    window = tk.Tk()
    window.geometry("1280x1000")
    window.title("High Temperature")
    panel = InitiateActonTfit(window, 0, 0, "COM7", "COM6")
    window.mainloop()
