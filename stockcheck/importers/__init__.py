"""Order importers registry and auto-detection."""

from typing import List, Dict, Any, Tuple
from stockcheck.models import Component
from stockcheck.importers.base import BaseOrderImporter
from stockcheck.importers.lcsc import LCSCImporter
from stockcheck.importers.mouser import MouserImporter
from stockcheck.importers.digikey import DigiKeyImporter
from stockcheck.importers.generic import GenericImporter

AVAILABLE_IMPORTERS: List[BaseOrderImporter] = [
    LCSCImporter(),
    MouserImporter(),
    DigiKeyImporter(),
    GenericImporter(),  # Fallback
]


def detect_importer(file_path: str) -> BaseOrderImporter:
    """Inspect CSV header and return the best matching order importer."""
    headers, _ = BaseOrderImporter.read_csv_rows(file_path)
    for importer in AVAILABLE_IMPORTERS[:-1]:  # Check specific distributors first
        if importer.can_handle(headers):
            return importer
    return AVAILABLE_IMPORTERS[-1]  # Generic fallback


def import_order_file(file_path: str) -> Tuple[Dict[str, Any], List[Component]]:
    """Automatically detect format and parse distributor order file."""
    importer = detect_importer(file_path)
    return importer.parse_file(file_path)
