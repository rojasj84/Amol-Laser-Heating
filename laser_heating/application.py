"""Application ownership and startup. Windows share explicit configuration."""
import argparse
from dataclasses import replace
import tkinter as tk
from tkinter import messagebox

from PIL import Image, ImageTk
import serial.tools.list_ports

import hardware_mode
import theme
from comms_monitor import CommsMonitorPanel
from festo_control import FestoControlWindow
from laser_communication import LaserCommunication
from piezo_motor_control import InitiatePiezoMotorControls

from .config import APP_ROOT, ApplicationConfig
from .readers import ReaderRegistry
from .ui.temperature import TemperaturePanel


class ConnectionSettingsWindow(tk.Toplevel):
    def __init__(self, parent, application):
        super().__init__(parent)
        self.application = application
        self.title("Instrument Connections")
        self.geometry("390x270")
        settings = application.config.hardware
        self.values = {}
        fields = (("agilis_port", "AGILIS motors"), ("left_relay_port", "Left relays"),
                  ("right_relay_port", "Right relays"), ("left_laser_ip", "Left laser address"),
                  ("right_laser_ip", "Right laser address"))
        ports = [] if hardware_mode.is_debug() else [port.device for port in serial.tools.list_ports.comports()]
        ports = list(dict.fromkeys(ports + [settings.agilis_port, settings.left_relay_port, settings.right_relay_port]))
        for row, (key, label) in enumerate(fields):
            tk.Label(self, text=label).place(x=10, y=15+row*36, width=140, height=25)
            variable = tk.StringVar(self, value=getattr(settings, key))
            self.values[key] = variable
            if key.endswith("_port"):
                widget = tk.OptionMenu(self, variable, *ports)
            else:
                widget = tk.Entry(self, textvariable=variable)
            widget.place(x=155, y=15+row*36, width=220, height=25)
        self.error = tk.Label(self, text="", fg="#FF5252")
        self.error.place(x=10, y=196, width=370, height=20)
        tk.Button(self, text="Apply", command=self.apply).place(x=95, y=225, width=200, height=30)
        theme.apply_dark_titlebar(self)

    def apply(self):
        values = {key: variable.get().strip() for key, variable in self.values.items()}
        if not all(values.values()):
            self.error.config(text="Each instrument needs a port or address")
            return
        self.application.set_connections(replace(self.application.config.hardware, **values))


class HeatingApplication:
    """Own configuration, panels, and the lifetime of all auxiliary windows."""

    def __init__(self, root, config=None, readers=None, camera=None):
        self.root = root
        self.config = config or ApplicationConfig()
        self.readers = readers or ReaderRegistry.defaults()
        self.readers.get(self.config.camera.reader)
        self.windows = {}
        self.panels = {}
        theme.apply_dark_theme(root)
        root.title("EPL Laser Heating Control" + (" [DEBUG - instruments simulated]" if hardware_mode.is_debug() else ""))
        theme.center_on_primary_monitor(root, 1280, 1032)
        theme.apply_dark_titlebar(root)
        self.icon = ImageTk.PhotoImage(Image.open(APP_ROOT / "images" / "laser-icon.png"))
        root.wm_iconphoto(False, self.icon)
        hardware = self.config.hardware
        self.temperature = TemperaturePanel(root, 0, 32, hardware.left_relay_port,
                                            hardware.right_relay_port, self.config, self.readers, camera)
        self._build_menu()
        # Preserve the existing startup layout; other windows are built on demand.
        self.open_window("piezo")
        self.open_window("festo")
        theme.modernize_widgets(root)

    def open_window(self, name):
        existing = self.windows.get(name)
        if existing is not None and existing.winfo_exists():
            existing.deiconify()
            existing.lift()
            return existing
        if name == "connections":
            window = ConnectionSettingsWindow(self.root, self)
        else:
            window = tk.Toplevel(self.root)
            hardware = self.config.hardware
            if name == "piezo":
                window.title("AGILIS Control Window")
                window.geometry("505x600")
                self.panels[name] = InitiatePiezoMotorControls(window, 0, 0, hardware.agilis_port,
                                                             hardware.left_laser_ip, hardware.right_laser_ip)
            elif name == "festo":
                window.title("Festo Control Window")
                window.geometry("280x445")
                self.panels[name] = FestoControlWindow(window, hardware.left_relay_port, hardware.right_relay_port)
            elif name == "laser":
                window.title("Laser Control Window")
                window.geometry("505x500")
                LaserCommunication(window, hardware.left_laser_ip, 20, 20)
                LaserCommunication(window, hardware.right_laser_ip, 260, 20)
            elif name == "monitor":
                window.title("Communications Monitor")
                window.geometry("710x420")
                self.panels[name] = CommsMonitorPanel(window)
            else:
                window.destroy()
                raise ValueError(f"Unknown window {name!r}")
        theme.modernize_widgets(window)
        theme.apply_dark_titlebar(window)
        self.windows[name] = window
        return window

    def set_connections(self, settings):
        self.config.hardware = settings
        filters = self.temperature.TransmissionFilter
        filters.left_denkovi_com_port = settings.left_relay_port
        filters.right_denkovi_com_port = settings.right_relay_port
        if self.windows.get("piezo") is not None and self.windows["piezo"].winfo_exists():
            motors = self.panels["piezo"]
            motors.set_com_port(settings.agilis_port)
            motors.left_laser_ip, motors.right_laser_ip = settings.left_laser_ip, settings.right_laser_ip
        if self.windows.get("festo") is not None and self.windows["festo"].winfo_exists():
            self.panels["festo"].set_com_ports(settings.left_relay_port, settings.right_relay_port)
        if self.windows.get("laser") is not None and self.windows["laser"].winfo_exists():
            self.windows["laser"].destroy()
            self.open_window("laser")

    def _build_menu(self):
        bar = tk.Frame(self.root, bg=theme.PANEL_BG, height=32)
        bar.place(x=0, y=0, width=1280, height=32)

        def menu(label):
            button = tk.Menubutton(bar, text=label, bg=theme.PANEL_BG, fg=theme.FG,
                                   activebackground=theme.SELECT_BG, activeforeground=theme.FG,
                                   relief="flat", padx=12, pady=6)
            button.pack(side="left")
            commands = tk.Menu(button, tearoff=0, bg=theme.PANEL_BG, fg=theme.FG,
                               activebackground=theme.SELECT_BG, activeforeground=theme.FG)
            button.config(menu=commands)
            return commands

        menu("Main").add_command(label="Exit", command=self.root.destroy)
        camera = menu("Spectrometer")
        camera.add_command(label="Camera Control", command=lambda: self.temperature.select_file_handling(3))
        camera.add_command(label="ROI Settings", command=self.temperature.open_roi_settings)
        camera.add_command(label="Camera Profile", command=lambda: messagebox.showinfo(
            "Camera Profile", f"{self.config.camera.name}\nSaved images: {self.config.camera.width} x {self.config.camera.height}", parent=self.root))
        communications = menu("Communications")
        communications.add_command(label="COM Ports", command=lambda: self.open_window("connections"))
        communications.add_command(label="Laser IPs", command=lambda: self.open_window("connections"))
        communications.add_command(label="Communications Monitor", command=lambda: self.open_window("monitor"))
        windows = menu("Windows")
        for key, label in (("piezo", "Piezo Controls"), ("festo", "Festo Controls"), ("laser", "Laser Controls")):
            windows.add_command(label=label, command=lambda name=key: self.open_window(name))
        if hardware_mode.is_debug():
            tk.Label(bar, text="DEBUG: instruments simulated", fg="#FFB74D",
                     bg=theme.PANEL_BG, padx=10).pack(side="right", fill="y")


def run(argv=None):
    parser = argparse.ArgumentParser(description="EPL Laser Heating Control")
    parser.add_argument("--debug", action="store_true", help="Simulate instrument connections")
    parser.add_argument("--config", default=str(APP_ROOT / "config" / "default.json"),
                        help="Application JSON: camera profile, ROI, calibration, and connections")
    args = parser.parse_args(argv)
    try:
        config = ApplicationConfig.load(args.config)
        ReaderRegistry.defaults().get(config.camera.reader)
    except (OSError, ValueError, TypeError) as error:
        parser.error(str(error))
    hardware_mode.configure(debug=args.debug)
    root = tk.Tk()
    application = HeatingApplication(root, config)
    root.mainloop()
    return application
