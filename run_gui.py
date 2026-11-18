"""Standalone launcher for KiCad-StockCheck GUI."""

import sys
import os

# Ensure repo root is on sys.path
repo_root = os.path.dirname(os.path.abspath(__file__))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

import wx
from stockcheck.ui.main_frame import StockCheckFrame
from stockcheck.kicad_parser import KiCadParser, find_open_kicad_board


def main():
    app = wx.App(False)
    board_items = None
    board_name = ""

    open_path = find_open_kicad_board()
    if open_path and os.path.exists(open_path):
        try:
            board_items = KiCadParser.parse_file(open_path)
            board_name = os.path.basename(open_path)
        except Exception:
            board_items = None
            board_name = ""

    frame = StockCheckFrame(board_items=board_items, board_name=board_name)
    frame.Show()
    app.MainLoop()


if __name__ == "__main__":
    main()
