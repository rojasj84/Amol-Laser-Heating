import tkinter as tk
import numpy as np 
import sys
import ftd2xx

import import_calibration as calib_find
from pathlib import Path
import ftdi_denkokvi_control as ftdenk

from watchdog.observers import Observer
from watchdog.events import PatternMatchingEventHandler
from tkinter import filedialog
from matplotlib import pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

import TemperatureFit.TemperatureFitting as tfit
import TemperatureFit.SpeFile as spe

default_calubration_temperature = 2255

class LogoDisplay(tk.Frame):
    def __init__(self,container,x_position, y_position):
        #tk.Frame.__init__(self, container)
        super().__init__(container)

        #Frame visual configuration
        self.configure(width=1260,height=40,background="White", highlightbackground="black", highlightthickness=1)

        #Frame position information
        self.place(x = x_position, y = y_position)

        #Set logo
        self.logotext = tk.Label(self, text="High T : Acton-PIXIS 400", font=('Helvetica', 20), background="White")
        self.logotext.place(x = 5, y = 0, width=1250, height=35)

class CalibrationFileSelection(tk.Frame):
    def __init__(self, container, x_position, y_position, left_calibration_file, right_calibration_file, autofit_folderpath):
        #tk.Frame.__init__(self, container)
        super().__init__(container)
        
        #Frame visual configuration
        self.configure(width=320,height=320,background="White", highlightbackground="black", highlightthickness=1)
        
        #Frame position information
        self.x_position = x_position
        self.y_position = y_position
        self.place(x = self.x_position, y = self.y_position)

        #Left Side Calibration
        
        load_left_file = tk.Button(self, text="Select Left Calibration File", command=lambda: self.calibration_file_open_dialog(1), font=('Helvetica', 10))
        load_left_file.place(x = 10, y=10, width = 300, height=25)

        self.left_file_location = tk.Text(self, bg = "light gray", font=('Helvetica', 10))#, relief=tk.FLAT)
        self.left_file_location.place(x = 10, y=45, width = 300, height=50) 

        left_calibration_file = Path(left_calibration_file)
        left_calibration_file = left_calibration_file.absolute()
        self.left_file_location.insert("end-1c", left_calibration_file)
        
        self.set_left_temperature = tk.Text(self, background="light gray", font=('Helvetica', 10))
        self.set_left_temperature.place(x=210, y=100, width = 100, height=25)

        set_left_temperature_label = tk.Label(self, text="Left Calib. Temperature (K)",  borderwidth=2, relief="groove", background="white", font=('Helvetica', 10))
        set_left_temperature_label.place(x=10, y=100, width = 200, height=25)

        self.set_left_temperature.insert("end-1c", default_calubration_temperature)

        #Right Side Calibration
        
        load_right_file = tk.Button(self, text="Select Right Calibration File", command=lambda: self.calibration_file_open_dialog(2), font=('Helvetica', 10))
        load_right_file.place(x = 10, y=150, width = 300, height=25)

        self.right_file_location = tk.Text(self, bg = "light gray", font=('Helvetica', 10))#, relief=tk.FLAT)
        self.right_file_location.place(x = 10, y=185, width = 300, height=50) 
        
        right_calibration_file = Path(right_calibration_file)
        right_calibration_file = right_calibration_file.absolute()
        self.right_file_location.insert("end-1c", right_calibration_file)

        self.set_right_temperature = tk.Text(self, background="light gray", font=('Helvetica', 10))
        self.set_right_temperature.place(x=210, y=240, width = 100, height=25)

        set_right_temperature_label = tk.Label(self, text="Right Calib. Temperature (K)",  borderwidth=2, relief="groove", background="white", font=('Helvetica', 10))
        set_right_temperature_label.place(x=10, y=240, width = 200, height=25)

        self.set_right_temperature.insert("end-1c", default_calubration_temperature)
    

    def calibration_file_open_dialog(self, file_location_number):
        #Differentiates between the light field spectra and the t-rax folder
        open_file_path = filedialog.askopenfilename()
        if file_location_number == 1:
            #print(open_file_name)
            self.left_file_location.config(state="normal")
            self.left_file_location.delete("1.0",tk.END)
            self.left_file_location.insert(tk.END, open_file_path)
            self.left_file_location.config(state="disabled")
        elif file_location_number == 2:
            self.right_file_location.config(state="normal")
            self.right_file_location.delete("1.0",tk.END)
            self.right_file_location.insert(tk.END, open_file_path)
            self.right_file_location.config(state="disabled")        
    
class TransmissionFilterSelection(tk.Frame):
    def __init__(self, container, x_position, y_position):
        #tk.Frame.__init__(self, container)
        super().__init__(container)

        #Frame visual configuration
        self.configure(width=930,height=250,background="White", highlightbackground="black", highlightthickness=1)
        
        #Frame position information
        self.x_position = x_position
        self.y_position = y_position
        #self.place(x = self.x_position, y = self.y_position)

        self.select_one_transmission_filter_logo = tk.Label(self, text = "Select One Transmission Filter", font=('Helvetica', 15), background="White")
        self.select_one_transmission_filter_logo.place(x=5,y=5, width=920, height=30)

        self.select_one_transmission_filter_logo = tk.Label(self, text = "Select Iris Status and Magnification", font=('Helvetica', 15), background="White")
        self.select_one_transmission_filter_logo.place(x=5,y=135, width=920, height=30)

        
        ftdi_list = ftd2xx.listDevices() #Lists out all connected FTDI devices
        print(ftdi_list)
        # Device name is DAE004hC for Right
        # DAE004hB is Left

        self.left_denkovi_relays = ftdenk.RelayConnect(b'DAE004hB')
        self.right_denkovi_relays = ftdenk.RelayConnect(b'DAE004hC')
        
        # Filter Determination Raio Buttons for the Left Side
        
        self.filter_variable_left = tk.IntVar()
        self.iris_variable_left = tk.IntVar()
        self.magnifaction_varabile_left = tk.IntVar()        

        self.left_no_filter_selection = tk.Radiobutton(self,text="NO FILTER", font=('Helvetica', 10), indicatoron = 0, variable = self.filter_variable_left, value = 0b000, selectcolor="Light Blue", background="Light Blue", command=self.UpdateFestoStates) #Value corresponds to the binary state of 000 for all 3 NDFs
        self.left_no_filter_selection.place(x=30, y = 50, width=90, height=30)
        self.left_no_filter_selection.select()

        self.left_700_filter_selection = tk.Radiobutton(self,text="70% FILTER", font=('Helvetica', 10), indicatoron = 0, variable = self.filter_variable_left, value = 0b001, selectcolor="Light Blue", background="Light Blue", command=self.UpdateFestoStates) #NDF state 100, value 4
        self.left_700_filter_selection.place(x=130, y = 50, width=90, height=30)

        self.left_500_filter_selection = tk.Radiobutton(self,text="50% FILTER", font=('Helvetica', 10), indicatoron = 0, variable = self.filter_variable_left, value = 0b010, selectcolor="Light Blue", background="Light Blue", command=self.UpdateFestoStates) #NDF state 010, value 2
        self.left_500_filter_selection.place(x=230, y = 50, width=90, height=30)

        self.left_350_filter_selection = tk.Radiobutton(self,text="35% FILTER", font=('Helvetica', 10), indicatoron = 0, variable = self.filter_variable_left, value = 0b011, selectcolor="Light Blue", background="Light Blue", command=self.UpdateFestoStates) #NDF state 110, value 6
        self.left_350_filter_selection.place(x=330, y = 50, width=90, height=30)
        
        self.left_100_filter_selection = tk.Radiobutton(self,text="10% FILTER", font=('Helvetica', 10), indicatoron = 0, variable = self.filter_variable_left, value = 0b100, selectcolor="Light Blue", background="Light Blue", command=self.UpdateFestoStates) #NDF state 001, value 1
        self.left_100_filter_selection.place(x=30, y = 90, width=90, height=30)

        self.left_070_filter_selection = tk.Radiobutton(self,text="7% FILTER", font=('Helvetica', 10), indicatoron = 0, variable = self.filter_variable_left, value = 0b101, selectcolor="Light Blue", background="Light Blue", command=self.UpdateFestoStates) #NDF state 101, value 5
        self.left_070_filter_selection.place(x=130, y = 90, width=90, height=30)

        self.left_050_filter_selection = tk.Radiobutton(self,text="5% FILTER", font=('Helvetica', 10), indicatoron = 0, variable = self.filter_variable_left, value = 0b110, selectcolor="Light Blue", background="Light Blue", command=self.UpdateFestoStates) #NDF state 011, value 3
        self.left_050_filter_selection.place(x=230, y = 90, width=90, height=30)

        self.left_035_filter_selection = tk.Radiobutton(self,text="3.5% FILTER", font=('Helvetica', 10), indicatoron = 0, variable = self.filter_variable_left, value = 0b111, selectcolor="Light Blue", background="Light Blue", command=self.UpdateFestoStates) #NDF state 111, value 7
        self.left_035_filter_selection.place(x=330, y = 90, width=90, height=30)

        self.left_iris_selection_out = tk.Radiobutton(self, text = "Iris Out", font=('Helvetica', 12), indicatoron=0, variable=self.iris_variable_left, value = 0b0, selectcolor="Light Blue", background="Light Blue", command=self.UpdateFestoStates)
        self.left_iris_selection_out.place(x = 30, y = 160, width=90, height=50)
        
        self.left_iris_selection_in = tk.Radiobutton(self, text = "Iris In", font=('Helvetica', 12), indicatoron=0, variable=self.iris_variable_left, value = 0b1, selectcolor="Light Blue", background="Light Blue", command=self.UpdateFestoStates)
        self.left_iris_selection_in.place(x = 130, y = 160, width=90, height=50)

        self.left_magnification_selection_15 = tk.Radiobutton(self, text = "15x", font=('Helvetica', 12), indicatoron=0, variable=self.magnifaction_varabile_left, value = 0b0, selectcolor="Light Blue", background="Light Blue", command=self.UpdateFestoStates)
        self.left_magnification_selection_15.place(x = 230, y = 160, width=90, height=50)
        
        self.left_magnification_selection_20 = tk.Radiobutton(self, text = "20x", font=('Helvetica', 12), indicatoron=0, variable=self.magnifaction_varabile_left, value = 0b1, selectcolor="Light Blue", background="Light Blue", command=self.UpdateFestoStates)
        self.left_magnification_selection_20.place(x = 330, y = 160, width=90, height=50)

        # Filter Determination Raio Buttons for the Right Side
        
        self.filter_variable_right = tk.IntVar()
        self.iris_variable_right = tk.IntVar()
        self.magnifaction_varabile_right = tk.IntVar()

        self.right_no_filter_selection = tk.Radiobutton(self,text="NO FILTER", font=('Helvetica', 10), indicatoron = 0, variable = self.filter_variable_right, value = 0b000, selectcolor="Pink", background="Pink", command=self.UpdateFestoStates)
        self.right_no_filter_selection.place(x=930-90-330, y = 50, width=90, height=30)
        self.right_no_filter_selection.select()

        self.right_700_filter_selection = tk.Radiobutton(self,text="70% FILTER", font=('Helvetica', 10), indicatoron = 0, variable = self.filter_variable_right, value = 0b100, selectcolor="Pink", background="Pink", command=self.UpdateFestoStates)
        self.right_700_filter_selection.place(x=930-90-230, y = 50, width=90, height=30)

        self.right_500_filter_selection = tk.Radiobutton(self,text="50% FILTER", font=('Helvetica', 10), indicatoron = 0, variable = self.filter_variable_right, value = 0b010, selectcolor="Pink", background="Pink", command=self.UpdateFestoStates)
        self.right_500_filter_selection.place(x=930-90-130, y = 50, width=90, height=30)

        self.right_350_filter_selection = tk.Radiobutton(self,text="35% FILTER", font=('Helvetica', 10), indicatoron = 0, variable = self.filter_variable_right, value = 0b110, selectcolor="Pink", background="Pink", command=self.UpdateFestoStates)
        self.right_350_filter_selection.place(x=930-90-30, y = 50, width=90, height=30)
        
        self.right_100_filter_selection = tk.Radiobutton(self,text="10% FILTER", font=('Helvetica', 10), indicatoron = 0, variable = self.filter_variable_right, value = 0b001, selectcolor="Pink", background="Pink", command=self.UpdateFestoStates)
        self.right_100_filter_selection.place(x=930-90-330, y = 90, width=90, height=30)

        self.right_070_filter_selection = tk.Radiobutton(self,text="7% FILTER", font=('Helvetica', 10), indicatoron = 0, variable = self.filter_variable_right, value = 0b101, selectcolor="Pink", background="Pink", command=self.UpdateFestoStates)
        self.right_070_filter_selection.place(x=930-90-230, y = 90, width=90, height=30)

        self.right_050_filter_selection = tk.Radiobutton(self,text="5% FILTER", font=('Helvetica', 10), indicatoron = 0, variable = self.filter_variable_right, value = 0b011, selectcolor="Pink", background="Pink", command=self.UpdateFestoStates)
        self.right_050_filter_selection.place(x=930-90-130, y = 90, width=90, height=30)

        self.right_035_filter_selection = tk.Radiobutton(self,text="3.5% FILTER", font=('Helvetica', 10), indicatoron = 0, variable = self.filter_variable_right, value = 0b111, selectcolor="Pink", background="Pink", command=self.UpdateFestoStates)
        self.right_035_filter_selection.place(x=930-90-30, y = 90, width=90, height=30)

        self.right_iris_selection_out = tk.Radiobutton(self, text = "Iris Out", font=('Helvetica', 12), indicatoron=0, variable=self.iris_variable_right, value = 0, selectcolor="Pink", background="Pink", command=self.UpdateFestoStates)
        self.right_iris_selection_out.place(x = 930-90-330, y = 160, width=90, height=50)
        
        self.right_iris_selection_in = tk.Radiobutton(self, text = "Iris In", font=('Helvetica', 12), indicatoron=0, variable=self.iris_variable_right, value = 1, selectcolor="Pink", background="Pink", command=self.UpdateFestoStates)
        self.right_iris_selection_in.place(x = 930-90-230, y = 160, width=90, height=50)

        self.right_magnification_selection_15 = tk.Radiobutton(self, text = "15x", font=('Helvetica', 12), indicatoron=0, variable=self.magnifaction_varabile_right, value = 0, selectcolor="Pink", background="Pink", command=self.UpdateFestoStates)
        self.right_magnification_selection_15.place(x = 930-90-130, y = 160, width=90, height=50)
        
        self.right_magnification_selection_20 = tk.Radiobutton(self, text = "20x", font=('Helvetica', 12), indicatoron=0, variable=self.magnifaction_varabile_right, value = 1, selectcolor="Pink", background="Pink", command=self.UpdateFestoStates)
        self.right_magnification_selection_20.place(x = 930-90-30, y = 160, width=90, height=50)

        #self.CalibrationChecking = calib_find.FestoStateCalibrationsCheck("TemperatureFit\calibration_file_table.csv")
        self.RightCalibrationChecking = calib_find.FestoStateCalibrationsCheck("TemperatureFit\calibration_file_table_right_side.csv")
        self.LeftCalibrationChecking = calib_find.FestoStateCalibrationsCheck("TemperatureFit\calibration_file_table_left_side.csv")

        self.UpdateFestoStates()

    def UpdateFestoStates(self):

        #obtain the states from the radio buttons in the class and format them properly        
        left_three_ndfs_binary = format(self.filter_variable_left.get(), '03b')
        left_iris_binary = format(self.iris_variable_left.get(), '01b')
        left_magnification_binary = format(self.magnifaction_varabile_left.get(), '01b')

        right_three_ndfs_binary = format(self.filter_variable_right.get(), '03b')
        right_iris_binary = format(self.iris_variable_right.get(), '01b')
        right_magnification_binary = format(self.magnifaction_varabile_right.get(), '01b')
        
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
        self.left_denkovi_relays.write_relay_state(left_state_binary_string_totransmit)
        self.right_denkovi_relays.write_relay_state(right_state_binary_string_totransmit)

        #Convert into numpy integer array used into the calibration 
        left_side_states = np.array(list(left_state_binary_string), dtype=int)
        right_side_states = np.array(list(right_state_binary_string), dtype=int)
        
        print(self.LeftCalibrationChecking.compare_rows_return_calibration_file(left_side_states))
        print(self.RightCalibrationChecking.compare_rows_return_calibration_file(right_side_states))


class PlotGraphs(tk.Frame):
    def __init__(self, container, x_position, y_position, left_calibration_file, right_calibration_file, default_fit_file):
        #tk.Frame.__init__(self, container)
        super().__init__(container)

        #Frame visual configuration
        self.configure(width=930,height=640,background="White", highlightbackground="black", highlightthickness=1)
        
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

        self.left_temperature_label = tk.Label(self, text="TEST", font=('Helvetica', 15), background="White")
        self.left_temperature_label.place(x=10, y= 10, width = 200, height = 50)

        self.left_calibration_temperature = 2255
        self.right_calibration_temperature = 2255
        self.left_calibration_file = spe.SpeFile(left_calibration_file)
        self.right_calibration_file = spe.SpeFile(right_calibration_file)
        self.data_file = spe.SpeFile(default_fit_file)
        self.update_graphs()

    def update_graphs(self):
        A = self.left_calibration_file
        B = self.data_file
        C = self.right_calibration_file


        ccd_information = A.img
        ccd_data_size = np.shape(A.img)

        ccd_information2 = B.img
        ccd_data_size2 = np.shape(B.img)

        ccd_information3 = C.img
        ccd_data_size3 = np.shape(C.img)


        #Setting an ROI for testing purposes 
        self.left_roi_xo = 50
        self.left_roi_xf = 1004
        self.left_roi_yo = 13
        self.left_roi_yf = 27

        self.right_roi_xo = 50
        self.right_roi_xf = 1004
        self.right_roi_yo = 41
        self.right_roi_yf = 55

        
        #Setting an ROI for testing purposes 
        self.left_roi_xo = 1
        self.left_roi_xf = 1339
        self.left_roi_yo = 0
        self.left_roi_yf = 34

        self.right_roi_xo = 1
        self.right_roi_xf = 1339
        self.right_roi_yo = 35
        self.right_roi_yf = 69
        
        #print(A.x_calibration)
        #print(A.roi_width)
        #print(A.roi_y)
        #print(A.roi_height)
        
        
        #Left Spectrum
        left_x_axis_wavelengths = A.x_calibration[self.left_roi_xo:self.left_roi_xf]        
        left_y_axis_ccd_selected_region = ccd_information[self.left_roi_yo:self.left_roi_yf, self.left_roi_xo:self.left_roi_xf]
        left_calibration_summed_ccd_selected_region = np.sum(left_y_axis_ccd_selected_region,axis=0)
        
        left_x_axis_wavelengths = B.x_calibration[self.left_roi_xo:self.left_roi_xf]
        left_y_axis_ccd_selected_region = ccd_information2[self.left_roi_yo:self.left_roi_yf, self.left_roi_xo:self.left_roi_xf]
        left_summed_ccd_selected_region = np.sum(left_y_axis_ccd_selected_region,axis=0)

        #Right Spectrum
        right_x_axis_wavelengths = C.x_calibration[self.right_roi_xo:self.right_roi_xf]        
        right_y_axis_ccd_selected_region = ccd_information3[self.right_roi_yo:self.right_roi_yf, self.right_roi_xo:self.right_roi_xf]
        right_calibration_summed_ccd_selected_region = np.sum(right_y_axis_ccd_selected_region,axis=0)
        
        right_x_axis_wavelengths = B.x_calibration[self.right_roi_xo:self.right_roi_xf]
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

        self.axis[0, 0].clear()
        self.axis[0, 0].plot(self.left_wavelengths, self.left_corrected, self.left_wavelengths, self.left_fit)
        self.axis[0, 0].set_title('LEFT FIT')

        self.axis[0, 1].clear()
        self.axis[0, 1].plot(self.right_wavelengths, self.right_corrected, self.right_wavelengths, self.right_fit)
        self.axis[0, 1].set_title('RIGHT FIT')

        self.axis[1, 0].clear()
        self.axis[1, 0].plot(self.left_wavelengths, self.left_raw)
        self.axis[1, 0].set_title('LEFT RAW')

        self.axis[1, 1].clear()
        self.axis[1, 1].plot(self.right_wavelengths, self.right_raw)
        self.axis[1, 1].set_title('RIGHT RAW')
 
        self.graph_canvas = FigureCanvasTkAgg(self.fig, master=self)
        self.graph_canvas.draw()
        self.graph_canvas.get_tk_widget().place(x = 0, y = 0, width=928, height=638)
        
        left_temperature_string = "T= " + str(round(Estimated_Temperature_Left.fit_T)) + " +/- " + str(round(Estimated_Temperature_Left.sigT)) + " K"
        right_temperature_string = "T= " + str(round(Estimated_Temperature_Right.fit_T)) + " +/- " + str(round(Estimated_Temperature_Right.sigT)) + " K"

        # Place the labels containing the temepratures of the fit
        self.left_temperature_label = tk.Label(self, text=left_temperature_string, font=('Helvetica', 15), background="White", anchor="w")# highlightbackground="black", highlightthickness=1)
        self.left_temperature_label.place(x=77, y= 30, width = 200, height = 30)

        self.left_temperature_label = tk.Label(self, text=right_temperature_string, font=('Helvetica', 15), background="White", anchor="w")# highlightbackground="black", highlightthickness=1)
        self.left_temperature_label.place(x=530, y= 30, width = 200, height = 30)

class DataFileHandling(tk.Frame):
    def __init__(self, container, temperature_plots, calibration_files, x_position, y_position, autofit_folderpath):
        #tk.Frame.__init__(self, container)
        super().__init__(container)
        
        #Frame visual configuration
        self.configure(width=320,height=370,background="White", highlightbackground="black", highlightthickness=1)
        
        #Frame position information
        self.place(x = x_position, y = y_position)
        self.plots = temperature_plots
        self.calibration_files = calibration_files

        #Check button variable
        self.automatic_fitting_button_state = tk.IntVar()
        self.auto_fitting_folder_path = tk.StringVar()

        #Frame buttons and labels
        self.select_lightfield_spectra = tk.Button(self, text="Select Single .spe for T-fit", font=('Helvetica', 10), command=lambda: self.data_file_open_dialog(1))
        self.select_lightfield_spectra.place(x = 10, y = 10, width=300, height = 30)
        self.selected_lightfield_spectra = tk.Text(self, font=('Helvetica', 10), highlightbackground="black", highlightthickness=0, background="Light Gray")
        self.selected_lightfield_spectra.place(x = 10, y = 50, width=300, height = 50)

        self.select_folder_to_save_tfit = tk.Button(self, text="Select Folder for T-fit", font=('Helvetica', 10), command=lambda: self.data_file_open_dialog(2))
        self.select_folder_to_save_tfit.place(x = 10, y = 110, width=300, height = 30)
        self.selected_folder_to_save_tfit = tk.Text(self, font=('Helvetica', 10), highlightbackground="black", highlightthickness=0, background="Light Gray")
        self.selected_folder_to_save_tfit.place(x = 10, y = 150, width=300, height = 50)
        self.select_automatic_fit = tk.Checkbutton(self, text="Automatic Fitting", bg = "White", font=('Helvetica', 10), variable = self.automatic_fitting_button_state, command=lambda: self.automatic_file_fitting())
        self.select_automatic_fit.place(x = 10, y = 200, width= 150, height= 30)

        autofit_folderpath = Path(autofit_folderpath)
        autofit_folderpath = autofit_folderpath.absolute()
        self.selected_folder_to_save_tfit.insert("end-1c", autofit_folderpath)

        self.enter_output_filename = tk.Label(self, text="Enter output filename", font=('Helvetica', 10), highlightbackground="black", highlightthickness=1)
        self.enter_output_filename.place(x = 10, y = 250, width=300, height = 30)
        self.entered_output_filename = tk.Text(self, font=('Helvetica', 10), highlightbackground="black", highlightthickness=0, background="Light Gray")
        self.entered_output_filename.place(x = 10, y = 290, width=300, height = 30)
        self.select_folder_to_save_tfit = tk.Button(self, text="Save Temperature Fit", font=('Helvetica', 10), command=lambda: self.data_file_open_dialog(2))
        self.select_folder_to_save_tfit.place(x = 10, y = 325, width=300, height = 30)

    # Create the handling for adding an spe file automatically when created in the folder
    #This is the event that watchdog is looking for.
    def file_created(self, event):
        #print(f"hey, {event.src_path} has been created!")
        #Update the values in the plots class

        #Update the calibration files and temperatures
        left_calibration_file_location = r"{}".format(self.calibration_files.left_file_location.get("1.0",tk.END))            
        left_calibration_file_location = left_calibration_file_location.replace("\n", "")

        right_calibration_file_location = r"{}".format(self.calibration_files.right_file_location.get("1.0",tk.END))
        right_calibration_file_location = right_calibration_file_location.replace("\n", "")

        #Update the calibration temperature values
        left_calibration_temperature = float(self.calibration_files.set_left_temperature.get("1.0",tk.END))
        right_calibration_temperature = float(self.calibration_files.set_left_temperature.get("1.0",tk.END))

        self.plots.left_calibration_temperature = left_calibration_temperature
        self.plots.right_calibration_temperature = right_calibration_temperature
        self.plots.left_calibration_file = spe.SpeFile(left_calibration_file_location)
        self.plots.right_calibration_file = spe.SpeFile(right_calibration_file_location)
        self.plots.data_file = spe.SpeFile(r'{}'.format(event.src_path))
        self.plots.update_graphs()

    def automatic_file_fitting(self):
        if self.automatic_fitting_button_state.get() == 1:
            print("Automatic file fitting enabled")

            #Create the watchdog that looks out for new files created in selected directory
            self.folder_path = self.selected_folder_to_save_tfit.get("1.0",tk.END).strip()  # Current directory, can be changed to the desired folder path
            self.folder_path = self.folder_path.replace("/", "\\")        
            self.my_event_handler = PatternMatchingEventHandler()
            self.my_event_handler.on_created = self.file_created
            self.my_observer = Observer()
            self.my_observer.schedule(self.my_event_handler, self.folder_path, recursive=True)

            #Starts watchdog and calls for function to check
            self.my_observer.start()
            self.file_fitting_thread()
    
    #Checks for new files and waits until the checkbox is unchecked to stop the watchdog
    def file_fitting_thread(self):
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
            #print(open_file_name)
            self.selected_lightfield_spectra.delete("1.0",tk.END)
            self.selected_lightfield_spectra.insert(tk.END, self.open_file_path)

            #print(r'{}'.format(self.open_file_path))
            #self.plots.update_test()

            #Update the calibration files and temperatures
            left_calibration_file_location = r"{}".format(self.calibration_files.left_file_location.get("1.0",tk.END))            
            left_calibration_file_location = left_calibration_file_location.replace("\n", "")

            right_calibration_file_location = r"{}".format(self.calibration_files.right_file_location.get("1.0",tk.END))
            right_calibration_file_location = right_calibration_file_location.replace("\n", "")

            #Update the calibration temperature values
            left_calibration_temperature = float(self.calibration_files.set_left_temperature.get("1.0",tk.END))
            right_calibration_temperature = float(self.calibration_files.set_left_temperature.get("1.0",tk.END))

            #Update the values in the plots class
            self.plots.left_calibration_temperature = left_calibration_temperature
            self.plots.right_calibration_temperature = right_calibration_temperature
            self.plots.left_calibration_file = spe.SpeFile(left_calibration_file_location)
            self.plots.right_calibration_file = spe.SpeFile(right_calibration_file_location)
            self.plots.data_file = spe.SpeFile(r'{}'.format(self.open_file_path))
            self.plots.update_graphs()
            
        elif file_location_number == 2:
            self.open_folder_path = filedialog.askdirectory()
            #print(open_file_name)
            self.selected_folder_to_save_tfit.delete("1.0",tk.END)
            self.selected_folder_to_save_tfit.insert(tk.END, self.open_folder_path)        

class InitiateActonTfit(tk.Frame):
    #def __init__(self, x_position, y_position):
    #    tk.Frame.__init__(self)
    def __init__(self, container, x_position, y_position):
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
        # CalibrationFile = CalibrationFileSelection(10, 360)
        self.TransmissionFilter = TransmissionFilterSelection (self, 340, 60)
        self.TransmissionFilter.place(x = 340, y = 60)

        self.Tempreature_graphs = PlotGraphs(self, 340, 320, self.left_calibration_file, self.right_calibration_file, default_fit_file)
        self.CalibrationFileSelect = CalibrationFileSelection(self, 10, 90, self.left_calibration_file, self.right_calibration_file, self.autofit_folderpath)
        self.DataFileSelect = DataFileHandling(self, self.Tempreature_graphs, self.CalibrationFileSelect, 10, 90, self.autofit_folderpath)
        
        self.DataFileSelect_placedata = self.DataFileSelect.place_info()
        self.CalibrationFileSelect_placedata = self.CalibrationFileSelect.place_info()

        self.show_data_selection_window = tk.Button(self, text="Temperature Fit", command=lambda: self.select_file_handling(2))
        self.show_data_selection_window.place(x = 170, y = 60, width = 160, height = 25)
        self.show_data_selection_window.config(state="disable")

        #Buttons for showing the correct file handling window
        self.show_calibration_selection_window = tk.Button(self, text="Calibration Selection", command=lambda: self.select_file_handling(1))
        self.show_calibration_selection_window.place(x = 10, y = 60, width = 160, height = 25)
        self.show_calibration_selection_window.config(state="active")

    def select_file_handling(self, input):
        x = 0
        if input == 1:
            self.DataFileSelect.place_forget()
            self.CalibrationFileSelect.place(self.CalibrationFileSelect_placedata)
            self.show_data_selection_window.config(state="active")
            self.show_calibration_selection_window.config(state="disabled")
        elif input == 2:
            self.CalibrationFileSelect.place_forget()
            self.DataFileSelect.place(self.DataFileSelect_placedata)
            self.show_calibration_selection_window.config(state="active")
            self.show_data_selection_window.config(state="disabled")


if __name__ == "__main__":

    mainwindow = tk.Tk()
    mainwindow.geometry('1280x1000')
    mainwindow.title("High T: Acton-PIXIS 400")

    A = InitiateActonTfit(mainwindow,0,0)

    mainwindow.mainloop()


    