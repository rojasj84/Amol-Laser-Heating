import tkinter as tk
import serial.tools.list_ports


class ComPortSelection(tk.Frame):
    def __init__(self, container):
        #tk.Frame.__init__(self, container)
        super().__init__(container)

        self.place(x = 0, y = 0, width = 360, height = 200)

        agilis_com_port = tk.StringVar(self)
        agilis_com_port.set("COM11")

        right_relays_com_port = tk.StringVar(self)
        right_relays_com_port.set("COM6")

        left_relays_com_port = tk.StringVar(self)
        left_relays_com_port.set("COM7")

        options = self.get_com_ports()

        agilis_label = tk.Label(self, text = "AGILIS Piezo Motors", font=("Arial", 10))
        agilis_label.place(x = 10, y = 20)
        agilis_dropdown = tk.OptionMenu(self, agilis_com_port, options[0], *options)
        agilis_dropdown.place(x = 150, y = 20, width=200, height=25)

        right_side_relays_label = tk.Label(self, text = "Right Side Relays", font=("Arial", 10))
        right_side_relays_label.place(x = 10, y = 50)
        right_side_relay_dropdown = tk.OptionMenu(self, right_relays_com_port, options[0], *options)
        right_side_relay_dropdown.place(x = 150, y = 50, width=200, height=25)

        left_side_relays_label = tk.Label(self, text = "Left Side Relays", font=("Arial", 10))
        left_side_relays_label.place(x = 10, y = 80)
        left_side_relay_dropdown = tk.OptionMenu(self, left_relays_com_port, options[0], *options)
        left_side_relay_dropdown.place(x = 150, y = 80, width=200, height=25)

        update_button = tk.Button(self, text="Update")
        update_button.place(x = 75, y = 120, width=200)

    def get_com_ports(self):
        ports = [port.device for port in serial.tools.list_ports.comports()]
        return ports
    
    def update_com_ports(self):
        return 0


if __name__ == "__main__":
     # Begin code with window code
    window = tk.Tk()
    window.title("Festo Control Window")
    window.geometry("360x200")

    A = ComPortSelection(window)

    window.mainloop()