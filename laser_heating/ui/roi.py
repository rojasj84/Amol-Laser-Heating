"""Camera-sized ROI editor with validation and JSON persistence."""
import tkinter as tk
from tkinter import filedialog
import json
import numpy as np
from matplotlib import pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import theme
from laser_heating.models import RegionOfInterest
from .roi_drag import ROIDragController

class ROISelectionWindow(tk.Toplevel):
    def __init__(self, parent, plot_graphs_instance):
        super().__init__(parent)
        self.title("Dynamic ROI Configuration")
        self.geometry("900x700")

        theme.apply_dark_theme(self)
        theme.apply_dark_titlebar(self)

        self.plot_graphs = plot_graphs_instance

        img_data = self.plot_graphs.data_file.frame(self.plot_graphs.current_frame_index)
        self.image_height, self.image_width = img_data.shape

        # Left Panel - Image Plot
        self.fig, self.ax = plt.subplots(figsize=(6.5, 5.5))
        self.fig.patch.set_facecolor(theme.PANEL_BG)
        self.ax.set_facecolor(theme.PANEL_BG)

        # Calculate dynamic vmin/vmax to avoid blowing out contrast
        vmax = np.percentile(img_data, 99) if np.max(img_data) > 0 else 1000
        self.im = self.ax.imshow(img_data, aspect='auto', cmap='viridis', vmax=vmax,
                                 extent=(0, self.image_width, self.image_height, 0))
        # Include a small margin so handles at the image boundaries stay pickable.
        self.ax.set_xlim(-0.02*self.image_width, 1.02*self.image_width)
        self.ax.set_ylim(1.02*self.image_height, -0.02*self.image_height)
        self.fig.colorbar(self.im, ax=self.ax)
        self.ax.set_title("CCD Image", color="white")
        self.ax.tick_params(colors="white")

        self.canvas = FigureCanvasTkAgg(self.fig, master=self)
        self.canvas.draw()
        self.canvas.get_tk_widget().place(x=10, y=10, width=650, height=650)

        self.mouse_hint = tk.Label(self, bg=theme.PANEL_BG, fg=theme.FG,
                                   text="Drag corners/edges to resize; drag inside to move.\nClick a side title to choose overlapping ROIs.")
        self.mouse_hint.place(x=10, y=663, width=650, height=32)
        self._syncing_roi_fields = False

        # Right Panel - Controls
        control_frame = tk.Frame(self, bg=theme.PANEL_BG)
        control_frame.place(x=670, y=10, width=220, height=680)

        tk.Button(control_frame, text="Left Spectrum (Green)", command=lambda: self.drag_controller.select_side("left"), bg=theme.PANEL_BG, fg="green", font=("Helvetica", 11, "bold")).pack(pady=(5, 2))

        # X and Y controls for Left
        tk.Label(control_frame, text="X-Start:", bg=theme.PANEL_BG, fg=theme.FG).pack()
        self.left_x_start_var = tk.StringVar(value=str(self.plot_graphs.left_roi.x_start))
        tk.Spinbox(control_frame, from_=0, to=self.image_width, textvariable=self.left_x_start_var, command=self.update_lines, bg=theme.TEXT_BG, fg=theme.FG).pack()
        self.left_x_start_var.trace("w", lambda name, index, mode: self.update_lines())

        tk.Label(control_frame, text="X-End:", bg=theme.PANEL_BG, fg=theme.FG).pack()
        self.left_x_end_var = tk.StringVar(value=str(self.plot_graphs.left_roi.x_end))
        tk.Spinbox(control_frame, from_=0, to=self.image_width, textvariable=self.left_x_end_var, command=self.update_lines, bg=theme.TEXT_BG, fg=theme.FG).pack()
        self.left_x_end_var.trace("w", lambda name, index, mode: self.update_lines())

        tk.Label(control_frame, text="Y-Start:", bg=theme.PANEL_BG, fg=theme.FG).pack()
        self.left_y_start_var = tk.StringVar(value=str(self.plot_graphs.left_roi.y_start))
        tk.Spinbox(control_frame, from_=0, to=self.image_height, textvariable=self.left_y_start_var, command=self.update_lines, bg=theme.TEXT_BG, fg=theme.FG).pack()
        self.left_y_start_var.trace("w", lambda name, index, mode: self.update_lines())

        tk.Label(control_frame, text="Y-End:", bg=theme.PANEL_BG, fg=theme.FG).pack()
        self.left_y_end_var = tk.StringVar(value=str(self.plot_graphs.left_roi.y_end))
        tk.Spinbox(control_frame, from_=0, to=self.image_height, textvariable=self.left_y_end_var, command=self.update_lines, bg=theme.TEXT_BG, fg=theme.FG).pack()
        self.left_y_end_var.trace("w", lambda name, index, mode: self.update_lines())

        tk.Button(control_frame, text="Right Spectrum (Red)", command=lambda: self.drag_controller.select_side("right"), bg=theme.PANEL_BG, fg="red", font=("Helvetica", 11, "bold")).pack(pady=(15, 2))

        # X and Y controls for Right
        tk.Label(control_frame, text="X-Start:", bg=theme.PANEL_BG, fg=theme.FG).pack()
        self.right_x_start_var = tk.StringVar(value=str(self.plot_graphs.right_roi.x_start))
        tk.Spinbox(control_frame, from_=0, to=self.image_width, textvariable=self.right_x_start_var, command=self.update_lines, bg=theme.TEXT_BG, fg=theme.FG).pack()
        self.right_x_start_var.trace("w", lambda name, index, mode: self.update_lines())

        tk.Label(control_frame, text="X-End:", bg=theme.PANEL_BG, fg=theme.FG).pack()
        self.right_x_end_var = tk.StringVar(value=str(self.plot_graphs.right_roi.x_end))
        tk.Spinbox(control_frame, from_=0, to=self.image_width, textvariable=self.right_x_end_var, command=self.update_lines, bg=theme.TEXT_BG, fg=theme.FG).pack()
        self.right_x_end_var.trace("w", lambda name, index, mode: self.update_lines())

        tk.Label(control_frame, text="Y-Start:", bg=theme.PANEL_BG, fg=theme.FG).pack()
        self.right_y_start_var = tk.StringVar(value=str(self.plot_graphs.right_roi.y_start))
        tk.Spinbox(control_frame, from_=0, to=self.image_height, textvariable=self.right_y_start_var, command=self.update_lines, bg=theme.TEXT_BG, fg=theme.FG).pack()
        self.right_y_start_var.trace("w", lambda name, index, mode: self.update_lines())

        tk.Label(control_frame, text="Y-End:", bg=theme.PANEL_BG, fg=theme.FG).pack()
        self.right_y_end_var = tk.StringVar(value=str(self.plot_graphs.right_roi.y_end))
        tk.Spinbox(control_frame, from_=0, to=self.image_height, textvariable=self.right_y_end_var, command=self.update_lines, bg=theme.TEXT_BG, fg=theme.FG).pack()
        self.right_y_end_var.trace("w", lambda name, index, mode: self.update_lines())

        # Save / Load Config Buttons
        btn_frame = tk.Frame(control_frame, bg=theme.PANEL_BG)
        btn_frame.pack(pady=10)
        tk.Button(btn_frame, text="Load Config", command=self.load_config, font=("Helvetica", 9), bg=theme.PANEL_BG, fg=theme.FG).pack(side="left", padx=5)
        tk.Button(btn_frame, text="Save Config", command=self.save_config, font=("Helvetica", 9), bg=theme.PANEL_BG, fg=theme.FG).pack(side="left", padx=5)

        self.btn_apply = tk.Button(control_frame, text="Apply & Close", command=self.apply_and_close, font=("Helvetica", 11, "bold"), bg=theme.SELECT_BG, fg=theme.FG)
        self.btn_apply.pack(pady=10)
        self.error_label = tk.Label(control_frame, text="", fg="#FF5252", wraplength=210, bg=theme.PANEL_BG)
        self.error_label.pack()

        self.drag_controller = ROIDragController(self.ax, self.image_width, self.image_height,
                                                  self._on_roi_drag, self._on_roi_hover)
        # Keep the named rectangle references for existing callers.
        self.left_rect = self.drag_controller.rectangles["left"]
        self.right_rect = self.drag_controller.rectangles["right"]

        theme.style_button(self.btn_apply, kind="primary")
        theme.modernize_widgets(self)
        theme.style_plot_axis(self.ax)
        self.update_lines()

    def save_config(self):
        file_path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON files", "*.json")])
        if not file_path:
            return
        config = {
            "camera_width": self.image_width,
            "camera_height": self.image_height,
            "left_x_start": int(self.left_x_start_var.get()),
            "left_x_end": int(self.left_x_end_var.get()),
            "left_y_start": int(self.left_y_start_var.get()),
            "left_y_end": int(self.left_y_end_var.get()),
            "right_x_start": int(self.right_x_start_var.get()),
            "right_x_end": int(self.right_x_end_var.get()),
            "right_y_start": int(self.right_y_start_var.get()),
            "right_y_end": int(self.right_y_end_var.get())
        }
        with open(file_path, "w") as f:
            json.dump(config, f, indent=4)

    def load_config(self):
        file_path = filedialog.askopenfilename(filetypes=[("JSON files", "*.json")])
        if not file_path:
            return
        try:
            with open(file_path, "r") as f:
                config = json.load(f)
            if (config.get("camera_width", self.image_width), config.get("camera_height", self.image_height)) != (self.image_width, self.image_height):
                raise ValueError("Saved ROIs belong to a different camera image size")
            self.left_x_start_var.set(str(config.get("left_x_start", self.plot_graphs.left_roi.x_start)))
            self.left_x_end_var.set(str(config.get("left_x_end", self.plot_graphs.left_roi.x_end)))
            self.left_y_start_var.set(str(config.get("left_y_start", self.plot_graphs.left_roi.y_start)))
            self.left_y_end_var.set(str(config.get("left_y_end", self.plot_graphs.left_roi.y_end)))

            self.right_x_start_var.set(str(config.get("right_x_start", self.plot_graphs.right_roi.x_start)))
            self.right_x_end_var.set(str(config.get("right_x_end", self.plot_graphs.right_roi.x_end)))
            self.right_y_start_var.set(str(config.get("right_y_start", self.plot_graphs.right_roi.y_start)))
            self.right_y_end_var.set(str(config.get("right_y_end", self.plot_graphs.right_roi.y_end)))

            self.update_lines()
        except Exception as e:
            self.error_label.config(text=f"Failed to load config: {e}")

    def _roi_from_fields(self, side):
        return RegionOfInterest(*(int(getattr(self, f"{side}_{field}_var").get())
                                  for field in ("x_start", "x_end", "y_start", "y_end")))

    def update_lines(self):
        if self._syncing_roi_fields or not hasattr(self, "drag_controller"):
            return
        rois = {}
        for side in ("left", "right"):
            try:
                roi = self._roi_from_fields(side)
                roi.validate(self.image_width, self.image_height)
                rois[side] = roi
            except ValueError:
                # Hide invalid previews while the user edits numeric text.
                continue
        self.drag_controller.set_rois(rois)

    def _on_roi_drag(self, side, roi):
        self._syncing_roi_fields = True
        try:
            for field in ("x_start", "x_end", "y_start", "y_end"):
                getattr(self, f"{side}_{field}_var").set(str(getattr(roi, field)))
        finally:
            self._syncing_roi_fields = False
        self.error_label.config(text="")
        self.update_lines()

    def _on_roi_hover(self, side, handle):
        cursors = {"top": "sb_v_double_arrow", "bottom": "sb_v_double_arrow",
                   "left": "sb_h_double_arrow", "right": "sb_h_double_arrow",
                   "top_left": "top_left_corner", "top_right": "top_right_corner",
                   "bottom_left": "bottom_left_corner", "bottom_right": "bottom_right_corner",
                   "move": "fleur"}
        self.canvas.get_tk_widget().configure(cursor=cursors.get(handle, "arrow"))
        if side is None:
            text = "Drag corners/edges to resize; drag inside to move.\nClick a side title to choose overlapping ROIs."
        else:
            action = "move rectangle" if handle == "move" else f"resize {handle.replace('_', ' ')}"
            text = f"{side.title()} ROI: click and hold to {action}."
        self.mouse_hint.config(text=text)

    def apply_and_close(self):
        previous = self.plot_graphs.left_roi, self.plot_graphs.right_roi
        try:
            rois = []
            for side in ("left", "right"):
                roi = self._roi_from_fields(side)
                roi.validate(self.image_width, self.image_height)
                rois.append(roi)
            self.plot_graphs.left_roi, self.plot_graphs.right_roi = rois
            self.plot_graphs.update_graphs()
        except ValueError as error:
            self.plot_graphs.left_roi, self.plot_graphs.right_roi = previous
            self.error_label.config(text=str(error))
            return
        self.destroy()

    def destroy(self):
        self.drag_controller.disconnect()
        # Traces may have queued an idle draw just before this window closes.
        if self.canvas._idle_draw_id is not None:
            self.canvas.get_tk_widget().after_cancel(self.canvas._idle_draw_id)
            self.canvas._idle_draw_id = None
        plt.close(self.fig)
        super().destroy()
