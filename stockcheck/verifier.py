"""Board Verification Engine: cross-references KiCad components against on-device stock."""

from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional, Any
from stockcheck.models import BoardItem, Component
from stockcheck.db import Database
from stockcheck.normalizer import (
    clean_mpn, packages_match, values_match, normalize_package
)


@dataclass
class GroupedBoardMatch:
    """Represents a grouped set of identical components on a board and their stock status."""
    key: str                                    # e.g. "resistor:10k:0805" or "ic:STM32F401CEU6:QFN-48"
    category: str
    value: str
    package: str
    footprint: str
    references: List[str] = field(default_factory=list)
    needed_qty: int = 0
    available_qty: int = 0
    status: str = "MISSING"                     # IN_STOCK, COMPATIBLE, LOW_STOCK, MISSING, DNP
    matched_component: Optional[Component] = None
    alternatives: List[Component] = field(default_factory=list)
    match_note: str = ""
    mpn: str = ""
    lcsc: str = ""


class BoardVerifier:
    """Cross-references board items against the inventory database."""

    def __init__(self, db: Database):
        self.db = db

    def verify_board(self, items: List[BoardItem]) -> Dict[str, Any]:
        """
        Verify all board items against stock.
        Groups identical components together and calculates stock availability.
        """
        # Group items
        groups: Dict[str, GroupedBoardMatch] = {}

        for item in items:
            if item.dnp:
                key = f"DNP:{item.reference}"
            elif item.category in ("resistor", "capacitor", "inductor"):
                norm_str = f"{item.norm_value}" if item.norm_value is not None else item.value
                key = f"{item.category}:{norm_str}:{item.package}"
            elif item.lcsc:
                key = f"lcsc:{item.lcsc}"
            elif item.mpn:
                key = f"mpn:{clean_mpn(item.mpn)}:{item.package}"
            else:
                key = f"{item.category}:{item.value}:{item.package}"

            if key not in groups:
                groups[key] = GroupedBoardMatch(
                    key=key,
                    category=item.category,
                    value=item.value,
                    package=item.package,
                    footprint=item.footprint,
                    mpn=item.mpn,
                    lcsc=item.lcsc,
                )

            groups[key].references.append(item.reference)
            groups[key].needed_qty += 1

        # Match each group against inventory
        matched_results: List[GroupedBoardMatch] = []
        
        # Track reserved quantities during board check so overlapping parts aren't double-counted
        consumed_stock: Dict[int, int] = {}

        for key, grp in groups.items():
            if key.startswith("DNP:"):
                grp.status = "DNP"
                grp.match_note = "Marked as Do Not Populate (DNP)"
                matched_results.append(grp)
                continue

            self._match_group(grp, consumed_stock)
            matched_results.append(grp)

        # Sort: Missing & Low Stock first, then Compatible, then In Stock, then DNP
        status_priority = {
            "MISSING": 0,
            "LOW_STOCK": 1,
            "COMPATIBLE": 2,
            "IN_STOCK": 3,
            "DNP": 4
        }
        matched_results.sort(key=lambda g: (status_priority.get(g.status, 5), g.category, g.value))

        # Calculate statistics
        total_board_parts = sum(g.needed_qty for g in matched_results if g.status != "DNP")
        in_stock_qty = sum(g.needed_qty for g in matched_results if g.status == "IN_STOCK")
        missing_count = sum(1 for g in matched_results if g.status == "MISSING")
        low_stock_count = sum(1 for g in matched_results if g.status == "LOW_STOCK")
        compatible_count = sum(1 for g in matched_results if g.status == "COMPATIBLE")
        in_stock_count = sum(1 for g in matched_results if g.status == "IN_STOCK")

        return {
            "groups": matched_results,
            "total_components": total_board_parts,
            "unique_groups": len([g for g in matched_results if g.status != "DNP"]),
            "in_stock_groups": in_stock_count,
            "compatible_groups": compatible_count,
            "low_stock_groups": low_stock_count,
            "missing_groups": missing_count,
            "fulfillment_rate": round((in_stock_qty / max(1, total_board_parts)) * 100, 1)
        }

    def _match_group(self, grp: GroupedBoardMatch, consumed_stock: Dict[int, int]):
        """Find matching inventory component for a group."""
        matched: Optional[Component] = None
        match_type = ""
        alternatives: List[Component] = []

        # 1. Check by explicit LCSC Part Number
        if grp.lcsc:
            sku_matches = self.db.find_by_sku(grp.lcsc)
            if sku_matches:
                matched = sku_matches[0]
                match_type = f"Exact LCSC SKU ({grp.lcsc})"

        # 2. Check by explicit MPN
        if not matched and grp.mpn:
            mpn_matches = self.db.find_by_mpn(grp.mpn)
            for cand in mpn_matches:
                if packages_match(cand.package, grp.package):
                    matched = cand
                    match_type = f"Exact MPN ({cand.mpn})"
                    break
            if not matched and mpn_matches:
                # Same MPN but different package variant
                alternatives.extend(mpn_matches)

        # 3. Check passives (Resistor, Capacitor, Inductor) by value + package
        if not matched and grp.category in ("resistor", "capacitor", "inductor"):
            # Compute numeric value if not already done
            from stockcheck.normalizer import (
                parse_resistor_value, parse_capacitor_value, parse_inductor_value
            )
            norm_val = None
            if grp.category == "resistor":
                norm_val, _ = parse_resistor_value(grp.value)
            elif grp.category == "capacitor":
                norm_val, _ = parse_capacitor_value(grp.value)
            elif grp.category == "inductor":
                norm_val, _ = parse_inductor_value(grp.value)

            if norm_val is not None:
                exact_passives = self.db.find_passives(grp.category, norm_val, grp.package)
                if exact_passives:
                    # Pick part with highest available quantity
                    matched = max(exact_passives, key=lambda c: c.quantity)
                    match_type = f"Value + Package ({grp.value} {grp.package})"
                else:
                    # Look for compatible alternatives (e.g. higher voltage rating cap)
                    compatibles = self.db.find_compatible_passives(grp.category, norm_val, grp.package)
                    if compatibles:
                        alternatives.extend(compatibles)

        # 4. Check active/other components where value is the part name (e.g. STM32F401, AMS1117-3.3, 1N4148)
        if not matched and grp.value:
            val_mpn_matches = self.db.find_by_mpn(grp.value)
            for cand in val_mpn_matches:
                if packages_match(cand.package, grp.package):
                    matched = cand
                    match_type = f"Part match ({cand.mpn})"
                    break
            if not matched and val_mpn_matches:
                alternatives.extend(val_mpn_matches)

        # Determine final status based on available quantity
        if matched:
            used = consumed_stock.get(matched.id, 0)
            avail = max(0, matched.quantity - used)
            grp.matched_component = matched
            grp.available_qty = avail

            if avail >= grp.needed_qty:
                grp.status = "IN_STOCK"
                grp.match_note = f"✓ {match_type} — {avail} in stock (need {grp.needed_qty})"
                consumed_stock[matched.id] = used + grp.needed_qty
            else:
                grp.status = "LOW_STOCK"
                short = grp.needed_qty - avail
                grp.match_note = f"⚠ Low Stock: {avail} in stock, need {grp.needed_qty} (short by {short})"
                consumed_stock[matched.id] = matched.quantity
        elif alternatives:
            grp.status = "COMPATIBLE"
            alt = alternatives[0]
            grp.matched_component = alt
            grp.available_qty = alt.quantity
            grp.alternatives = alternatives
            grp.match_note = f"⚡ Compatible alternative available: {alt.mpn or alt.value} ({alt.package}, {alt.quantity} in stock)"
        else:
            grp.status = "MISSING"
            grp.available_qty = 0
            grp.match_note = "❌ 0 in stock — needs order"
