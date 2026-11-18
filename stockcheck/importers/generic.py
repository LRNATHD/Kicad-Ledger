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
        total_cost = 0.0
        distributors = set()
        order_ids = set()

        def normalize_category(cat_raw: str, desc_text: str, val_text: str) -> str:
            c = cat_raw.strip().lower()
            if c in ("resistors", "resistor"):
                return "resistor"
            if c in ("capacitors", "capacitor"):
                return "capacitor"
            if c.startswith("inductor"):
                return "inductor"
            if "integrated circuit" in c or c == "ic":
                return "ic"
            if c.startswith("connector"):
                return "connector"
            if c.startswith("crystal"):
                return "crystal"
            if c in ("switches", "switch"):
                return "switch"
            if c == "optoelectronics" and "led" in desc_text.lower():
                return "led"
            inferred = infer_category(desc=desc_text, value=val_text)
            if inferred != "other":
                return inferred
            return c or "other"

        for row in rows:
            mpn = get_val(row, "MPN", "Manufacturer Part #", "Manufacturer Part Number", "MFR Part Number", "Mfr Part #", "Mfr. Part #", "MFR.Part #", "Part Number", "Part #", "Item")
            val_in = get_val(row, "Value", "Val", "Resistance", "Capacitance")
            pkg_raw = get_val(row, "Package", "Footprint", "Case", "Size")
            qty_str = get_val(row, "Quantity", "Qty", "Count", "Stock")
            desc = get_val(row, "Description", "Desc", "Name", "Title")
            cat_in = get_val(row, "Category", "Type")
            bin_loc = get_val(row, "Bin", "Location", "Drawer", "Box")
            dist = get_val(row, "Distributor", "Vendor", "Supplier", "Source") or "Custom"
            sku = get_val(row, "SKU", "Distributor Part #", "Distributor Part Number", "Part No", "Order Code")
            row_order_id = get_val(row, "Order ID", "Order Number", "Order #") or os.path.basename(file_path)
            order_date = get_val(row, "Order Date", "Date")
            price_str = get_val(row, "Unit Price (USD)", "Unit Price($)", "Unit Price", "Price (USD)", "Price")

            if not mpn and not val_in and not desc:
                continue

            try:
                qty = int(float(re.sub(r"[^\d.]", "", qty_str))) if qty_str else 0
            except ValueError:
                qty = 0

            try:
                unit_price = float(re.sub(r"[^\d.]", "", price_str)) if price_str else 0.0
            except ValueError:
                unit_price = 0.0

            total_cost += unit_price * qty
            distributors.add(dist)
            if row_order_id:
                order_ids.add(row_order_id)

            category = normalize_category(cat_in, desc, val_in)

            norm_val = None
            val_display = val_in

            if category == "resistor":
                if val_in:
                    norm_val, formatted = parse_resistor_value(val_in)
                    if formatted:
                        val_display = formatted
                else:
                    m = re.search(r"\b(\d+(?:\.\d+)?\s*(?:[rRkKmMgG]?Ω|[rRkKmMgG]?\s*(?:OHM|Ohm|ohm|Ohms|Kohms|Mohms)|[rRkKmM]))\b", desc)
                    if m:
                        norm_val, val_display = parse_resistor_value(m.group(1))
            elif category == "capacitor":
                if val_in:
                    norm_val, formatted = parse_capacitor_value(val_in)
                    if formatted:
                        val_display = formatted
                else:
                    m = re.search(r"\b(\d+(?:\.\d+)?\s*[pPnNuUµm]F)\b", desc)
                    if m:
                        norm_val, val_display = parse_capacitor_value(m.group(1))
            elif category == "inductor":
                if val_in:
                    norm_val, formatted = parse_inductor_value(val_in)
                    if formatted:
                        val_display = formatted
                else:
                    m = re.search(r"\b(\d+(?:\.\d+)?\s*[nNuUµm]H)\b", desc)
                    if m:
                        norm_val, val_display = parse_inductor_value(m.group(1))

            if not val_display:
                val_display = mpn

            package = normalize_package(pkg_raw) or normalize_package(desc, strict=True)
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
                unit_price=unit_price,
                order_id=row_order_id,
                order_date=order_date,
            )
            components.append(comp)

        dist_label = ", ".join(sorted(distributors)) if distributors else "Custom"
        oid_label = next(iter(order_ids)) if len(order_ids) == 1 else os.path.basename(file_path)

        metadata = {
            "distributor": dist_label,
            "order_id": oid_label,
            "total_items": len(components),
            "total_cost": round(total_cost, 2),
            "file_path": file_path
        }
        return metadata, components
