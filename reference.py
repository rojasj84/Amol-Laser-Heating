# Importing libraries
import tkinter as tk
import time
from PIL import ImageTk, Image
from threading import Thread

# Importing local .py files
from instrument_gauges import rotery_gauge
from niusb6001 import read_ai
from denkser import setbit
from denkser import readdenk

#Create Classes
class GaugeImage(tk.Frame):
    def __init__(self, container, min_pressure, max_pressure, pressure_value, scale, x_position, y_position, analog_port):
        super().__init__(container)

        # Variables for the gauge
        self.min_pressure = min_pressure
        self.max_pressure = max_pressure
        self.pressure_value = pressure_value
        self.scale = scale
        self.x_position = x_position
        self.y_position = y_position
        self.analog_port = analog_port

        #Variables for displaying
        frame_padding = 2

        img_CLP = rotery_gauge(min_pressure,max_pressure,pressure_value)
        img_width, img_height = img_CLP.size
        img_CLP = img_CLP.resize((img_width // scale, img_height // scale), resample=Image.Resampling.LANCZOS)
        img_CLP = ImageTk.PhotoImage(img_CLP)

        frame_height = (img_width / scale) + frame_padding + 50
        frame_width = (img_width / scale) + frame_padding + 2

        # show the frame on the container
        self.config(background=win_color)
        self.place(x=x_position,y=y_position,height = frame_height,width = frame_width)

        # display gauge               
        self.pressure_gauge = tk.Label(self, image = img_CLP, background=win_color)
        self.pressure_gauge.image = img_CLP # keep a reference!
        self.pressure_gauge.place(x=frame_padding/2,y=frame_padding/2)        
        
        # pressure numbers display
        self.pressure_numbers = tk.Label(self,text= str(pressure_value) + " psi", background=win_color,font=('Helvatical bold',15), justify=tk.RIGHT, bg="White", highlightthickness=2, highlightbackground="Black")
        self.pressure_numbers.place(x=0,y=frame_height-40, height = 30, width=frame_width)

        self.update_gauge_data()

    def update_gauge_data(self):

        refresh_time = 100 #Milliseconds 

        self.pressure_value = int(read_ai(self.analog_port)*self.max_pressure/5)

        #Variables for displaying
        frame_padding = 2

        # updating valve image
        img_CLP = rotery_gauge(self.min_pressure,self.max_pressure,self.pressure_value)
        img_width, img_height = img_CLP.size
        img_CLP = img_CLP.resize((img_width // self.scale, img_height // self.scale), resample=Image.Resampling.LANCZOS)
        img_CLP = ImageTk.PhotoImage(img_CLP)

        # updating display gauge               
        self.pressure_gauge.config(image=img_CLP)
        self.pressure_gauge.image = img_CLP
        
        # updating pressure numbers display
        self.pressure_numbers.config(text = str(self.pressure_value) + " psi")

        self.after(refresh_time,self.update_gauge_data)

class AirLinePressure(tk.Frame):
    def __init__(self, container, min_pressure, max_pressure, pressure_value, x_position, y_position, analog_port):
        super().__init__(container)

        # Variables for the gauge
        self.min_pressure = min_pressure
        self.max_pressure = max_pressure
        self.pressure_value = pressure_value
        self.x_position = x_position
        self.y_position = y_position
        self.analog_port = analog_port

        #Variables for displaying
        frame_padding = 2

        img_width = 200
        img_height = 70

        # show the frame on the container
        self.config(background=win_color)
        self.place(x=x_position,y=y_position,height = img_height,width = img_width)     
        
         # pressure numbers display
        self.pressure_label = tk.Label(self,text= "Airline Pressure", background=win_color,font=('Helvatical bold',15), justify=tk.RIGHT, bg=win_color, highlightthickness=0, highlightbackground="Black")
        self.pressure_label.place(x=0,y=0, height = img_height/2, width=img_width)
        
        # pressure numbers display
        self.pressure_numbers = tk.Label(self,text= str(pressure_value) + " psi", background=win_color,font=('Helvatical bold',15), justify=tk.RIGHT, bg="White", highlightthickness=2, highlightbackground="Black")
        self.pressure_numbers.place(x=0,y=35, height = img_height/2, width=img_width)

        self.update_gauge_data()

    def update_gauge_data(self):

        refresh_time = 100 #Milliseconds 

        self.pressure_value = int(read_ai(self.analog_port)*self.max_pressure/5)
        
        # updating pressure numbers display
        self.pressure_numbers.config(text = str(self.pressure_value) + " psi")

        self.after(refresh_time,self.update_gauge_data)

class PressureLineCanvas(tk.Canvas):
    def __init__(self, container, relay_states):
        super().__init__(container)

        self.pressure_line_states = ["Red", "Red", "Blue", "Blue", "Blue", "Blue"]    
        self.relay_states = relay_states

        # print(self.pressure_line_states)
        self.set_pressure_line_states(relay_states)

        # print(self.pressure_line_states)

        self.canvas_height = 600
        self.canvas_width = 1000
        self.pressure_line_width = 12

        self.place(x=25,y=150,height = self.canvas_height,width = self.canvas_width)
        self.config(background=win_color, relief=tk.FLAT, bd=0, highlightthickness=0)

        self.gas_bottle_image = ImageTk.PhotoImage(self.scale_images("images/bottle2.png", 3))      
        self.cl_chamber_image = ImageTk.PhotoImage(self.scale_images("images/cl-chamber2.png", 6))
        self.lecture_bottle_image = ImageTk.PhotoImage(self.scale_images("images/lecture-bottle2.png", 4))
        self.gas_bottle_incanvas = self.create_image(81,150, image=self.gas_bottle_image, anchor = tk.NW)
        self.gas_bottle_incanvas = self.create_image(440,10, image=self.cl_chamber_image, anchor = tk.NW)
        self.gas_bottle_incanvas = self.create_image(440,490, image=self.lecture_bottle_image, anchor = tk.NW)

        self.draw_the_pressure_lines()                  
    
    def set_pressure_line_states(self, relay_states):
        for i in range(2):
            if relay_states[i] == 1:
                self.pressure_line_states[i] = "Blue"
            else:
                self.pressure_line_states[i] = "Red"

        for i in range(2,6):
            if relay_states[i] == 1:
                self.pressure_line_states[i] = "Red"
            else:
                self.pressure_line_states[i] = "Blue"
    
    def draw_the_pressure_lines(self):        

        self.valve3_line_1  = self.create_line(300+self.pressure_line_width/2, self.canvas_height/2, 300+self.pressure_line_width/2, self.canvas_height*0.25, width=self.pressure_line_width, fill=self.pressure_line_states[2])        
        self.valve3_line_2  = self.create_line(300, self.canvas_height*0.25+self.pressure_line_width/2, 500, self.canvas_height*0.25+self.pressure_line_width/2, width=self.pressure_line_width, fill=self.pressure_line_states[2])
        
        self.valve4_line_1  = self.create_line(300+self.pressure_line_width/2, self.canvas_height/2, 300+self.pressure_line_width/2, self.canvas_height*0.75, width=self.pressure_line_width, fill=self.pressure_line_states[3])
        self.valve4_line_2  = self.create_line(300, self.canvas_height*0.75-self.pressure_line_width/2, 500, self.canvas_height*0.75-self.pressure_line_width/2, width=self.pressure_line_width, fill=self.pressure_line_states[3])
        
        self.valve5_line_1  = self.create_line(700+self.pressure_line_width/2, self.canvas_height/2, 700+self.pressure_line_width/2, self.canvas_height*0.25, width=self.pressure_line_width, fill=self.pressure_line_states[4])        
        self.valve5_line_2  = self.create_line(500, self.canvas_height*0.25+self.pressure_line_width/2, 700, self.canvas_height*0.25+self.pressure_line_width/2, width=self.pressure_line_width, fill=self.pressure_line_states[4])

        self.valve6_line_1  = self.create_line(700+self.pressure_line_width/2, self.canvas_height/2, 700+self.pressure_line_width/2, self.canvas_height*0.75, width=self.pressure_line_width, fill=self.pressure_line_states[5])
        self.valve6_line_2  = self.create_line(500, self.canvas_height*0.75-self.pressure_line_width/2, 700, self.canvas_height*0.75-self.pressure_line_width/2, width=self.pressure_line_width, fill=self.pressure_line_states[5])

        self.bottle_inlet_line  = self.create_line(150, self.canvas_height/2, 300 + self.pressure_line_width, self.canvas_height/2, width=self.pressure_line_width, fill=self.pressure_line_states[0])   
        self.cl_vessel_line  = self.create_line(500, self.canvas_height*0.25+self.pressure_line_width, 500, 100, width=self.pressure_line_width, fill="blue") 
        self.lecture_bottle_line  = self.create_line(500, self.canvas_height*0.75-self.pressure_line_width, 500, self.canvas_height-80-self.pressure_line_width, width=self.pressure_line_width, fill="blue")        
        self.exhaust_outlet_line = self.create_line(700, self.canvas_height/2, 850, self.canvas_height/2, width=self.pressure_line_width, fill=self.pressure_line_states[1]) 

        self.compressor_inlet_line  = self.create_line(300 + self.pressure_line_width/2, self.canvas_height/2, 350, self.canvas_height/2, width=self.pressure_line_width, fill="blue", arrow=tk.LAST, arrowshape=(20,20,15))         
        self.compressor_inlet_node = self.create_oval(296,self.canvas_height/2-10, 316, self.canvas_height/2+10, fill="Blue", outline="")

        self.compressor_outlet_line  = self.create_line(650 + self.pressure_line_width/2, self.canvas_height/2, 700, self.canvas_height/2, width=self.pressure_line_width, fill="blue", arrow=tk.LAST, arrowshape=(20,20,15))         
        # self.compressor_inlet_line  = self.create_line(650 + self.pressure_line_width/2, self.canvas_height/2, 700, self.canvas_height/2, width=self.pressure_line_width, fill="blue")
        self.compressor_inlet_node = self.create_oval(696,self.canvas_height/2-10, 716, self.canvas_height/2+10, fill="Blue", outline="")

        self.compressor_inlet_text = self.create_text(390, self.canvas_height/2, text="INLET", font=('Helvetica','18','bold'), fill="Blue", width=100, justify=tk.LEFT)
        self.compressor_outlet_text = self.create_text(600, self.canvas_height/2, text="OUTLET", font=('Helvetica','18','bold'), fill="Blue", width=100, justify=tk.RIGHT)



    def scale_images(self, file_loc,scale):
        img = Image.open(file_loc)
        img_width, img_height = img.size
        img = img.resize((img_width // scale, img_height // scale), resample=Image.Resampling.LANCZOS)
        return img     
        
class ControlValve(tk.Frame):
    def __init__(self,container,valvetype, valvestate, x_position, y_position, valvenumber):
        super().__init__(container)
        # Varibles for creating the valve check button
        self.valvetype = valvetype
        self.valvestate = valvestate
        self.x_position = x_position
        self.y_position = y_position        
        self.valvenumber = valvenumber
        self.relaynumber = valvenumber - 1

        # Load images for the checkbox valves
        if valvetype == "NC":
            valve_image_normal = ImageTk.PhotoImage(self.get_valve_image("images/NCC.png"))            
            valve_image_opposite = ImageTk.PhotoImage(self.get_valve_image("images/NCO.png"))
        elif valvetype == "NO":
            valve_image_normal = ImageTk.PhotoImage(self.get_valve_image("images/NOO.png"))            
            valve_image_opposite = ImageTk.PhotoImage(self.get_valve_image("images/NOC.png"))

        # print(x_position)
        # print(y_position)
        # Show the frame on the container
        self.config(background=win_color)
        self.place(x=x_position,y=y_position,height = 65,width = 58)
        
        # Create a variable to keep track of state        
        self.button_state = tk.IntVar(self)
        # Show the valve using the conditional to determine the valve initial state

        self.bt_valve = tk.Checkbutton(self, text = "Valve", command = self.valve_actuation, variable = self.button_state, indicatoron = False, image=valve_image_normal, selectimage=valve_image_opposite, relief = tk.FLAT)
        self.bt_valve.image = valve_image_normal
        self.bt_valve.selectimage = valve_image_opposite
        self.bt_valve.place(x=0,y=0)
        
        # Update valve button state status
        # print(valvestate)
        if self.valvestate == 1:
            self.bt_valve.select()        
        else:
            self.bt_valve.deselect()

    # Places the initial state of the check button

    def get_valve_image(self, file_loc):
        # Valve images are 100x56
        img = Image.open(file_loc)
        img_width, img_height = img.size
        area = (25, 0, 75, 56)
        img = img.crop(area)
        return img
    
    def valve_actuation(self):        
        x = 0
        # Update variable to keep track of state        
          
        gauge_thread = Thread(target=self.command_relay)
        gauge_thread.start()

        # Conditional statements to check the valve number and determined appropriate color for passing or blocking the flow
        if self.valvenumber < 3:
            if self.button_state.get() == 1:
                window.Pressure_Lines.pressure_line_states[self.valvenumber-1] = "Blue"
            else:
                window.Pressure_Lines.pressure_line_states[self.valvenumber-1] = "Red"
        else:
            if self.button_state.get() == 1:
                window.Pressure_Lines.pressure_line_states[self.valvenumber-1] = "Red"
            else:
                window.Pressure_Lines.pressure_line_states[self.valvenumber-1] = "Blue"
        PressureLineCanvas.draw_the_pressure_lines(window.Pressure_Lines)

    def command_relay(self):

        button_state = self.button_state.get()
        
        #Disable button to prevent fast clicking
        self.bt_valve.config(state=tk.DISABLED)
        
        setbit(COMPORT, self.relaynumber, button_state)
        time.sleep(0.1)
        
        #Re-enable button
        self.bt_valve.config(state=tk.NORMAL)

        return 0
                  
class SlideSwitches(tk.Frame):
    def __init__(self,container, x_position, y_position, button_text, relaynumber):
        super().__init__(container)    
        
        self.relaynumber = relaynumber
        
        slide_height = 25
        slide_width = 50
        
        # Slider image
        self.on_image = tk.PhotoImage(width=slide_width, height=slide_height)
        self.off_image = tk.PhotoImage(width=slide_width, height=slide_height)
        self.on_image.put(("red",), to=(0, 0, 23,23))
        self.off_image.put(("blue",), to=(23, 0, 48, 23))

        self.config(background=win_color)
        self.place(x=x_position,y=y_position,height = 30,width = 200)

        self.button_state = tk.IntVar(self)

        self.slider_switch_label = tk.Label(self, text = button_text, font=("Helvetica", 12, "bold"), bg = win_color, anchor="w", width = 13)
        self.slider_switch_label.place(x=55,y=3)
        self.slider_switch = tk.Checkbutton(self, text = button_text, onvalue = 1, offvalue = 0, height=slide_height-3, width = slide_width-3, indicatoron = False, image=self.on_image, selectimage=self.off_image, relief=tk.FLAT, bd=1, command=self.switch_actuation, variable = self.button_state)
        self.slider_switch.place(x=0,y=0)
    
    def switch_actuation(self):        
        
        # Update variable to keep track of state        
        # self.button_state = self.slider_switch.get()

        
        gauge_thread = Thread(target=self.command_relay)
        gauge_thread.start()
    
    def command_relay(self):

        button_state = self.button_state.get()
        
        #Disable button to prevent fast clicking
        self.slider_switch.config(state=tk.DISABLED)
        
        setbit(COMPORT, self.relaynumber-1, button_state)
        time.sleep(0.2)
        
        #Re-enable button
        self.slider_switch.config(state=tk.NORMAL)

        return 0
     
class MainWindow(tk.Tk):
    def __init__(self):
        super().__init__()
        # configure the root window
        self.title('Gas Loader Controls')
        self.geometry('1300x850')
        self.configure(bg=win_color)

        intial_relay_state = readdenk(COMPORT)

        # Draw Pressure Lines in Initial State
        self.Pressure_Lines = PressureLineCanvas(self, intial_relay_state)        

        # Draw Gauges to display Pressure Data
        self.gas_bottle_guage = GaugeImage(self, 0, 5000, 2000, 4, 50, 50, 0)
        self.cl_chamber_guage = GaugeImage(self, 0, 30000, 2000, 3, 700, 10, 1)
        self.lecture_bottle_guage = GaugeImage(self, 0, 5000, 2000, 5, 300, 650, 2)
        self.air_pressure = AirLinePressure(self, 0, 150, 20, 1000, 600, 3)

        # Draw Valve Control Buttons
        self.Valve1 = ControlValve(self,"NC", intial_relay_state[0], 200, 420, 1)
        self.Valve2 = ControlValve(self,"NC", intial_relay_state[1], 750, 420, 2)
        self.Valve3 = ControlValve(self,"NO", intial_relay_state[2], 375, 275, 3)
        self.Valve4 = ControlValve(self,"NO", intial_relay_state[3], 375, 565, 4)
        self.Valve5 = ControlValve(self,"NO", intial_relay_state[4], 600, 275, 5)
        self.Valve4 = ControlValve(self,"NO", intial_relay_state[5], 600, 565, 6)

        self.manual_control_frame = tk.Frame(self, bd=2, relief=tk.RAISED, bg=win_color)
        self.manual_control_frame.place(x = 980, y = 75, width = 250, height = 205)

        self.auto_control_frame = tk.Frame(self, bd=2, relief=tk.RAISED, bg=win_color)       
        self.auto_control_frame.place(x = 980, y = 300, width = 250, height = 205)

        #Draw the motor automatic control components, text box and buttons
        self.motor_travel_angle_label = tk.Label(self, text = "Motor Travel Angle", font=('Helvetica','12','bold'), bg=win_color)
        self.motor_travel_angle_label.place(x = 1000, y = 325, width=200, height = 20)
        
        self.motor_travel_angle_textbox = tk.Text(self)
        self.motor_travel_angle_textbox.insert(tk.END, "45")
        self.motor_travel_angle_textbox.place(x = 1000, y = 350, width=200, height = 30)

        self.cw_travel_angle_button = tk.Button(self, text = "Rotate CW", font=('Helvetica','12','bold'), command= lambda:self.auto_rotate("CW"))
        self.cw_travel_angle_button.place(x = 1000, y = 400, width=200, height = 40)
        self.ccw_travel_angle_button = tk.Button(self, text = "Rotate CCW", font=('Helvetica','12','bold'), command= lambda:self.auto_rotate("CCW"))
        self.ccw_travel_angle_button.place(x = 1000, y = 450, width=200, height = 40)

        # Draw the Slider Switches for the other functions
        self.compressor_switch = SlideSwitches(self, 1000, 100, "Compressor", 8)
        self.vacuum_pump_switch = SlideSwitches(self, 1000, 130, "Vacuum Pump", 11)
        self.motor_ccw_switch = SlideSwitches(self, 1000, 160, "Motor CCW", 10)
        self.motor_cw_switch = SlideSwitches(self, 1000, 190, "Motor CW", 9)
        self.motor_cw_switch = SlideSwitches(self, 1000, 220, "Valve Unstick", 7)

        # self.Pressure_Lines.draw_the_pressure_lines()

    def auto_rotate(self, direction):
        #testing rotation time accuracy
        
        motor_rpm = 269
        gear_readuction = 16
        motor_constant = motor_rpm/gear_readuction/60 #rotation per second at stem

        try:
            rotation_angle = float(self.motor_travel_angle_textbox.get("1.0","end-1c"))
            time_on = rotation_angle/360/motor_constant
        except:
            print("Input valid angle")
        else:
            if direction == "CW":
                relay_value = 8
            elif direction == "CCW":
                relay_value = 9

            # print(time_on)

        #Start Thread to begin rotation
        start = time.time()        
        start_rotation = Thread(target=self.turn_on_turn_off, args=(COMPORT, relay_value, time_on))
        start_rotation.start()

        

    def turn_on_turn_off(self, por, bit, time_on):
        
        #Disable buttons while motor is turning to prevent multi clicks
        self.cw_travel_angle_button.config(state=tk.DISABLED)
        self.ccw_travel_angle_button.config(state=tk.DISABLED)
        setbit(por, bit, 1)

        time.sleep(time_on)

        setbit(por, bit, 0)

        #Re-enable buttons
        self.cw_travel_angle_button.config(state=tk.NORMAL)
        self.ccw_travel_angle_button.config(state=tk.NORMAL)

        return 0
        
if __name__ == "__main__":
    win_color = 'light gray'
    COMPORT = "COM10"

    # Creating the main window
    window = MainWindow()
    window.mainloop()


    #***** Laser 1 Joging and Focus controls *****
    # Jog position variables
    x_j = 125
    y_j = 150
    xs_j = 60
    ys_j = 60
    bt_scale = 8

    # ***********************************************************Laser 1***********************************************************
    img = Image.open("images/laser_1.png")
    img_width, img_height = img.size
    laser1_lbl = ImageTk.PhotoImage(scale_images("images/laser_1.png",bt_scale))
    laser_label = tk.Label(window, text = "Laser BG", image = laser1_lbl,bg = win_color).place(x=x_j-img_width/(bt_scale*2),y=y_j-img_height/(bt_scale*2)+95)

    img = Image.open("images/up_jog.png")
    img_width, img_height = img.size
    # Jog Up
    up_jog = ImageTk.PhotoImage(scale_images("images/up_jog.png",bt_scale))
    laser1_up_jog = tk.Button(window, text = "Laz1_UP", image = up_jog, bg = win_color, relief="flat")
    laser1_up_jog.place(x=x_j-img_width/(bt_scale*2),y=y_j-img_height/(bt_scale*2)-ys_j)
    laser1_up_jog.bind("<ButtonPress>", lambda event:  pz_travel_JA(1,2,jog_speed))
    laser1_up_jog.bind("<ButtonRelease>", lambda event:   pz_travel_ST(1,2))

    # Jog Down
    down_jog = ImageTk.PhotoImage(scale_images("images/down_jog.png",bt_scale))
    laser1_up_jog = tk.Button(window, text = "Laz1_DOWN", image = down_jog, bg = win_color, relief="flat")
    laser1_up_jog.place(x=x_j-img_width/(bt_scale*2),y=y_j-img_height/(bt_scale*2)+ys_j)
    laser1_up_jog.bind("<ButtonPress>", lambda event:  pz_travel_JA(1,2,-jog_speed))
    laser1_up_jog.bind("<ButtonRelease>", lambda event:   pz_travel_ST(1,2))

    # Jog Left
    left_jog = ImageTk.PhotoImage(scale_images("images/left_jog.png",bt_scale))
    laser1_up_jog = tk.Button(window, text = "Laz1_LEFT", image = left_jog, bg = win_color, relief="flat")
    laser1_up_jog.place(x=x_j-img_width/(bt_scale*2)-xs_j,y=y_j-img_height/(bt_scale*2))
    laser1_up_jog.bind("<ButtonPress>", lambda event:  pz_travel_JA(1,1,jog_speed))
    laser1_up_jog.bind("<ButtonRelease>", lambda event:   pz_travel_ST(1,1))

    # Jog Right
    right_jog = ImageTk.PhotoImage(scale_images("images/right_jog.png",bt_scale))
    laser1_up_jog = tk.Button(window, text = "Laz1_RIGHT", image = right_jog, bg = win_color, relief="flat")
    laser1_up_jog.place(x=x_j-img_width/(bt_scale*2)+xs_j,y=y_j-img_height/(bt_scale*2))
    laser1_up_jog.bind("<ButtonPress>", lambda event:  pz_travel_JA(1,1,-jog_speed))
    laser1_up_jog.bind("<ButtonRelease>", lambda event:   pz_travel_ST(1,1))

    #Left Focus
    left_focus = ImageTk.PhotoImage(scale_images("images/left_focus.png",bt_scale))
    laser1_left_focus = tk.Button(window, text = "Laz1_LFocusT", image = left_focus, bg = win_color, relief="flat")
    laser1_left_focus.place(x=x_j-img_width/(bt_scale*2)-xs_j+25,y=y_j-img_height/(bt_scale*2)+160)
    laser1_left_focus.bind("<ButtonPress>", lambda event:  pz_travel_JA(3,1,-jog_speed))
    laser1_left_focus.bind("<ButtonRelease>", lambda event:   pz_travel_ST(3,1))

    #Right Focus
    right_focus = ImageTk.PhotoImage(scale_images("images/right_focus.png",bt_scale))
    laser1_right_focus = tk.Button(window, text = "Laz1_RFocusT", image = right_focus, bg = win_color, relief="flat")
    laser1_right_focus.place(x=x_j-img_width/(bt_scale*2)+xs_j-25,y=y_j-img_height/(bt_scale*2)+160)
    laser1_right_focus.bind("<ButtonPress>", lambda event:  pz_travel_JA(3,1,jog_speed))
    laser1_right_focus.bind("<ButtonRelease>", lambda event:   pz_travel_ST(3,1))

    img = Image.open("images/speed-down.png")
    img_width, img_height = img.size
    #Low Speed
    lspeed = ImageTk.PhotoImage(scale_images("images/speed-down.png",bt_scale))
    laser1_lspeed = tk.Button(window, text = "Laz1_RFocusT", image = lspeed, bg = win_color, relief="flat")
    laser1_lspeed.place(x=x_j-img_width/(bt_scale*2)-xs_j,y=y_j-img_height/(bt_scale*2)+255)
    laser1_lspeed.bind("<ButtonPress>", lambda event:  change_jog_speed(1, "-"))

    #Speed Indicator
    speed_ind = ImageTk.PhotoImage(scale_images("images/speed-1.png",bt_scale))
    laser1_speed_ind = tk.Label(window, text = "Laz1_RFocusT", image = speed_ind, bg = win_color, relief="flat")
    laser1_speed_ind.place(x=x_j-img_width/(bt_scale*2)+1,y=y_j-img_height/(bt_scale*2)+256)

    #High Speed
    hspeed = ImageTk.PhotoImage(scale_images("images/speed-up.png",bt_scale))
    laser1_hspeed = tk.Button(window, text = "Laz1_RFocusT", image = hspeed, bg = win_color, relief="flat")
    laser1_hspeed.place(x=x_j-img_width/(bt_scale*2)+xs_j,y=y_j-img_height/(bt_scale*2)+255)
    laser1_hspeed.bind("<ButtonPress>", lambda event:  change_jog_speed(1, "+"))

    # ***********************************************************Laser 2***********************************************************
    x_spacing = 230

    img = Image.open("images/laser_2.png")
    img_width, img_height = img.size
    laser2_lbl = ImageTk.PhotoImage(scale_images("images/laser_2.png",bt_scale))
    laser_label = tk.Label(window, text = "Laser BG", image = laser2_lbl,bg = win_color).place(x=x_spacing+x_j-img_width/(bt_scale*2),y=y_j-img_height/(bt_scale*2)+95)

    img = Image.open("images/up_jog.png")
    img_width, img_height = img.size
    # Jog Up
    laser2_up_jog = tk.Button(window, text = "Laz2_UP", image = up_jog, bg = win_color, relief="flat")
    laser2_up_jog.place(x=x_spacing+x_j-img_width/(bt_scale*2),y=y_j-img_height/(bt_scale*2)-ys_j)
    laser2_up_jog.bind("<ButtonPress>", lambda event:  pz_travel_JA(2,2,jog_speed_2))
    laser2_up_jog.bind("<ButtonRelease>", lambda event:   pz_travel_ST(2,2))

    # Jog Down
    laser2_up_jog = tk.Button(window, text = "Laz2_DOWN", image = down_jog, bg = win_color, relief="flat")
    laser2_up_jog.place(x=x_spacing+x_j-img_width/(bt_scale*2),y=y_j-img_height/(bt_scale*2)+ys_j)
    laser2_up_jog.bind("<ButtonPress>", lambda event:  pz_travel_JA(2,2,-jog_speed_2))
    laser2_up_jog.bind("<ButtonRelease>", lambda event:   pz_travel_ST(2,2))

    # Jog Left
    laser2_up_jog = tk.Button(window, text = "Laz2_LEFT", image = left_jog, bg = win_color, relief="flat")
    laser2_up_jog.place(x=x_spacing+x_j-img_width/(bt_scale*2)-xs_j,y=y_j-img_height/(bt_scale*2))
    laser2_up_jog.bind("<ButtonPress>", lambda event:  pz_travel_JA(2,1,jog_speed_2))
    laser2_up_jog.bind("<ButtonRelease>", lambda event:   pz_travel_ST(2,1))

    # Jog Right
    laser2_up_jog = tk.Button(window, text = "Laz2_RIGHT", image = right_jog, bg = win_color, relief="flat")
    laser2_up_jog.place(x=x_spacing+x_j-img_width/(bt_scale*2)+xs_j,y=y_j-img_height/(bt_scale*2))
    laser2_up_jog.bind("<ButtonPress>", lambda event:  pz_travel_JA(2,1,-jog_speed_2))
    laser2_up_jog.bind("<ButtonRelease>", lambda event:   pz_travel_ST(2,1))

    #Left Focus
    laser2_left_focus = tk.Button(window, text = "Laz2_LFocusT", image = left_focus, bg = win_color, relief="flat")
    laser2_left_focus.place(x=x_spacing+x_j-img_width/(bt_scale*2)-xs_j+25,y=y_j-img_height/(bt_scale*2)+160)
    laser2_left_focus.bind("<ButtonPress>", lambda event:  pz_travel_JA(3,2,-jog_speed_2))
    laser2_left_focus.bind("<ButtonRelease>", lambda event:   pz_travel_ST(3,2))

    #Right Focus
    laser2_right_focus = tk.Button(window, text = "Laz2_RFocusT", image = right_focus, bg = win_color, relief="flat")
    laser2_right_focus.place(x=x_spacing+x_j-img_width/(bt_scale*2)+xs_j-25,y=y_j-img_height/(bt_scale*2)+160)
    laser2_right_focus.bind("<ButtonPress>", lambda event:  pz_travel_JA(3,2,jog_speed_2))
    laser2_right_focus.bind("<ButtonRelease>", lambda event:   pz_travel_ST(3,2))

    #Low Speed
    laser2_lspeed = tk.Button(window, text = "Laz2_RFocusT", image = lspeed, bg = win_color, relief="flat")
    laser2_lspeed.place(x=x_spacing+x_j-img_width/(bt_scale*2)-xs_j,y=y_j-img_height/(bt_scale*2)+255)
    laser2_lspeed.bind("<ButtonPress>", lambda event:  change_jog_speed(2, "-"))

    #Speed Indicator
    laser2_speed_ind = tk.Label(window, text = "Laz2_RFocusT", image = speed_ind, bg = win_color, relief="flat")
    laser2_speed_ind.place(x=x_spacing+x_j-img_width/(bt_scale*2)+1,y=y_j-img_height/(bt_scale*2)+256)

    #High Speed
    laser2_hspeed = tk.Button(window, text = "Laz2_RFocusT", image = hspeed, bg = win_color, relief="flat")
    laser2_hspeed.place(x=x_spacing+x_j-img_width/(bt_scale*2)+xs_j,y=y_j-img_height/(bt_scale*2)+255)
    laser2_hspeed.bind("<ButtonPress>", lambda event:  change_jog_speed(2, "+"))