"""Mouser order CSV importer."""

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


class MouserImporter(BaseOrderImporter):
    distributor_name = "Mouser"

    def can_handle(self, headers: List[str]) -> bool:
        lower_headers = [h.lower() for h in headers]
        return any("mouser part" in h or "mouser #" in h or "mouser part number" in h for h in lower_headers)

    def parse_file(self, file_path: str) -> Tuple[Dict[str, Any], List[Component]]:
        headers, rows = self.read_csv_rows(file_path)

        def get_val(row: Dict[str, str], *keys: str) -> str:
            row_lower = {k.lower().strip(): v for k, v in row.items() if k}
            for k in keys:
                val = row_lower.get(k.lower().strip())
                if val is not None:
                    return str(val).strip()
            return ""

        order_id = ""
        components: List[Component] = []
        total_cost = 0.0

        for row in rows:
            mouser_sku = get_val(row, "Mouser Part Number", "Mouser Part #", "Mouser #", "Part Number")
            if not mouser_sku:
                continue

            mpn = get_val(row, "Manufacturer Part Number", "Mfr Part #", "Mfr. Part #", "Mfr Part Number", "MPN")
            pkg_raw = get_val(row, "Package / Case", "Package/Case", "Package", "Footprint")
            desc = get_val(row, "Description", "Product Description", "Item Description")
            mfr = get_val(row, "Manufacturer", "Mfr.")
            row_order_id = get_val(row, "Sales Order Number", "Order Number", "Order #", "Invoice Number", "PO Number")
            if row_order_id and not order_id:
                order_id = row_order_id

            qty_str = get_val(row, "Order Qty.", "Order Qty", "Quantity", "Qty", "Shipped Qty")
            try:
                qty = int(float(re.sub(r"[^\d.]", "", qty_str))) if qty_str else 0
            except ValueError:
                qty = 0

            price_str = get_val(row, "Price (USD)", "Unit Price (USD)", "Price", "Unit Price")
            try:
                price = float(re.sub(r"[^\d.]", "", price_str)) if price_str else 0.0
            except ValueError:
                price = 0.0

            total_cost += price * qty
            category = infer_category(desc=desc)

            norm_val = None
            val_display = ""

            if category == "resistor":
                m = re.search(r"\b(\d+(?:\.\d+)?[rRkKmM]?\s*(?:Ω|Ohm|ohm|Ohms|Kohms|Mohms)?)\b", desc)
                if m:
                    norm_val, val_display = parse_resistor_value(m.group(1))
            elif category == "capacitor":
                m = re.search(r"\b(\d+(?:\.\d+)?[pPnNuUµ]F?)\b", desc)
                if m:
                    norm_val, val_display = parse_capacitor_value(m.group(1))
            elif category == "inductor":
                m = re.search(r"\b(\d+(?:\.\d+)?[nNuUµmM]H?)\b", desc)
                if m:
                    norm_val, val_display = parse_inductor_value(m.group(1))
            else:
                val_display = mpn or (desc.split()[0] if desc else "")

            if not val_display:
                val_display = mpn

            volt_str, volt_num = extract_voltage(desc)
            tol = extract_tolerance(desc)
            dielectric = extract_dielectric(desc)

            package = normalize_package(pkg_raw) or normalize_package(desc)

            comp = Component(
                category=category,
                mpn=mpn,
                clean_mpn=clean_mpn(mpn),
                manufacturer=mfr,
                value=val_display,
                norm_value=norm_val,
                package=package,
                package_raw=pkg_raw,
                quantity=qty,
                distributor="Mouser",
                distributor_sku=mouser_sku,
                voltage=volt_str,
                voltage_num=volt_num,
                tolerance=tol,
                dielectric=dielectric,
                description=desc,
                unit_price=price,
                order_id=order_id or os.path.basename(file_path),
            )
            components.append(comp)

        metadata = {
            "distributor": "Mouser",
            "order_id": order_id or os.path.basename(file_path),
            "total_items": len(components),
            "total_cost": round(total_cost, 2),
            "file_path": file_path
        }
        return metadata, components
