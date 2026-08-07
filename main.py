# Importing python libraries
import tkinter as tk
import serial.tools.list_ports
from PIL import ImageTk, Image

# Importing local libraries
from agilis_control import *
from denkovi_serial import *
from acton_pixis import *
from piezo_motor_control import *
from laser_communication import *
from festo_control import *
from comms_monitor import CommsMonitorPanel
import theme

# The Acton/TemperatureFit panel is the main window's content and is deliberately sized
# for 1280x1000 (see acton_pixis.InitiateActonTfit). MENU_BAR_HEIGHT reserves room above
# it for the custom (themable) menu bar built in __main__.
ACTON_PANEL_WIDTH = 1280
ACTON_PANEL_HEIGHT = 1000
MENU_BAR_HEIGHT = 32
MAIN_WINDOW_WIDTH = ACTON_PANEL_WIDTH
MAIN_WINDOW_HEIGHT = ACTON_PANEL_HEIGHT + MENU_BAR_HEIGHT

win_color = theme.PANEL_BG

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
        theme.apply_dark_titlebar(self)

class Piezo_Controls(tk.Toplevel):
    def __init__(self):
        tk.Toplevel.__init__(self)
        self.title("AGILIS Control Window")
        self.geometry("505x600")
        self.PiezoControlClass = InitiatePiezoMotorControls(self,0,0,agilis_com_port)
        print(agilis_com_port)
        theme.apply_dark_titlebar(self)

class Festo_Controls(tk.Toplevel):
     def __init__(self):
        tk.Toplevel.__init__(self)
        self.title("Festo Control Window")
        self.geometry("280x445")
        self.FestoControlClass = FestoControlWindow(self, left_denkovi_com_port, right_denkovi_com_port)
        theme.apply_dark_titlebar(self)

class CommsMonitor_Controls(tk.Toplevel):
    def __init__(self):
        tk.Toplevel.__init__(self)
        self.title("Communications Monitor")
        self.geometry("710x420")
        self.CommsMonitorPanel = CommsMonitorPanel(self)
        theme.apply_dark_titlebar(self)

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
        if not options:
            # No serial devices detected (e.g. running away from the rig with nothing
            # plugged in) - fall back to a placeholder so the dropdowns can still build.
            options = ["No COM ports detected"]

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

        theme.apply_dark_titlebar(self)

    def get_com_ports(self):
        ports = [port.device for port in serial.tools.list_ports.comports()]
        return ports
    
    def update_com_ports(self):
        #If statement for updating the Peizo Control Window
        if PiezoControlWindow.winfo_exists():
            #update global variable
            globals()['agilis_com_port'] = self.local_agilis_com_port.get()
            #setting the com ports for laser 1 and laser 2 piezos if window already exists
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
        if FestoControlWindow.winfo_exists():
            #Updating the values within the global variables for festo comports
            globals()['right_denkovi_com_port'] = self.right_relays_com_port.get()
            globals()['left_denkovi_com_port'] = self.left_relays_com_port.get()

            #Updating the values within the existing classes
            FestoControlWindow.FestoControlClass.RightSideControls.right_side_comport = self.right_relays_com_port.get()
            FestoControlWindow.FestoControlClass.LeftSideControls.left_side_comport = self.left_relays_com_port.get()
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
            globals()['FestoControlWindow'] = Festo_Controls()    
        elif window_value == 3:
            globals()['LaserControlWindow'] = Laser_Controls()
        elif window_value == 4:
            globals()['ComPortControlWindow'] = ComPort_Controls()
        elif window_value == 5:
            globals()['CommsMonitorWindow'] = CommsMonitor_Controls()
        else:
            do_nothing()
    

if __name__ == "__main__":

    #***** Building USER GUI *****

    # Begin code with window code
    window = tk.Tk()
    window.title("EPL Laser Heating Control")

    # Apply the dark theme before building any content, so every widget created from
    # here on (in this window and every Toplevel opened later) picks up the theme.
    theme.apply_dark_theme(window)

    theme.center_on_primary_monitor(window, MAIN_WINDOW_WIDTH, MAIN_WINDOW_HEIGHT)
    theme.apply_dark_titlebar(window)

    ico = Image.open("images/laser-icon.png")
    photo = ImageTk.PhotoImage(ico)
    window.wm_iconphoto(False, photo)
    
    ActonControlWindow = ActonPixis = InitiateActonTfit(window, 0, MENU_BAR_HEIGHT, left_denkovi_com_port, right_denkovi_com_port)
    LaserControlWindow = Laser_Controls()
    PiezoControlWindow = Piezo_Controls()
    FestoControlWindow = Festo_Controls()
    ComPortControlWindow = ComPort_Controls()
    CommsMonitorWindow = CommsMonitor_Controls()

    LaserControlWindow.destroy() 
    #FestoControlWindow.destroy() 
    PiezoControlWindow.destroy() 
    ComPortControlWindow.destroy()
    CommsMonitorWindow.destroy()
    
    # Creating a top menu. Built from plain Tk widgets (Frame + Menubutton) rather than
    # the native window menu (.config(menu=...)) - on Windows, the native menu bar is
    # drawn by the OS itself and ignores Tk's color settings, which left a bright white
    # strip across the top of an otherwise dark window. Menubuttons are regular themable
    # Tk widgets, so this one picks up the dark theme like everything else.
    menu_bar_frame = tk.Frame(window, bg=theme.PANEL_BG, height=MENU_BAR_HEIGHT)
    menu_bar_frame.place(x=0, y=0, width=MAIN_WINDOW_WIDTH, height=MENU_BAR_HEIGHT)

    def add_menu(label):
        button = tk.Menubutton(menu_bar_frame, text=label, bg=theme.PANEL_BG, fg=theme.FG,
                                activebackground=theme.SELECT_BG, activeforeground=theme.FG,
                                relief="flat", padx=12, pady=6)
        button.pack(side="left")
        menu = tk.Menu(button, tearoff=0, bg=theme.PANEL_BG, fg=theme.FG,
                        activebackground=theme.SELECT_BG, activeforeground=theme.FG)
        button.configure(menu=menu)
        return menu

    file_menu = add_menu("Main")
    file_menu.add_command(label="Exit", command=window.quit)

    # Create a Spectrometer menu
    spectrometer_menu = add_menu("Spectrometer")
    spectrometer_menu.add_command(label="High Temperature", command=do_nothing)
    spectrometer_menu.add_command(label="Low Temperature", command=do_nothing)
    spectrometer_menu.add_command(label="2D", command=do_nothing)

    # Create a Communications menu
    communications_menu = add_menu("Communications")
    communications_menu.add_command(label="COM Ports", command=lambda: open_window(4, ComPortControlWindow))
    communications_menu.add_command(label="Laser IPs", command=do_nothing)
    communications_menu.add_command(label="Communications Monitor", command=lambda: open_window(5, CommsMonitorWindow))

    # Create a Windows menu
    windows_menu = add_menu("Windows")
    windows_menu.add_command(label="Piezo Controls", command=lambda: open_window(1, PiezoControlWindow))
    windows_menu.add_command(label="Festo Controls", command=lambda: open_window(2, FestoControlWindow))
    windows_menu.add_command(label="Laser Controls", command=lambda: open_window(3, LaserControlWindow))

    window.mainloop()