import socket
import tkinter as tk
import time
import serial

class LaserCommunication(tk.Frame):
    
    def laser_send_command(self, laser_ip, command_string):
        # laser_ip = '192.168.0.100'
        TCP_PORT = 10001
        BUFFER_SIZE = 1024

        message = command_string + "\r"

        laser_ip_connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        laser_ip_connection.connect((laser_ip, TCP_PORT))
        laser_ip_connection.send(message.encode())
        # print("1")
        laser_dataread = laser_ip_connection.recv(1024).decode()
        # print("2")
        laser_ip_connection.close()

        print(laser_dataread)
        #laser_output_label_display.configure(text=laser_dataread)

    def laser_send_command_RS232(self, com_port, command_string):
        # serial port settings
        ser = serial.Serial(com_port, baudrate=57600, timeout=1, parity=serial.PARITY_NONE, bytesize=serial.EIGHTBITS, stopbits=serial.STOPBITS_ONE)

        # add a carrige return to the command
        message = command_string + "\r"

        # Send the command to the laser
        ser.write(message.encode())
        
        # Read the message back from the laser
        laser_dataread = ser.read()

        #Close the serial connection
        ser.close()

        print(laser_dataread)
        #laser_output_label_display.configure(text=laser_dataread)

    def timed_laser_fire(self):
        # test
        time_of_fire = float(self.text_laser_fire_time_textbox.get("1.0",'end-1c'))
        # Tell laser to fire
        #laser_send_command(laser_ip_textbox.get("1.0","end-1c"),"EMON")
        print(time_of_fire)
        
        #Wait Time
        time.sleep(time_of_fire)    

        #Tell laser to stop fire
        #laser_send_command(laser_ip_textbox.get("1.0","end-1c"),"EMOFF")
        print("Test done!")

    
    #def __init__(self, master, laser_IP, x_position, y_position):
        #tk.Frame.__init__(self)
    def __init__(self, container, laser_IP, x_position, y_position):
        #tk.Frame.__init__(self, container)
        super().__init__(container)

        #Frame visual configuration
        self.configure(width=225,height=430)
        self.config(background="light gray", highlightbackground="black", highlightthickness=1, relief="raised")
        
        #Frame position information
        self.place(x = x_position, y = y_position)

        disable_hw_emmission_ctrl_button = tk.Button(self, text="Disable HW Emission Control", command=lambda: self.laser_send_command(laser_IP,"DLE"))
        disable_hw_emmission_ctrl_button.place(x=10, y=20, width=200, height=25)

        enable_hw_emmission_ctrl_button = tk.Button(self, text="Enable HW Emission Control", command=lambda: self.laser_send_command(laser_IP,"ELE"))
        enable_hw_emmission_ctrl_button.place(x=10, y=50, width=200, height=25)

        emmission_on_button = tk.Button(self, text="Emission ON", command=lambda: self.laser_send_command(laser_IP,"EMON"))
        emmission_on_button.place(x=10, y=80, width=200, height=25)

        emmission_off_button = tk.Button(self, text="Emission OFF", command=lambda: self.laser_send_command(laser_IP,"EMOFF"))
        emmission_off_button.place(x=10, y=110, width=200, height=25)

        enable_external_control_button = tk.Button(self, text="Enable External PWR Control", command=lambda: self.laser_send_command(laser_IP,"EEC"))
        enable_external_control_button.place(x=10, y=140, width=200, height=25)

        disable_external_control_button = tk.Button(self, text="Disable External PWR Control", command=lambda: self.laser_send_command(laser_IP,"DEC"))
        disable_external_control_button.place(x=10, y=170, width=200, height=25)

        #send_command_button = tk.Button(self, text="Send Command", command=lambda: self.laser_send_command(laser_IP,text_command_textbox.get("1.0","end-1c")))
        #send_command_button.place(x=20, y=230, width=200, height=25)

        red_laser_on_button = tk.Button(self, text="Red Laser ON", command=lambda: self.laser_send_command(laser_IP,"ABN"))
        red_laser_on_button.place(x=10, y=200, width=200, height=25)

        red_laser_off_button = tk.Button(self, text="Red Laser OFF", command=lambda: self.laser_send_command(laser_IP,"ABF"))
        red_laser_off_button.place(x=10, y=230, width=200, height=25)

        laser_ip_label = tk.Label(self, text="Laser IP/COM Port")
        #laser_ip_label.place(x=250, y = 10, width=200, height=20)

        laser_power_button = tk.Button(self, text="Set Laser Power", command=lambda: self.laser_send_command(laser_IP,"SDC " + laser_power_textbox.get("1.0","end-1c")))
        laser_power_button.place(x=10, y=260, width=200, height=25)

        laser_ip_textbox = tk.Text(self)
        #laser_ip_textbox.place(x=250, y=30, width=200, height=20)
        #laser_ip_textbox.insert(0.0,"COM1")

        laser_power_textbox = tk.Text(self)
        laser_power_textbox.place(x=10, y=290, width=200, height=20)

        text_command_label = tk.Label(self, text="Text Command")
        #text_command_label.place(x=250, y = 90, width=200, height=20)

        text_command_textbox = tk.Text(self)
        #text_command_textbox.place(x=250, y=110, width=200, height=20)

        laser_output_label = tk.Label(self, text="Laser Output")
        #laser_output_label.place(x=250, y = 130, width=200, height=20)

        laser_output_label_display = tk.Label(self, text="", bd = 1, relief=tk.SUNKEN)
        #laser_output_label_display.place(x=250, y = 150, width=200, height=20)

        #Adding timed fire functionality
        text_laser_fire_time = tk.Label(self, text="Laser Fire Time (seconds)")
        text_laser_fire_time.place(x=10, y = 320, width=200, height=20)

        self.text_laser_fire_time_textbox = tk.Text(self)
        self.text_laser_fire_time_textbox.insert(0.0,"1.0")
        self.text_laser_fire_time_textbox.place(x=10, y=350, width=200, height=20)

        timed_heating_button = tk.Button(self, text="Timed Laser Firing", command=self.timed_laser_fire)
        timed_heating_button.place(x=10, y=380, width=200, height=25)

        laser_power_label = tk.Label(self, text="Laser Power")
        #laser_power_label.place(x=20, y = 410, width=200, height=20)

if __name__ == "__main__":

    mainwindow = tk.Tk()
    mainwindow.title("Laser Troubleshooting")
    #mainwindow.config(width=200, height=420)

    
    left_laser_control = LaserCommunication("192.168.1.100", 0,0)



    mainwindow.mainloop()
