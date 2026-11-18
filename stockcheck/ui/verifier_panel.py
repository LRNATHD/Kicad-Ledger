"""KiCad Board Verification Panel."""

import os
import csv
from typing import List, Optional, Dict, Any
import wx
import wx.dataview as dv

from stockcheck.models import BoardItem, Component
from stockcheck.db import Database
from stockcheck.kicad_parser import KiCadParser, find_open_kicad_board
from stockcheck.normalizer import (
    clean_mpn, parse_resistor_value, parse_capacitor_value, parse_inductor_value
)
from stockcheck.verifier import BoardVerifier, GroupedBoardMatch
from stockcheck.ui.theme import (
    COLOR_SUCCESS, COLOR_WARNING, COLOR_DANGER, COLOR_INFO, COLOR_DNP,
    get_status_color, get_row_bg
)


class VerifierPanel(wx.Panel):
    """Interactive board verification panel."""

    def __init__(self, parent, db: Database, board_items: Optional[List[BoardItem]] = None,
                 board_name: str = "", on_data_updated=None):
        super().__init__(parent)
        self.db = db
        self.board_items = board_items or []
        self.board_name = board_name
        self.on_data_updated = on_data_updated
        self.current_results: List[GroupedBoardMatch] = []
        self.visible_results: List[GroupedBoardMatch] = []
        self.current_filter = "ALL"

        self._init_ui()

        if self.board_items:
            self.run_verification()

    def _init_ui(self):
        main_sizer = wx.BoxSizer(wx.VERTICAL)

        # Top Control Bar (File selection and actions)
        file_box = wx.StaticBox(self, label="KiCad Board / Schematic Source")
        file_sizer = wx.StaticBoxSizer(file_box, wx.HORIZONTAL)

        self.lbl_file = wx.StaticText(self, label=self.board_name or "No KiCad board loaded.")
        font = self.lbl_file.GetFont()
        font.SetWeight(wx.FONTWEIGHT_BOLD)
        self.lbl_file.SetFont(font)
        file_sizer.Add(self.lbl_file, 1, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 5)

        btn_browse = wx.Button(self, label="📁 Open .kicad_pcb / .kicad_sch")
        btn_browse.Bind(wx.EVT_BUTTON, self.on_browse_file)
        file_sizer.Add(btn_browse, 0, wx.ALL, 5)

        btn_detect = wx.Button(self, label="🔍 Detect Open Board")
        btn_detect.Bind(wx.EVT_BUTTON, self.on_detect_open)
        file_sizer.Add(btn_detect, 0, wx.ALL, 5)

        btn_sample = wx.Button(self, label="⚡ Load Sample Board")
        btn_sample.Bind(wx.EVT_BUTTON, self.on_load_sample)
        file_sizer.Add(btn_sample, 0, wx.ALL, 5)

        btn_refresh = wx.Button(self, label="🔄 Re-Verify Stock")
        btn_refresh.Bind(wx.EVT_BUTTON, lambda evt: self.run_verification())
        file_sizer.Add(btn_refresh, 0, wx.ALL, 5)

        main_sizer.Add(file_sizer, 0, wx.EXPAND | wx.ALL, 8)

        # Summary Statistics Bar
        self.stat_box = wx.BoxSizer(wx.HORIZONTAL)
        self.lbl_stat_total = wx.StaticText(self, label="Total Parts: 0")
        self.lbl_stat_rate = wx.StaticText(self, label="Fulfillment: 0%")
        self.lbl_stat_instock = wx.StaticText(self, label="✓ In Stock: 0")
        self.lbl_stat_low = wx.StaticText(self, label="⚠ Low Stock: 0")
        self.lbl_stat_missing = wx.StaticText(self, label="❌ Missing: 0")
        self.lbl_stat_compat = wx.StaticText(self, label="⚡ Compatible: 0")

        self.lbl_stat_instock.SetForegroundColour(COLOR_SUCCESS)
        self.lbl_stat_low.SetForegroundColour(COLOR_WARNING)
        self.lbl_stat_missing.SetForegroundColour(COLOR_DANGER)
        self.lbl_stat_compat.SetForegroundColour(COLOR_INFO)

        for w in [self.lbl_stat_total, self.lbl_stat_rate, self.lbl_stat_instock,
                  self.lbl_stat_low, self.lbl_stat_missing, self.lbl_stat_compat]:
            f = w.GetFont()
            f.SetWeight(wx.FONTWEIGHT_BOLD)
            w.SetFont(f)
            self.stat_box.Add(w, 0, wx.RIGHT | wx.ALIGN_CENTER_VERTICAL, 15)

        main_sizer.Add(self.stat_box, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        # Filter Tabs / Radio
        filter_sizer = wx.BoxSizer(wx.HORIZONTAL)
        filter_sizer.Add(wx.StaticText(self, label="Filter: "), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)

        self.filter_choices = ["All Components", "Missing Only (Action Needed)", "Low Stock", "In Stock"]
        self.choice_filter = wx.Choice(self, choices=self.filter_choices)
        self.choice_filter.SetSelection(0)
        self.choice_filter.Bind(wx.EVT_CHOICE, self.on_filter_changed)
        filter_sizer.Add(self.choice_filter, 0, wx.ALIGN_CENTER_VERTICAL)

        filter_sizer.AddStretchSpacer()

        btn_own = wx.Button(self, label="✓ I Own This")
        btn_own.Bind(wx.EVT_BUTTON, self.on_mark_owned)
        filter_sizer.Add(btn_own, 0, wx.RIGHT, 5)

        btn_copy_missing = wx.Button(self, label="📋 Copy Missing to Clipboard")
        btn_copy_missing.Bind(wx.EVT_BUTTON, self.on_copy_missing)
        filter_sizer.Add(btn_copy_missing, 0, wx.RIGHT, 5)

        btn_export_missing = wx.Button(self, label="💾 Export Missing CSV")
        btn_export_missing.Bind(wx.EVT_BUTTON, self.on_export_missing)
        filter_sizer.Add(btn_export_missing, 0)

        main_sizer.Add(filter_sizer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        # Verification Results Table
        self.list_ctrl = dv.DataViewListCtrl(self, style=wx.BORDER_THEME | dv.DV_ROW_LINES | dv.DV_MULTIPLE)
        self.list_ctrl.AppendTextColumn("Status", width=110)
        self.list_ctrl.AppendTextColumn("Needed", width=60, align=wx.ALIGN_RIGHT)
        self.list_ctrl.AppendTextColumn("Available", width=70, align=wx.ALIGN_RIGHT)
        self.list_ctrl.AppendTextColumn("Category", width=85)
        self.list_ctrl.AppendTextColumn("Value", width=95)
        self.list_ctrl.AppendTextColumn("Package", width=80)
        self.list_ctrl.AppendTextColumn("References", width=150)
        self.list_ctrl.AppendTextColumn("Match Note & Location", width=340)

        main_sizer.Add(self.list_ctrl, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)
        self.SetSizer(main_sizer)

    def set_board_items(self, items: List[BoardItem], name: str = ""):
        self.board_items = items
        self.board_name = name
        self.lbl_file.SetLabel(f"Active Board: {name} ({len(items)} components)")
        self.run_verification()

    def run_verification(self):
        if not self.board_items:
            self.list_ctrl.DeleteAllItems()
            return

        verifier = BoardVerifier(self.db)
        report = verifier.verify_board(self.board_items)
        self.current_results = report["groups"]

        # Update stats
        self.lbl_stat_total.SetLabel(f"Total Parts: {report['total_components']}")
        self.lbl_stat_rate.SetLabel(f"Fulfillment: {report['fulfillment_rate']}%")
        self.lbl_stat_instock.SetLabel(f"✓ In Stock: {report['in_stock_groups']}")
        self.lbl_stat_low.SetLabel(f"⚠ Low Stock: {report['low_stock_groups']}")
        self.lbl_stat_missing.SetLabel(f"❌ Missing: {report['missing_groups']}")
        self.lbl_stat_compat.SetLabel(f"⚡ Compatible: {report['compatible_groups']}")

        self.apply_filter()

    def apply_filter(self):
        self.list_ctrl.DeleteAllItems()
        self.visible_results = []
        sel = self.choice_filter.GetSelection()

        status_symbols = {
            "IN_STOCK": "✓ In Stock",
            "LOW_STOCK": "⚠ Low Stock",
            "COMPATIBLE": "⚡ Compatible",
            "MISSING": "❌ Missing",
            "DNP": "⚪ DNP"
        }

        for grp in self.current_results:
            if sel == 1 and grp.status != "MISSING":
                continue
            elif sel == 2 and grp.status != "LOW_STOCK":
                continue
            elif sel == 3 and grp.status != "IN_STOCK":
                continue

            self.visible_results.append(grp)

            ref_str = ", ".join(grp.references[:8])
            if len(grp.references) > 8:
                ref_str += f" (+{len(grp.references) - 8} more)"

            status_text = status_symbols.get(grp.status, grp.status)
            avail_str = str(grp.available_qty) if grp.status != "DNP" else "-"
            
            note = grp.match_note
            if grp.matched_component and grp.matched_component.bin_location:
                note += f" [Bin: {grp.matched_component.bin_location}]"

            row_data = [
                status_text,
                str(grp.needed_qty),
                avail_str,
                grp.category.capitalize(),
                grp.value,
                grp.package,
                ref_str,
                note
            ]
            self.list_ctrl.AppendItem(row_data)

    def on_filter_changed(self, event):
        self.apply_filter()

    def on_detect_open(self, event):
        open_path = find_open_kicad_board()
        if open_path and os.path.exists(open_path):
            try:
                items = KiCadParser.parse_file(open_path)
                self.set_board_items(items, os.path.basename(open_path))
            except Exception as e:
                wx.MessageBox(f"Failed to parse open board: {e}", "Parse Error", wx.OK | wx.ICON_ERROR)
        else:
            wx.MessageBox(
                "No open KiCad board or schematic was detected.\n"
                "Make sure a project is open in KiCad, or use 'Open .kicad_pcb / .kicad_sch' to select it manually.",
                "No Open Board Found",
                wx.OK | wx.ICON_INFORMATION,
            )

    def on_mark_owned(self, event):
        selections = self.list_ctrl.GetSelections()
        if not selections:
            wx.MessageBox("Select one or more rows first, then click '✓ I Own This'.",
                          "No Row Selected", wx.OK | wx.ICON_INFORMATION)
            return

        saved = 0
        for item in selections:
            row_idx = self.list_ctrl.ItemToRow(item)
            if row_idx == wx.NOT_FOUND or row_idx >= len(self.visible_results):
                continue
            grp = self.visible_results[row_idx]
            if grp.status == "DNP":
                continue

            if grp.matched_component and grp.status == "LOW_STOCK":
                grp.matched_component.quantity = max(grp.matched_component.quantity, grp.needed_qty)
                self.db.update_component(grp.matched_component)
            else:
                norm_val = None
                if grp.category == "resistor":
                    norm_val, _ = parse_resistor_value(grp.value)
                elif grp.category == "capacitor":
                    norm_val, _ = parse_capacitor_value(grp.value)
                elif grp.category == "inductor":
                    norm_val, _ = parse_inductor_value(grp.value)

                val_clean = grp.value.strip() if grp.value else ""
                if val_clean in ("", "~", "-"):
                    mpn_val = grp.mpn or grp.package or grp.footprint
                    val_store = grp.package or grp.footprint or val_clean
                else:
                    mpn_val = grp.mpn or val_clean
                    val_store = val_clean

                comp = Component(
                    category=grp.category,
                    mpn=mpn_val,
                    clean_mpn=clean_mpn(mpn_val),
                    value=val_store,
                    norm_value=norm_val,
                    package=grp.package,
                    package_raw=grp.footprint,
                    quantity=max(grp.needed_qty, 1),
                    distributor="Manual",
                    distributor_sku=grp.lcsc,
                    notes="Marked as owned",
                )
                self.db.add_component(comp)
            saved += 1

        if saved:
            if self.on_data_updated:
                self.on_data_updated()
            else:
                self.run_verification()

    def on_browse_file(self, event):
        wildcard = "KiCad Files (*.kicad_pcb;*.kicad_sch;*.csv)|*.kicad_pcb;*.kicad_sch;*.csv"
        dlg = wx.FileDialog(self, "Open KiCad Board or Schematic", wildcard=wildcard, style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST)
        if dlg.ShowModal() == wx.ID_OK:
            path = dlg.GetPath()
            try:
                items = KiCadParser.parse_file(path)
                self.set_board_items(items, os.path.basename(path))
            except Exception as e:
                wx.MessageBox(f"Failed to parse file: {e}", "Parse Error", wx.OK | wx.ICON_ERROR)
        dlg.Destroy()

    def on_load_sample(self, event):
        sample_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            "examples", "sample_board", "demo_board.kicad_pcb"
        )
        if os.path.exists(sample_path):
            items = KiCadParser.parse_file(sample_path)
            self.set_board_items(items, "Demo Sample Board")
        else:
            wx.MessageBox("Sample board file not found.", "Info", wx.OK | wx.ICON_INFORMATION)

    def on_copy_missing(self, event):
        missing = [g for g in self.current_results if g.status in ("MISSING", "LOW_STOCK")]
        if not missing:
            wx.MessageBox("No missing or low stock parts! Everything is in stock.", "Great News", wx.OK | wx.ICON_INFORMATION)
            return

        lines = ["KiCad-Ledger Missing Parts:"]
        for g in missing:
            shortage = g.needed_qty - g.available_qty
            lines.append(f"- Need {shortage}x {g.value} (Package: {g.package}, Category: {g.category}) for {', '.join(g.references)}")

        text = "\n".join(lines)
        if wx.TheClipboard.Open():
            wx.TheClipboard.SetData(wx.TextDataObject(text))
            wx.TheClipboard.Close()
            wx.MessageBox(f"Copied {len(missing)} missing part groups to clipboard!", "Copied", wx.OK | wx.ICON_INFORMATION)

    def on_export_missing(self, event):
        missing = [g for g in self.current_results if g.status in ("MISSING", "LOW_STOCK")]
        if not missing:
            wx.MessageBox("No missing or low stock components to export.", "Info", wx.OK | wx.ICON_INFORMATION)
            return

        dlg = wx.FileDialog(self, "Export Missing Parts CSV", wildcard="CSV files (*.csv)|*.csv",
                            style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT)
        if dlg.ShowModal() == wx.ID_OK:
            path = dlg.GetPath()
            with open(path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["Value", "Package", "Category", "Needed Qty", "In Stock Qty", "Shortage", "References", "Status", "Note"])
                for g in missing:
                    short = max(0, g.needed_qty - g.available_qty)
                    writer.writerow([
                        g.value, g.package, g.category, g.needed_qty,
                        g.available_qty, short, ", ".join(g.references), g.status, g.match_note
                    ])
            wx.MessageBox(f"Exported {len(missing)} missing items to:\n{path}", "Export Complete", wx.OK | wx.ICON_INFORMATION)
        dlg.Destroy()
