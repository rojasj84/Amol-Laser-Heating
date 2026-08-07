import tkinter as tk
import numpy as np
import sys
import queue

import import_calibration as calib_find
from pathlib import Path
import denkovi_serial as DenkTalk
import theme

from watchdog.observers import Observer
from watchdog.events import PatternMatchingEventHandler
from tkinter import filedialog
from matplotlib import pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.patches as patches
import json

import TemperatureFit.TemperatureFitting as tfit
import TemperatureFit.SpeFile as spe

plt.style.use('dark_background')

default_calibration_temperature = 2255

class LogoDisplay(tk.Frame):
    def __init__(self,container,x_position, y_position):
        #tk.Frame.__init__(self, container)
        super().__init__(container)

        #Frame visual configuration
        self.configure(width=1260,height=40,background=theme.PANEL_BG, highlightbackground=theme.BORDER, highlightthickness=1)

        #Frame position information
        self.place(x = x_position, y = y_position)

        #Set logo
        self.logotext = tk.Label(self, text="High T : Acton-PIXIS 400", font=('Helvetica', 20), background=theme.PANEL_BG)
        self.logotext.place(x = 5, y = 0, width=1250, height=35)

class CalibrationFileSelection(tk.Frame):
    def __init__(self, container, x_position, y_position, left_calibration_file, right_calibration_file, autofit_folderpath):
        #tk.Frame.__init__(self, container)
        super().__init__(container)
        
        #Frame visual configuration
        self.configure(width=320,height=320,background=theme.PANEL_BG, highlightbackground=theme.BORDER, highlightthickness=1)
        
        #Frame position information
        self.x_position = x_position
        self.y_position = y_position
        self.place(x = self.x_position, y = self.y_position)

        #Left Side Calibration
        
        load_left_file = tk.Button(self, text="Select Left Calibration File", command=lambda: self.calibration_file_open_dialog(1), font=('Helvetica', 10))
        load_left_file.place(x = 10, y=10, width = 300, height=25)

        self.left_file_location = tk.Text(self, bg = theme.TEXT_BG, font=('Helvetica', 10))#, relief=tk.FLAT)
        self.left_file_location.place(x = 10, y=45, width = 300, height=50) 

        left_calibration_file = Path(left_calibration_file)
        left_calibration_file = left_calibration_file.absolute()
        self.left_file_location.insert("end-1c", left_calibration_file)
        
        self.set_left_temperature = tk.Text(self, background=theme.TEXT_BG, font=('Helvetica', 10))
        self.set_left_temperature.place(x=210, y=100, width = 100, height=25)

        set_left_temperature_label = tk.Label(self, text="Left Calib. Temperature (K)",  borderwidth=2, relief="groove", background=theme.PANEL_BG, font=('Helvetica', 10))
        set_left_temperature_label.place(x=10, y=100, width = 200, height=25)

        self.set_left_temperature.insert("end-1c", default_calibration_temperature)

        self.left_status_label = tk.Label(self, text="", font=('Helvetica', 9, 'bold'), background=theme.PANEL_BG, borderwidth=2, relief="groove")
        self.left_status_label.place(x=10, y=128, width=300, height=22)

        #Right Side Calibration
        
        load_right_file = tk.Button(self, text="Select Right Calibration File", command=lambda: self.calibration_file_open_dialog(2), font=('Helvetica', 10))
        load_right_file.place(x = 10, y=155, width = 300, height=25)

        self.right_file_location = tk.Text(self, bg = theme.TEXT_BG, font=('Helvetica', 10))#, relief=tk.FLAT)
        self.right_file_location.place(x = 10, y=185, width = 300, height=50) 
        
        right_calibration_file = Path(right_calibration_file)
        right_calibration_file = right_calibration_file.absolute()
        self.right_file_location.insert("end-1c", right_calibration_file)

        self.set_right_temperature = tk.Text(self, background=theme.TEXT_BG, font=('Helvetica', 10))
        self.set_right_temperature.place(x=210, y=240, width = 100, height=25)

        set_right_temperature_label = tk.Label(self, text="Right Calib. Temperature (K)",  borderwidth=2, relief="groove", background=theme.PANEL_BG, font=('Helvetica', 10))
        set_right_temperature_label.place(x=10, y=240, width = 200, height=25)

        self.set_right_temperature.insert("end-1c", default_calibration_temperature)

        # Calibration status indicators
        self.right_status_label = tk.Label(self, text="", font=('Helvetica', 9, 'bold'), background=theme.PANEL_BG, borderwidth=2, relief="groove")
        self.right_status_label.place(x=10, y=270, width=300, height=22)
    

    def update_status(self, left_exists, right_exists):
        if left_exists:
            self.left_status_label.config(text="Left Calibration File: OK", fg="#4CAF50")
        else:
            self.left_status_label.config(text="Left Calibration File: Missing", fg="#FF5252")

        if right_exists:
            self.right_status_label.config(text="Right Calibration File: OK", fg="#4CAF50")
        else:
            self.right_status_label.config(text="Right Calibration File: Missing", fg="#FF5252")

    def has_valid_calibration(self):
        left_path_str = self.left_file_location.get("1.0", tk.END).strip().replace("\n", "")
        right_path_str = self.right_file_location.get("1.0", tk.END).strip().replace("\n", "")
        return Path(left_path_str).is_file() and Path(right_path_str).is_file()

    def update_left_calibration_file(self, file_path):
        file_path = Path(file_path).absolute()
        self.left_file_location.config(state="normal")
        self.left_file_location.delete("1.0", tk.END)
        self.left_file_location.insert(tk.END, str(file_path))
        self.left_file_location.config(state="disabled")

    def update_right_calibration_file(self, file_path):
        file_path = Path(file_path).absolute()
        self.right_file_location.config(state="normal")
        self.right_file_location.delete("1.0", tk.END)
        self.right_file_location.insert(tk.END, str(file_path))
        self.right_file_location.config(state="disabled")

    def calibration_file_open_dialog(self, file_location_number):
        #Differentiates between the light field spectra and the t-rax folder
        open_file_path = filedialog.askopenfilename()
        if open_file_path:
            if file_location_number == 1:
                self.update_left_calibration_file(open_file_path)
            elif file_location_number == 2:
                self.update_right_calibration_file(open_file_path)        
    
class TransmissionFilterSelection(tk.Frame):
    def __init__(self, container, x_position, y_position, left_denkovi_com_port, right_denkovi_com_port, calibration_file_select=None):
        #tk.Frame.__init__(self, container)
        super().__init__(container)

        #Frame visual configuration
        self.configure(width=930,height=250,background=theme.PANEL_BG, highlightbackground=theme.BORDER, highlightthickness=1)
        
        #Frame position information
        self.x_position = x_position
        self.y_position = y_position
        #self.place(x = self.x_position, y = self.y_position)

        self.select_one_transmission_filter_logo = tk.Label(self, text = "Select One Transmission Filter", font=('Helvetica', 15), background=theme.PANEL_BG)
        self.select_one_transmission_filter_logo.place(x=5,y=5, width=920, height=30)

        self.select_one_transmission_filter_logo = tk.Label(self, text = "Select Iris Status and Magnification", font=('Helvetica', 15), background=theme.PANEL_BG)
        self.select_one_transmission_filter_logo.place(x=5,y=135, width=920, height=30)

        self.left_denkovi_com_port = left_denkovi_com_port
        self.right_denkovi_com_port = right_denkovi_com_port
        self.calibration_file_select = calibration_file_select


        # Filter Determination Raio Buttons for the Left Side
        
        self.filter_variable_left = tk.IntVar()
        self.iris_variable_left = tk.IntVar()
        self.magnification_variable_left = tk.IntVar()        

        self.left_no_filter_selection = tk.Radiobutton(self,text="NO FILTER", font=('Helvetica', 10), indicatoron = 0, variable = self.filter_variable_left, value = 0b000, selectcolor=theme.LEFT_ACCENT, background=theme.LEFT_ACCENT, command=self.UpdateFestoStates) #Value corresponds to the binary state of 000 for all 3 NDFs
        self.left_no_filter_selection.place(x=30, y = 50, width=90, height=30)
        self.left_no_filter_selection.select()

        self.left_700_filter_selection = tk.Radiobutton(self,text="70% FILTER", font=('Helvetica', 10), indicatoron = 0, variable = self.filter_variable_left, value = 0b001, selectcolor=theme.LEFT_ACCENT, background=theme.LEFT_ACCENT, command=self.UpdateFestoStates) #NDF state 100, value 4
        self.left_700_filter_selection.place(x=130, y = 50, width=90, height=30)

        self.left_500_filter_selection = tk.Radiobutton(self,text="50% FILTER", font=('Helvetica', 10), indicatoron = 0, variable = self.filter_variable_left, value = 0b010, selectcolor=theme.LEFT_ACCENT, background=theme.LEFT_ACCENT, command=self.UpdateFestoStates) #NDF state 010, value 2
        self.left_500_filter_selection.place(x=230, y = 50, width=90, height=30)

        self.left_350_filter_selection = tk.Radiobutton(self,text="35% FILTER", font=('Helvetica', 10), indicatoron = 0, variable = self.filter_variable_left, value = 0b011, selectcolor=theme.LEFT_ACCENT, background=theme.LEFT_ACCENT, command=self.UpdateFestoStates) #NDF state 110, value 6
        self.left_350_filter_selection.place(x=330, y = 50, width=90, height=30)
        
        self.left_100_filter_selection = tk.Radiobutton(self,text="10% FILTER", font=('Helvetica', 10), indicatoron = 0, variable = self.filter_variable_left, value = 0b100, selectcolor=theme.LEFT_ACCENT, background=theme.LEFT_ACCENT, command=self.UpdateFestoStates) #NDF state 001, value 1
        self.left_100_filter_selection.place(x=30, y = 90, width=90, height=30)

        self.left_070_filter_selection = tk.Radiobutton(self,text="7% FILTER", font=('Helvetica', 10), indicatoron = 0, variable = self.filter_variable_left, value = 0b101, selectcolor=theme.LEFT_ACCENT, background=theme.LEFT_ACCENT, command=self.UpdateFestoStates) #NDF state 101, value 5
        self.left_070_filter_selection.place(x=130, y = 90, width=90, height=30)

        self.left_050_filter_selection = tk.Radiobutton(self,text="5% FILTER", font=('Helvetica', 10), indicatoron = 0, variable = self.filter_variable_left, value = 0b110, selectcolor=theme.LEFT_ACCENT, background=theme.LEFT_ACCENT, command=self.UpdateFestoStates) #NDF state 011, value 3
        self.left_050_filter_selection.place(x=230, y = 90, width=90, height=30)

        self.left_035_filter_selection = tk.Radiobutton(self,text="3.5% FILTER", font=('Helvetica', 10), indicatoron = 0, variable = self.filter_variable_left, value = 0b111, selectcolor=theme.LEFT_ACCENT, background=theme.LEFT_ACCENT, command=self.UpdateFestoStates) #NDF state 111, value 7
        self.left_035_filter_selection.place(x=330, y = 90, width=90, height=30)

        self.left_iris_selection_out = tk.Radiobutton(self, text = "Iris Out", font=('Helvetica', 12), indicatoron=0, variable=self.iris_variable_left, value = 0b0, selectcolor=theme.LEFT_ACCENT, background=theme.LEFT_ACCENT, command=self.UpdateFestoStates)
        self.left_iris_selection_out.place(x = 30, y = 160, width=90, height=50)
        
        self.left_iris_selection_in = tk.Radiobutton(self, text = "Iris In", font=('Helvetica', 12), indicatoron=0, variable=self.iris_variable_left, value = 0b1, selectcolor=theme.LEFT_ACCENT, background=theme.LEFT_ACCENT, command=self.UpdateFestoStates)
        self.left_iris_selection_in.place(x = 130, y = 160, width=90, height=50)

        self.left_magnification_selection_15 = tk.Radiobutton(self, text = "15x", font=('Helvetica', 12), indicatoron=0, variable=self.magnification_variable_left, value = 0b0, selectcolor=theme.LEFT_ACCENT, background=theme.LEFT_ACCENT, command=self.UpdateFestoStates)
        self.left_magnification_selection_15.place(x = 230, y = 160, width=90, height=50)
        
        self.left_magnification_selection_20 = tk.Radiobutton(self, text = "20x", font=('Helvetica', 12), indicatoron=0, variable=self.magnification_variable_left, value = 0b1, selectcolor=theme.LEFT_ACCENT, background=theme.LEFT_ACCENT, command=self.UpdateFestoStates)
        self.left_magnification_selection_20.place(x = 330, y = 160, width=90, height=50)

        # Filter Determination Raio Buttons for the Right Side
        
        self.filter_variable_right = tk.IntVar()
        self.iris_variable_right = tk.IntVar()
        self.magnification_variable_right = tk.IntVar()

        self.right_no_filter_selection = tk.Radiobutton(self,text="NO FILTER", font=('Helvetica', 10), indicatoron = 0, variable = self.filter_variable_right, value = 0b000, selectcolor=theme.RIGHT_ACCENT, background=theme.RIGHT_ACCENT, command=self.UpdateFestoStates)
        self.right_no_filter_selection.place(x=930-90-330, y = 50, width=90, height=30)
        self.right_no_filter_selection.select()

        self.right_700_filter_selection = tk.Radiobutton(self,text="70% FILTER", font=('Helvetica', 10), indicatoron = 0, variable = self.filter_variable_right, value = 0b100, selectcolor=theme.RIGHT_ACCENT, background=theme.RIGHT_ACCENT, command=self.UpdateFestoStates)
        self.right_700_filter_selection.place(x=930-90-230, y = 50, width=90, height=30)

        self.right_500_filter_selection = tk.Radiobutton(self,text="50% FILTER", font=('Helvetica', 10), indicatoron = 0, variable = self.filter_variable_right, value = 0b010, selectcolor=theme.RIGHT_ACCENT, background=theme.RIGHT_ACCENT, command=self.UpdateFestoStates)
        self.right_500_filter_selection.place(x=930-90-130, y = 50, width=90, height=30)

        self.right_350_filter_selection = tk.Radiobutton(self,text="35% FILTER", font=('Helvetica', 10), indicatoron = 0, variable = self.filter_variable_right, value = 0b110, selectcolor=theme.RIGHT_ACCENT, background=theme.RIGHT_ACCENT, command=self.UpdateFestoStates)
        self.right_350_filter_selection.place(x=930-90-30, y = 50, width=90, height=30)
        
        self.right_100_filter_selection = tk.Radiobutton(self,text="10% FILTER", font=('Helvetica', 10), indicatoron = 0, variable = self.filter_variable_right, value = 0b001, selectcolor=theme.RIGHT_ACCENT, background=theme.RIGHT_ACCENT, command=self.UpdateFestoStates)
        self.right_100_filter_selection.place(x=930-90-330, y = 90, width=90, height=30)

        self.right_070_filter_selection = tk.Radiobutton(self,text="7% FILTER", font=('Helvetica', 10), indicatoron = 0, variable = self.filter_variable_right, value = 0b101, selectcolor=theme.RIGHT_ACCENT, background=theme.RIGHT_ACCENT, command=self.UpdateFestoStates)
        self.right_070_filter_selection.place(x=930-90-230, y = 90, width=90, height=30)

        self.right_050_filter_selection = tk.Radiobutton(self,text="5% FILTER", font=('Helvetica', 10), indicatoron = 0, variable = self.filter_variable_right, value = 0b011, selectcolor=theme.RIGHT_ACCENT, background=theme.RIGHT_ACCENT, command=self.UpdateFestoStates)
        self.right_050_filter_selection.place(x=930-90-130, y = 90, width=90, height=30)

        self.right_035_filter_selection = tk.Radiobutton(self,text="3.5% FILTER", font=('Helvetica', 10), indicatoron = 0, variable = self.filter_variable_right, value = 0b111, selectcolor=theme.RIGHT_ACCENT, background=theme.RIGHT_ACCENT, command=self.UpdateFestoStates)
        self.right_035_filter_selection.place(x=930-90-30, y = 90, width=90, height=30)

        self.right_iris_selection_out = tk.Radiobutton(self, text = "Iris Out", font=('Helvetica', 12), indicatoron=0, variable=self.iris_variable_right, value = 0, selectcolor=theme.RIGHT_ACCENT, background=theme.RIGHT_ACCENT, command=self.UpdateFestoStates)
        self.right_iris_selection_out.place(x = 930-90-330, y = 160, width=90, height=50)
        
        self.right_iris_selection_in = tk.Radiobutton(self, text = "Iris In", font=('Helvetica', 12), indicatoron=0, variable=self.iris_variable_right, value = 1, selectcolor=theme.RIGHT_ACCENT, background=theme.RIGHT_ACCENT, command=self.UpdateFestoStates)
        self.right_iris_selection_in.place(x = 930-90-230, y = 160, width=90, height=50)

        self.right_magnification_selection_15 = tk.Radiobutton(self, text = "15x", font=('Helvetica', 12), indicatoron=0, variable=self.magnification_variable_right, value = 0, selectcolor=theme.RIGHT_ACCENT, background=theme.RIGHT_ACCENT, command=self.UpdateFestoStates)
        self.right_magnification_selection_15.place(x = 930-90-130, y = 160, width=90, height=50)
        
        self.right_magnification_selection_20 = tk.Radiobutton(self, text = "20x", font=('Helvetica', 12), indicatoron=0, variable=self.magnification_variable_right, value = 1, selectcolor=theme.RIGHT_ACCENT, background=theme.RIGHT_ACCENT, command=self.UpdateFestoStates)
        self.right_magnification_selection_20.place(x = 930-90-30, y = 160, width=90, height=50)

        #self.CalibrationChecking = calib_find.FestoStateCalibrationsCheck("TemperatureFit\calibration_file_table.csv")
        self.RightCalibrationChecking = calib_find.FestoStateCalibrationsCheck(r"TemperatureFit\calibration_file_table_right_side.csv")
        self.LeftCalibrationChecking = calib_find.FestoStateCalibrationsCheck(r"TemperatureFit\calibration_file_table_left_side.csv")

        self.UpdateFestoStates()

    def resolve_calibration_file_path(self, calib_name):
        if not calib_name:
            return None
        base_dir = Path("TemperatureFit")
        target_name = f"{calib_name}.spe" if not str(calib_name).endswith(".spe") else str(calib_name)
        
        # 1. Exact glob match anywhere under TemperatureFit
        matches = list(base_dir.glob(f"**/{target_name}"))
        if matches:
            return matches[0].absolute()
        
        # 2. Handle known filename variations on disk (T7050 vs T70T50, T70T10 vs T7010)
        variations = []
        if "T7050" in target_name:
            variations.append(target_name.replace("T7050", "T70T50"))
        if "T70T10" in target_name:
            variations.append(target_name.replace("T70T10", "T7010"))
        
        for var in variations:
            m = list(base_dir.glob(f"**/{var}"))
            if m:
                return m[0].absolute()

        # 3. Check for exposure suffix variants (e.g. woI -> woI_300ms, woI_200ms)
        stem = target_name[:-4] if target_name.endswith(".spe") else target_name
        woi_matches = list(base_dir.glob(f"**/{stem}*.spe"))
        if woi_matches:
            return woi_matches[0].absolute()

        # 4. If file is missing on disk, construct the expected calibration subfolder path
        side = "L" if stem.startswith("L_") else ("R" if stem.startswith("R_") else "")
        mag = "15x" if "15x" in stem else ("20x" if "20x" in stem else "")
        if mag and side:
            mag_folder = f"{mag}Mag"
            side_folder = f"{mag}{side}"
            expected = base_dir / "T_Calib_20250314" / mag_folder / side_folder / target_name
            return expected.absolute()

        return (base_dir / target_name).absolute()

    def UpdateFestoStates(self):

        #obtain the states from the radio buttons in the class and format them properly        
        left_three_ndfs_binary = format(self.filter_variable_left.get(), '03b')
        left_iris_binary = format(self.iris_variable_left.get(), '01b')
        left_magnification_binary = format(self.magnification_variable_left.get(), '01b')

        right_three_ndfs_binary = format(self.filter_variable_right.get(), '03b')
        right_iris_binary = format(self.iris_variable_right.get(), '01b')
        right_magnification_binary = format(self.magnification_variable_right.get(), '01b')
        
        #create a string of 0s and 1s to send to the festo
        #left_state_binary_string = str(format(0b000,'03b')) + str(left_iris_binary) + str(left_three_ndfs_binary) + str(left_magnification_binary) + str(left_magnification_binary) + str(format(0b010,'03b')) 
        left_state_binary_string = str(format(0b010,'03b')) + str(left_magnification_binary) + str(left_magnification_binary) + str(left_three_ndfs_binary) + str(left_iris_binary) + str(format(0b001,'03b'))
        right_state_binary_string = str(format(0b100,'03b')) + str(right_iris_binary) + str(right_three_ndfs_binary) + str(right_magnification_binary) + str(right_magnification_binary) + str(format(0b010,'03b')) 

        #left_relay_list = list(map(int, left_state_binary_string))
        #left_relay_list = left_relay_list[::-1]
        #left_relay_list = left_relay_list[::-1]

       

        left_state_binary_string_totransmit = left_state_binary_string + str(format(0b0000,'04b'))
        #left_state_binary_string_totransmit = left_state_binary_string_totransmit[::-1]
        right_state_binary_string_totransmit = right_state_binary_string + str(format(0b0000,'04b'))

        #print(left_state_binary_string_totransmit)
        DenkTalk.write_relay_state(self.left_denkovi_com_port, left_state_binary_string_totransmit)
        DenkTalk.write_relay_state(self.right_denkovi_com_port, right_state_binary_string_totransmit)

        #Convert into numpy integer array used into the calibration 
        left_side_states = np.array(list(left_state_binary_string), dtype=int)
        right_side_states = np.array(list(right_state_binary_string), dtype=int)
        
        left_calib_result = self.LeftCalibrationChecking.compare_rows_return_calibration_file(left_side_states)
        right_calib_result = self.RightCalibrationChecking.compare_rows_return_calibration_file(right_side_states)

        print(left_calib_result)
        print(right_calib_result)

        left_exists = False
        right_exists = False

        if left_calib_result is not None:
            left_filename = left_calib_result[0] if isinstance(left_calib_result, (list, np.ndarray)) else str(left_calib_result)
            left_path = self.resolve_calibration_file_path(left_filename)
            left_exists = left_path.is_file() if left_path else False
            if left_path and self.calibration_file_select:
                self.calibration_file_select.update_left_calibration_file(left_path)

        if right_calib_result is not None:
            right_filename = right_calib_result[0] if isinstance(right_calib_result, (list, np.ndarray)) else str(right_calib_result)
            right_path = self.resolve_calibration_file_path(right_filename)
            right_exists = right_path.is_file() if right_path else False
            if right_path and self.calibration_file_select:
                self.calibration_file_select.update_right_calibration_file(right_path)

        if self.calibration_file_select:
            self.calibration_file_select.update_status(left_exists, right_exists)


class PlotGraphs(tk.Frame):
    def __init__(self, container, x_position, y_position, left_calibration_file, right_calibration_file, default_fit_file):
        #tk.Frame.__init__(self, container)
        super().__init__(container)

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

        self.left_temperature_label = tk.Label(self, text="TEST", font=('Helvetica', 15), background=theme.PANEL_BG)
        self.left_temperature_label.place(x=10, y= 10, width = 200, height = 50)

        # Setting default ROI variables in the class state
        self.left_roi_xo = 1
        self.left_roi_xf = 1339
        self.left_roi_yo = 0
        self.left_roi_yf = 34

        self.right_roi_xo = 1
        self.right_roi_xf = 1339
        self.right_roi_yo = 35
        self.right_roi_yf = 69

        self.current_frame_index = 0
        
        # Frame navigator controls
        self.btn_prev_frame = tk.Button(self, text="<", font=('Helvetica', 12, 'bold'), command=self.prev_frame)
        self.btn_prev_frame.place(x=320, y=30, width=30, height=30)
        
        self.frame_status_label = tk.Label(self, text="Frame: 1 / 1", font=('Helvetica', 12), background=theme.PANEL_BG)
        self.frame_status_label.place(x=360, y=30, width=120, height=30)

        self.btn_next_frame = tk.Button(self, text=">", font=('Helvetica', 12, 'bold'), command=self.next_frame)
        self.btn_next_frame.place(x=490, y=30, width=30, height=30)

        self.left_calibration_temperature = 2255
        self.right_calibration_temperature = 2255
        self.left_calibration_file = spe.SpeFile(left_calibration_file)
        self.right_calibration_file = spe.SpeFile(right_calibration_file)
        self.data_file = spe.SpeFile(default_fit_file)
        self.update_graphs()

    def prev_frame(self):
        if hasattr(self, 'data_file') and getattr(self.data_file, 'num_frames', 1) > 1:
            if self.current_frame_index > 0:
                self.current_frame_index -= 1
                self.update_graphs()

    def next_frame(self):
        if hasattr(self, 'data_file') and getattr(self.data_file, 'num_frames', 1) > 1:
            if self.current_frame_index < self.data_file.num_frames - 1:
                self.current_frame_index += 1
                self.update_graphs()


    def update_graphs(self):
        left_calibration_data = self.left_calibration_file
        measurement_data = self.data_file
        right_calibration_data = self.right_calibration_file


        ccd_information = left_calibration_data.img
        ccd_data_size = np.shape(left_calibration_data.img)

        # --- Handle multi-frame or single-frame measurement data ---
        num_frames = getattr(measurement_data, 'num_frames', 1)
        if num_frames > 1:
            # Bound the frame index just in case a new file has fewer frames
            if self.current_frame_index >= num_frames:
                self.current_frame_index = 0
            ccd_information2 = measurement_data.img[self.current_frame_index]
        else:
            self.current_frame_index = 0
            ccd_information2 = measurement_data.img
            
        # Update frame status UI
        self.frame_status_label.config(text=f"Frame: {self.current_frame_index + 1} / {num_frames}")
        
        # Toggle buttons based on frame bounds
        self.btn_prev_frame.config(state="normal" if self.current_frame_index > 0 else "disabled")
        self.btn_next_frame.config(state="normal" if self.current_frame_index < num_frames - 1 else "disabled")

        ccd_data_size2 = np.shape(ccd_information2)

        ccd_information3 = right_calibration_data.img
        ccd_data_size3 = np.shape(right_calibration_data.img)


        ccd_data_size3 = np.shape(right_calibration_data.img)


        #Left Spectrum
        left_x_axis_wavelengths = left_calibration_data.x_calibration[self.left_roi_xo:self.left_roi_xf]
        left_y_axis_ccd_selected_region = ccd_information[self.left_roi_yo:self.left_roi_yf, self.left_roi_xo:self.left_roi_xf]
        left_calibration_summed_ccd_selected_region = np.sum(left_y_axis_ccd_selected_region,axis=0)

        left_x_axis_wavelengths = measurement_data.x_calibration[self.left_roi_xo:self.left_roi_xf]
        left_y_axis_ccd_selected_region = ccd_information2[self.left_roi_yo:self.left_roi_yf, self.left_roi_xo:self.left_roi_xf]
        left_summed_ccd_selected_region = np.sum(left_y_axis_ccd_selected_region,axis=0)

        #Right Spectrum
        right_x_axis_wavelengths = right_calibration_data.x_calibration[self.right_roi_xo:self.right_roi_xf]
        right_y_axis_ccd_selected_region = ccd_information3[self.right_roi_yo:self.right_roi_yf, self.right_roi_xo:self.right_roi_xf]
        right_calibration_summed_ccd_selected_region = np.sum(right_y_axis_ccd_selected_region,axis=0)

        right_x_axis_wavelengths = measurement_data.x_calibration[self.right_roi_xo:self.right_roi_xf]
        right_y_axis_ccd_selected_region = ccd_information2[self.right_roi_yo:self.right_roi_yf, self.right_roi_xo:self.right_roi_xf]
        right_summed_ccd_selected_region = np.sum(right_y_axis_ccd_selected_region,axis=0)

        # Setting threshold to maximum size
        np.set_printoptions(threshold=sys.maxsize)
        #print(right_x_axis_wavelengths, right_calibration_summed_ccd_selected_region, right_summed_ccd_selected_region)    
        
        #Call the Temperature fitting class to get data for fit
        Estimated_Temperature_Left = tfit.Temperature_Measurement(1500, 0.5, self.left_calibration_temperature, left_x_axis_wavelengths, left_calibration_summed_ccd_selected_region, left_summed_ccd_selected_region)
        Estimated_Temperature_Right = tfit.Temperature_Measurement(1500, 0.5, self.right_calibration_temperature, right_x_axis_wavelengths, right_calibration_summed_ccd_selected_region, right_summed_ccd_selected_region)           

        self.left_wavelengths = left_x_axis_wavelengths
        self.left_fit = Estimated_Temperature_Left.gray_body_spectrum
        self.left_corrected = Estimated_Temperature_Left.unknown_graybody_spectrum
        self.left_raw = left_summed_ccd_selected_region

        self.right_wavelengths = right_x_axis_wavelengths
        self.right_fit = Estimated_Temperature_Right.gray_body_spectrum
        self.right_corrected = Estimated_Temperature_Right.unknown_graybody_spectrum
        self.right_raw = right_summed_ccd_selected_region

        
        #self.fig, self.axis = plt.subplots(2, 2)
        #plt.tight_layout()

        for row in self.axis:
            for single_axis in row:
                single_axis.clear()
                single_axis.set_facecolor(theme.PANEL_BG)

        self.axis[0, 0].plot(self.left_wavelengths, self.left_corrected, self.left_wavelengths, self.left_fit)
        self.axis[0, 0].set_title('LEFT FIT')

        self.axis[0, 1].plot(self.right_wavelengths, self.right_corrected, self.right_wavelengths, self.right_fit)
        self.axis[0, 1].set_title('RIGHT FIT')

        self.axis[1, 0].plot(self.left_wavelengths, self.left_raw)
        self.axis[1, 0].set_title('LEFT RAW')

        self.axis[1, 1].plot(self.right_wavelengths, self.right_raw)
        self.axis[1, 1].set_title('RIGHT RAW')
 
        self.graph_canvas = FigureCanvasTkAgg(self.fig, master=self)
        self.graph_canvas.draw()
        self.graph_canvas.get_tk_widget().place(x = 0, y = 0, width=928, height=638)
        
        left_temperature_string = "T= " + str(round(Estimated_Temperature_Left.fit_T)) + " +/- " + str(round(Estimated_Temperature_Left.sigT)) + " K"
        right_temperature_string = "T= " + str(round(Estimated_Temperature_Right.fit_T)) + " +/- " + str(round(Estimated_Temperature_Right.sigT)) + " K"

        # Place the labels containing the temperatures of the fit
        self.left_temperature_label = tk.Label(self, text=left_temperature_string, font=('Helvetica', 15), background=theme.PANEL_BG, anchor="w")# highlightbackground=theme.BORDER, highlightthickness=1)
        self.left_temperature_label.place(x=77, y= 30, width = 230, height = 30)

        self.right_temperature_label = tk.Label(self, text=right_temperature_string, font=('Helvetica', 15), background=theme.PANEL_BG, anchor="w")# highlightbackground=theme.BORDER, highlightthickness=1)
        self.right_temperature_label.place(x=530, y= 30, width = 230, height = 30)

class DataFileHandling(tk.Frame):
    def __init__(self, container, temperature_plots, calibration_files, x_position, y_position, autofit_folderpath):
        #tk.Frame.__init__(self, container)
        super().__init__(container)
        
        #Frame visual configuration
        self.configure(width=320,height=370,background=theme.PANEL_BG, highlightbackground=theme.BORDER, highlightthickness=1)
        
        #Frame position information
        self.place(x = x_position, y = y_position)
        self.plots = temperature_plots
        self.calibration_files = calibration_files

        #Check button variable
        self.automatic_fitting_button_state = tk.IntVar()
        self.auto_fitting_folder_path = tk.StringVar()

        # watchdog calls file_created() on its own background thread, but Tkinter/matplotlib
        # calls are only safe from the main thread. New files are handed off through this
        # thread-safe queue and actually processed in file_fitting_thread(), which runs on
        # the main thread via self.after().
        self._new_spe_file_queue = queue.Queue()
        self._spe_file_retry_counts = {}

        #Frame buttons and labels
        self.select_lightfield_spectra = tk.Button(self, text="Select Single .spe for T-fit", font=('Helvetica', 10), command=lambda: self.data_file_open_dialog(1))
        self.select_lightfield_spectra.place(x = 10, y = 10, width=300, height = 30)
        self.selected_lightfield_spectra = tk.Text(self, font=('Helvetica', 10), highlightbackground=theme.BORDER, highlightthickness=0, background=theme.TEXT_BG)
        self.selected_lightfield_spectra.place(x = 10, y = 50, width=300, height = 50)

        self.select_folder_to_save_tfit = tk.Button(self, text="Select Folder for T-fit", font=('Helvetica', 10), command=lambda: self.data_file_open_dialog(2))
        self.select_folder_to_save_tfit.place(x = 10, y = 110, width=300, height = 30)
        self.selected_folder_to_save_tfit = tk.Text(self, font=('Helvetica', 10), highlightbackground=theme.BORDER, highlightthickness=0, background=theme.TEXT_BG)
        self.selected_folder_to_save_tfit.place(x = 10, y = 150, width=300, height = 50)
        self.select_automatic_fit = tk.Checkbutton(self, text="Automatic Fitting", bg = theme.PANEL_BG, font=('Helvetica', 10), variable = self.automatic_fitting_button_state, command=lambda: self.automatic_file_fitting())
        self.select_automatic_fit.place(x = 10, y = 200, width= 150, height= 30)

        autofit_folderpath = Path(autofit_folderpath)
        autofit_folderpath = autofit_folderpath.absolute()
        self.selected_folder_to_save_tfit.insert("end-1c", autofit_folderpath)

        self.enter_output_filename = tk.Label(self, text="Enter output filename", font=('Helvetica', 10), highlightbackground=theme.BORDER, highlightthickness=1)
        self.enter_output_filename.place(x = 10, y = 250, width=300, height = 30)
        self.entered_output_filename = tk.Text(self, font=('Helvetica', 10), highlightbackground=theme.BORDER, highlightthickness=0, background=theme.TEXT_BG)
        self.entered_output_filename.place(x = 10, y = 290, width=300, height = 30)
        self.select_folder_to_save_tfit = tk.Button(self, text="Save Temperature Fit", font=('Helvetica', 10), command=lambda: self.data_file_open_dialog(2))
        self.select_folder_to_save_tfit.place(x = 10, y = 325, width=300, height = 30)

    # This is the event that watchdog calls when a new .spe file appears in the watched
    # folder. IMPORTANT: this runs on watchdog's own background thread, not the Tkinter
    # main thread, so it must NOT touch any Tkinter widgets or the matplotlib canvas
    # directly - doing so is unsafe and was the likely source of past intermittent
    # glitches. It only hands the path off; file_fitting_thread() does the real work.
    def file_created(self, event):
        self._new_spe_file_queue.put(event.src_path)

    # Runs on the main thread (via self.after below), so it's safe to update the plots here.
    def process_new_spe_file(self, file_path):
        try:
            if not self.calibration_files.has_valid_calibration():
                print(f"Skipping fit for {file_path}: This state doesn't have a Calibration File.")
                return True

            #Update the calibration files and temperatures
            left_calibration_file_location = r"{}".format(self.calibration_files.left_file_location.get("1.0",tk.END))
            left_calibration_file_location = left_calibration_file_location.replace("\n", "")

            right_calibration_file_location = r"{}".format(self.calibration_files.right_file_location.get("1.0",tk.END))
            right_calibration_file_location = right_calibration_file_location.replace("\n", "")

            #Update the calibration temperature values
            left_calibration_temperature = float(self.calibration_files.set_left_temperature.get("1.0",tk.END))
            right_calibration_temperature = float(self.calibration_files.set_right_temperature.get("1.0",tk.END))

            self.plots.left_calibration_temperature = left_calibration_temperature
            self.plots.right_calibration_temperature = right_calibration_temperature
            self.plots.left_calibration_file = spe.SpeFile(left_calibration_file_location)
            self.plots.right_calibration_file = spe.SpeFile(right_calibration_file_location)
            self.plots.data_file = spe.SpeFile(r'{}'.format(file_path))
            self.plots.current_frame_index = 0
            self.plots.update_graphs()
            return True
        except Exception as read_error:
            # Most likely the acquisition software is still writing this file - retry
            # on the next poll instead of losing it.
            print(f"Could not process {file_path} yet ({read_error})")
            return False

    def automatic_file_fitting(self):
        if self.automatic_fitting_button_state.get() == 1:
            print("Automatic file fitting enabled")

            #Create the watchdog that looks out for new .spe files created in selected directory
            self.folder_path = self.selected_folder_to_save_tfit.get("1.0",tk.END).strip()  # Current directory, can be changed to the desired folder path
            self.folder_path = self.folder_path.replace("/", "\\")
            self.my_event_handler = PatternMatchingEventHandler(patterns=["*.spe"], ignore_directories=True)
            self.my_event_handler.on_created = self.file_created
            self.my_observer = Observer()
            self.my_observer.schedule(self.my_event_handler, self.folder_path, recursive=True)

            #Starts watchdog and calls for function to check
            self.my_observer.start()
            self.file_fitting_thread()

    #Runs on the main thread. Drains any new files watchdog has queued up and processes
    #them here (where it's safe to touch the GUI), then waits until the checkbox is
    #unchecked to stop the watchdog.
    def file_fitting_thread(self):
        pending_files = []
        while not self._new_spe_file_queue.empty():
            pending_files.append(self._new_spe_file_queue.get())

        max_retries = 5
        for file_path in pending_files:
            if self.process_new_spe_file(file_path):
                self._spe_file_retry_counts.pop(file_path, None)
            else:
                retry_count = self._spe_file_retry_counts.get(file_path, 0) + 1
                if retry_count <= max_retries:
                    self._spe_file_retry_counts[file_path] = retry_count
                    self._new_spe_file_queue.put(file_path)
                else:
                    print(f"Giving up on {file_path} after {max_retries} attempts")
                    del self._spe_file_retry_counts[file_path]

        if self.automatic_fitting_button_state.get() == 1:
            self.after(1000, self.file_fitting_thread)
        else:
            print("Automatic file fitting disabled")
            self.my_observer.stop()
            self.my_observer.join()


    def data_file_open_dialog(self, file_location_number):
        #Differentiates between the light field spectra and the t-rax folder
        if file_location_number == 1:
            self.open_file_path = filedialog.askopenfilename(filetypes=[("Lightfield spectrum", "*.spe"), ("All files", "*.*")])
            if not self.open_file_path:
                return
            self.selected_lightfield_spectra.delete("1.0",tk.END)
            self.selected_lightfield_spectra.insert(tk.END, self.open_file_path)

            if not self.calibration_files.has_valid_calibration():
                print("Cannot fit data: This state doesn't have a Calibration File.")
                return

            #print(r'{}'.format(self.open_file_path))
            #self.plots.update_test()

            #Update the calibration files and temperatures
            left_calibration_file_location = r"{}".format(self.calibration_files.left_file_location.get("1.0",tk.END))            
            left_calibration_file_location = left_calibration_file_location.replace("\n", "")

            right_calibration_file_location = r"{}".format(self.calibration_files.right_file_location.get("1.0",tk.END))
            right_calibration_file_location = right_calibration_file_location.replace("\n", "")

            #Update the calibration temperature values
            left_calibration_temperature = float(self.calibration_files.set_left_temperature.get("1.0",tk.END))
            right_calibration_temperature = float(self.calibration_files.set_right_temperature.get("1.0",tk.END))

            #Update the values in the plots class
            self.plots.left_calibration_temperature = left_calibration_temperature
            self.plots.right_calibration_temperature = right_calibration_temperature
            self.plots.left_calibration_file = spe.SpeFile(left_calibration_file_location)
            self.plots.right_calibration_file = spe.SpeFile(right_calibration_file_location)
            self.plots.data_file = spe.SpeFile(r'{}'.format(self.open_file_path))
            self.plots.current_frame_index = 0
            self.plots.update_graphs()
            
        elif file_location_number == 2:
            self.open_folder_path = filedialog.askdirectory()
            #print(open_file_name)
            self.selected_folder_to_save_tfit.delete("1.0",tk.END)
            self.selected_folder_to_save_tfit.insert(tk.END, self.open_folder_path)        

class ROISelectionWindow(tk.Toplevel):
    def __init__(self, parent, plot_graphs_instance):
        super().__init__(parent)
        self.title("Dynamic ROI Configuration")
        self.geometry("900x700")
        
        theme.apply_dark_theme(self)
        theme.apply_dark_titlebar(self)
        
        self.plot_graphs = plot_graphs_instance
        
        # Get data for image
        if hasattr(self.plot_graphs, 'data_file') and self.plot_graphs.data_file is not None:
            measurement_data = self.plot_graphs.data_file
            num_frames = getattr(measurement_data, 'num_frames', 1)
            if num_frames > 1:
                img_data = measurement_data.img[self.plot_graphs.current_frame_index]
            else:
                img_data = measurement_data.img
        else:
            # Fallback to empty array
            img_data = np.zeros((100, 1340))
            
        # Left Panel - Image Plot
        self.fig, self.ax = plt.subplots(figsize=(6.5, 5.5))
        self.fig.patch.set_facecolor(theme.PANEL_BG)
        self.ax.set_facecolor(theme.PANEL_BG)
        
        # Calculate dynamic vmin/vmax to avoid blowing out contrast
        vmax = np.percentile(img_data, 99) if np.max(img_data) > 0 else 1000
        self.im = self.ax.imshow(img_data, aspect='auto', cmap='viridis', vmax=vmax)
        self.fig.colorbar(self.im, ax=self.ax)
        self.ax.set_title("CCD Image", color="white")
        self.ax.tick_params(colors="white")
        
        self.canvas = FigureCanvasTkAgg(self.fig, master=self)
        self.canvas.draw()
        self.canvas.get_tk_widget().place(x=10, y=10, width=650, height=650)
        
        # Right Panel - Controls
        control_frame = tk.Frame(self, bg=theme.PANEL_BG)
        control_frame.place(x=670, y=10, width=220, height=680)
        
        tk.Label(control_frame, text="Left Spectrum (Green)", bg=theme.PANEL_BG, fg="green", font=("Helvetica", 11, "bold")).pack(pady=(5, 2))
        
        # X and Y controls for Left
        tk.Label(control_frame, text="X-Start:", bg=theme.PANEL_BG, fg=theme.FG).pack()
        self.left_x_start_var = tk.StringVar(value=str(self.plot_graphs.left_roi_xo))
        tk.Spinbox(control_frame, from_=0, to=2048, textvariable=self.left_x_start_var, command=self.update_lines, bg=theme.TEXT_BG, fg=theme.FG).pack()
        self.left_x_start_var.trace("w", lambda name, index, mode: self.update_lines())

        tk.Label(control_frame, text="X-End:", bg=theme.PANEL_BG, fg=theme.FG).pack()
        self.left_x_end_var = tk.StringVar(value=str(self.plot_graphs.left_roi_xf))
        tk.Spinbox(control_frame, from_=0, to=2048, textvariable=self.left_x_end_var, command=self.update_lines, bg=theme.TEXT_BG, fg=theme.FG).pack()
        self.left_x_end_var.trace("w", lambda name, index, mode: self.update_lines())

        tk.Label(control_frame, text="Y-Start:", bg=theme.PANEL_BG, fg=theme.FG).pack()
        self.left_y_start_var = tk.StringVar(value=str(self.plot_graphs.left_roi_yo))
        tk.Spinbox(control_frame, from_=0, to=2048, textvariable=self.left_y_start_var, command=self.update_lines, bg=theme.TEXT_BG, fg=theme.FG).pack()
        self.left_y_start_var.trace("w", lambda name, index, mode: self.update_lines())
        
        tk.Label(control_frame, text="Y-End:", bg=theme.PANEL_BG, fg=theme.FG).pack()
        self.left_y_end_var = tk.StringVar(value=str(self.plot_graphs.left_roi_yf))
        tk.Spinbox(control_frame, from_=0, to=2048, textvariable=self.left_y_end_var, command=self.update_lines, bg=theme.TEXT_BG, fg=theme.FG).pack()
        self.left_y_end_var.trace("w", lambda name, index, mode: self.update_lines())
        
        tk.Label(control_frame, text="Right Spectrum (Red)", bg=theme.PANEL_BG, fg="red", font=("Helvetica", 11, "bold")).pack(pady=(15, 2))
        
        # X and Y controls for Right
        tk.Label(control_frame, text="X-Start:", bg=theme.PANEL_BG, fg=theme.FG).pack()
        self.right_x_start_var = tk.StringVar(value=str(self.plot_graphs.right_roi_xo))
        tk.Spinbox(control_frame, from_=0, to=2048, textvariable=self.right_x_start_var, command=self.update_lines, bg=theme.TEXT_BG, fg=theme.FG).pack()
        self.right_x_start_var.trace("w", lambda name, index, mode: self.update_lines())

        tk.Label(control_frame, text="X-End:", bg=theme.PANEL_BG, fg=theme.FG).pack()
        self.right_x_end_var = tk.StringVar(value=str(self.plot_graphs.right_roi_xf))
        tk.Spinbox(control_frame, from_=0, to=2048, textvariable=self.right_x_end_var, command=self.update_lines, bg=theme.TEXT_BG, fg=theme.FG).pack()
        self.right_x_end_var.trace("w", lambda name, index, mode: self.update_lines())

        tk.Label(control_frame, text="Y-Start:", bg=theme.PANEL_BG, fg=theme.FG).pack()
        self.right_y_start_var = tk.StringVar(value=str(self.plot_graphs.right_roi_yo))
        tk.Spinbox(control_frame, from_=0, to=2048, textvariable=self.right_y_start_var, command=self.update_lines, bg=theme.TEXT_BG, fg=theme.FG).pack()
        self.right_y_start_var.trace("w", lambda name, index, mode: self.update_lines())
        
        tk.Label(control_frame, text="Y-End:", bg=theme.PANEL_BG, fg=theme.FG).pack()
        self.right_y_end_var = tk.StringVar(value=str(self.plot_graphs.right_roi_yf))
        tk.Spinbox(control_frame, from_=0, to=2048, textvariable=self.right_y_end_var, command=self.update_lines, bg=theme.TEXT_BG, fg=theme.FG).pack()
        self.right_y_end_var.trace("w", lambda name, index, mode: self.update_lines())
        
        # Save / Load Config Buttons
        btn_frame = tk.Frame(control_frame, bg=theme.PANEL_BG)
        btn_frame.pack(pady=10)
        tk.Button(btn_frame, text="Load Config", command=self.load_config, font=("Helvetica", 9), bg=theme.PANEL_BG, fg=theme.FG).pack(side="left", padx=5)
        tk.Button(btn_frame, text="Save Config", command=self.save_config, font=("Helvetica", 9), bg=theme.PANEL_BG, fg=theme.FG).pack(side="left", padx=5)

        self.btn_apply = tk.Button(control_frame, text="Apply & Close", command=self.apply_and_close, font=("Helvetica", 11, "bold"), bg=theme.SELECT_BG, fg=theme.FG)
        self.btn_apply.pack(pady=10)
        
        # Bounding boxes references
        self.left_rect = None
        self.right_rect = None
        
        self.update_lines()

    def save_config(self):
        file_path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON files", "*.json")])
        if not file_path:
            return
        config = {
            "left_x_start": int(self.left_x_start_var.get()),
            "left_x_end": int(self.left_x_end_var.get()),
            "left_y_start": int(self.left_y_start_var.get()),
            "left_y_end": int(self.left_y_end_var.get()),
            "right_x_start": int(self.right_x_start_var.get()),
            "right_x_end": int(self.right_x_end_var.get()),
            "right_y_start": int(self.right_y_start_var.get()),
            "right_y_end": int(self.right_y_end_var.get())
        }
        with open(file_path, "w") as f:
            json.dump(config, f, indent=4)
            
    def load_config(self):
        file_path = filedialog.askopenfilename(filetypes=[("JSON files", "*.json")])
        if not file_path:
            return
        try:
            with open(file_path, "r") as f:
                config = json.load(f)
            self.left_x_start_var.set(str(config.get("left_x_start", 1)))
            self.left_x_end_var.set(str(config.get("left_x_end", 1339)))
            self.left_y_start_var.set(str(config.get("left_y_start", 0)))
            self.left_y_end_var.set(str(config.get("left_y_end", 34)))
            
            self.right_x_start_var.set(str(config.get("right_x_start", 1)))
            self.right_x_end_var.set(str(config.get("right_x_end", 1339)))
            self.right_y_start_var.set(str(config.get("right_y_start", 35)))
            self.right_y_end_var.set(str(config.get("right_y_end", 69)))
            
            self.update_lines()
        except Exception as e:
            print(f"Failed to load config: {e}")
        
    def update_lines(self):
        try:
            lx_start = int(self.left_x_start_var.get())
            lx_end = int(self.left_x_end_var.get())
            ly_start = int(self.left_y_start_var.get())
            ly_end = int(self.left_y_end_var.get())
            
            rx_start = int(self.right_x_start_var.get())
            rx_end = int(self.right_x_end_var.get())
            ry_start = int(self.right_y_start_var.get())
            ry_end = int(self.right_y_end_var.get())
        except ValueError:
            return # Ignore if not a valid integer
            
        if self.left_rect: self.left_rect.remove()
        if self.right_rect: self.right_rect.remove()
        
        # Rectangle(xy, width, height)
        # We use ly_start as y, and ly_end-ly_start as height
        self.left_rect = patches.Rectangle((lx_start, ly_start), lx_end - lx_start, ly_end - ly_start, 
                                           linewidth=2, edgecolor='green', facecolor='none', linestyle='--')
        self.ax.add_patch(self.left_rect)
        
        self.right_rect = patches.Rectangle((rx_start, ry_start), rx_end - rx_start, ry_end - ry_start, 
                                            linewidth=2, edgecolor='red', facecolor='none', linestyle='--')
        self.ax.add_patch(self.right_rect)
        
        self.canvas.draw_idle()
        
    def apply_and_close(self):
        try:
            self.plot_graphs.left_roi_xo = int(self.left_x_start_var.get())
            self.plot_graphs.left_roi_xf = int(self.left_x_end_var.get())
            self.plot_graphs.left_roi_yo = int(self.left_y_start_var.get())
            self.plot_graphs.left_roi_yf = int(self.left_y_end_var.get())
            
            self.plot_graphs.right_roi_xo = int(self.right_x_start_var.get())
            self.plot_graphs.right_roi_xf = int(self.right_x_end_var.get())
            self.plot_graphs.right_roi_yo = int(self.right_y_start_var.get())
            self.plot_graphs.right_roi_yf = int(self.right_y_end_var.get())
            
            self.plot_graphs.update_graphs()
            self.destroy()
        except ValueError:
            pass

class InitiateActonTfit(tk.Frame):
    #def __init__(self, x_position, y_position):
    #    tk.Frame.__init__(self)
    def __init__(self, container, x_position, y_position, left_denkovi_com_port, right_denkovi_com_port):
        #tk.Frame.__init__(self, container)
        super().__init__(container)

        #Frame visual configuration
        self.configure(width=1280,height=1000)

        #Frame position information
        self.place(x = x_position, y = y_position)

        self.right_calibration_file = r"TemperatureFit\\T_Calib_20250314\\15xMag\\R_2255K_15x_wI.spe"
        self.left_calibration_file = r"TemperatureFit\\T_Calib_20250314\\15xMag\\L_2255K_15x_wI.spe"
        self.autofit_folderpath = r"TemperatureFit"
        default_fit_file = r"TemperatureFit\\T_Calib_20250314\\15xMag\\R_2255K_15x_wI.spe"


        self.Logo = LogoDisplay(self, 10,10)
        self.CalibrationFileSelect = CalibrationFileSelection(self, 10, 90, self.left_calibration_file, self.right_calibration_file, self.autofit_folderpath)
        self.TransmissionFilter = TransmissionFilterSelection (self, 340, 60, left_denkovi_com_port, right_denkovi_com_port, calibration_file_select=self.CalibrationFileSelect)
        self.TransmissionFilter.place(x = 340, y = 60)

        self.Temperature_graphs = PlotGraphs(self, 340, 320, self.left_calibration_file, self.right_calibration_file, default_fit_file)
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


if __name__ == "__main__":

    mainwindow = tk.Tk()
    mainwindow.geometry('1280x1000')
    mainwindow.title("High T: Acton-PIXIS 400")

    A = InitiateActonTfit(mainwindow,0,0,"COM7","COM6")

    mainwindow.mainloop()


    