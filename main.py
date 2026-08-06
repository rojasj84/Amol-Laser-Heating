# Importing python libraries
import tkinter as tk
from PIL import ImageTk, Image

# Importing local libraries
from agilis_control import *
from denkovi_serial import *
from acton_pixis import *
from piezo_motor_control import *
from laser_communication import *
from festo_control import *
from comport_selection import *

win_color = "light gray"

#Global variables to store laser IPs and COM Ports for the various systems

left_laser_ip = "192.168.1.100"
right_laser_ip = "192.168.0.100"
agilis_com_port = "COM11"
left_denkovi_com_port = "COM7"
right_denkovi_com_port = "COM6"

class Laser_Controls(tk.Toplevel):
    def __init__(self):
        tk.Toplevel.__init__(self)
        self.title("Laser Control Window")
        self.geometry("505x500")
        LaserCommunication(self,left_laser_ip, 20,20)
        LaserCommunication(self,right_laser_ip, 260,20)

class Piezo_Controls(tk.Toplevel):
    def __init__(self):
        tk.Toplevel.__init__(self)
        self.title("AGILIS Control Window")
        self.geometry("505x600")
        self.PiezoControlClass = InitiatePiezoMotorControls(self,0,0,agilis_com_port)
        print(agilis_com_port)          

class Festo_Controls(tk.Toplevel):
     def __init__(self):
        tk.Toplevel.__init__(self)
        self.title("Festo Control Window")
        self.geometry("280x445")
        self.FestoControlClass = FestoControlWindow(self, left_denkovi_com_port, right_denkovi_com_port)

class ComPort_Controls(tk.Toplevel):
    def __init__(self):
        tk.Toplevel.__init__(self)
        self.title("Com Port Selection Window")
        self.geometry("360x200")

        #self.place(x = 0, y = 0, width = 360, height = 200)

        self.local_agilis_com_port = tk.StringVar(self)
        self.local_agilis_com_port.set(agilis_com_port)

        self.right_relays_com_port = tk.StringVar(self)
        self.right_relays_com_port.set(right_denkovi_com_port)

        self.left_relays_com_port = tk.StringVar(self)
        self.left_relays_com_port.set(left_denkovi_com_port)

        options = self.get_com_ports()

        agilis_label = tk.Label(self, text = "AGILIS Piezo Motors", font=("Arial", 10))
        agilis_label.place(x = 10, y = 20)
        agilis_dropdown = tk.OptionMenu(self, self.local_agilis_com_port, options[0], *options)
        agilis_dropdown.place(x = 150, y = 20, width=200, height=25)

        right_side_relays_label = tk.Label(self, text = "Right Side Relays", font=("Arial", 10))
        right_side_relays_label.place(x = 10, y = 50)
        right_side_relay_dropdown = tk.OptionMenu(self, self.right_relays_com_port, options[0], *options)
        right_side_relay_dropdown.place(x = 150, y = 50, width=200, height=25)

        left_side_relays_label = tk.Label(self, text = "Left Side Relays", font=("Arial", 10))
        left_side_relays_label.place(x = 10, y = 80)
        left_side_relay_dropdown = tk.OptionMenu(self, self.left_relays_com_port, options[0], *options)
        left_side_relay_dropdown.place(x = 150, y = 80, width=200, height=25)

        update_button = tk.Button(self, text="Update", command=self.update_com_ports)
        update_button.place(x = 75, y = 120, width=200)

    def get_com_ports(self):
        ports = [port.device for port in serial.tools.list_ports.comports()]
        return ports
    
    def update_com_ports(self):
        #If statement for updating the Peizo Control Window
        if PiezoControlWindow.winfo_exists():
            #update global variable
            globals()['agilis_com_port'] = self.local_agilis_com_port.get()
            #settingt the com ports for laser 1 and laser 2 piezos if window already xists
            PiezoControlWindow.PiezoControlClass.laser1_PiezoMotors.Laser_Jog_Down.agilis_comport = self.local_agilis_com_port.get()
            PiezoControlWindow.PiezoControlClass.laser1_PiezoMotors.Laser_Jog_Up.agilis_comport = self.local_agilis_com_port.get()
            PiezoControlWindow.PiezoControlClass.laser1_PiezoMotors.Laser_Jog_Right.agilis_comport = self.local_agilis_com_port.get()
            PiezoControlWindow.PiezoControlClass.laser1_PiezoMotors.Laser_Jog_Left.agilis_comport = self.local_agilis_com_port.get()
            PiezoControlWindow.PiezoControlClass.laser1_PiezoMotors.laser_left_focus.agilis_comport = self.local_agilis_com_port.get()
            PiezoControlWindow.PiezoControlClass.laser1_PiezoMotors.laser_right_focus.agilis_comport = self.local_agilis_com_port.get()

            PiezoControlWindow.PiezoControlClass.laser2_PiezoMotors.Laser_Jog_Down.agilis_comport = self.local_agilis_com_port.get()
            PiezoControlWindow.PiezoControlClass.laser2_PiezoMotors.Laser_Jog_Up.agilis_comport = self.local_agilis_com_port.get()
            PiezoControlWindow.PiezoControlClass.laser2_PiezoMotors.Laser_Jog_Right.agilis_comport = self.local_agilis_com_port.get()
            PiezoControlWindow.PiezoControlClass.laser2_PiezoMotors.Laser_Jog_Left.agilis_comport = self.local_agilis_com_port.get()
            PiezoControlWindow.PiezoControlClass.laser2_PiezoMotors.laser_left_focus.agilis_comport = self.local_agilis_com_port.get()
            PiezoControlWindow.PiezoControlClass.laser2_PiezoMotors.laser_right_focus.agilis_comport = self.local_agilis_com_port.get()        
            print("Updating COM Ports with window open")
        else:
            globals()['agilis_com_port'] = self.local_agilis_com_port.get()

        #If statement for updating the Festo Relays 
        if FestControlWindow.winfo_exists():
            #Updating the values within the global variables for festo comports
            globals()['right_denkovi_com_port'] = self.right_relays_com_port.get()
            globals()['left_denkovi_com_port'] = self.left_relays_com_port.get()

            #Updating the values within the existing classes
            FestControlWindow.FestoControlClass.RightSideControls.right_side_comport = self.right_relays_com_port.get()
            FestControlWindow.FestoControlClass.LeftSideControls.left_side_comport = self.left_relays_com_port.get()
        else:
            #Updating the values within the global variables for festo comports
            globals()['right_denkovi_com_port'] = self.right_relays_com_port.get()
            globals()['left_denkovi_com_port'] = self.left_relays_com_port.get()

        

# Function to open various windows in the program
def open_window(window_value, window_in_question):
    if window_in_question.winfo_exists(): #Checks if the window in question already exists
            do_nothing()
    else:
        if window_value == 1:   #Check for which window to reopen               
            globals()['PiezoControlWindow'] = Piezo_Controls()    
        elif window_value == 2:   #Check for which window to reopen               
            globals()['FestControlWindow'] = Festo_Controls()    
        elif window_value == 3:
            globals()['LaserControlWindow'] = Laser_Controls()
        elif window_value == 4:
            globals()['ComPortControlWindow'] = ComPort_Controls()
        else:
            do_nothing()
    

if __name__ == "__main__":

    #***** Building USER GUI *****

    # Begin code with window code
    window = tk.Tk()
    window.title("EPL Laser Heating Control")
    window.geometry("1280x1010")

    ico = Image.open("images/laser-icon.png")
    photo = ImageTk.PhotoImage(ico)
    window.wm_iconphoto(False, photo)
    
    ActonControlWindow = ActonPixis = InitiateActonTfit(window, 0,0)
    LaserControlWindow = Laser_Controls()
    PiezoControlWindow = Piezo_Controls()
    FestControlWindow = Festo_Controls()
    ComPortControlWindow = ComPort_Controls()

    LaserControlWindow.destroy() #Removing festo control from display since the user doesn't normally need to access directly the Festo States
    FestControlWindow.destroy() #Removing festo control from display since the user doesn't normally need to access directly the Festo States
    PiezoControlWindow.destroy() #Removing festo control from display since the user doesn't normally need to access directly the Festo States
    ComPortControlWindow.destroy() 
    
    #Creating a top menu
    menu_bar = tk.Menu(window)
    file_menu = tk.Menu(menu_bar, tearoff=0)
    file_menu.add_command(label="Exit", command=window.quit)
    menu_bar.add_cascade(label="Main", menu=file_menu)

    # Create a Spectrometer menu
    edit_menu = tk.Menu(menu_bar, tearoff=0)
    edit_menu.add_command(label="High Temperature", command=do_nothing)
    edit_menu.add_command(label="Low Temperature", command=do_nothing)
    edit_menu.add_command(label="2D", command=do_nothing)
    menu_bar.add_cascade(label="Spectrometer", menu=edit_menu)

    # Create a Communications menu
    edit_menu = tk.Menu(menu_bar, tearoff=0)
    edit_menu.add_command(label="COM Ports", command=lambda: open_window(4, ComPortControlWindow))
    edit_menu.add_command(label="Laser IPs", command=do_nothing)
    menu_bar.add_cascade(label="Communications", menu=edit_menu)

    # Create a Windows menu
    edit_menu = tk.Menu(menu_bar, tearoff=0)
    edit_menu.add_command(label="Piezo Controls", command=lambda: open_window(1, PiezoControlWindow))
    edit_menu.add_command(label="Festo Controls", command=lambda: open_window(2, FestControlWindow))
    edit_menu.add_command(label="Laser Controls", command=lambda: open_window(3, LaserControlWindow))
    menu_bar.add_cascade(label="Windows", menu=edit_menu)


    # Add the menu bar to the window
    window.config(menu=menu_bar)

    

    window.mainloop()