"""Component normalization engine: values, SI units, and package/footprint aliasing."""

import re
import math
from typing import Optional, Tuple

# EIA Imperial to Metric SMD aliases
EIA_IMPERIAL_TO_METRIC = {
    "01005": "0402",
    "0201": "0603",
    "0402": "1005",
    "0603": "1608",
    "0805": "2012",
    "1206": "3216",
    "1210": "3225",
    "1812": "4532",
    "2010": "5025",
    "2512": "6432",
}

EIA_METRIC_TO_IMPERIAL = {v: k for k, v in EIA_IMPERIAL_TO_METRIC.items()}


def normalize_package(pkg_str: str, strict: bool = False) -> str:
    """Normalize a footprint/package string to a canonical package name.

    When strict=True, returns "" if no recognized package pattern is found
    (useful when scanning free-form description text).
    """
    if not pkg_str:
        return ""
    
    # Strip KiCad library prefix (e.g. "Resistor_SMD:R_0805_2012Metric" -> "R_0805_2012Metric")
    clean = pkg_str.split(":")[-1].upper()
    
    # Replace non-alphanumeric with spaces for easy token matching
    token_str = re.sub(r"[^A-Z0-9]", " ", clean)
    tokens = set(token_str.split())

    # Check SMD passives - look for standard imperial EIA codes first
    # KiCad footprints usually have: "R_0603_1608Metric" where 0603 is imperial and 1608 is metric.
    # We prioritize the imperial code unless it's explicitly suffixed with "Metric" (e.g. 0603Metric -> 0201).
    for imp in ["01005", "0201", "0402", "0603", "0805", "1206", "1210", "1812", "2010", "2512"]:
        # If imperial appears as a standalone token or part of R_0805_...
        if re.search(rf"(?:^|[_\s\-])[RCL_]*{imp}(?:[_\s\-]|$)", clean):
            return imp

    # Check metric aliases if only metric code was provided
    if "1608METRIC" in tokens or "1608" in tokens:
        return "0603"
    if "2012METRIC" in tokens or "2012" in tokens:
        return "0805"
    if "1005METRIC" in tokens or "1005" in tokens:
        return "0402"
    if "3216METRIC" in tokens or "3216" in tokens:
        return "1206"
    if "3225METRIC" in tokens or "3225" in tokens:
        return "1210"
    if "0603METRIC" in tokens:
        return "0201"
    if "0402METRIC" in tokens:
        return "01005"

    # SOT packages
    m = re.search(r"TSOT[-_ ]?23(?:[-_ ]?(\d+))?", clean)
    if m:
        pin = m.group(1)
        return f"SOT-23-{pin}" if pin and pin not in ("3", "") else "SOT-23"
    m = re.search(r"SOT[-_ ]?23(?:[-_ ]?(\d+))?", clean)
    if m:
        pin = m.group(1)
        return f"SOT-23-{pin}" if pin and pin not in ("3", "") else "SOT-23"
    if re.search(r"SOT[-_ ]?25\b", clean):
        return "SOT-23-5"
    m = re.search(r"SC[-_ ]?70(?:[-_ ]?(\d+))?", clean)
    if m:
        pin = m.group(1)
        return f"SC-70-{pin}" if pin else "SC-70"
    if "SOT223" in clean or "SOT-223" in clean:
        return "SOT-223"
    if "SOT89" in clean or "SOT-89" in clean:
        return "SOT-89"
    if "SOT323" in clean or "SOT-323" in clean:
        return "SOT-323"
    if "SOT363" in clean or "SOT-363" in clean:
        return "SOT-363"

    # Diodes (SOD, SMA, SMB, SMC)
    if "SOD123" in clean or "SOD-123" in clean:
        return "SOD-123"
    if "SOD323" in clean or "SOD-323" in clean:
        return "SOD-323"
    if "SOD523" in clean or "SOD-523" in clean:
        return "SOD-523"
    if "SMA" in tokens or "DO 214AC" in token_str or "DO214AC" in clean:
        return "SMA"
    if "SMB" in tokens or "DO 214AA" in token_str or "DO214AA" in clean:
        return "SMB"
    if "SMC" in tokens or "DO 214AB" in token_str or "DO214AB" in clean:
        return "SMC"

    # SOIC / SOP / TSSOP / SSOP
    m = re.search(r"(?:SOIC|SOP)[-_ ]?(\d+)", clean)
    if m:
        return f"SOIC-{m.group(1)}"
    m = re.search(r"TSSOP[-_ ]?(\d+)", clean)
    if m:
        return f"TSSOP-{m.group(1)}"
    m = re.search(r"SSOP[-_ ]?(\d+)", clean)
    if m:
        return f"SSOP-{m.group(1)}"
    m = re.search(r"MSOP[-_ ]?(\d+)", clean)
    if m:
        return f"MSOP-{m.group(1)}"

    # QFN / DFN / QFP / WSON
    m = re.search(r"(?:V|W|VF|WQ)?QFP?N[-_ ]?(\d+)", clean)
    if m:
        return f"QFN-{m.group(1)}"
    m = re.search(r"(\d+)WSON|WSON[-_ ]?(\d+)", clean)
    if m:
        pin = m.group(1) or m.group(2)
        return f"WSON-{pin}"
    m = re.search(r"DFN[-_ ]?(\d+)", clean)
    if m:
        return f"DFN-{m.group(1)}"
    m = re.search(r"(?:L)?QFP[-_ ]?(\d+)", clean)
    if m:
        return f"LQFP-{m.group(1)}"

    # Through-hole (DIP, TO-92, TO-220, Axial)
    m = re.search(r"DIP[-_ ]?(\d+)", clean)
    if m:
        return f"DIP-{m.group(1)}"
    if "TO 92" in token_str or "TO92" in clean:
        return "TO-92"
    if "TO 220" in token_str or "TO220" in clean:
        return "TO-220"
    if "TO 252" in token_str or "TO252" in clean or "DPAK" in clean:
        return "TO-252"
    if "TO 263" in token_str or "TO263" in clean or "D2PAK" in clean:
        return "TO-263"
    if "AXIAL" in clean:
        return "Axial"

    if strict:
        return ""

    # Fallback: clean symbols, remove pad descriptions
    clean = re.sub(r"_PAD.*$", "", clean)
    clean = re.sub(r"^(?:R_|C_|L_|D_|LED_)", "", clean)
    return clean.strip()


def packages_match(pkg1: str, pkg2: str) -> bool:
    """Check if two package strings refer to compatible/equivalent footprints."""
    if not pkg1 or not pkg2:
        return False
        
    n1 = normalize_package(pkg1).upper()
    n2 = normalize_package(pkg2).upper()
    
    if n1 == n2:
        return True
        
    # Check imperial vs metric passive mapping
    if n1 in EIA_IMPERIAL_TO_METRIC and n2 == EIA_IMPERIAL_TO_METRIC[n1]:
        return True
    if n2 in EIA_IMPERIAL_TO_METRIC and n1 == EIA_IMPERIAL_TO_METRIC[n2]:
        return True
        
    # SOT-23 variants (SOT-23 and SOT-23-3 are identical 3-pin)
    if {n1, n2} <= {"SOT-23", "SOT-23-3"}:
        return True
        
    # Substring contains (e.g. "0805" in "0805_2012Metric")
    if n1 in n2 or n2 in n1:
        return True

    return False


def values_match(val1: Optional[float], val2: Optional[float], rel_tol: float = 1e-4) -> bool:
    """Check if two numeric component values match within standard tolerance."""
    if val1 is None or val2 is None:
        return False
    if val1 == 0.0 and val2 == 0.0:
        return True
    if val1 == 0.0 or val2 == 0.0:
        return False
    return math.isclose(val1, val2, rel_tol=rel_tol)


def parse_resistor_value(val_str: str) -> Tuple[Optional[float], str]:
    """Parse a resistor value string (e.g. '10k', '4k7', '0R1', '100') into (Ohms, Canonical)."""
    if not val_str:
        return None, ""
    
    s = val_str.strip().replace("Ω", "").replace("Ohm", "").replace("ohm", "").replace("OHM", "").strip()
    
    # 0 Ohm special case
    if s in ("0", "0R", "0.0", "0.00", "0R0"):
        return 0.0, "0R"

    # Letter as decimal point: 4k7 -> 4.7k, 2R2 -> 2.2, 0R05 -> 0.05
    letter_dec = re.match(r"^(\d+)([RrkKMmGg])(\d+)$", s)
    if letter_dec:
        whole, unit, frac = letter_dec.groups()
        s = f"{whole}.{frac}{unit}"

    # General pattern: Number + optional unit (R, k, M, G, m)
    m = re.match(r"^([\d.]+)\s*([rRkKmMgg])?$", s)
    if m:
        num_str, mult_str = m.groups()
        try:
            val = float(num_str)
        except ValueError:
            return None, val_str
            
        mult_str = mult_str or ""
        mult = 1.0
        if mult_str.lower() == "k":
            mult = 1e3
        elif mult_str == "M":
            mult = 1e6
        elif mult_str.lower() == "g":
            mult = 1e9
        elif mult_str == "m":
            mult = 1e-3
            
        total_ohms = round(val * mult, 6)
        return total_ohms, format_resistor_value(total_ohms)

    return None, val_str


def format_resistor_value(ohms: float) -> str:
    """Format numeric Ohms to clean engineering notation (e.g. 10k, 4.7k, 100R)."""
    if ohms == 0.0:
        return "0R"
    if ohms >= 1e6:
        m = ohms / 1e6
        return f"{m:g}M"
    if ohms >= 1e3:
        k = ohms / 1e3
        return f"{k:g}k"
    return f"{ohms:g}R"


def parse_capacitor_value(val_str: str) -> Tuple[Optional[float], str]:
    """Parse capacitor string (e.g. '100nF', '0.1uF', '10pF') into (Farads, Canonical)."""
    if not val_str:
        return None, ""
        
    s = val_str.strip().replace("F", "").replace("f", "").strip()
    
    # Notation like 4n7 -> 4.7n, 1u5 -> 1.5u
    letter_dec = re.match(r"^(\d+)([pnuµm])(\d+)$", s)
    if letter_dec:
        whole, unit, frac = letter_dec.groups()
        s = f"{whole}.{frac}{unit}"
        
    m = re.match(r"^([\d.]+)\s*([pPnNuUµmM]?)?$", s)
    if m:
        num_str, mult_str = m.groups()
        try:
            val = float(num_str)
        except ValueError:
            return None, val_str
            
        mult_str = (mult_str or "").lower()
        if mult_str in ("u", "µ"):
            mult = 1e-6
        elif mult_str == "n":
            mult = 1e-9
        elif mult_str == "p":
            mult = 1e-12
        elif mult_str == "m":
            mult = 1e-3
        else:
            # Default to uF if value < 1, or pF if >= 1
            if val < 1.0:
                mult = 1e-6
            else:
                mult = 1e-12
                
        # Round to 15 decimal places to avoid floating point representation quirks
        total_farads = round(val * mult, 15)
        return total_farads, format_capacitor_value(total_farads)
        
    return None, val_str


def format_capacitor_value(farads: float) -> str:
    """Format Farads to engineering notation (e.g. 100nF, 10uF, 22pF)."""
    if farads >= 1e-3:
        m = round(farads * 1e3, 4)
        return f"{m:g}mF"
    if farads >= 1e-6:
        u = round(farads * 1e6, 4)
        return f"{u:g}uF"
    if farads >= 1e-9:
        n = round(farads * 1e9, 4)
        return f"{n:g}nF"
    p = round(farads * 1e12, 4)
    return f"{p:g}pF"


def parse_inductor_value(val_str: str) -> Tuple[Optional[float], str]:
    """Parse inductor string (e.g. '10uH', '100nH', '1mH') into (Henries, Canonical)."""
    if not val_str:
        return None, ""
        
    s = val_str.strip().replace("H", "").replace("h", "").strip()
    m = re.match(r"^([\d.]+)\s*([nNuUµmM]?)?$", s)
    if m:
        num_str, mult_str = m.groups()
        try:
            val = float(num_str)
        except ValueError:
            return None, val_str
            
        mult_str = (mult_str or "").lower()
        if mult_str in ("u", "µ"):
            mult = 1e-6
        elif mult_str == "n":
            mult = 1e-9
        elif mult_str == "m":
            mult = 1e-3
        else:
            mult = 1e-6
            
        total_henries = round(val * mult, 15)
        return total_henries, format_inductor_value(total_henries)
        
    return None, val_str


def format_inductor_value(henries: float) -> str:
    """Format Henries to engineering notation (e.g. 10uH, 100nH, 1mH)."""
    if henries >= 1e-3:
        m = round(henries * 1e3, 4)
        return f"{m:g}mH"
    if henries >= 1e-6:
        u = round(henries * 1e6, 4)
        return f"{u:g}uH"
    n = round(henries * 1e9, 4)
    return f"{n:g}nH"


def extract_voltage(text: str) -> Tuple[str, Optional[float]]:
    """Extract voltage rating like '50V', '25V', '3.3V', '6.3V'."""
    if not text:
        return "", None
    m = re.search(r"\b(\d+(?:\.\d+)?)\s*V(?:DC)?\b", text, re.IGNORECASE)
    if m:
        try:
            num = float(m.group(1))
            return f"{m.group(1)}V", num
        except ValueError:
            pass
    return "", None


def extract_tolerance(text: str) -> str:
    """Extract tolerance like '1%', '5%', '0.1%'."""
    if not text:
        return ""
    m = re.search(r"(?:±|\+/-)?\s*(\d+(?:\.\d+)?)\s*%", text)
    if m:
        return f"±{m.group(1)}%"
    return ""


def extract_dielectric(text: str) -> str:
    """Extract capacitor dielectric like X7R, X5R, C0G, NP0, Y5V."""
    if not text:
        return ""
    m = re.search(r"\b(X7R|X5R|C0G|NP0|Y5V|X8R)\b", text, re.IGNORECASE)
    if m:
        return m.group(1).upper()
    return ""


def clean_mpn(mpn_str: str) -> str:
    """Normalize MPN for fuzzy comparison (strips reel suffixes, punctuation)."""
    if not mpn_str:
        return ""
    s = mpn_str.strip().upper()
    
    # Strip common reel/packaging suffixes
    s = re.sub(r"[-_/]?(?:TR|T&R|REEL|TAPE|CUT|TRAY|TUBE)$", "", s)
    s = re.sub(r"#PBF$", "", s)
    s = re.sub(r"/NOPB$", "", s)
    s = re.sub(r"-ND$", "", s)  # DigiKey suffix
    s = re.sub(r"_C\d{4,}$", "", s)  # EasyEDA / LCSC SKU suffix (e.g. TP4057_C725791)
    return s.strip()


def infer_category(ref: str = "", desc: str = "", value: str = "") -> str:
    """Infer component category from reference designator, description, or value."""
    ref_up = ref.upper()
    
    # From KiCad reference designator
    if re.match(r"^R\d+", ref_up):
        return "resistor"
    if re.match(r"^C\d+", ref_up):
        return "capacitor"
    if re.match(r"^L\d+", ref_up):
        return "inductor"
    if re.match(r"^D\d+", ref_up):
        if "LED" in desc.upper() or "LED" in value.upper():
            return "led"
        return "diode"
    if re.match(r"^LED\d+", ref_up):
        return "led"
    if re.match(r"^Q\d+", ref_up):
        return "transistor"
    if re.match(r"^U\d+", ref_up):
        return "ic"
    if re.match(r"^J\d+", ref_up) or re.match(r"^P\d+", ref_up):
        return "connector"
    if re.match(r"^Y\d+", ref_up) or re.match(r"^X\d+", ref_up):
        return "crystal"
    if re.match(r"^SW\d+", ref_up):
        return "switch"
    if re.match(r"^F\d+", ref_up):
        return "fuse"
    if re.match(r"^FB\d+", ref_up):
        return "ferrite_bead"
    if re.match(r"^TP\d+", ref_up):
        return "testpoint"

    # From description keywords
    desc_up = desc.upper()
    if "RESISTOR" in desc_up or "RES " in desc_up:
        return "resistor"
    if "CAPACITOR" in desc_up or "CAP " in desc_up:
        return "capacitor"
    if "INDUCTOR" in desc_up or "FIXED IND" in desc_up:
        return "inductor"
    if "DIODE" in desc_up:
        return "diode"
    if "LED" in desc_up:
        return "led"
    if "TRANSISTOR" in desc_up or "MOSFET" in desc_up or "BJT" in desc_up:
        return "transistor"
    if "IC" in desc_up or "MCU" in desc_up or "REGULATOR" in desc_up:
        return "ic"
    if "CONNECTOR" in desc_up or "HEADER" in desc_up or "USB" in desc_up:
        return "connector"
    if "CRYSTAL" in desc_up or "OSCILLATOR" in desc_up:
        return "crystal"

    return "other"
