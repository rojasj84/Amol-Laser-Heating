"""Camera tab: exposure, experiment file, acquisition, background and flatfield.

Camera calls can take seconds (LightField start-up, long exposures), so they
run on one worker thread. Results return through a queue that is read on the
Tk thread; widgets, plots and fitting are only touched there.
"""
from pathlib import Path
import queue
import shutil
import threading
import time
import tkinter as tk
from tkinter import filedialog
import traceback

import comms_monitor
import theme


class CameraControlPanel(tk.Frame):
    UNITS = {"µs": 1e-6, "ms": 1e-3, "s": 1.0}
    POLL_MS = 50

    def __init__(self, container, camera, temperature_plots, calibration_files, data_files,
                 x_position, y_position, exposure_seconds=0.1):
        super().__init__(container)
        self.configure(width=320, height=370, background=theme.PANEL_BG,
                       highlightbackground=theme.BORDER, highlightthickness=1)
        self.place(x=x_position, y=y_position)
        self.camera = camera
        self.plots = temperature_plots
        self.calibration_files = calibration_files
        self.data_files = data_files
        self.busy = False
        self.background_path = None
        self.flatfield_paths = {"left": None, "right": None}

        self._jobs = queue.Queue()
        self._results = queue.Queue()
        self._poll_id = None
        self._worker = threading.Thread(target=self._work, name="camera-control", daemon=True)
        self._worker.start()
        self.bind("<Destroy>", self._on_destroy, add="+")

        self.exposure_value = tk.StringVar(self)
        self.exposure_unit = tk.StringVar(self, value="ms")
        self.flatfield_side = tk.StringVar(self, value="left")
        self.reference_temperature = tk.StringVar(self)
        self._buttons = []

        def label(text, x, y, width, height=22, **options):
            options.setdefault("anchor", "w")
            options.setdefault("font", theme.FONT_SMALL)
            widget = tk.Label(self, text=text, background=theme.PANEL_BG, **options)
            widget.place(x=x, y=y, width=width, height=height)
            return widget

        def button(text, command, x, y, width, height=26, kind="secondary"):
            widget = tk.Button(self, text=text, command=command)
            widget.place(x=x, y=y, width=width, height=height)
            theme.style_button(widget, kind=kind)
            widget.configure(padx=2, pady=2)
            self._buttons.append(widget)
            return widget

        self.connection_label = label("Camera not connected", 10, 8, 200, fg=theme.FG_MUTED)
        self.connect_button = button("Connect", self.connect, 215, 6, 95)

        label("Exposure", 10, 40, 62)
        self.exposure_entry = tk.Entry(self, textvariable=self.exposure_value, justify="right")
        self.exposure_entry.place(x=74, y=38, width=82, height=26)
        self.exposure_entry.bind("<Return>", lambda event: self.apply_exposure())
        self.unit_menu = tk.OptionMenu(self, self.exposure_unit, *self.UNITS)
        self.unit_menu.configure(background=theme.BUTTON_BG, foreground=theme.FG, highlightthickness=0,
                                 activebackground=theme.BUTTON_ACTIVE_BG, activeforeground=theme.FG,
                                 relief="flat", borderwidth=0)
        self.unit_menu["menu"].configure(background=theme.PANEL_BG, foreground=theme.FG,
                                         activebackground=theme.SELECT_BG, activeforeground=theme.FG)
        self.unit_menu.place(x=160, y=38, width=66, height=26)
        self.set_exposure_button = button("Set", self.apply_exposure, 230, 38, 80)

        # Only the driver back end needs a wavelength reference.
        self.has_reference = hasattr(self.camera, "set_reference")
        self.experiment_name = None
        self.load_experiment_button = button("Load LF Exp. Setup file", self.load_experiment, 10, 70,
                                             186 if self.has_reference else 300)
        if self.has_reference:
            self.reference_button = button("Wavelength ref.", self.choose_reference, 200, 70, 110)
        self.experiment_label = label("", 10, 98, 300, 18, fg=theme.FG_MUTED)
        self._show_setup()

        self.acquire_button = button("Acquire Spectrum", self.acquire_spectrum, 10, 120, 300, 30, kind="primary")

        label("Background", 10, 158, 300, 18, font=(theme.FONT_FAMILY, 9, "bold"))
        self.collect_background_button = button("Collect", self.collect_background, 10, 178, 72)
        self.save_background_button = button("Save", self.save_background, 86, 178, 72)
        self.load_background_button = button("Load", self.load_background, 162, 178, 72)
        self.clear_background_button = button("Clear", self.clear_background, 238, 178, 72)
        self.background_label = label("No background subtracted", 10, 206, 300, 18, fg=theme.FG_MUTED)

        label("Flatfield", 10, 232, 70, 22, font=(theme.FONT_FAMILY, 9, "bold"))
        self.side_buttons = {}
        for index, (side, color) in enumerate((("left", theme.LEFT_ACCENT), ("right", theme.RIGHT_ACCENT))):
            radio = tk.Radiobutton(self, text=side.capitalize(), indicatoron=0, value=side,
                                   variable=self.flatfield_side, selectcolor=color,
                                   command=self._show_flatfield_status)
            radio.place(x=160 + index * 76, y=230, width=74, height=24)
            self.side_buttons[side] = radio
        label("Ref T (K)", 10, 260, 62)
        self.reference_entry = tk.Entry(self, textvariable=self.reference_temperature, justify="right")
        self.reference_entry.place(x=74, y=258, width=82, height=26)
        self.collect_flatfield_button = button("Collect", self.collect_flatfield, 10, 288, 97)
        self.save_flatfield_button = button("Save", self.save_flatfield, 111, 288, 97)
        self.load_flatfield_button = button("Load", self.load_flatfield, 212, 288, 98)
        self.flatfield_label = label("", 10, 316, 300, 18, fg=theme.FG_MUTED)

        self.status_label = label("", 10, 342, 300, 20, fg=theme.FG_MUTED)

        self._show_exposure(exposure_seconds)
        self.reference_temperature.set(self.calibration_files.set_left_temperature.get("1.0", tk.END).strip())
        self._show_flatfield_status()
        theme.modernize_widgets(self)

    # ---- worker thread -------------------------------------------------
    def _work(self):
        while True:
            job = self._jobs.get()
            if job is None:
                return
            work, on_success = job
            try:
                self._results.put((True, work(), on_success))
            except Exception as error:  # reported on the Tk thread
                self._results.put((False, (error, traceback.format_exc()), None))

    def _submit(self, message, work, on_success):
        """Run work() off the Tk thread; on_success(result) runs on the Tk thread."""
        if self.busy:
            return False
        self.busy = True
        for widget in self._buttons:
            widget.configure(state="disabled")
        self._status(message)
        self._jobs.put((work, on_success))
        self._poll_id = self.after(self.POLL_MS, self._poll)
        return True

    def _poll(self):
        self._poll_id = None
        try:
            ok, result, on_success = self._results.get_nowait()
        except queue.Empty:
            self._poll_id = self.after(self.POLL_MS, self._poll)
            return
        self.busy = False
        for widget in self._buttons:
            widget.configure(state="normal")
        self._show_connection()
        if not ok:
            error, details = result
            self._status(str(error), error=True, details=details)
            return
        try:
            on_success(result)
        except Exception as error:
            self._status(str(error), error=True, details=traceback.format_exc())

    def _on_destroy(self, event):
        if event.widget is not self:
            return
        if self._poll_id is not None:
            self.after_cancel(self._poll_id)
            self._poll_id = None
        # Close LightField on the thread that opened it, then stop the worker.
        self._jobs.put((self.camera.close, None))
        self._jobs.put(None)
        self._worker.join(timeout=5)

    # ---- small helpers -------------------------------------------------
    def _status(self, message, error=False, details=""):
        """One-line status; errors also open a window where the whole message can be read."""
        self.status_label.configure(text=message, fg="#FF5252" if error else theme.FG_MUTED)
        if error:
            comms_monitor.log("Camera tab", f"Error: {message}", ok=True)
            self._show_error(message, details)

    def _show_error(self, message, details=""):
        """Non-blocking window with the full, selectable error text. Reused while open."""
        self.last_error = message + (f"\n\n{'-' * 40}\nDetails for troubleshooting:\n{details}" if details else "")
        dialog = getattr(self, "error_dialog", None)
        if dialog is None or not dialog.winfo_exists():
            dialog = self.error_dialog = tk.Toplevel(self)
            dialog.title("Camera message")
            dialog.configure(background=theme.PANEL_BG)
            dialog.minsize(420, 220)
            buttons = tk.Frame(dialog, background=theme.PANEL_BG)
            buttons.pack(side="bottom", fill="x", padx=12, pady=(0, 12))
            close = tk.Button(buttons, text="Close", command=dialog.destroy, width=10)
            close.pack(side="right")
            copy = tk.Button(buttons, text="Copy text", command=self._copy_error, width=10)
            copy.pack(side="right", padx=(0, 8))
            theme.style_button(close, kind="primary")
            theme.style_button(copy)
            scrollbar = tk.Scrollbar(dialog)
            scrollbar.pack(side="right", fill="y", pady=12, padx=(0, 12))
            dialog.error_text = tk.Text(dialog, wrap="word", font=theme.FONT_BODY, background=theme.TEXT_BG,
                                        foreground=theme.FG, relief="flat", padx=12, pady=10,
                                        yscrollcommand=scrollbar.set)
            dialog.error_text.pack(side="left", fill="both", expand=True, padx=(12, 0), pady=12)
            dialog.error_text.tag_configure("message", font=(theme.FONT_FAMILY, 11, "bold"), foreground="#FF8A80",
                                            spacing3=6)
            dialog.error_text.tag_configure("details", font=("Consolas", 9), foreground=theme.FG_MUTED)
            scrollbar.configure(command=dialog.error_text.yview)
            dialog.bind("<Escape>", lambda event: dialog.destroy())
            top = self.winfo_toplevel()
            dialog.geometry(f"620x320+{top.winfo_rootx() + 340}+{top.winfo_rooty() + 120}")
            dialog.transient(top)
            theme.apply_dark_titlebar(dialog)
        text = dialog.error_text
        text.configure(state="normal")
        text.delete("1.0", tk.END)
        text.insert(tk.END, message, "message")
        if details:
            text.insert(tk.END, f"\n\nDetails for troubleshooting:\n{details}", "details")
        text.configure(state="disabled")  # still selectable for copying
        dialog.lift()

    def _copy_error(self):
        self.clipboard_clear()
        self.clipboard_append(getattr(self, "last_error", ""))

    def _show_connection(self):
        if self.camera.connected:
            self.connection_label.configure(text=f"Connected: {self.camera.name}", fg="#4CAF50")
        else:
            self.connection_label.configure(text="Camera not connected", fg=theme.FG_MUTED)

    def _show_exposure(self, seconds):
        """Show a camera value as %.2f, moving to a finer unit rather than rounding it away."""
        units = [self.exposure_unit.get()] + [unit for unit in ("s", "ms", "µs")]
        for unit in units:
            value = seconds / self.UNITS[unit]
            if abs(round(value, 2) - value) <= 0.005 * value:
                break
        self.exposure_unit.set(unit)
        self.exposure_value.set(f"{value:.2f}")

    def _exposure_seconds(self):
        try:
            value = float(self.exposure_value.get())
        except ValueError:
            raise ValueError("Exposure time must be a number") from None
        if not value > 0 or value == float("inf"):
            raise ValueError("Exposure time must be greater than zero")
        self.exposure_value.set(f"{value:.2f}")
        seconds = round(value, 2) * self.UNITS[self.exposure_unit.get()]
        if not seconds > 0:
            raise ValueError("Exposure time must be at least 0.01 in the selected unit")
        return seconds

    def _reference_kelvin(self):
        try:
            value = float(self.reference_temperature.get())
        except ValueError:
            raise ValueError("Ref T must be a number in kelvin") from None
        if not 0 < value < float("inf"):
            raise ValueError("Ref T must be greater than zero")
        return value

    def _capture_folder(self):
        text = self.data_files.selected_folder_to_save_tfit.get("1.0", tk.END).strip()
        if not text:
            raise ValueError("Choose a folder for T-fit on the Temperature Fit tab first")
        return Path(text).expanduser().resolve()

    def _new_capture(self, prefix):
        """Unique base name; the folder watcher is told to leave the file alone."""
        folder = self._capture_folder()
        stamp = time.strftime("%Y%m%d_%H%M%S")
        base, count = f"{prefix}_{stamp}", 1
        while any((folder / f"{base}{suffix}").exists() for suffix in (".spe", ".npz")):
            count += 1
            base = f"{prefix}_{stamp}_{count}"
        ignore = getattr(self.data_files, "ignore_capture", None)
        if ignore is not None:
            for name in (f"{base}.spe", f"{base}-raw.spe", f"{base}.npz"):
                ignore(folder / name)
        return folder, base

    def _acquire(self, prefix, kind, message, on_success):
        try:
            seconds = self._exposure_seconds()
            folder, base = self._new_capture(prefix)
        except ValueError as error:
            self._status(str(error), error=True)
            return

        def work():
            self.camera.connect()
            self.camera.set_exposure_seconds(seconds)
            return self.camera.acquire(folder, base, kind)
        self._submit(message, work, on_success)

    # ---- connection, exposure, experiment ------------------------------
    def connect(self):
        def work():
            self.camera.connect()
            return self.camera.get_exposure_seconds()

        def done(seconds):
            self._show_exposure(seconds)
            self._status("Camera ready")
        self._submit(f"Connecting to {self.camera.name}…", work, done)

    def apply_exposure(self):
        try:
            seconds = self._exposure_seconds()
        except ValueError as error:
            self._status(str(error), error=True)
            return

        def work():
            self.camera.connect()
            self.camera.set_exposure_seconds(seconds)
            return self.camera.get_exposure_seconds()

        def done(actual):
            self._show_exposure(actual)
            self._status(f"Exposure set to {self.exposure_value.get()} {self.exposure_unit.get()}")
        self._submit("Setting exposure…", work, done)

    def load_experiment(self):
        path = filedialog.askopenfilename(
            parent=self, title="LightField experiment setup",
            initialdir=str(Path.home() / "Documents" / "LightField" / "Experiments"),
            filetypes=[("LightField experiment", "*.lfe"), ("All files", "*.*")])
        if not path:
            return

        def work():
            self.camera.connect()
            return self.camera.load_experiment(path), self.camera.get_exposure_seconds()

        def done(result):
            self.experiment_name, seconds = result
            self._show_setup()
            self._show_exposure(seconds)
            self._status(getattr(self.camera, "experiment_note", "") or "Experiment loaded")
        self._submit("Loading experiment…", work, done)

    def _show_setup(self):
        parts = []
        if self.has_reference:
            parts.append(f"Ref: {self.camera.reference_name}")
        if self.experiment_name:
            parts.append(f"Exp: {self.experiment_name}" if self.has_reference else f"Experiment: {self.experiment_name}")
        self.experiment_label.configure(text="  ·  ".join(parts) or "No experiment file loaded",
                                        fg=theme.FG if parts else theme.FG_MUTED)

    def choose_reference(self):
        """Pick the SPE whose wavelength axis and readout regions the driver uses."""
        path = filedialog.askopenfilename(parent=self, title="Wavelength reference (LightField SPE)",
                                          filetypes=[("LightField spectrum", "*.spe"), ("All files", "*.*")])
        if not path:
            return

        def done(name):
            self._show_setup()
            self._status(f"Wavelengths from {name}")
        self._submit("Reading reference…", lambda: self.camera.set_reference(path), done)

    # ---- measurement ---------------------------------------------------
    def acquire_spectrum(self):
        def done(path):
            if self.data_files.process_new_spe_file(str(path)):
                self._status(f"Fitted {path.name}")
            else:
                self._status(self.data_files.autofit_status.cget("text"), error=True)
        self._acquire("spectrum", "spectrum", "Acquiring spectrum…", done)

    # ---- background ----------------------------------------------------
    def _use_background(self, path):
        path = Path(path)
        self.plots.set_background(self.plots.load_capture(path))
        self.background_path = path
        self.background_label.configure(text=f"Subtracting: {path.name}", fg=theme.FG)
        self._show_flatfield_status()
        self._status("Background applied")

    def collect_background(self):
        self._acquire("background", "background", "Collecting background…", self._use_background)

    def load_background(self):
        path = filedialog.askopenfilename(parent=self, title="Load background", filetypes=self._capture_filetypes())
        if not path:
            return
        try:
            self._use_background(path)
        except Exception as error:
            self._status(str(error), error=True)

    def clear_background(self):
        try:
            self.plots.set_background(None)
        except Exception as error:
            self._status(str(error), error=True)
            return
        self.background_path = None
        self.background_label.configure(text="No background subtracted", fg=theme.FG_MUTED)
        self._show_flatfield_status()
        self._status("Background cleared")

    def save_background(self):
        self._save_copy(self.background_path, "background", "Collect or load a background first")

    # ---- flatfield (the calibration for one side) ----------------------
    def _use_flatfield(self, side, path, reference_kelvin):
        """Make this capture the side's calibration only if both sides still fit."""
        path = Path(path).resolve()
        files = self.calibration_files
        fields = {"left": (files.left_file_location, files.set_left_temperature),
                  "right": (files.right_file_location, files.set_right_temperature)}
        paths = {name: field.get("1.0", tk.END).strip() for name, (field, _) in fields.items()}
        temperatures = {}
        for name, (_, temperature) in fields.items():
            if name != side:
                temperatures[name] = float(temperature.get("1.0", tk.END))
        paths[side], temperatures[side] = str(path), reference_kelvin
        needs_background = {name: name == side or files.is_raw_flatfield(paths[name]) for name in paths}
        captures = {name: self.plots.load_capture(paths[name]) for name in paths}
        self.plots.set_capture(self.plots.data_file, captures["left"], captures["right"],
                               temperatures["left"], temperatures["right"], needs_background)
        files.mark_raw_flatfield(path)
        getattr(files, f"update_{side}_calibration_file")(path)
        temperature_field = fields[side][1]
        temperature_field.delete("1.0", tk.END)
        temperature_field.insert(tk.END, f"{reference_kelvin:g}")
        files.update_status(Path(paths["left"]).is_file(), Path(paths["right"]).is_file())
        self.flatfield_paths[side] = path
        self._show_flatfield_status()
        self._status(f"{side.capitalize()} flatfield applied")

    def _show_flatfield_status(self):
        side = self.flatfield_side.get()
        path = self.flatfield_paths[side]
        if path is None:
            self.flatfield_label.configure(text=f"{side.capitalize()}: using calibration file", fg=theme.FG_MUTED)
        else:
            note = "" if self.plots.background is not None else " (no background)"
            self.flatfield_label.configure(text=f"{side.capitalize()}: {path.name}{note}", fg=theme.FG)

    def collect_flatfield(self):
        side = self.flatfield_side.get()
        try:
            reference = self._reference_kelvin()
        except ValueError as error:
            self._status(str(error), error=True)
            return
        self._acquire(f"flatfield_{side}", "flatfield", f"Collecting {side} flatfield…",
                      lambda path: self._use_flatfield(side, path, reference))

    def load_flatfield(self):
        side = self.flatfield_side.get()
        try:
            reference = self._reference_kelvin()
        except ValueError as error:
            self._status(str(error), error=True)
            return
        path = filedialog.askopenfilename(parent=self, title=f"Load {side} flatfield",
                                          filetypes=self._capture_filetypes())
        if not path:
            return
        try:
            self._use_flatfield(side, path, reference)
        except Exception as error:
            self._status(str(error), error=True)

    def save_flatfield(self):
        side = self.flatfield_side.get()
        self._save_copy(self.flatfield_paths[side], f"flatfield_{side}",
                        f"Collect or load a {side} flatfield first")

    # ---- files ---------------------------------------------------------
    def _capture_filetypes(self):
        return [("Camera capture", "*.spe *.npz"), ("All files", "*.*")]

    def _save_copy(self, source, title, missing_message):
        if source is None:
            self._status(missing_message, error=True)
            return
        target = filedialog.asksaveasfilename(parent=self, title=f"Save {title}", initialfile=source.name,
                                              defaultextension=source.suffix,
                                              filetypes=[("Camera capture", f"*{source.suffix}")])
        if not target:
            return
        target = Path(target)
        if target.suffix.lower() != source.suffix.lower():
            target = target.with_name(target.name + source.suffix)
        try:
            if target.resolve() != source.resolve():
                shutil.copyfile(source, target)
        except OSError as error:
            self._status(f"Could not save: {error}", error=True)
            return
        self._status(f"Saved {target.name}")
