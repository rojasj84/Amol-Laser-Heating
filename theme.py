# Shared dark theme applied across every window in the program. Tkinter has no global
# stylesheet the way ttk does, so this does two things: (1) sets application-wide default
# widget colors via Tk's option database, which any widget that doesn't set its own colors
# picks up automatically (including widgets in windows created later), and (2) provides
# named color constants for the places in the GUI code that do set explicit colors, so
# those can be swapped from the old light palette to this one.

BG = "#1e1e1e"              # main window / frame background
PANEL_BG = "#252526"        # slightly raised panel background (was "White")
TEXT_BG = "#2d2d2d"         # Text/Entry widget background (was "light gray")
BORDER = "#4a4a4a"          # frame border / divider color (was "black" - invisible on a dark background)
FG = "#e6e6e6"              # primary text color
FG_MUTED = "#9a9a9a"        # secondary/disabled text color
BUTTON_BG = "#3a3a3a"
BUTTON_ACTIVE_BG = "#4a4a4a"
SELECT_BG = "#0a5a8a"       # selection / active highlight

LEFT_ACCENT = "#2f6f9f"     # left-side controls (was "Light Blue")
RIGHT_ACCENT = "#9f3f5f"    # right-side controls (was "Pink")


def apply_dark_theme(root):
    """Sets dark defaults for every widget class used in this program via the Tk option
    database. Call once, right after creating the root Tk() window and before building
    any other widgets - the defaults apply to every widget created afterward, in every
    window, since they all share the same underlying Tcl interpreter."""

    root.configure(bg=BG)

    root.option_add("*Background", BG)
    root.option_add("*Foreground", FG)
    root.option_add("*activeBackground", BUTTON_ACTIVE_BG)
    root.option_add("*activeForeground", FG)
    root.option_add("*selectBackground", SELECT_BG)
    root.option_add("*selectForeground", FG)
    root.option_add("*disabledForeground", FG_MUTED)
    root.option_add("*highlightBackground", BG)
    root.option_add("*highlightColor", BORDER)
    root.option_add("*insertBackground", FG)  # text cursor color

    root.option_add("*Button.background", BUTTON_BG)
    root.option_add("*Button.activeBackground", BUTTON_ACTIVE_BG)
    root.option_add("*Text.background", TEXT_BG)
    root.option_add("*Entry.background", TEXT_BG)
    root.option_add("*Listbox.background", TEXT_BG)
    root.option_add("*OptionMenu.background", BUTTON_BG)

    root.option_add("*Menu.background", PANEL_BG)
    root.option_add("*Menu.foreground", FG)
    root.option_add("*Menu.activeBackground", SELECT_BG)
    root.option_add("*Menu.activeForeground", FG)


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
