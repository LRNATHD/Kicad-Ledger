"""Distributor Order Import Panel for Mouser, LCSC, DigiKey."""

import os
from typing import List, Dict, Any, Optional
import wx
import wx.dataview as dv

from stockcheck.models import Component
from stockcheck.db import Database
from stockcheck.importers import import_order_file
from stockcheck.ui.theme import COLOR_SUCCESS, COLOR_INFO


class ImportPanel(wx.Panel):
    """Panel to import Mouser, LCSC, and DigiKey orders into local inventory."""

    def __init__(self, parent, db: Database, on_import_success=None):
        super().__init__(parent)
        self.db = db
        self.on_import_success = on_import_success
        self.parsed_items: List[Component] = []
        self.order_meta: Dict[str, Any] = {}

        self._init_ui()

    def _init_ui(self):
        main_sizer = wx.BoxSizer(wx.VERTICAL)

        # File Selection & Sample Loaders
        top_box = wx.StaticBox(self, label="Select Distributor Order CSV")
        top_sizer = wx.StaticBoxSizer(top_box, wx.VERTICAL)

        row1 = wx.BoxSizer(wx.HORIZONTAL)
        self.lbl_file = wx.StaticText(self, label="No order file selected.")
        row1.Add(self.lbl_file, 1, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)

        btn_browse = wx.Button(self, label="📁 Browse Order CSV...")
        btn_browse.Bind(wx.EVT_BUTTON, self.on_browse)
        row1.Add(btn_browse, 0)
        top_sizer.Add(row1, 0, wx.EXPAND | wx.ALL, 6)

        # Quick sample test buttons
        sample_sizer = wx.BoxSizer(wx.HORIZONTAL)
        sample_sizer.Add(wx.StaticText(self, label="Quick Test Samples: "), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 8)

        btn_sample_lcsc = wx.Button(self, label="Load Sample LCSC Order")
        btn_sample_lcsc.Bind(wx.EVT_BUTTON, lambda evt: self.load_sample("lcsc_sample_order.csv"))
        sample_sizer.Add(btn_sample_lcsc, 0, wx.RIGHT, 6)

        btn_sample_mouser = wx.Button(self, label="Load Sample Mouser Order")
        btn_sample_mouser.Bind(wx.EVT_BUTTON, lambda evt: self.load_sample("mouser_sample_order.csv"))
        sample_sizer.Add(btn_sample_mouser, 0, wx.RIGHT, 6)

        btn_sample_digikey = wx.Button(self, label="Load Sample DigiKey Order")
        btn_sample_digikey.Bind(wx.EVT_BUTTON, lambda evt: self.load_sample("digikey_sample_order.csv"))
        sample_sizer.Add(btn_sample_digikey, 0)

        top_sizer.Add(sample_sizer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 6)
        main_sizer.Add(top_sizer, 0, wx.EXPAND | wx.ALL, 8)

        # Order Overview Badge / Info
        self.lbl_overview = wx.StaticText(self, label="Distributor: - | Order #: - | Total Items: 0 | Total Cost: $0.00")
        f = self.lbl_overview.GetFont()
        f.SetWeight(wx.FONTWEIGHT_BOLD)
        self.lbl_overview.SetFont(f)
        main_sizer.Add(self.lbl_overview, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        # Preview Table
        self.list_ctrl = dv.DataViewListCtrl(self, style=wx.BORDER_THEME | dv.DV_ROW_LINES)
        self.list_ctrl.AppendTextColumn("Distributor", width=85)
        self.list_ctrl.AppendTextColumn("Category", width=85)
        self.list_ctrl.AppendTextColumn("Value", width=95)
        self.list_ctrl.AppendTextColumn("Package", width=80)
        self.list_ctrl.AppendTextColumn("Order Qty", width=75, align=wx.ALIGN_RIGHT)
        self.list_ctrl.AppendTextColumn("Unit Price", width=75, align=wx.ALIGN_RIGHT)
        self.list_ctrl.AppendTextColumn("MPN", width=140)
        self.list_ctrl.AppendTextColumn("Distributor SKU", width=120)
        self.list_ctrl.AppendTextColumn("Description", width=300)

        main_sizer.Add(self.list_ctrl, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        # Bottom Import Button
        bottom_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.btn_import = wx.Button(self, label="✓ Confirm & Save to Local Inventory Database")
        self.btn_import.SetFont(f)
        self.btn_import.Disable()
        self.btn_import.Bind(wx.EVT_BUTTON, self.on_confirm_import)
        bottom_sizer.AddStretchSpacer()
        bottom_sizer.Add(self.btn_import, 0, wx.ALIGN_CENTER_VERTICAL)

        main_sizer.Add(bottom_sizer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)
        self.SetSizer(main_sizer)

    def on_browse(self, event):
        wildcard = "Order CSV files (*.csv;*.txt)|*.csv;*.txt|All files (*.*)|*.*"
        dlg = wx.FileDialog(self, "Open Mouser / LCSC / DigiKey Order Export", wildcard=wildcard,
                            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST)
        if dlg.ShowModal() == wx.ID_OK:
            self.load_order_file(dlg.GetPath())
        dlg.Destroy()

    def load_sample(self, filename: str):
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        path = os.path.join(base_dir, "examples", "sample_orders", filename)
        if os.path.exists(path):
            self.load_order_file(path)
        else:
            wx.MessageBox(f"Sample file not found: {path}", "Error", wx.OK | wx.ICON_ERROR)

    def load_order_file(self, file_path: str):
        try:
            meta, items = import_order_file(file_path)
            self.order_meta = meta
            self.parsed_items = items

            self.lbl_file.SetLabel(f"Loaded: {os.path.basename(file_path)}")
            dist = meta.get("distributor", "Unknown")
            oid = meta.get("order_id", "-")
            cost = meta.get("total_cost", 0.0)
            self.lbl_overview.SetLabel(f"Distributor: {dist} | Order #: {oid} | Items: {len(items)} | Total: ${cost:.2f}")

            self.list_ctrl.DeleteAllItems()
            for c in items:
                row = [
                    c.distributor,
                    c.category.capitalize(),
                    c.value,
                    c.package,
                    str(c.quantity),
                    f"${c.unit_price:.4f}" if c.unit_price else "-",
                    c.mpn or "-",
                    c.distributor_sku or "-",
                    c.description
                ]
                self.list_ctrl.AppendItem(row)

            self.btn_import.Enable(len(items) > 0)
        except Exception as e:
            wx.MessageBox(f"Error parsing order file: {e}", "Parse Error", wx.OK | wx.ICON_ERROR)

    def on_confirm_import(self, event):
        if not self.parsed_items:
            return

        inserted, updated = self.db.import_order(self.order_meta, self.parsed_items)
        msg = f"Import Successful!\n\n- New components added: {inserted}\n- Existing stock updated: {updated}\n\nStored safely in your on-device SQLite database."
        wx.MessageBox(msg, "Order Imported", wx.OK | wx.ICON_INFORMATION)

        if self.on_import_success:
            self.on_import_success()

        self.btn_import.Disable()
