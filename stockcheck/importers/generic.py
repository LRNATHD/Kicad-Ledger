"""Generic / Custom CSV importer for manual inventory lists."""

import os
import re
from typing import List, Dict, Any, Tuple
from stockcheck.models import Component
from stockcheck.importers.base import BaseOrderImporter
from stockcheck.normalizer import (
    normalize_package, parse_resistor_value, parse_capacitor_value,
    parse_inductor_value, extract_voltage, extract_tolerance,
    extract_dielectric, clean_mpn, infer_category
)


class GenericImporter(BaseOrderImporter):
    distributor_name = "Custom / Generic"

    def can_handle(self, headers: List[str]) -> bool:
        # Generic fallback always accepts if basic columns exist
        return True

    def parse_file(self, file_path: str) -> Tuple[Dict[str, Any], List[Component]]:
        headers, rows = self.read_csv_rows(file_path)

        def get_val(row: Dict[str, str], *keys: str) -> str:
            row_lower = {k.lower().strip(): v for k, v in row.items() if k}
            for k in keys:
                val = row_lower.get(k.lower().strip())
                if val is not None:
                    return str(val).strip()
            return ""

        components: List[Component] = []

        for row in rows:
            mpn = get_val(row, "MPN", "Part Number", "Part #", "MFR Part Number", "Item")
            val_in = get_val(row, "Value", "Val", "Resistance", "Capacitance")
            pkg_raw = get_val(row, "Package", "Footprint", "Case", "Size")
            qty_str = get_val(row, "Quantity", "Qty", "Count", "Stock")
            desc = get_val(row, "Description", "Desc", "Name", "Title")
            cat_in = get_val(row, "Category", "Type")
            bin_loc = get_val(row, "Bin", "Location", "Drawer", "Box")
            dist = get_val(row, "Distributor", "Supplier", "Source") or "Custom"
            sku = get_val(row, "SKU", "Part No", "Order Code")

            if not mpn and not val_in and not desc:
                continue

            try:
                qty = int(float(re.sub(r"[^\d.]", "", qty_str))) if qty_str else 0
            except ValueError:
                qty = 0

            category = cat_in.lower() if cat_in else infer_category(desc=desc, value=val_in)

            norm_val = None
            val_display = val_in

            target_val_str = val_in or desc
            if category == "resistor":
                norm_val, formatted = parse_resistor_value(target_val_str)
                if formatted:
                    val_display = formatted
            elif category == "capacitor":
                norm_val, formatted = parse_capacitor_value(target_val_str)
                if formatted:
                    val_display = formatted
            elif category == "inductor":
                norm_val, formatted = parse_inductor_value(target_val_str)
                if formatted:
                    val_display = formatted

            if not val_display:
                val_display = mpn

            package = normalize_package(pkg_raw) or normalize_package(desc)
            volt_str, volt_num = extract_voltage(desc or val_in)

            comp = Component(
                category=category,
                mpn=mpn,
                clean_mpn=clean_mpn(mpn),
                manufacturer=get_val(row, "Manufacturer", "MFR"),
                value=val_display,
                norm_value=norm_val,
                package=package,
                package_raw=pkg_raw,
                quantity=qty,
                bin_location=bin_loc,
                distributor=dist,
                distributor_sku=sku,
                voltage=volt_str,
                voltage_num=volt_num,
                tolerance=extract_tolerance(desc or val_in),
                dielectric=extract_dielectric(desc or val_in),
                description=desc,
                order_id=os.path.basename(file_path)
            )
            components.append(comp)

        metadata = {
            "distributor": "Custom",
            "order_id": os.path.basename(file_path),
            "total_items": len(components),
            "total_cost": 0.0,
            "file_path": file_path
        }
        return metadata, components
