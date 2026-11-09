"""Data models for KiCad-StockCheck."""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any


@dataclass
class Component:
    """Represents a physical electronics component in on-device inventory."""
    id: Optional[int] = None
    category: str = "other"                     # resistor, capacitor, inductor, ic, diode, transistor, etc.
    mpn: str = ""                               # Manufacturer Part Number
    clean_mpn: str = ""                         # Normalized MPN (stripped of reel/packaging suffixes)
    manufacturer: str = ""
    value: str = ""                             # e.g. "10k", "100nF", "AMS1117-3.3"
    norm_value: Optional[float] = None          # Base SI unit value (Ohms, Farads, Henries)
    package: str = ""                           # Canonical package: 0805, 0603, SOT-23, SOIC-8, etc.
    package_raw: str = ""                       # Original raw package string
    quantity: int = 0                           # Current in-stock quantity
    bin_location: str = ""                      # Drawer/Bin/Book location e.g. "A1", "0805-Box"
    distributor: str = ""                       # LCSC, Mouser, DigiKey, etc.
    distributor_sku: str = ""                   # C2040, 71-CRCW..., 311-...
    voltage: str = ""                           # e.g. "50V", "16V"
    voltage_num: Optional[float] = None         # Numeric voltage in Volts
    tolerance: str = ""                         # e.g. "1%", "5%"
    dielectric: str = ""                        # e.g. "X7R", "C0G", "NPO"
    power: str = ""                             # e.g. "1/8W", "0.25W"
    description: str = ""
    unit_price: float = 0.0
    order_id: str = ""                          # Distributor Order/PO number
    order_date: str = ""
    notes: str = ""
    created_at: str = ""
    updated_at: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {k: v for k, v in self.__dict__.items()}


@dataclass
class BoardItem:
    """Represents a component on a KiCad PCB or schematic."""
    reference: str                              # e.g. "R1", "C5", "U2"
    value: str                                  # e.g. "10k", "100nF", "STM32F401CEU6"
    footprint: str                              # e.g. "Resistor_SMD:R_0805_2012Metric"
    category: str = "other"                     # resistor, capacitor, etc.
    norm_value: Optional[float] = None
    package: str = ""                           # Canonical package (0805, SOT-23, etc.)
    mpn: str = ""                               # Explicit MPN property if defined in KiCad
    lcsc: str = ""                              # Explicit LCSC property if defined
    dnp: bool = False                           # Do Not Populate flag
    sheet_path: str = ""


@dataclass
class MatchResult:
    """Result of matching a board item against local inventory."""
    board_item: BoardItem
    status: str                                 # IN_STOCK, COMPATIBLE, LOW_STOCK, MISSING, DNP
    matched_component: Optional[Component] = None
    needed_qty: int = 1
    available_qty: int = 0
    match_type: str = "exact"                   # exact_mpn, exact_sku, value_package, compatible
    match_note: str = ""
    alternatives: list = field(default_factory=list)
