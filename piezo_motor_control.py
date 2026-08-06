# Importing python libraries
import tkinter as tk
from PIL import ImageTk, Image

# Importing local libraries
from agilis_control import *
from denkovi_serial import *

win_color = "light gray"

#***** Define Functions *****
def do_nothing():
    x = 0
    print("Nothing is done")

def get_image(file_loc):
    # Valve images are 100x56
    img = Image.open(file_loc)
    return img

def scale_images(file_loc,scale):
    img = Image.open(file_loc)
    img_width, img_height = img.size
    img = img.resize((img_width // scale, img_height // scale), resample=Image.Resampling.LANCZOS)
    return img


    global jog_speed
    global jog_speed_2

    if (axis == 1):
        if(delta == "+"):
            jog_speed = jog_speed + 1
        elif(delta == "-"):
            jog_speed = jog_speed - 1
        if(jog_speed > 3):
            jog_speed = 3
        elif(jog_speed < 1):
            jog_speed = 1
    elif(axis == 2):
        if(delta == "+"):
            jog_speed_2 = jog_speed_2 + 1
        elif(delta == "-"):
            jog_speed_2 = jog_speed_2 - 1
        if(jog_speed_2 > 3):
            jog_speed_2 = 3
        elif(jog_speed_2 < 1):
            jog_speed_2 = 1


    if (axis == 1):
        if(jog_speed == 1):
            speed_img = ImageTk.PhotoImage(scale_images("images/speed-1.png",bt_scale))
            laser1_speed_ind.configure(image=speed_img)
            laser1_speed_ind.image = speed_img
        elif(jog_speed == 2):
            image=speed_img = ImageTk.PhotoImage(scale_images("images/speed-2.png",bt_scale))
            laser1_speed_ind.configure(image=speed_img)
            laser1_speed_ind.image = speed_img
        elif(jog_speed == 3):
            image=speed_img = ImageTk.PhotoImage(scale_images("images/speed-3.png",bt_scale))
            laser1_speed_ind.configure(image=speed_img)
            laser1_speed_ind.image = speed_img
    elif(axis == 2):
        if(jog_speed_2 == 1):
            speed_img = ImageTk.PhotoImage(scale_images("images/speed-1.png",bt_scale))
            laser2_speed_ind.configure(image=speed_img)
            laser2_speed_ind.image = speed_img
        elif(jog_speed_2 == 2):
            image=speed_img = ImageTk.PhotoImage(scale_images("images/speed-2.png",bt_scale))
            laser2_speed_ind.configure(image=speed_img)
            laser2_speed_ind.image = speed_img
        elif(jog_speed_2 == 3):
            image=speed_img = ImageTk.PhotoImage(scale_images("images/speed-3.png",bt_scale))
            laser2_speed_ind.configure(image=speed_img)
            laser2_speed_ind.image = speed_img

def initiate_remote_control(laser1_motors, laser2_motors):
    RemoteControlWindow(laser1_motors, laser2_motors)

#***** Classes for building GUI *****
class AgilisControlPanel(tk.Frame):

    jog_speed_local = 1
    bt_scale = 8

    def __init__(self, container, xy_channel, focus_channel, focus_axis, x_location, y_location, side, agilis_comport):
        super().__init__(container)
     
        frame_width = 225
        frame_height = 500

        self.side = side

        # show the frame on the container
        self.config(background=win_color, highlightbackground="black", highlightthickness=1, relief="raised")
        self.place(x=x_location,y=y_location,width = frame_width,height = frame_height)

        #Populate labels    
        #laser_label = tk.Label(self, text = "LASER " + str(xy_channel), bg=win_color, font=('Agency FB', 20, 'bold')).place(relx=0.5, rely=0.05,anchor="center")
        
        if xy_channel == 1:
            laser_label = tk.Label(self, text = "LEFT LASER", bg=win_color, font=('Agency FB', 20, 'bold')).place(relx=0.5, rely=0.05,anchor="center")
        else:
            laser_label = tk.Label(self, text = "RIGTH LASER", bg=win_color, font=('Agency FB', 20, 'bold')).place(relx=0.5, rely=0.05,anchor="center")

        position_label = tk.Label(self, text = "POSITION", bg=win_color, font=('Agency FB', 14, 'bold')).place(relx=0.5, rely=0.49,anchor="center")
        
        # Adding conditional statement to check which side is being populated
        # Left and Right have opposite directions for focus and defocus
        if self.side == "left":
            focus_label = tk.Label(self, text = "  FOCUS     DEFOCUS", bg=win_color, font=('Agency FB', 10, 'bold')).place(relx=0.5, rely=0.7,anchor="center")
            self.laser_left_focus = self.AxisControl(self, "FOCUS LEFT", "images/left_focus.png", self.bt_scale, frame_width/3, 310, focus_channel, focus_axis, -1, 3, 2, agilis_comport)
            self.laser_right_focus = self.AxisControl(self, "FOCUS RIGHT", "images/right_focus.png", self.bt_scale, frame_width*2/3, 310, focus_channel, focus_axis, 1, 3, 2, agilis_comport)
        else:
            focus_label = tk.Label(self, text = "DEFOCUS     FOCUS  ", bg=win_color, font=('Agency FB', 10, 'bold')).place(relx=0.5, rely=0.7,anchor="center")
            self.laser_left_focus = self.AxisControl(self, "FOCUS LEFT", "images/left_focus.png", self.bt_scale, frame_width/3, 310, focus_channel, focus_axis, 1, 3, 2, agilis_comport)
            self.laser_right_focus = self.AxisControl(self, "FOCUS RIGHT", "images/right_focus.png", self.bt_scale, frame_width*2/3, 310, focus_channel, focus_axis, -1, 3, 2, agilis_comport)
        
        #focus_label = tk.Label(self, text = "DEFOCUS", bg=win_color, font=('Agency FB', 14, 'bold')).place(relx=0.7, rely=0.7,anchor="center")
        focus_label = tk.Label(self, text = "SPEED", bg=win_color, font=('Agency FB', 14, 'bold')).place(relx=0.5, rely=0.9,anchor="center")

        #Populate control buttons for agilis axis
        self.Laser_Jog_Up = self.AxisControl(self, "UP", "images/up_jog.png", self.bt_scale, frame_width/2, 85, xy_channel, 2, 1, 2, 1, agilis_comport)
        self.Laser_Jog_Down = self.AxisControl(self, "DOWN", "images/down_jog.png", self.bt_scale, frame_width/2, 205, xy_channel, 2, -1, 2, 1, agilis_comport)
        self.Laser_Jog_Right = self.AxisControl(self, "RIGHT", "images/right_jog.png", self.bt_scale, frame_width*3/4, 145, xy_channel, 1, -1, 2, 1, agilis_comport)
        self.Laser_Jog_Left = self.AxisControl(self, "LEFT", "images/left_jog.png", self.bt_scale, frame_width/4, 145, xy_channel, 1, 1, 2, 1, agilis_comport)

        

        #Populate contorl buttons for jog speed
        self.laser_jog_speed_down = self.JogSpeedButton(self, "JOG SPEED DOWN", "images/speed-down.png", self.bt_scale, frame_width/5, 410, "-")
        self.laser_jog_speed_up = self.JogSpeedButton(self, "JOG SPEED UP", "images/speed-up.png", self.bt_scale, frame_width*4/5, 410, "+")
        self.laser_jog_speed = self.JogSpeedDisplay(self, "JOG SPEED", "images/speed-1.png", self.bt_scale, frame_width*2.5/5, 410)
        
        #Populate button checks for stream deck  

    def change_jog_speed_local(self, speed_change):

        if speed_change == "+":
            if self.jog_speed_local < 3:
                self.jog_speed_local = self.jog_speed_local + 1
            elif self.jog_speed_local >= 3:
                self.jog_speed_local = 3

        if speed_change == "-":
            if self.jog_speed_local > 1:
                self.jog_speed_local = self.jog_speed_local - 1
            elif self.jog_speed_local <= 1:
                self.jog_speed_local = 1
            
        if self.jog_speed_local == 1:
            speed_img = ImageTk.PhotoImage(scale_images("images/speed-1.png",self.bt_scale))
            self.laser_jog_speed.speed_display.config(image = speed_img)
            self.laser_jog_speed.speed_display.image = speed_img
        elif self.jog_speed_local == 2:
            speed_img = ImageTk.PhotoImage(scale_images("images/speed-2.png",self.bt_scale))
            self.laser_jog_speed.speed_display.config(image = speed_img)
            self.laser_jog_speed.speed_display.image = speed_img
        elif self.jog_speed_local == 3:
            speed_img = ImageTk.PhotoImage(scale_images("images/speed-3.png",self.bt_scale))
            self.laser_jog_speed.speed_display.config(image = speed_img)
            self.laser_jog_speed.speed_display.image = speed_img
            

        print(self.jog_speed_local)     

    class AxisControl(tk.Frame):
        def __init__(self, container, button_text, image_file_location, button_scale, x_location, y_location, channel, axis, direction, max_speed, min_speed, agilis_comport):
            super().__init__(container)

            button_width = 62
            self.config(background=win_color)
            self.place(x=x_location-button_width/2,y=y_location-button_width/2,height = button_width,width = button_width)
            self.button_image = ImageTk.PhotoImage(scale_images(image_file_location,button_scale))

            self.channel = channel
            self.axis = axis
            self.direction = direction
            self.max_speed = max_speed
            self.min_speed = min_speed
            self.agilis_comport = agilis_comport

            #Button information
            self.axis_button = tk.Button(self, text = button_text, bg = win_color, relief=tk.FLAT, image=self.button_image)
            self.axis_button.place(relx=0.5,rely=0.5, anchor="center")
            self.axis_button.bind("<ButtonPress>", lambda event:  self.Start_Piezo_Travel(channel,axis,direction*container.jog_speed_local))
            self.axis_button.bind("<ButtonRelease>", lambda event:   self.Stop_Piezo_Travel(channel,axis))

        def Start_Piezo_Travel(self,channel,axis,speed):
            
            # This check is for making sure that the translation of X and Y axis cannot exceed Speed 2 even if selected
            if speed**2 > self.max_speed**2:
                if speed < 0: 
                    speed = -self.max_speed
                else:
                    speed = self.max_speed

            # This check is for making sure that the focus axis cannot be less than Speed 2 even if selected
            if speed**2 < self.min_speed**2:
                if speed < 0: 
                    speed = -self.min_speed
                else:
                    speed = self.min_speed

            print(self.max_speed)
            
            print(channel,axis,speed)
            piezo_jog_at_speed(self.agilis_comport,channel,axis,speed)
            print(self.agilis_comport, channel,axis)

        def Stop_Piezo_Travel(self,channel,axis):
            piezo_stop(self.agilis_comport, channel,axis)

    class JogSpeedButton(tk.Frame):
        def __init__(self, container, button_text, image_file_location, button_scale, x_location, y_location, speed_change):
            super().__init__(container)

            button_width = 62
            self.config(background=win_color)
            self.place(x=x_location-button_width/2,y=y_location-button_width/2,height = button_width,width = button_width)
            self.button_image = ImageTk.PhotoImage(scale_images(image_file_location,button_scale))

            jog_button = tk.Button(self, text = button_text, bg = win_color, relief=tk.FLAT, image=self.button_image, command=lambda: container.change_jog_speed_local(speed_change))
            jog_button.place(relx=0.5,rely=0.5, anchor="center")  
           
    class JogSpeedDisplay(tk.Frame):
        def __init__(self, container, button_text, image_file_location, button_scale, x_location, y_location):
            super().__init__(container)

            button_width = 62
            self.config(background=win_color)
            self.place(x=x_location-button_width/2,y=y_location-button_width/2,height = button_width,width = button_width)
            self.button_image = ImageTk.PhotoImage(scale_images(image_file_location,button_scale))

            self.speed_display = tk.Label(self, text = button_text, bg = win_color, relief=tk.FLAT, image=self.button_image)
            self.speed_display.place(relx=0.5,rely=0.5, anchor="center")

class RemoteControlWindow(tk.Toplevel):
    def __init__(self, laser1_motors, laser2_motors):
        super().__init__()

        self.laser1_motors = laser1_motors
        self.laser2_motors = laser2_motors

        self.title("Stream Deck Remote Control")
        self.geometry("400x100")
        self.configure(bg=win_color)

        # Setting an innitial value to check for key pressed and make sure nothing happens after the key is first pressed
        # This is to make sure the behavior of key pressed on the stream deck match the press/hold and release behaviors of the mouse 
        # interphase for the main gui
        self.pressedkey = "0"

        RemoteContorLabel = tk.Label(self, bg=win_color, text = "Laser Remote Control is ACTIVE", fg='red', font=('Agency FB', 14, 'bold'))
        RemoteContorLabel.place(relx=0.5,rely=0.2,anchor=tk.CENTER)

        KillRemoteButton = tk.Button(self, text="End Remote Control", command=self.destroy)
        KillRemoteButton.place(relx=0.5,rely=0.6,anchor=tk.CENTER)

        self.bind("<KeyPress>", self.keydown)
        self.bind("<KeyRelease>", self.keyup)
        self.focus_set()

    # Hotkey setting for the release of a hotkey
    def keyup(self, e):
        laser1_PiezoMotors = self.laser1_motors
        laser2_PiezoMotors = self.laser2_motors

        #Laser 1 Hotkeys
        #Activating the laser axis translations
        if e.char == "a":
            laser1_PiezoMotors.Laser_Jog_Left.Stop_Piezo_Travel(laser1_PiezoMotors.Laser_Jog_Left.channel, laser1_PiezoMotors.Laser_Jog_Left.axis)
        if e.char == "d":
            laser1_PiezoMotors.Laser_Jog_Right.Stop_Piezo_Travel(laser1_PiezoMotors.Laser_Jog_Right.channel, laser1_PiezoMotors.Laser_Jog_Right.axis)
        if e.char == "w":
            laser1_PiezoMotors.Laser_Jog_Up.Stop_Piezo_Travel(laser1_PiezoMotors.Laser_Jog_Up.channel, laser1_PiezoMotors.Laser_Jog_Up.axis)
        if e.char == "s":
            laser1_PiezoMotors.Laser_Jog_Down.Stop_Piezo_Travel(laser1_PiezoMotors.Laser_Jog_Down.channel, laser1_PiezoMotors.Laser_Jog_Down.axis)
        if e.char == "q":
            laser1_PiezoMotors.laser_left_focus.Stop_Piezo_Travel(laser1_PiezoMotors.laser_left_focus.channel, laser1_PiezoMotors.laser_left_focus.axis)
        if e.char == "e":
            laser1_PiezoMotors.laser_right_focus.Stop_Piezo_Travel(laser1_PiezoMotors.laser_right_focus.channel, laser1_PiezoMotors.laser_right_focus.axis)
        if e.char == "3":
            #place holder for later, to fire guide laser
            do_nothing()

        #Laser 2 Hotkeys
        #Activating the laser axis translations
        if e.char == "j":
            laser2_PiezoMotors.Laser_Jog_Left.Stop_Piezo_Travel(laser2_PiezoMotors.Laser_Jog_Left.channel, laser2_PiezoMotors.Laser_Jog_Left.axis)
        if e.char == "l":
            laser2_PiezoMotors.Laser_Jog_Right.Stop_Piezo_Travel(laser2_PiezoMotors.Laser_Jog_Right.channel, laser2_PiezoMotors.Laser_Jog_Right.axis)
        if e.char == "i":
            laser2_PiezoMotors.Laser_Jog_Up.Stop_Piezo_Travel(laser2_PiezoMotors.Laser_Jog_Up.channel, laser2_PiezoMotors.Laser_Jog_Up.axis)
        if e.char == "k":
            laser2_PiezoMotors.Laser_Jog_Down.Stop_Piezo_Travel(laser2_PiezoMotors.Laser_Jog_Down.channel, laser2_PiezoMotors.Laser_Jog_Down.axis)
        if e.char == "u":
            laser2_PiezoMotors.laser_left_focus.Stop_Piezo_Travel(laser2_PiezoMotors.laser_left_focus.channel, laser2_PiezoMotors.laser_left_focus.axis)
        if e.char == "o":
            laser2_PiezoMotors.laser_right_focus.Stop_Piezo_Travel(laser2_PiezoMotors.laser_right_focus.channel, laser2_PiezoMotors.laser_right_focus.axis)
        if e.char == "0":
            #place holder for later, to fire guide laser
            do_nothing()

        self.pressedkey = 0

    # Hotkey setting for holding down a hotkey
    def keydown(self, e):
        laser1_PiezoMotors = self.laser1_motors
        laser2_PiezoMotors = self.laser2_motors

        if e.char != self.pressedkey:
            self.pressedkey = e.char
            #Laser 1 Hotkeys
            #Activating the laser axis translations
            if e.char == "a":
                #print("This is a test", self.pressedkey)
                laser1_PiezoMotors.Laser_Jog_Left.Start_Piezo_Travel(laser1_PiezoMotors.Laser_Jog_Left.channel, laser1_PiezoMotors.Laser_Jog_Left.axis, laser1_PiezoMotors.Laser_Jog_Left.direction*laser1_PiezoMotors.jog_speed_local)
            if e.char == "d":
                laser1_PiezoMotors.Laser_Jog_Right.Start_Piezo_Travel(laser1_PiezoMotors.Laser_Jog_Right.channel, laser1_PiezoMotors.Laser_Jog_Right.axis, laser1_PiezoMotors.Laser_Jog_Right.direction*laser1_PiezoMotors.jog_speed_local)
            if e.char == "w":
                laser1_PiezoMotors.Laser_Jog_Up.Start_Piezo_Travel(laser1_PiezoMotors.Laser_Jog_Up.channel, laser1_PiezoMotors.Laser_Jog_Up.axis, laser1_PiezoMotors.Laser_Jog_Up.direction*laser1_PiezoMotors.jog_speed_local)
            if e.char == "s":
                laser1_PiezoMotors.Laser_Jog_Down.Start_Piezo_Travel(laser1_PiezoMotors.Laser_Jog_Down.channel, laser1_PiezoMotors.Laser_Jog_Down.axis, laser1_PiezoMotors.Laser_Jog_Down.direction*laser1_PiezoMotors.jog_speed_local)
            if e.char == "q":
                laser1_PiezoMotors.laser_left_focus.Start_Piezo_Travel(laser1_PiezoMotors.laser_left_focus.channel, laser1_PiezoMotors.laser_left_focus.axis, laser1_PiezoMotors.laser_left_focus.direction*laser1_PiezoMotors.jog_speed_local)
            if e.char == "e":
                laser1_PiezoMotors.laser_right_focus.Start_Piezo_Travel(laser1_PiezoMotors.laser_right_focus.channel, laser1_PiezoMotors.laser_right_focus.axis, laser1_PiezoMotors.laser_right_focus.direction*laser1_PiezoMotors.jog_speed_local)
            if e.char == "3":
                #place holder for later, to fire guide laser
                do_nothing()

            #Laser 2 Hotkeys
            #Activating the laser axis translations
            if e.char == "j":
                #print("This is a test", self.pressedkey)
                laser2_PiezoMotors.Laser_Jog_Left.Start_Piezo_Travel(laser2_PiezoMotors.Laser_Jog_Left.channel, laser2_PiezoMotors.Laser_Jog_Left.axis, laser2_PiezoMotors.Laser_Jog_Left.direction*laser2_PiezoMotors.jog_speed_local)
            if e.char == "l":
                laser2_PiezoMotors.Laser_Jog_Right.Start_Piezo_Travel(laser2_PiezoMotors.Laser_Jog_Right.channel, laser2_PiezoMotors.Laser_Jog_Right.axis, laser2_PiezoMotors.Laser_Jog_Right.direction*laser2_PiezoMotors.jog_speed_local)
            if e.char == "i":
                laser2_PiezoMotors.Laser_Jog_Up.Start_Piezo_Travel(laser2_PiezoMotors.Laser_Jog_Up.channel, laser2_PiezoMotors.Laser_Jog_Up.axis, laser2_PiezoMotors.Laser_Jog_Up.direction*laser2_PiezoMotors.jog_speed_local)
            if e.char == "k":
                laser2_PiezoMotors.Laser_Jog_Down.Start_Piezo_Travel(laser2_PiezoMotors.Laser_Jog_Down.channel, laser2_PiezoMotors.Laser_Jog_Down.axis, laser2_PiezoMotors.Laser_Jog_Down.direction*laser2_PiezoMotors.jog_speed_local)
            if e.char == "u":
                laser2_PiezoMotors.laser_left_focus.Start_Piezo_Travel(laser2_PiezoMotors.laser_left_focus.channel, laser2_PiezoMotors.laser_left_focus.axis, laser2_PiezoMotors.laser_left_focus.direction*laser2_PiezoMotors.jog_speed_local)
            if e.char == "o":
                laser2_PiezoMotors.laser_right_focus.Start_Piezo_Travel(laser2_PiezoMotors.laser_right_focus.channel, laser2_PiezoMotors.laser_right_focus.axis, laser2_PiezoMotors.laser_right_focus.direction*laser2_PiezoMotors.jog_speed_local)
            if e.char == "0":
                #place holder for later, to fire guide laser
                do_nothing()


            # Changing the speed settings for lasers 1 and 2
            if e.char == "1":
                laser1_PiezoMotors.change_jog_speed_local("-")
            if e.char == "2":
                laser1_PiezoMotors.change_jog_speed_local("+")
            if e.char == "8":
                laser2_PiezoMotors.change_jog_speed_local("-")
            if e.char == "9":
                laser2_PiezoMotors.change_jog_speed_local("+")
       
class InitiatePiezoMotorControls(tk.Frame):
    #def __init__(self, x_position, y_position):
        #tk.Frame.__init__(self)
    def __init__(self, container, x_position, y_position, agilis_comport):
        #tk.Frame.__init__(self, container)
        super().__init__(container)

        #Visual configuration
        #self.geometry('1280x1000')
        #self.title("High T: Acton-PIXIS 400")

        #Frame visual configuration
        self.configure(width=1280,height=1000)
        
        #Frame position information
        self.x_position = x_position
        self.y_position = y_position
        self.place(x = self.x_position, y = self.y_position)
        self.agilis_comport = agilis_comport

        #Setting some values for laser piezo motor communication
        #Each channel controls 2 Axis for X and Y
        laser1_xy_channel = 1
        laser2_xy_channel = 2
        laser_focus_channel = 3 #Both focus motors are in the same channel, laser 1 on 1 and laser 2 on 2

        #Calling classes for the control buttons of laser 1 and 2
        self.laser1_PiezoMotors = AgilisControlPanel(self, laser1_xy_channel, laser_focus_channel, 1, 20, 10, "left", self.agilis_comport)
        self.laser2_PiezoMotors = AgilisControlPanel(self, laser2_xy_channel, laser_focus_channel, 2, 260, 10, "right", self.agilis_comport)

        RemoteControlButton = tk.Button(self, text="Remote Control", command=lambda: initiate_remote_control(self.laser1_PiezoMotors, self.laser2_PiezoMotors))
        RemoteControlButton.place(x=150,y=520, height = 30, width = 200)
             
       
if __name__ == "__main__":

    #***** Global variables *****
    refresh_time = 100  # time sensors refresh
    win_color = 'light grey'

    piezo_set_remote_mode()

    #***** Building USER GUI *****

    # Begin code with window code
    window = tk.Tk()
    window.title("EPL Laser Heating Control")
    window.geometry("500x580")
    window.configure(bg=win_color)

    ico = Image.open("images/laser-icon.png")
    photo = ImageTk.PhotoImage(ico)
    window.wm_iconphoto(False, photo)

    #Setting some values for laser piezo motor communication
    #Each channel controls 2 Axis for X and Y
    laser1_xy_channel = 1
    laser2_xy_channel = 2
    laser_focus_channel = 3 #Both focus motors are in the same channel, laser 1 on 1 and laser 2 on 2

    #Calling classes for the control buttons of laser 1 and 2
    laser1_PiezoMotors = AgilisControlPanel(window, laser1_xy_channel, laser_focus_channel, 1, 20, 10, "left")
    laser2_PiezoMotors = AgilisControlPanel(window, laser2_xy_channel, laser_focus_channel, 2, 260, 10, "right")

    RemoteControlButton = tk.Button(window, text="Remote Control", command=lambda: initiate_remote_control(laser1_PiezoMotors, laser2_PiezoMotors))
    RemoteControlButton.place(x=150,y=530, height = 30, width = 200)

    window.mainloop()
