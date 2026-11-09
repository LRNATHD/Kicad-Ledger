"""Inventory Search and Management Panel."""

from typing import List, Optional
import wx
import wx.dataview as dv

from stockcheck.models import Component
from stockcheck.db import Database
from stockcheck.ui.dialogs import EditComponentDialog, AddComponentDialog


class SearchPanel(wx.Panel):
    """Fast component search and inventory management panel."""

    def __init__(self, parent, db: Database):
        super().__init__(parent)
        self.db = db
        self.results: List[Component] = []

        self._init_ui()
        self.refresh_search()

    def _init_ui(self):
        main_sizer = wx.BoxSizer(wx.VERTICAL)

        # Search Bar Box
        search_box = wx.BoxSizer(wx.HORIZONTAL)
        
        lbl_search = wx.StaticText(self, label="🔍 Search:")
        search_box.Add(lbl_search, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)

        self.txt_search = wx.TextCtrl(self, style=wx.TE_PROCESS_ENTER)
        self.txt_search.SetHint("Type value, MPN, footprint, bin, or distributor (e.g. 10k, 0805, 100nF, STM32, C2040)...")
        self.txt_search.Bind(wx.EVT_TEXT, lambda evt: self.refresh_search())
        self.txt_search.Bind(wx.EVT_TEXT_ENTER, lambda evt: self.refresh_search())
        search_box.Add(self.txt_search, 1, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)

        # Category Filter
        search_box.Add(wx.StaticText(self, label="Category:"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 4)
        self.categories = ["All", "Resistor", "Capacitor", "Inductor", "IC", "Diode", "LED", "Transistor", "Connector", "Crystal", "Other"]
        self.choice_category = wx.Choice(self, choices=self.categories)
        self.choice_category.SetSelection(0)
        self.choice_category.Bind(wx.EVT_CHOICE, lambda evt: self.refresh_search())
        search_box.Add(self.choice_category, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)

        # Package Filter
        search_box.Add(wx.StaticText(self, label="Package:"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 4)
        self.packages = ["All", "0805", "0603", "0402", "1206", "SOT-23", "SOT-223", "SOIC-8", "SOIC-16", "QFN-32", "LQFP-48", "DIP-8"]
        self.choice_package = wx.Choice(self, choices=self.packages)
        self.choice_package.SetSelection(0)
        self.choice_package.Bind(wx.EVT_CHOICE, lambda evt: self.refresh_search())
        search_box.Add(self.choice_package, 0, wx.ALIGN_CENTER_VERTICAL)

        main_sizer.Add(search_box, 0, wx.EXPAND | wx.ALL, 8)

        # Inventory Table
        self.list_ctrl = dv.DataViewListCtrl(self, style=wx.BORDER_THEME | dv.DV_ROW_LINES)
        self.list_ctrl.AppendTextColumn("ID", width=45, align=wx.ALIGN_RIGHT)
        self.list_ctrl.AppendTextColumn("Category", width=85)
        self.list_ctrl.AppendTextColumn("Value", width=95)
        self.list_ctrl.AppendTextColumn("Package", width=75)
        self.list_ctrl.AppendTextColumn("Stock Qty", width=75, align=wx.ALIGN_RIGHT)
        self.list_ctrl.AppendTextColumn("Bin / Location", width=100)
        self.list_ctrl.AppendTextColumn("MPN / Part #", width=140)
        self.list_ctrl.AppendTextColumn("Distributor & SKU", width=130)
        self.list_ctrl.AppendTextColumn("Voltage / Tol / Specs", width=140)
        self.list_ctrl.AppendTextColumn("Description", width=260)

        self.list_ctrl.Bind(dv.EVT_DATAVIEW_ITEM_ACTIVATED, self.on_item_double_clicked)
        main_sizer.Add(self.list_ctrl, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        # Bottom Button Bar
        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)

        self.lbl_count = wx.StaticText(self, label="0 components in stock")
        btn_sizer.Add(self.lbl_count, 0, wx.ALIGN_CENTER_VERTICAL | wx.LEFT, 5)

        btn_sizer.AddStretchSpacer()

        btn_add = wx.Button(self, label="➕ Add Component")
        btn_add.Bind(wx.EVT_BUTTON, self.on_add_component)
        btn_sizer.Add(btn_add, 0, wx.RIGHT, 5)

        btn_edit = wx.Button(self, label="✏ Edit Stock / Bin")
        btn_edit.Bind(wx.EVT_BUTTON, self.on_edit_selected)
        btn_sizer.Add(btn_edit, 0, wx.RIGHT, 5)

        btn_deduct = wx.Button(self, label="➖ Deduct 1 Used")
        btn_deduct.Bind(wx.EVT_BUTTON, self.on_deduct_selected)
        btn_sizer.Add(btn_deduct, 0, wx.RIGHT, 5)

        btn_delete = wx.Button(self, label="🗑 Delete")
        btn_delete.Bind(wx.EVT_BUTTON, self.on_delete_selected)
        btn_sizer.Add(btn_delete, 0)

        main_sizer.Add(btn_sizer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)
        self.SetSizer(main_sizer)

    def refresh_search(self):
        query = self.txt_search.GetValue().strip()
        cat = self.choice_category.GetStringSelection()
        pkg = self.choice_package.GetStringSelection()

        cat_filter = None if cat == "All" else cat
        pkg_filter = None if pkg == "All" else pkg

        self.results = self.db.search_components(query=query, category=cat_filter, package=pkg_filter)
        self.list_ctrl.DeleteAllItems()

        for c in self.results:
            specs = []
            if c.voltage:
                specs.append(c.voltage)
            if c.tolerance:
                specs.append(c.tolerance)
            if c.dielectric:
                specs.append(c.dielectric)
            spec_str = " ".join(specs)

            sku_str = f"{c.distributor}: {c.distributor_sku}" if c.distributor_sku else c.distributor

            row = [
                str(c.id),
                c.category.capitalize(),
                c.value,
                c.package,
                str(c.quantity),
                c.bin_location or "-",
                c.mpn or "-",
                sku_str or "-",
                spec_str or "-",
                c.description
            ]
            self.list_ctrl.AppendItem(row)

        total_qty = sum(c.quantity for c in self.results)
        self.lbl_count.SetLabel(f"Showing {len(self.results)} unique parts ({total_qty} total units in stock)")

    def _get_selected_component(self) -> Optional[Component]:
        item = self.list_ctrl.GetSelection()
        if not item.IsOk():
            return None
        row = self.list_ctrl.ItemToRow(item)
        if 0 <= row < len(self.results):
            return self.results[row]
        return None

    def on_item_double_clicked(self, event):
        self.on_edit_selected(event)

    def on_edit_selected(self, event):
        comp = self._get_selected_component()
        if not comp:
            wx.MessageBox("Please select a component to edit.", "Notice", wx.OK | wx.ICON_INFORMATION)
            return

        dlg = EditComponentDialog(self, comp)
        if dlg.ShowModal() == wx.ID_OK:
            updated = dlg.get_component()
            self.db.update_component(updated)
            self.refresh_search()
        dlg.Destroy()

    def on_deduct_selected(self, event):
        comp = self._get_selected_component()
        if not comp:
            return
        if comp.quantity <= 0:
            wx.MessageBox("Stock quantity is already 0.", "Info", wx.OK | wx.ICON_INFORMATION)
            return
        self.db.adjust_quantity(comp.id, -1)
        self.refresh_search()

    def on_delete_selected(self, event):
        comp = self._get_selected_component()
        if not comp:
            return
        if wx.MessageBox(f"Delete '{comp.value}' ({comp.package}) from inventory?", "Confirm Delete",
                         wx.YES_NO | wx.ICON_QUESTION) == wx.YES:
            self.db.delete_component(comp.id)
            self.refresh_search()

    def on_add_component(self, event):
        dlg = AddComponentDialog(self)
        if dlg.ShowModal() == wx.ID_OK:
            new_comp = dlg.get_component()
            self.db.add_component(new_comp)
            self.refresh_search()
        dlg.Destroy()
