# Central log of every outgoing hardware communication (serial writes to COM ports,
# TCP sends to laser controllers) plus a window to display it. Lets the program be run
# away from the rig - with nothing physically connected - so outgoing commands can still
# be reviewed instead of the program either crashing or silently doing nothing.
import time
import tkinter as tk

_history = []
_max_history = 500
_subscribers = []


def log(target, message, ok=True):
    timestamp = time.strftime("%H:%M:%S")
    status = "" if ok else "   [NOT SENT - could not reach device]"
    entry = f"[{timestamp}] {target}:  {message}{status}"

    _history.append(entry)
    if len(_history) > _max_history:
        del _history[0]

    for callback in list(_subscribers):
        callback(entry)

    return entry


def get_history():
    return list(_history)


def subscribe(callback):
    _subscribers.append(callback)


def unsubscribe(callback):
    if callback in _subscribers:
        _subscribers.remove(callback)


class CommsMonitorPanel(tk.Frame):
    def __init__(self, container):
        super().__init__(container)

        self.configure(width=700, height=400)
        self.place(x=0, y=0, width=700, height=400)

        info_label = tk.Label(self, text="Outgoing hardware communications (COM ports / laser IPs)", anchor="w")
        info_label.place(x=5, y=5, width=580, height=25)

        clear_button = tk.Button(self, text="Clear", command=self.clear_log)
        clear_button.place(x=600, y=5, width=90, height=25)

        text_frame = tk.Frame(self)
        text_frame.place(x=5, y=35, width=690, height=360)

        scrollbar = tk.Scrollbar(text_frame)
        scrollbar.pack(side="right", fill="y")

        self.log_text = tk.Text(text_frame, wrap="none", yscrollcommand=scrollbar.set, state="disabled")
        self.log_text.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=self.log_text.yview)

        # Show whatever was already logged before this window existed, then keep it live.
        for entry in get_history():
            self._append(entry)
        subscribe(self._append)
        self.bind("<Destroy>", lambda event: unsubscribe(self._append))

    def _append(self, entry):
        self.log_text.configure(state="normal")
        self.log_text.insert("end", entry + "\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def clear_log(self):
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.configure(state="disabled")


if __name__ == "__main__":
    window = tk.Tk()
    window.title("Communications Monitor")
    window.geometry("710x420")

    log("Denkovi relay board (COM6)", "x\\x0c\\x00//")
    log("AGILIS piezo controller (COM10)", "CC1 / 1JA2")
    log("Laser (192.168.1.100)", "EMON", ok=False)

    panel = CommsMonitorPanel(window)

    window.mainloop()
