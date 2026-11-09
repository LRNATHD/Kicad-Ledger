"""Main application window for KiCad-StockCheck."""

import os
import sys
import shutil
import wx

from stockcheck.db import Database, DEFAULT_DB_PATH
from stockcheck.models import BoardItem
from stockcheck.ui.verifier_panel import VerifierPanel
from stockcheck.ui.search_panel import SearchPanel
from stockcheck.ui.import_panel import ImportPanel


class StockCheckFrame(wx.Frame):
    """Main application frame holding the notebook tabs."""

    def __init__(self, parent=None, title="KiCad-StockCheck — Component Verifier & Inventory",
                 board_items=None, board_name=""):
        super().__init__(parent, title=title, size=(1080, 720))
        self.db = Database()
        self.board_items = board_items
        self.board_name = board_name

        self._init_ui()
        self.Centre()

    def _init_ui(self):
        panel = wx.Panel(self)
        sizer = wx.BoxSizer(wx.VERTICAL)

        # Tabbed Notebook
        self.notebook = wx.Notebook(panel)

        # 1. Board Verifier Tab
        self.tab_verifier = VerifierPanel(self.notebook, self.db, self.board_items, self.board_name)
        self.notebook.AddPage(self.tab_verifier, "🔍 Board Verifier")

        # 2. Inventory Search Tab
        self.tab_search = SearchPanel(self.notebook, self.db)
        self.notebook.AddPage(self.tab_search, "📦 Inventory Search")

        # 3. Order Import Tab
        self.tab_import = ImportPanel(self.notebook, self.db, on_import_success=self.on_data_updated)
        self.notebook.AddPage(self.tab_import, "📥 Import Orders (Mouser/LCSC/DigiKey)")

        # 4. Privacy & Settings Tab
        self.tab_settings = self._create_settings_tab(self.notebook)
        self.notebook.AddPage(self.tab_settings, "🔒 Privacy & Settings")

        sizer.Add(self.notebook, 1, wx.EXPAND | wx.ALL, 5)

        # Status Bar
        self.CreateStatusBar(2)
        self.SetStatusWidths([-1, 260])
        self.SetStatusText("Ready. 100% on-device inventory.", 0)
        self.SetStatusText("🔒 Local Privacy: Git Excluded", 1)

        panel.SetSizer(sizer)

    def on_data_updated(self):
        """Called when a new order is imported or inventory modified."""
        self.tab_search.refresh_search()
        self.tab_verifier.run_verification()

    def _create_settings_tab(self, notebook) -> wx.Panel:
        panel = wx.Panel(notebook)
        sizer = wx.BoxSizer(wx.VERTICAL)

        # Privacy Box
        box_priv = wx.StaticBox(panel, label="On-Device Privacy & Git Protection")
        priv_sizer = wx.StaticBoxSizer(box_priv, wx.VERTICAL)

        badge_txt = wx.StaticText(panel, label="🛡️ 100% LOCAL & PRIVATE — ZERO CLOUD TELEMETRY")
        f = badge_txt.GetFont()
        f.SetWeight(wx.FONTWEIGHT_BOLD)
        f.SetPointSize(11)
        badge_txt.SetFont(f)
        badge_txt.SetForegroundColour(wx.Colour(40, 167, 69))
        priv_sizer.Add(badge_txt, 0, wx.ALL, 6)

        desc = (
            "All your parts, receipts, and order histories are stored strictly in your local SQLite database.\n"
            "This repository's .gitignore is configured to strictly exclude all databases (*.db, *.sqlite),\n"
            "user invoices, order CSVs, and settings from git commits."
        )
        priv_sizer.Add(wx.StaticText(panel, label=desc), 0, wx.ALL, 6)

        lbl_path = wx.StaticText(panel, label=f"Local Database File:\n{self.db.db_path}")
        lbl_path.SetForegroundColour(wx.Colour(100, 100, 100))
        priv_sizer.Add(lbl_path, 0, wx.ALL, 6)

        sizer.Add(priv_sizer, 0, wx.EXPAND | wx.ALL, 10)

        # Integration Box
        box_int = wx.StaticBox(panel, label="KiCad Integration & Hotkeys")
        int_sizer = wx.StaticBoxSizer(box_int, wx.VERTICAL)

        int_desc = (
            "KiCad Action Plugin:\n"
            "Allows launching StockCheck directly inside KiCad PCB Editor toolbar or with a KiCad hotkey.\n"
            "Global KiCad Hotkey Daemon:\n"
            "Monitors Ctrl+Shift+I (or F8). It checks whether KiCad is the foreground window and only opens\n"
            "when you are in KiCad. When working in any other app (Chrome, VS Code, etc.), it ignores the key."
        )
        int_sizer.Add(wx.StaticText(panel, label=int_desc), 0, wx.ALL, 6)

        btn_install = wx.Button(panel, label="⚡ Install KiCad PCB Action Plugin")
        btn_install.Bind(wx.EVT_BUTTON, self.on_install_plugin)
        int_sizer.Add(btn_install, 0, wx.ALL, 6)

        sizer.Add(int_sizer, 0, wx.EXPAND | wx.ALL, 10)

        # Data Management Box
        box_data = wx.StaticBox(panel, label="Database Management")
        data_sizer = wx.StaticBoxSizer(box_data, wx.VERTICAL)

        btn_wipe = wx.Button(panel, label="⚠️ Clear All Local Inventory Data")
        btn_wipe.Bind(wx.EVT_BUTTON, self.on_wipe_data)
        data_sizer.Add(btn_wipe, 0, wx.ALL, 6)

        sizer.Add(data_sizer, 0, wx.EXPAND | wx.ALL, 10)

        panel.SetSizer(sizer)
        return panel

    def on_install_plugin(self, event):
        """Installs KiCad Action Plugin into user's KiCad plugin directory."""
        from install_kicad_plugin import install_plugin
        success, message = install_plugin()
        if success:
            wx.MessageBox(message, "KiCad Plugin Installed", wx.OK | wx.ICON_INFORMATION)
        else:
            wx.MessageBox(f"Plugin installation error:\n{message}", "Error", wx.OK | wx.ICON_ERROR)

    def on_wipe_data(self, event):
        if wx.MessageBox("Are you sure you want to delete ALL inventory items and imported orders?",
                         "Confirm Reset", wx.YES_NO | wx.ICON_WARNING) == wx.YES:
            self.db.clear_all_data()
            self.on_data_updated()
            wx.MessageBox("Local inventory database has been reset.", "Cleared", wx.OK | wx.ICON_INFORMATION)
