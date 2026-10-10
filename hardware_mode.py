"""Explicit offline mode shared by all instrument communication functions.

Normal mode is the default. Configure once at startup, before creating controls.
"""
import comms_monitor

_debug = False


def configure(debug=False):
    global _debug
    _debug = bool(debug)


def is_debug():
    return _debug


def simulate_command(target, message):
    """Log and bypass instrument I/O in debug mode; return whether bypassed."""
    if not _debug:
        return False
    comms_monitor.log(target, f"[DEBUG - SIMULATED] {message}")
    return True
