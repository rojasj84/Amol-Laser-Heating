"""Shared modern dark palette and presentation helpers for the Tk application."""
import tkinter as tk
from tkinter import font as tkfont, ttk

BG = "#0C1220"
PANEL_BG = "#141E30"
TEXT_BG = "#0F1828"
PLOT_BG = "#111A2B"
BORDER = "#2B3950"
FG = "#EDF2FA"
FG_MUTED = "#97A8BF"
BUTTON_BG = "#223149"
BUTTON_ACTIVE_BG = "#304563"
SELECT_BG = "#356FE3"
PRIMARY_HOVER = "#4681F4"
LEFT_ACCENT = "#25527D"
RIGHT_ACCENT = "#713D57"
LEFT_FG = "#8AC8FA"
RIGHT_FG = "#F0AEC9"
FIT_COLOR = "#F2CC7B"

FONT_FAMILY = "Segoe UI"
FONT_BODY = (FONT_FAMILY, 10)
FONT_SMALL = (FONT_FAMILY, 9)
FONT_BUTTON = (FONT_FAMILY, 10, "bold")
FONT_HEADING = (FONT_FAMILY, 14, "bold")
FONT_TITLE = (FONT_FAMILY, 20, "bold")


def apply_dark_theme(root):
    """Set defaults for current and future windows, including ttk controls."""
    root.configure(bg=BG)
    defaults = {
        "*Font": FONT_BODY, "*Background": BG, "*Foreground": FG,
        "*activeBackground": BUTTON_ACTIVE_BG, "*activeForeground": FG,
        "*selectBackground": SELECT_BG, "*selectForeground": FG,
        "*disabledForeground": FG_MUTED, "*highlightBackground": BORDER,
        "*highlightColor": SELECT_BG, "*insertBackground": FG,
        "*Button.background": BUTTON_BG, "*Button.relief": "flat",
        "*Button.borderWidth": 0, "*Button.highlightThickness": 1,
        "*Text.background": TEXT_BG, "*Text.relief": "flat",
        "*Entry.background": TEXT_BG, "*Entry.relief": "flat",
        "*Listbox.background": TEXT_BG, "*Menu.background": PANEL_BG,
        "*Menu.foreground": FG, "*Menu.activeBackground": SELECT_BG,
        "*Menu.activeForeground": FG, "*Menu.borderWidth": 0,
    }
    for option, value in defaults.items():
        root.option_add(option, value)
    for name in ("TkDefaultFont", "TkTextFont", "TkMenuFont", "TkHeadingFont"):
        tkfont.nametofont(name, root=root).configure(family=FONT_FAMILY, size=10)
    style = ttk.Style(root)
    style.theme_use("clam")
    style.configure(".", background=BG, foreground=FG, font=FONT_BODY)
    style.configure("TFrame", background=BG)
    style.configure("TLabel", background=BG, foreground=FG)
    style.configure("TButton", background=BUTTON_BG, foreground=FG,
                    padding=(12, 5), borderwidth=0, relief="flat")
    style.map("TButton", background=[("disabled", PANEL_BG), ("active", BUTTON_ACTIVE_BG)],
              foreground=[("disabled", FG_MUTED)])
    for name in ("TEntry", "TCombobox", "TSpinbox"):
        style.configure(name, fieldbackground=TEXT_BG, background=BUTTON_BG,
                        foreground=FG, insertcolor=FG, bordercolor=BORDER,
                        lightcolor=BORDER, darkcolor=BORDER, arrowcolor=FG_MUTED)
        style.map(name, fieldbackground=[("readonly", TEXT_BG)],
                  foreground=[("disabled", FG_MUTED), ("readonly", FG)])


def style_button(widget, kind="secondary"):
    """Style a real Tk button without changing its command or mouse bindings."""
    primary = kind == "primary"
    widget._modern_base = SELECT_BG if primary else BUTTON_BG
    widget._modern_hover = PRIMARY_HOVER if primary else BUTTON_ACTIVE_BG
    foreground = FG if primary else widget.cget("foreground")
    widget.configure(background=widget._modern_base, foreground=foreground,
                     activebackground=widget._modern_hover, activeforeground=foreground,
                     disabledforeground=FG if primary else FG_MUTED,
                     font=FONT_BUTTON, relief="flat", overrelief="flat", borderwidth=0,
                     highlightthickness=1, highlightbackground=widget._modern_base,
                     highlightcolor=SELECT_BG, padx=10, pady=4, cursor="hand2")
    widget._modern_style_applied = True
    if not getattr(widget, "_modern_hover_bound", False):
        def hover(event, entered):
            if widget.cget("state") != "disabled":
                color = widget._modern_hover if entered else widget._modern_base
                widget.configure(background=color, highlightbackground=color)
        widget.bind("<Enter>", lambda event: hover(event, True), add="+")
        widget.bind("<Leave>", lambda event: hover(event, False), add="+")
        widget._modern_hover_bound = True


def modernize_widgets(container):
    """Apply consistent typography and flat controls to older panels as well."""
    widget = container
    if not getattr(widget, "_modern_style_applied", False):
        if isinstance(widget, tk.Button):
            style_button(widget)
        elif isinstance(widget, tk.Radiobutton):
            selected = widget.cget("selectcolor")
            widget.configure(font=FONT_BODY, background=BUTTON_BG,
                             selectcolor=selected, activebackground=BUTTON_ACTIVE_BG,
                             activeforeground=FG, foreground=FG, relief="flat",
                             offrelief="flat", overrelief="flat", borderwidth=0,
                             highlightthickness=1, highlightbackground=BORDER,
                             highlightcolor=SELECT_BG, padx=5, pady=3, cursor="hand2")
        elif isinstance(widget, tk.Checkbutton):
            widget.configure(font=FONT_BODY, relief="flat", borderwidth=0,
                             selectcolor=SELECT_BG, activebackground=widget.cget("background"),
                             highlightthickness=0, cursor="hand2")
        elif isinstance(widget, (tk.Text, tk.Entry, tk.Spinbox)):
            widget.configure(font=FONT_SMALL, background=TEXT_BG, foreground=FG,
                             relief="flat", borderwidth=0, highlightthickness=1,
                             highlightbackground=BORDER, highlightcolor=SELECT_BG,
                             insertbackground=FG)
            if isinstance(widget, tk.Text):
                widget.configure(padx=7, pady=2)
        elif isinstance(widget, (tk.Label, tk.Menubutton, tk.Scale)):
            current = tkfont.Font(root=widget, font=widget.cget("font")).actual()
            widget.configure(font=(FONT_FAMILY, current["size"], current["weight"]))
            if isinstance(widget, tk.Label):
                widget.configure(relief="flat", borderwidth=0, highlightthickness=0)
            elif isinstance(widget, tk.Menubutton):
                widget.configure(relief="flat", borderwidth=0)
            elif isinstance(widget, tk.Scale):
                widget.configure(relief="flat", borderwidth=0, troughcolor=TEXT_BG,
                                 highlightthickness=0, activebackground=SELECT_BG)
        elif isinstance(widget, tk.Frame):
            widget.configure(relief="flat", borderwidth=0)
        elif isinstance(widget, tk.Scrollbar):
            widget.configure(background=BUTTON_BG, troughcolor=TEXT_BG,
                             relief="flat", borderwidth=0, highlightthickness=0, width=12)
        widget._modern_style_applied = True
    for child in widget.winfo_children():
        modernize_widgets(child)


def style_plot_axis(axis):
    """Give spectra restrained grids and consistent labels on every redraw."""
    axis.set_facecolor(PLOT_BG)
    axis.set_axisbelow(True)
    axis.grid(visible=True, color=BORDER, alpha=0.4, linewidth=0.6)
    axis.tick_params(colors=FG_MUTED, labelsize=8, length=3, width=0.6)
    for spine in axis.spines.values():
        spine.set_color(BORDER)
        spine.set_linewidth(0.8)
    for text in (*axis.get_xticklabels(), *axis.get_yticklabels(),
                 axis.xaxis.get_offset_text(), axis.yaxis.get_offset_text()):
        text.set_fontfamily(FONT_FAMILY)
        text.set_color(FG_MUTED)
    for location in ("left", "center", "right"):
        axis.set_title(axis.get_title(loc=location), loc=location, fontfamily=FONT_FAMILY,
                       fontsize=11, fontweight="bold", color=FG)
    for label in (axis.xaxis.label, axis.yaxis.label):
        label.set(fontfamily=FONT_FAMILY, fontsize=8, color=FG_MUTED)


def apply_dark_titlebar(window):
    """Best-effort: asks Windows to draw this window's native title bar in dark mode
    (Windows 10 20H1+/11 only, via the same DWM attribute Windows' own dark-mode-aware
    apps use). Tk has no control over the title bar otherwise - it's OS chrome, not a
    Tk widget. Silently does nothing on older Windows or if the call fails for any
    reason; this is a cosmetic bonus the rest of the theme doesn't depend on."""

    try:
        import ctypes

        window.update_idletasks()
        GA_ROOT = 2
        hwnd = ctypes.windll.user32.GetAncestor(window.winfo_id(), GA_ROOT)

        DWMWA_USE_IMMERSIVE_DARK_MODE = 20
        value = ctypes.c_int(1)
        ctypes.windll.dwmapi.DwmSetWindowAttribute(
            hwnd, DWMWA_USE_IMMERSIVE_DARK_MODE, ctypes.byref(value), ctypes.sizeof(value)
        )
    except Exception:
        pass


def center_on_primary_monitor(window, width, height):
    """Positions the window at the given size, centered on the primary monitor,
    regardless of that monitor's resolution.

    Note: this takes an explicit target size rather than trying to auto-detect the
    window's required size. This program lays out every window with .place() (absolute
    pixel positions), which - unlike pack()/grid() - does not report its size back up to
    the parent, so Tk's own "how big does this window need to be" introspection would
    just return a meaningless default here rather than the actual content size.

    If the requested size is larger than the available screen, the window is clamped to
    fit the screen and anchored to the top-left corner instead of being centered
    partly off-screen.
    """

    screen_width = window.winfo_screenwidth()
    screen_height = window.winfo_screenheight()

    width = min(width, screen_width)
    height = min(height, screen_height)

    x = max((screen_width - width) // 2, 0)
    y = max((screen_height - height) // 2, 0)

    window.geometry(f"{width}x{height}+{x}+{y}")
    window.minsize(width, height)
