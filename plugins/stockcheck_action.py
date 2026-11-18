"""KiCad PCB Editor Action Plugin for KiCad-StockCheck."""

import os
import sys

# Ensure the parent directory containing stockcheck is on python path
plugin_dir = os.path.dirname(os.path.abspath(__file__))
repo_root = os.path.dirname(plugin_dir)
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

try:
    import pcbnew
    import wx
    from stockcheck.db import Database
    from stockcheck.kicad_parser import KiCadParser
    from stockcheck.verifier import BoardVerifier
    from stockcheck.ui.main_frame import StockCheckFrame

    class StockCheckActionPlugin(pcbnew.ActionPlugin):
        """ActionPlugin integrated directly into KiCad PCB Editor."""

        def defaults(self):
            self.name = "KiCad-Ledger: Verify Components & Inventory"
            self.category = "Manufacturing / BOM"
            self.description = "Instantly verify board components against your local on-device inventory."
            self.show_on_toolbar = True
            
            icon_path = os.path.join(repo_root, "stockcheck", "ui", "icon.png")
            if os.path.exists(icon_path):
                self.icon_file_name = icon_path
            self.dark_icon_file_name = icon_path

        def Run(self):
            """Triggered when the user clicks the toolbar icon or presses the assigned KiCad keybind."""
            board = pcbnew.GetBoard()
            if not board:
                wx.MessageBox("No active KiCad board found.", "StockCheck", wx.OK | wx.ICON_WARNING)
                return

            # Extract board items directly from memory
            items = KiCadParser.parse_from_pcbnew(board)
            board_name = os.path.basename(board.GetFileName()) if board.GetFileName() else "Active KiCad Board"

            # Create or bring up main frame
            frame = StockCheckFrame(None, title=f"KiCad-Ledger — {board_name}", board_items=items, board_name=board_name)
            frame.Show()
            frame.Raise()

    # Register the plugin inside KiCad
    StockCheckActionPlugin().register()

except ImportError:
    # Running outside KiCad environment
    pass
