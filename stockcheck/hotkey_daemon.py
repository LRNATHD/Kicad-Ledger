"""Windows KiCad-aware Global Hotkey Listener."""

import sys
import os
import time
import threading
from typing import Callable, Optional

# Windows-specific imports using ctypes
if sys.platform == "win32":
    import ctypes
    from ctypes import wintypes
    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32
else:
    user32 = None
    kernel32 = None


def get_foreground_window_title() -> str:
    """Return the title of the current foreground window on Windows."""
    if not user32:
        return ""
    hwnd = user32.GetForegroundWindow()
    if not hwnd:
        return ""
    length = user32.GetWindowTextLengthW(hwnd)
    if length <= 0:
        return ""
    buf = ctypes.create_unicode_buffer(length + 1)
    user32.GetWindowTextW(hwnd, buf, length + 1)
    return buf.value


def is_kicad_focused() -> bool:
    """Check if the currently focused window is part of KiCad."""
    title = get_foreground_window_title().lower()
    kicad_keywords = [
        "kicad",
        "schematic editor",
        "pcb editor",
        "eeschema",
        "pcbnew",
        "footprint editor",
        "symbol editor"
    ]
    return any(keyword in title for keyword in kicad_keywords)


class KiCadHotkeyDaemon:
    """
    Background daemon that monitors for a hotkey (default: Ctrl+Shift+I or F8).
    Only triggers the callback popup when KiCad is the active focused window.
    When any other application is active, the hotkey is ignored and untouched.
    """

    def __init__(self, callback: Callable[[], None], hotkey: str = "ctrl+shift+i"):
        self.callback = callback
        self.hotkey = hotkey.lower()
        self.running = False
        self._thread: Optional[threading.Thread] = None

    def start(self):
        """Start listener in background thread."""
        if self.running:
            return
        self.running = True
        self._thread = threading.Thread(target=self._run_listener, daemon=True)
        self._thread.start()

    def stop(self):
        self.running = False

    def _run_listener(self):
        """
        Poll keyboard state using GetAsyncKeyState for maximum compatibility
        and zero external dependencies.
        """
        if not user32:
            return

        VK_SHIFT = 0x10
        VK_CONTROL = 0x11
        VK_MENU = 0x12  # Alt
        VK_F8 = 0x77
        VK_I = 0x49
        VK_K = 0x4B

        # Parse hotkey config
        req_ctrl = "ctrl" in self.hotkey
        req_shift = "shift" in self.hotkey
        req_alt = "alt" in self.hotkey
        
        main_vk = VK_I
        if "f8" in self.hotkey:
            main_vk = VK_F8
            req_ctrl = False
            req_shift = False
        elif "k" in self.hotkey:
            main_vk = VK_K

        def key_down(vk):
            return (user32.GetAsyncKeyState(vk) & 0x8000) != 0

        was_pressed = False

        while self.running:
            try:
                # Check modifier keys
                ctrl_ok = key_down(VK_CONTROL) if req_ctrl else not key_down(VK_CONTROL)
                shift_ok = key_down(VK_SHIFT) if req_shift else not key_down(VK_SHIFT)
                alt_ok = key_down(VK_MENU) if req_alt else not key_down(VK_MENU)
                main_ok = key_down(main_vk)

                is_combo_down = ctrl_ok and shift_ok and alt_ok and main_ok

                if is_combo_down and not was_pressed:
                    was_pressed = True
                    # ONLY fire if KiCad is the active foreground window!
                    if is_kicad_focused():
                        self.callback()
                elif not is_combo_down:
                    was_pressed = False

                time.sleep(0.04)  # 25Hz poll, imperceptible CPU usage (<0.01%)
            except Exception:
                time.sleep(0.1)


if __name__ == "__main__":
    print("Testing KiCad Active Window Check:")
    print("Current window title:", get_foreground_window_title())
    print("Is KiCad focused?", is_kicad_focused())
