"""Background KiCad Hotkey Daemon for KiCad-StockCheck."""

import sys
import os
import glob

# Ensure repo root is on sys.path
repo_root = os.path.dirname(os.path.abspath(__file__))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

import wx
from stockcheck.hotkey_daemon import KiCadHotkeyDaemon, is_kicad_focused, get_foreground_window_title
from stockcheck.ui.main_frame import StockCheckFrame
from stockcheck.kicad_parser import KiCadParser


def find_most_recent_kicad_file() -> str:
    """Attempt to find recently modified KiCad PCB/schematic in common project folders."""
    candidates = []
    search_dirs = [os.getcwd(), os.path.dirname(repo_root)]
    
    for sdir in search_dirs:
        for ext in ("*.kicad_pcb", "*.kicad_sch"):
            for f in glob.glob(os.path.join(sdir, "**", ext), recursive=True):
                try:
                    candidates.append((os.path.getmtime(f), f))
                except OSError:
                    continue

    if candidates:
        candidates.sort(key=lambda x: x[0], reverse=True)
        return candidates[0][1]
    return ""


class HotkeyApp:
    def __init__(self, hotkey="ctrl+shift+i"):
        self.app = wx.App(False)
        self.frame: StockCheckFrame = None
        self.hotkey = hotkey
        self.daemon = KiCadHotkeyDaemon(callback=self.on_trigger, hotkey=self.hotkey)

    def start(self):
        print("=" * 65)
        print("KiCad-StockCheck Background Hotkey Daemon Running")
        print(f"Hotkey: [{self.hotkey.upper()}] (or press F8 if configured)")
        print("Rule  : Only activates when KiCad is the active foreground window.")
        print("=" * 65)
        print("Listening... (Press Ctrl+C to terminate)")

        self.daemon.start()
        self.app.MainLoop()

    def on_trigger(self):
        """Called by background thread when hotkey is pressed while KiCad is focused."""
        wx.CallAfter(self._show_window)

    def _show_window(self):
        if not self.frame:
            # Check if recent file can be pre-loaded
            recent_file = find_most_recent_kicad_file()
            board_items = []
            board_name = ""
            if recent_file and os.path.exists(recent_file):
                try:
                    board_items = KiCadParser.parse_file(recent_file)
                    board_name = os.path.basename(recent_file)
                except Exception:
                    pass

            self.frame = StockCheckFrame(None, board_items=board_items, board_name=board_name)

        self.frame.Show(True)
        self.frame.Raise()
        self.frame.SetFocus()


if __name__ == "__main__":
    hotkey = "ctrl+shift+i"
    if len(sys.argv) > 1:
        hotkey = sys.argv[1]
    app = HotkeyApp(hotkey=hotkey)
    app.start()
