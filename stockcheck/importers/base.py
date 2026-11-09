"""Base importer interface for component orders."""

import csv
import os
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Tuple
from stockcheck.models import Component


class BaseOrderImporter(ABC):
    """Abstract base class for distributor order parsers."""
    distributor_name = "Unknown"

    @abstractmethod
    def can_handle(self, headers: List[str]) -> bool:
        """Return True if this parser recognizes the CSV headers."""
        pass

    @abstractmethod
    def parse_file(self, file_path: str) -> Tuple[Dict[str, Any], List[Component]]:
        """Parse order file and return (order_metadata, list_of_components)."""
        pass

    @staticmethod
    def read_csv_rows(file_path: str) -> Tuple[List[str], List[Dict[str, str]]]:
        """Read CSV file with encoding fallbacks and return (headers, rows)."""
        encodings = ["utf-8-sig", "utf-8", "latin1", "cp1252"]
        
        for enc in encodings:
            try:
                with open(file_path, "r", encoding=enc, errors="replace") as f:
                    # Detect delimiter (comma, semicolon, tab)
                    sample = f.read(4096)
                    f.seek(0)
                    
                    dialect = csv.excel
                    if "\t" in sample and "," not in sample:
                        dialect = csv.excel_tab
                    elif ";" in sample and "," not in sample:
                        class SemicolonDialect(csv.excel):
                            delimiter = ";"
                        dialect = SemicolonDialect
                        
                    reader = csv.DictReader(f, dialect=dialect)
                    headers = reader.fieldnames or []
                    headers = [h.strip() for h in headers if h]
                    rows = list(reader)
                    return headers, rows
            except Exception:
                continue

        raise ValueError(f"Could not parse CSV file: {file_path}")
