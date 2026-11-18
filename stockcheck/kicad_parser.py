"""KiCad PCB and Schematic parser supporting .kicad_pcb, .kicad_sch, and native pcbnew."""

import os
import re
from typing import List, Optional, Dict
from stockcheck.models import BoardItem
from stockcheck.normalizer import (
    normalize_package, parse_resistor_value, parse_capacitor_value,
    parse_inductor_value, infer_category, clean_mpn
)


class KiCadParser:
    """Parses components from KiCad PCB and schematic files or direct pcbnew API."""

    @staticmethod
    def parse_file(file_path: str) -> List[BoardItem]:
        """Parse components from a .kicad_pcb or .kicad_sch file."""
        ext = os.path.splitext(file_path)[1].lower()
        if ext == ".kicad_pcb":
            return KiCadParser.parse_kicad_pcb(file_path)
        elif ext == ".kicad_sch":
            return KiCadParser.parse_kicad_sch(file_path)
        elif ext == ".csv":
            return KiCadParser.parse_bom_csv(file_path)
        else:
            raise ValueError(f"Unsupported board file type: {ext}")

    @staticmethod
    def parse_kicad_pcb(file_path: str) -> List[BoardItem]:
        """Parse .kicad_pcb S-expression file."""
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()

        items: List[BoardItem] = []

        # Pattern handles KiCad 6/7/8/9/10 (footprint ...) and KiCad 5 (module ...)
        footprint_pattern = re.compile(
            r'\((?:footprint|module)\s+"?([^"\s\)]+)"?(.*?)(?=\n\s*\((?:footprint|module)|\Z)',
            re.DOTALL
        )

        for match in footprint_pattern.finditer(content):
            fp_type = match.group(1).strip()
            body = match.group(2)

            # Check DNP (Do Not Populate)
            dnp = bool(re.search(r'\(attr\s+[^)]*dnp', body, re.IGNORECASE) or 
                       re.search(r'\(property\s+"dnp"\s+"(?:yes|true|1)"', body, re.IGNORECASE))

            # Extract Reference
            ref_match = re.search(r'\(property\s+"Reference"\s+"([^"]*)"', body, re.IGNORECASE)
            if not ref_match:
                ref_match = re.search(r'\(fp_text\s+reference\s+"([^"]*)"', body, re.IGNORECASE)
            ref = ref_match.group(1).strip() if ref_match else ""

            # Extract Value
            val_match = re.search(r'\(property\s+"Value"\s+"([^"]*)"', body, re.IGNORECASE)
            if not val_match:
                val_match = re.search(r'\(fp_text\s+value\s+"([^"]*)"', body, re.IGNORECASE)
            val = val_match.group(1).strip() if val_match else ""

            # Extract Footprint property if overridden
            fp_prop_match = re.search(r'\(property\s+"Footprint"\s+"([^"]*)"', body, re.IGNORECASE)
            footprint = fp_prop_match.group(1).strip() if fp_prop_match else fp_type

            # Extract optional custom properties
            lcsc_match = re.search(r'\(property\s+"(?:LCSC|LCSC Part|LCSC Part #)"\s+"([^"]*)"', body, re.IGNORECASE)
            lcsc = lcsc_match.group(1).strip() if lcsc_match else ""

            mpn_match = re.search(r'\(property\s+"(?:MPN|MFR\.Part #|MFR Part)"\s+"([^"]*)"', body, re.IGNORECASE)
            mpn = mpn_match.group(1).strip() if mpn_match else ""

            # Skip graphical footprints (e.g. logos, fiducials, mount holes, test points if unwanted)
            if not ref or ref.startswith("#") or ref.startswith("G***") or ref.startswith("LOGO"):
                continue

            item = KiCadParser._create_board_item(ref, val, footprint, mpn, lcsc, dnp)
            items.append(item)

        return items

    @staticmethod
    def parse_kicad_sch(file_path: str) -> List[BoardItem]:
        """Parse .kicad_sch S-expression file."""
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()

        items: List[BoardItem] = []

        symbol_pattern = re.compile(
            r'\(symbol\s+\(lib_id\s+"([^"]*)"\)(.*?)(?=\n\s*\(symbol\s+\(lib_id|\Z)',
            re.DOTALL
        )

        for match in symbol_pattern.finditer(content):
            lib_id = match.group(1).strip()
            body = match.group(2)

            # Check if in BOM and DNP
            in_bom_match = re.search(r'\(in_bom\s+(yes|no)\)', body, re.IGNORECASE)
            if in_bom_match and in_bom_match.group(1).lower() == "no":
                continue  # Not a physical component

            dnp_match = re.search(r'\(dnp\s+(yes|no)\)', body, re.IGNORECASE)
            dnp = bool(dnp_match and dnp_match.group(1).lower() == "yes")

            ref_match = re.search(r'\(property\s+"Reference"\s+"([^"]*)"', body)
            val_match = re.search(r'\(property\s+"Value"\s+"([^"]*)"', body)
            fp_match = re.search(r'\(property\s+"Footprint"\s+"([^"]*)"', body)
            lcsc_match = re.search(r'\(property\s+"(?:LCSC|LCSC Part|LCSC Part #)"\s+"([^"]*)"', body, re.IGNORECASE)
            mpn_match = re.search(r'\(property\s+"(?:MPN|MFR\.Part #|MFR Part)"\s+"([^"]*)"', body, re.IGNORECASE)

            ref = ref_match.group(1).strip() if ref_match else ""
            val = val_match.group(1).strip() if val_match else ""
            footprint = fp_match.group(1).strip() if fp_match else ""
            lcsc = lcsc_match.group(1).strip() if lcsc_match else ""
            mpn = mpn_match.group(1).strip() if mpn_match else ""

            # Ignore power symbols (#PWR, etc.)
            if not ref or ref.startswith("#") or ref == "~":
                continue

            item = KiCadParser._create_board_item(ref, val, footprint, mpn, lcsc, dnp)
            items.append(item)

        return items

    @staticmethod
    def parse_bom_csv(file_path: str) -> List[BoardItem]:
        """Parse exported KiCad BOM CSV."""
        import csv
        items: List[BoardItem] = []
        with open(file_path, "r", encoding="utf-8-sig", errors="replace") as f:
            reader = csv.DictReader(f)
            for row in reader:
                r_lower = {k.lower().strip(): v for k, v in row.items() if k}
                refs_str = r_lower.get("reference") or r_lower.get("designator") or ""
                val = r_lower.get("value") or r_lower.get("designation") or ""
                footprint = r_lower.get("footprint") or r_lower.get("package") or ""
                mpn = r_lower.get("mpn") or ""
                lcsc = r_lower.get("lcsc") or ""

                for ref in re.split(r"[\s,;]+", refs_str):
                    ref = ref.strip()
                    if ref:
                        items.append(KiCadParser._create_board_item(ref, val, footprint, mpn, lcsc))
        return items

    @staticmethod
    def parse_from_pcbnew(board=None) -> List[BoardItem]:
        """Extract components directly from KiCad pcbnew active board object."""
        try:
            import pcbnew
        except ImportError:
            raise RuntimeError("pcbnew Python module is only available inside KiCad.")

        if board is None:
            board = pcbnew.GetBoard()

        if board is None:
            return []

        items: List[BoardItem] = []
        for fp in board.GetFootprints():
            ref = fp.GetReference()
            val = fp.GetValue()
            footprint = str(fp.GetFPID().GetUniStringLibId())
            
            # Check DNP
            dnp = False
            if hasattr(fp, "IsDNP"):
                dnp = fp.IsDNP()
            elif hasattr(fp, "GetAttributes"):
                # Older KiCad check
                pass

            # Check properties
            props = {}
            if hasattr(fp, "GetProperties"):
                props = fp.GetProperties()
            
            lcsc = props.get("LCSC", "") or props.get("LCSC Part", "")
            mpn = props.get("MPN", "") or props.get("MFR.Part #", "")

            if not ref or ref.startswith("#") or ref.startswith("G***"):
                continue

            items.append(KiCadParser._create_board_item(ref, val, footprint, mpn, lcsc, dnp))

        return items

    @staticmethod
    def _create_board_item(ref: str, val: str, footprint: str, mpn: str = "", lcsc: str = "", dnp: bool = False) -> BoardItem:
        category = infer_category(ref=ref, value=val)
        norm_val = None

        if category == "resistor":
            norm_val, _ = parse_resistor_value(val)
        elif category == "capacitor":
            norm_val, _ = parse_capacitor_value(val)
        elif category == "inductor":
            norm_val, _ = parse_inductor_value(val)

        package = normalize_package(footprint)

        return BoardItem(
            reference=ref,
            value=val,
            footprint=footprint,
            category=category,
            norm_value=norm_val,
            package=package,
            mpn=mpn,
            lcsc=lcsc,
            dnp=dnp
        )


def find_open_kicad_board() -> str:
    """Detect an actively open KiCad board (.kicad_pcb) or schematic (.kicad_sch).

    Inspects %APPDATA%\\kicad\\*\\kicad.json for open_projects and recent file_history,
    prioritizing projects with active KiCad lock files (~*.kicad_pcb.lck / ~*.kicad_sch.lck).
    """
    import glob
    import json

    appdata = os.environ.get("APPDATA", "")
    if not appdata:
        return ""

    kicad_base = os.path.join(appdata, "kicad")
    if not os.path.isdir(kicad_base):
        return ""

    config_files = sorted(glob.glob(os.path.join(kicad_base, "*", "kicad.json")), reverse=True)
    candidate_dirs = []
    open_proj_dirs = []

    for cfg_path in config_files:
        try:
            with open(cfg_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            sys_sec = data.get("system", {})
            for p in sys_sec.get("open_projects") or []:
                d = os.path.dirname(p)
                if os.path.isdir(d) and d not in open_proj_dirs:
                    open_proj_dirs.append(d)
            for p in sys_sec.get("file_history") or []:
                d = os.path.dirname(p)
                if os.path.isdir(d) and d not in candidate_dirs:
                    candidate_dirs.append(d)
        except Exception:
            continue

    for d in open_proj_dirs + candidate_dirs:
        for ext in (".kicad_pcb", ".kicad_sch"):
            for lck in glob.glob(os.path.join(d, f"~*{ext}.lck")):
                target = os.path.join(d, os.path.basename(lck)[1:-4])
                if os.path.isfile(target):
                    return target

    for d in open_proj_dirs:
        for ext in ("*.kicad_pcb", "*.kicad_sch"):
            matches = glob.glob(os.path.join(d, ext))
            if matches:
                return matches[0]

    return ""
