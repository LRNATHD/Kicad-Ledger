"""Dialogs for manual component addition, editing, and batch actions."""

import wx
from stockcheck.models import Component
from stockcheck.normalizer import (
    normalize_package, parse_resistor_value, parse_capacitor_value,
    parse_inductor_value, extract_voltage, extract_tolerance,
    extract_dielectric, clean_mpn, infer_category
)


class EditComponentDialog(wx.Dialog):
    """Dialog to edit stock quantity, bin location, and details of an existing component."""

    def __init__(self, parent, comp: Component):
        super().__init__(parent, title=f"Edit Component — {comp.value} ({comp.package})", size=(450, 420))
        self.comp = comp
        self._init_ui()

    def _init_ui(self):
        panel = wx.Panel(self)
        sizer = wx.BoxSizer(wx.VERTICAL)
        grid = wx.FlexGridSizer(rows=7, cols=2, vgap=10, hgap=10)
        grid.AddGrowableCol(1)

        grid.Add(wx.StaticText(panel, label="Value:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.txt_val = wx.TextCtrl(panel, value=self.comp.value)
        grid.Add(self.txt_val, 1, wx.EXPAND)

        grid.Add(wx.StaticText(panel, label="Package:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.txt_pkg = wx.TextCtrl(panel, value=self.comp.package)
        grid.Add(self.txt_pkg, 1, wx.EXPAND)

        grid.Add(wx.StaticText(panel, label="In-Stock Quantity:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.spn_qty = wx.SpinCtrl(panel, min=0, max=999999, initial=self.comp.quantity)
        grid.Add(self.spn_qty, 1, wx.EXPAND)

        grid.Add(wx.StaticText(panel, label="Bin / Drawer / Book:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.txt_bin = wx.TextCtrl(panel, value=self.comp.bin_location)
        grid.Add(self.txt_bin, 1, wx.EXPAND)

        grid.Add(wx.StaticText(panel, label="MPN (Part #):"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.txt_mpn = wx.TextCtrl(panel, value=self.comp.mpn)
        grid.Add(self.txt_mpn, 1, wx.EXPAND)

        grid.Add(wx.StaticText(panel, label="Distributor SKU:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.txt_sku = wx.TextCtrl(panel, value=self.comp.distributor_sku)
        grid.Add(self.txt_sku, 1, wx.EXPAND)

        grid.Add(wx.StaticText(panel, label="Notes:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.txt_notes = wx.TextCtrl(panel, value=self.comp.notes)
        grid.Add(self.txt_notes, 1, wx.EXPAND)

        sizer.Add(grid, 1, wx.EXPAND | wx.ALL, 15)

        btn_sizer = wx.StdDialogButtonSizer()
        btn_ok = wx.Button(panel, wx.ID_OK, label="Save Changes")
        btn_cancel = wx.Button(panel, wx.ID_CANCEL)
        btn_sizer.AddButton(btn_ok)
        btn_sizer.AddButton(btn_cancel)
        btn_sizer.Realize()

        sizer.Add(btn_sizer, 0, wx.ALIGN_RIGHT | wx.ALL, 12)
        panel.SetSizer(sizer)

    def get_component(self) -> Component:
        self.comp.value = self.txt_val.GetValue().strip()
        self.comp.package = normalize_package(self.txt_pkg.GetValue().strip())
        self.comp.quantity = self.spn_qty.GetValue()
        self.comp.bin_location = self.txt_bin.GetValue().strip()
        self.comp.mpn = self.txt_mpn.GetValue().strip()
        self.comp.clean_mpn = clean_mpn(self.comp.mpn)
        self.comp.distributor_sku = self.txt_sku.GetValue().strip()
        self.comp.notes = self.txt_notes.GetValue().strip()

        # Recalculate norm_value if passive
        if self.comp.category == "resistor":
            self.comp.norm_value, _ = parse_resistor_value(self.comp.value)
        elif self.comp.category == "capacitor":
            self.comp.norm_value, _ = parse_capacitor_value(self.comp.value)
        elif self.comp.category == "inductor":
            self.comp.norm_value, _ = parse_inductor_value(self.comp.value)

        return self.comp


class AddComponentDialog(wx.Dialog):
    """Dialog to manually add a component to inventory."""

    def __init__(self, parent):
        super().__init__(parent, title="Add Component to Inventory", size=(450, 480))
        self._init_ui()

    def _init_ui(self):
        panel = wx.Panel(self)
        sizer = wx.BoxSizer(wx.VERTICAL)
        grid = wx.FlexGridSizer(rows=8, cols=2, vgap=10, hgap=10)
        grid.AddGrowableCol(1)

        grid.Add(wx.StaticText(panel, label="Category:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.choice_cat = wx.Choice(panel, choices=[
            "resistor", "capacitor", "inductor", "ic", "diode", "led", "transistor", "connector", "crystal", "other"
        ])
        self.choice_cat.SetSelection(0)
        grid.Add(self.choice_cat, 1, wx.EXPAND)

        grid.Add(wx.StaticText(panel, label="Value:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.txt_val = wx.TextCtrl(panel)
        self.txt_val.SetHint("e.g. 10k, 100nF, STM32F401, AMS1117-3.3")
        grid.Add(self.txt_val, 1, wx.EXPAND)

        grid.Add(wx.StaticText(panel, label="Package:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.txt_pkg = wx.TextCtrl(panel)
        self.txt_pkg.SetHint("e.g. 0805, 0603, SOT-23, SOIC-8, QFN-32")
        grid.Add(self.txt_pkg, 1, wx.EXPAND)

        grid.Add(wx.StaticText(panel, label="Quantity:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.spn_qty = wx.SpinCtrl(panel, min=1, max=999999, initial=50)
        grid.Add(self.spn_qty, 1, wx.EXPAND)

        grid.Add(wx.StaticText(panel, label="Bin / Drawer:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.txt_bin = wx.TextCtrl(panel)
        self.txt_bin.SetHint("e.g. Drawer A3, SMD Book 1")
        grid.Add(self.txt_bin, 1, wx.EXPAND)

        grid.Add(wx.StaticText(panel, label="MPN (Part #):"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.txt_mpn = wx.TextCtrl(panel)
        grid.Add(self.txt_mpn, 1, wx.EXPAND)

        grid.Add(wx.StaticText(panel, label="Distributor:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.choice_dist = wx.Choice(panel, choices=["Manual", "LCSC", "Mouser", "DigiKey", "Other"])
        self.choice_dist.SetSelection(0)
        grid.Add(self.choice_dist, 1, wx.EXPAND)

        grid.Add(wx.StaticText(panel, label="Distributor SKU:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.txt_sku = wx.TextCtrl(panel)
        grid.Add(self.txt_sku, 1, wx.EXPAND)

        sizer.Add(grid, 1, wx.EXPAND | wx.ALL, 15)

        btn_sizer = wx.StdDialogButtonSizer()
        btn_ok = wx.Button(panel, wx.ID_OK, label="Add to Inventory")
        btn_cancel = wx.Button(panel, wx.ID_CANCEL)
        btn_sizer.AddButton(btn_ok)
        btn_sizer.AddButton(btn_cancel)
        btn_sizer.Realize()

        sizer.Add(btn_sizer, 0, wx.ALIGN_RIGHT | wx.ALL, 12)
        panel.SetSizer(sizer)

    def get_component(self) -> Component:
        cat = self.choice_cat.GetStringSelection()
        val_str = self.txt_val.GetValue().strip()
        pkg_raw = self.txt_pkg.GetValue().strip()
        package = normalize_package(pkg_raw)
        mpn = self.txt_mpn.GetValue().strip()

        norm_val = None
        if cat == "resistor":
            norm_val, formatted = parse_resistor_value(val_str)
            if formatted:
                val_str = formatted
        elif cat == "capacitor":
            norm_val, formatted = parse_capacitor_value(val_str)
            if formatted:
                val_str = formatted
        elif cat == "inductor":
            norm_val, formatted = parse_inductor_value(val_str)
            if formatted:
                val_str = formatted

        return Component(
            category=cat,
            value=val_str or mpn,
            norm_value=norm_val,
            package=package,
            package_raw=pkg_raw,
            quantity=self.spn_qty.GetValue(),
            bin_location=self.txt_bin.GetValue().strip(),
            mpn=mpn,
            clean_mpn=clean_mpn(mpn),
            distributor=self.choice_dist.GetStringSelection(),
            distributor_sku=self.txt_sku.GetValue().strip()
        )
