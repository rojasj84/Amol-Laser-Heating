"""Calibration selection and optical relay controls."""
import tkinter as tk
from tkinter import filedialog
from pathlib import Path
import numpy as np
import import_calibration as calib_find
import denkovi_serial as DenkTalk
import theme
from laser_heating.config import CalibrationSettings

default_calibration_temperature = 2255

class CalibrationFileSelection(tk.Frame):
    def __init__(self, container, x_position, y_position, left_calibration_file, right_calibration_file, autofit_folderpath):
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


    # Raw flatfields come from the Camera tab and need background subtraction.
    # Tracking by path means choosing any other calibration file clears it.
    def mark_raw_flatfield(self, file_path):
        if not hasattr(self, "_raw_flatfields"):
            self._raw_flatfields = set()
        self._raw_flatfields.add(str(Path(file_path).resolve()))

    def is_raw_flatfield(self, file_path):
        return bool(file_path) and str(Path(file_path).resolve()) in getattr(self, "_raw_flatfields", ())

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
        file_path = str(Path(file_path).resolve()) if file_path else ""
        self.left_file_location.config(state="normal")
        self.left_file_location.delete("1.0", tk.END)
        self.left_file_location.insert(tk.END, str(file_path))
        self.left_file_location.config(state="disabled")

    def update_right_calibration_file(self, file_path):
        file_path = str(Path(file_path).resolve()) if file_path else ""
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
            left_path = self.left_file_location.get("1.0", tk.END).strip()
            right_path = self.right_file_location.get("1.0", tk.END).strip()
            self.update_status(Path(left_path).is_file(), Path(right_path).is_file())


class TransmissionFilterSelection(tk.Frame):
    def __init__(self, container, x_position, y_position, left_denkovi_com_port, right_denkovi_com_port, calibration_file_select=None, calibration_settings=None):
        super().__init__(container)

        #Frame visual configuration
        self.configure(width=930,height=250,background=theme.PANEL_BG, highlightbackground=theme.BORDER, highlightthickness=1)

        #Frame position information
        self.x_position = x_position
        self.y_position = y_position
        #self.place(x = self.x_position, y = self.y_position)

        self.select_one_transmission_filter_logo = tk.Label(self, text = "Transmission filters", font=theme.FONT_HEADING, background=theme.PANEL_BG)
        self.select_one_transmission_filter_logo.place(x=5,y=5, width=920, height=30)

        self.select_one_transmission_filter_logo = tk.Label(self, text = "Iris and magnification", font=theme.FONT_HEADING, background=theme.PANEL_BG)
        self.select_one_transmission_filter_logo.place(x=5,y=135, width=920, height=30)

        self.left_denkovi_com_port = left_denkovi_com_port
        self.right_denkovi_com_port = right_denkovi_com_port
        self.calibration_file_select = calibration_file_select
        self.calibration_settings = calibration_settings or CalibrationSettings()


        # Filter Determination Raio Buttons for the Left Side

        self.filter_variable_left = tk.IntVar()
        self.iris_variable_left = tk.IntVar(value=1)
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

        if self.calibration_settings.use_filter_table:
            self.RightCalibrationChecking = calib_find.FestoStateCalibrationsCheck(self.calibration_settings.right_table)
            self.LeftCalibrationChecking = calib_find.FestoStateCalibrationsCheck(self.calibration_settings.left_table)

        self.select_one_transmission_filter_logo.place(x=30, y=139, width=870, height=24)
        # Color denotes the optical path; only selected options use a filled accent.
        for side, color, x in (("left", theme.LEFT_FG, 30), ("right", theme.RIGHT_FG, 510)):
            tk.Label(self, text=f"{side.upper()} OPTICAL PATH", fg=color, bg=theme.PANEL_BG,
                     font=(theme.FONT_FAMILY, 9, "bold"), anchor="w").place(x=x, y=34, width=390, height=16)
        for widget in self.winfo_children():
            if isinstance(widget, tk.Radiobutton):
                label = widget.cget("text")
                if label.endswith(" FILTER"):
                    widget.config(text="No filter" if label == "NO FILTER" else label.replace(" FILTER", ""))
                position = widget.place_info()
                y = int(position["y"])
                widget.place_configure(y={50: 56, 90: 94, 160: 174}.get(y, y),
                                       height=42 if y == 160 else 30)
        theme.modernize_widgets(self)
        self.UpdateFestoStates()

    def resolve_calibration_file_path(self, calib_name):
        return calib_find.resolve_calibration_file(calib_name, self.calibration_settings.root)

    def UpdateFestoStates(self):

        #obtain the states from the radio buttons in the class and format them properly
        left_three_ndfs_binary = format(self.filter_variable_left.get(), '03b')
        left_iris_binary = format(self.iris_variable_left.get(), '01b')
        left_magnification_binary = format(self.magnification_variable_left.get(), '01b')

        right_three_ndfs_binary = format(self.filter_variable_right.get(), '03b')
        right_iris_binary = format(self.iris_variable_right.get(), '01b')
        right_magnification_binary = format(self.magnification_variable_right.get(), '01b')

        #create a string of 0s and 1s to send to the festo
        left_state_binary_string = str(format(0b010,'03b')) + str(left_magnification_binary) + str(left_magnification_binary) + str(left_three_ndfs_binary) + str(left_iris_binary) + str(format(0b001,'03b'))
        right_state_binary_string = str(format(0b100,'03b')) + str(right_iris_binary) + str(right_three_ndfs_binary) + str(right_magnification_binary) + str(right_magnification_binary) + str(format(0b010,'03b'))




        left_state_binary_string_totransmit = left_state_binary_string + str(format(0b0000,'04b'))
        right_state_binary_string_totransmit = right_state_binary_string + str(format(0b0000,'04b'))

        DenkTalk.write_relay_state(self.left_denkovi_com_port, left_state_binary_string_totransmit)
        DenkTalk.write_relay_state(self.right_denkovi_com_port, right_state_binary_string_totransmit)

        if not self.calibration_settings.use_filter_table:
            if self.calibration_file_select:
                left = self.calibration_file_select.left_file_location.get("1.0", tk.END).strip()
                right = self.calibration_file_select.right_file_location.get("1.0", tk.END).strip()
                self.calibration_file_select.update_status(Path(left).is_file(), Path(right).is_file())
            return

        #Convert into numpy integer array used into the calibration
        left_side_states = np.array(list(left_state_binary_string), dtype=int)
        right_side_states = np.array(list(right_state_binary_string), dtype=int)

        left_calib_result = self.LeftCalibrationChecking.compare_rows_return_calibration_file(left_side_states)
        right_calib_result = self.RightCalibrationChecking.compare_rows_return_calibration_file(right_side_states)

        left_filename = left_calib_result[0] if left_calib_result is not None else None
        right_filename = right_calib_result[0] if right_calib_result is not None else None
        left_path = self.resolve_calibration_file_path(left_filename)
        right_path = self.resolve_calibration_file_path(right_filename)

        if self.calibration_file_select:
            # Always update both fields, including clearing an unavailable state.
            self.calibration_file_select.update_left_calibration_file(left_path)
            self.calibration_file_select.update_right_calibration_file(right_path)
            self.calibration_file_select.update_status(left_path is not None, right_path is not None)
