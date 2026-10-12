"""Manual loading and automatic acquisition coordination for the Tk view."""
import tkinter as tk
from tkinter import filedialog
from pathlib import Path
import queue
import time
from watchdog.observers import Observer
from watchdog.events import PatternMatchingEventHandler
import theme

class DataFileHandling(tk.Frame):
    AUTOFIT_POLL_MS = 1000
    AUTOFIT_SETTLE_SECONDS = 1.0
    AUTOFIT_MAX_READ_RETRIES = 5

    def __init__(self, container, temperature_plots, calibration_files, x_position, y_position, autofit_folderpath):
        super().__init__(container)

        #Frame visual configuration
        self.configure(width=320,height=370,background=theme.PANEL_BG, highlightbackground=theme.BORDER, highlightthickness=1)

        #Frame position information
        self.place(x = x_position, y = y_position)
        self.plots = temperature_plots
        self.file_extensions = temperature_plots.file_extensions
        self.calibration_files = calibration_files

        #Check button variable
        self.automatic_fitting_button_state = tk.IntVar()
        self.auto_fitting_folder_path = tk.StringVar()

        # watchdog calls file_created() on its own background thread, but Tkinter/matplotlib
        # calls are only safe from the main thread. New files are handed off through this
        # thread-safe queue and actually processed in file_fitting_thread(), which runs on
        # the main thread via self.after().
        self._new_spe_file_queue = queue.Queue()
        self._pending_spe_files = {}
        self._processed_spe_files = set()
        self._failed_spe_files = {}
        self._watch_generation = 0
        self._autofit_after_id = None
        self.my_observer = None
        self.folder_path = None
        self.bind("<Destroy>", self._on_autofit_destroy, add="+")

        #Frame buttons and labels
        self.select_lightfield_spectra = tk.Button(self, text="Select Spectrum for T-fit", font=('Helvetica', 10), command=lambda: self.data_file_open_dialog(1))
        self.select_lightfield_spectra.place(x = 10, y = 10, width=300, height = 30)
        self.selected_lightfield_spectra = tk.Text(self, font=('Helvetica', 10), highlightbackground=theme.BORDER, highlightthickness=0, background=theme.TEXT_BG)
        self.selected_lightfield_spectra.place(x = 10, y = 50, width=300, height = 50)

        self.select_folder_to_save_tfit = tk.Button(self, text="Select Folder for T-fit", font=('Helvetica', 10), command=lambda: self.data_file_open_dialog(2))
        self.select_folder_to_save_tfit.place(x = 10, y = 110, width=300, height = 30)
        self.selected_folder_to_save_tfit = tk.Text(self, font=('Helvetica', 10), highlightbackground=theme.BORDER, highlightthickness=0, background=theme.TEXT_BG)
        self.selected_folder_to_save_tfit.place(x = 10, y = 150, width=300, height = 50)
        self.select_automatic_fit = tk.Checkbutton(self, text="Automatic Fitting", bg = theme.PANEL_BG, font=('Helvetica', 10), variable = self.automatic_fitting_button_state, command=lambda: self.automatic_file_fitting())
        self.select_automatic_fit.place(x = 10, y = 200, width= 150, height= 30)
        self.autofit_status = tk.Label(self, text="Automatic fitting stopped", anchor="w", font=('Helvetica', 8))
        self.autofit_status.place(x=10, y=232, width=300, height=18)

        autofit_folderpath = Path(autofit_folderpath)
        autofit_folderpath = autofit_folderpath.absolute()
        self.selected_folder_to_save_tfit.insert("end-1c", autofit_folderpath)

        self.enter_output_filename = tk.Label(self, text="Enter output filename", font=('Helvetica', 10), highlightbackground=theme.BORDER, highlightthickness=1)
        self.enter_output_filename.place(x = 10, y = 250, width=300, height = 30)
        self.entered_output_filename = tk.Text(self, font=('Helvetica', 10), highlightbackground=theme.BORDER, highlightthickness=0, background=theme.TEXT_BG)
        self.entered_output_filename.place(x = 10, y = 290, width=300, height = 30)
        self.select_folder_to_save_tfit = tk.Button(self, text="Save Temperature Fit", font=('Helvetica', 10), command=lambda: self.data_file_open_dialog(2))
        self.select_folder_to_save_tfit.place(x = 10, y = 325, width=300, height = 30)
        self.enter_output_filename.config(text="Output filename", anchor="w", fg=theme.FG_MUTED)
        self.autofit_status.config(fg=theme.FG_MUTED)
        theme.modernize_widgets(self)

    # Watchdog callbacks only enqueue paths. All Tk access, reads, and fitting
    # happen on the main thread. A generation token rejects old-session events.
    def file_created(self, event, generation=None):
        if event.is_directory:
            return
        path = getattr(event, "dest_path", None) or event.src_path
        if Path(path).suffix.lower() in self.file_extensions:
            token = self._watch_generation if generation is None else generation
            self._new_spe_file_queue.put((token, str(Path(path).resolve())))

    def process_new_spe_file(self, file_path):
        try:
            if not self.calibration_files.has_valid_calibration():
                self.autofit_status.config(text="Skipped: calibration missing")
                print(f"Skipping fit for {file_path}: This state doesn't have a Calibration File.")
                return True

            left_path = self.calibration_files.left_file_location.get("1.0", tk.END).strip()
            right_path = self.calibration_files.right_file_location.get("1.0", tk.END).strip()
            left_temperature = float(self.calibration_files.set_left_temperature.get("1.0", tk.END))
            right_temperature = float(self.calibration_files.set_right_temperature.get("1.0", tk.END))
            # Finish all reads before replacing the currently displayed data.
            left_calibration = self.plots.load_capture(left_path)
            right_calibration = self.plots.load_capture(right_path)
            measurement = self.plots.load_capture(file_path)
            self.plots.set_capture(measurement, left_calibration, right_calibration,
                                   left_temperature, right_temperature)
            self.selected_lightfield_spectra.delete("1.0", tk.END)
            self.selected_lightfield_spectra.insert(tk.END, file_path)
            self.autofit_status.config(text=f"Fitted: {Path(file_path).name}")
            return True
        except Exception as read_error:
            self.autofit_status.config(text=f"Cannot fit: {read_error}")
            print(f"Could not process {file_path} yet ({read_error})")
            return False

    def _scan_spe_files(self):
        return {str(path.resolve()) for path in Path(self.folder_path).rglob("*")
                if path.is_file() and path.suffix.lower() in self.file_extensions}

    def automatic_file_fitting(self):
        if not self.automatic_fitting_button_state.get():
            self.stop_automatic_fitting()
            return
        chosen_path = self.selected_folder_to_save_tfit.get("1.0", tk.END).strip()
        folder = Path(chosen_path).expanduser().resolve() if chosen_path else None
        if self.my_observer is not None and str(folder) == self.folder_path and self.my_observer.is_alive():
            return
        self.stop_automatic_fitting()
        if folder is None or not folder.is_dir():
            self.autofit_status.config(text="Choose an existing folder for T-fit")
            return
        try:
            self.folder_path = str(folder)
            # Existing files are not refitted merely by enabling automatic mode.
            self._processed_spe_files = self._scan_spe_files()
            self._watch_generation += 1
            generation = self._watch_generation
            self.my_event_handler = PatternMatchingEventHandler(patterns=[f"*{suffix}" for suffix in self.file_extensions], ignore_directories=True,
                                                               case_sensitive=False)
            callback = lambda event: self.file_created(event, generation)
            self.my_event_handler.on_created = callback
            self.my_event_handler.on_moved = callback
            self.my_event_handler.on_modified = callback
            self.my_observer = Observer()
            self.my_observer.schedule(self.my_event_handler, self.folder_path, recursive=True)
            self.my_observer.start()
        except Exception as watch_error:
            self.stop_automatic_fitting()
            self.autofit_status.config(text="Could not watch the selected folder")
            print(f"Could not start automatic fitting: {watch_error}")
            return
        self.automatic_fitting_button_state.set(1)
        self.autofit_status.config(text="Watching for new spectra")
        print(f"Automatic file fitting enabled: {self.folder_path}")
        self.file_fitting_thread()

    def stop_automatic_fitting(self):
        self._watch_generation += 1
        self.automatic_fitting_button_state.set(0)
        if self._autofit_after_id is not None:
            self.after_cancel(self._autofit_after_id)
            self._autofit_after_id = None
        observer, self.my_observer = self.my_observer, None
        if observer is not None:
            observer.stop()
            if observer.ident is not None:
                observer.join(timeout=2)
        self._pending_spe_files.clear()
        self._processed_spe_files.clear()
        self._failed_spe_files.clear()
        while True:
            try:
                self._new_spe_file_queue.get_nowait()
            except queue.Empty:
                break
        if self.autofit_status.winfo_exists():
            self.autofit_status.config(text="Automatic fitting stopped")

    def _on_autofit_destroy(self, event):
        if event.widget is self:
            self.stop_automatic_fitting()

    def file_fitting_thread(self):
        self._autofit_after_id = None
        if not self.automatic_fitting_button_state.get():
            return
        if self.my_observer is None or not self.my_observer.is_alive():
            self.stop_automatic_fitting()
            self.autofit_status.config(text="Folder watcher stopped unexpectedly")
            return
        now = time.monotonic()
        new_paths = set()
        while True:
            try:
                generation, path = self._new_spe_file_queue.get_nowait()
            except queue.Empty:
                break
            if generation == self._watch_generation:
                new_paths.add(path)
        # Recover arrivals even if an OS event is missed, including renamed or
        # slowly written files. Duplicate events still produce a single fit.
        try:
            new_paths.update(self._scan_spe_files())
        except OSError as scan_error:
            print(f"Could not scan {self.folder_path}: {scan_error}")
        for path in new_paths - self._processed_spe_files:
            if not Path(path).is_relative_to(self.folder_path):
                continue
            self._pending_spe_files.setdefault(path, {"signature": None, "changed_at": now, "retries": 0})
        for path, pending in list(self._pending_spe_files.items()):
            try:
                stat = Path(path).stat()
                signature = (stat.st_size, stat.st_mtime_ns)
            except FileNotFoundError:
                self._pending_spe_files.pop(path, None)
                continue
            except OSError:
                continue
            if self._failed_spe_files.get(path) == signature:
                self._pending_spe_files.pop(path, None)
                continue
            if signature != pending["signature"]:
                pending.update(signature=signature, changed_at=now, retries=0)
                continue
            if stat.st_size == 0 or now - pending["changed_at"] < self.AUTOFIT_SETTLE_SECONDS:
                continue
            if self.process_new_spe_file(path):
                self._processed_spe_files.add(path)
                self._pending_spe_files.pop(path, None)
                self._failed_spe_files.pop(path, None)
            else:
                pending["retries"] += 1
                if pending["retries"] >= self.AUTOFIT_MAX_READ_RETRIES:
                    # Retry again if writing resumes; do not lose a late footer.
                    self._failed_spe_files[path] = signature
                    self._pending_spe_files.pop(path, None)
                    self.autofit_status.config(text=f"Failed to fit: {Path(path).name}")
                    print(f"Waiting for changes to unreadable spectrum: {path}")
        self._autofit_after_id = self.after(self.AUTOFIT_POLL_MS, self.file_fitting_thread)

    def data_file_open_dialog(self, file_location_number):
        #Differentiates between the light field spectra and the t-rax folder
        if file_location_number == 1:
            self.open_file_path = filedialog.askopenfilename(filetypes=[("Camera spectrum", " ".join(f"*{suffix}" for suffix in self.file_extensions)), ("All files", "*.*")])
            if not self.open_file_path:
                return
            self.process_new_spe_file(self.open_file_path)

        elif file_location_number == 2:
            self.open_folder_path = filedialog.askdirectory()
            if not self.open_folder_path:
                return
            self.selected_folder_to_save_tfit.delete("1.0", tk.END)
            self.selected_folder_to_save_tfit.insert(tk.END, self.open_folder_path)
            if self.automatic_fitting_button_state.get():
                self.automatic_file_fitting()
