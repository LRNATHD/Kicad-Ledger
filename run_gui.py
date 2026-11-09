"""Standalone launcher for KiCad-StockCheck GUI."""

import sys
import os

# Ensure repo root is on sys.path
repo_root = os.path.dirname(os.path.abspath(__file__))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

import wx
from stockcheck.ui.main_frame import StockCheckFrame


def main():
    app = wx.App(False)
    frame = StockCheckFrame()
    frame.Show()
    app.MainLoop()


if __name__ == "__main__":
    main()
