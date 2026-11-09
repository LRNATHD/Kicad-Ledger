"""SQLite Local-Only Database Manager for KiCad-StockCheck."""

import os
import sqlite3
from datetime import datetime
from typing import List, Optional, Tuple, Dict, Any

from stockcheck.models import Component
from stockcheck.normalizer import clean_mpn, values_match, packages_match


DEFAULT_DB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
DEFAULT_DB_PATH = os.path.join(DEFAULT_DB_DIR, "inventory.db")


class Database:
    """Manages the local SQLite component inventory database."""

    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            self.db_path = DEFAULT_DB_PATH
        else:
            self.db_path = os.path.abspath(db_path)

        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self.init_db()

    def get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self):
        """Create tables and indexes if they do not exist."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS components (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    category TEXT NOT NULL,
                    mpn TEXT,
                    clean_mpn TEXT,
                    manufacturer TEXT,
                    value TEXT,
                    norm_value REAL,
                    package TEXT,
                    package_raw TEXT,
                    quantity INTEGER DEFAULT 0,
                    bin_location TEXT,
                    distributor TEXT,
                    distributor_sku TEXT,
                    voltage TEXT,
                    voltage_num REAL,
                    tolerance TEXT,
                    dielectric TEXT,
                    power TEXT,
                    description TEXT,
                    unit_price REAL DEFAULT 0.0,
                    order_id TEXT,
                    order_date TEXT,
                    notes TEXT,
                    created_at TEXT,
                    updated_at TEXT
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS orders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    distributor TEXT NOT NULL,
                    order_id TEXT,
                    order_date TEXT,
                    total_items INTEGER DEFAULT 0,
                    total_cost REAL DEFAULT 0.0,
                    imported_at TEXT
                )
            """)

            # Indexes for fast lookup
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_comp_mpn ON components(clean_mpn)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_comp_cat ON components(category)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_comp_pkg ON components(package)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_comp_sku ON components(distributor_sku)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_comp_val ON components(norm_value)")
            conn.commit()

    def _row_to_component(self, row: sqlite3.Row) -> Component:
        return Component(
            id=row["id"],
            category=row["category"] or "other",
            mpn=row["mpn"] or "",
            clean_mpn=row["clean_mpn"] or "",
            manufacturer=row["manufacturer"] or "",
            value=row["value"] or "",
            norm_value=row["norm_value"],
            package=row["package"] or "",
            package_raw=row["package_raw"] or "",
            quantity=row["quantity"] or 0,
            bin_location=row["bin_location"] or "",
            distributor=row["distributor"] or "",
            distributor_sku=row["distributor_sku"] or "",
            voltage=row["voltage"] or "",
            voltage_num=row["voltage_num"],
            tolerance=row["tolerance"] or "",
            dielectric=row["dielectric"] or "",
            power=row["power"] or "",
            description=row["description"] or "",
            unit_price=row["unit_price"] or 0.0,
            order_id=row["order_id"] or "",
            order_date=row["order_date"] or "",
            notes=row["notes"] or "",
            created_at=row["created_at"] or "",
            updated_at=row["updated_at"] or ""
        )

    def add_component(self, comp: Component) -> int:
        """Add a new component to inventory."""
        now = datetime.now().isoformat()
        if not comp.clean_mpn:
            comp.clean_mpn = clean_mpn(comp.mpn)

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO components (
                    category, mpn, clean_mpn, manufacturer, value, norm_value,
                    package, package_raw, quantity, bin_location, distributor,
                    distributor_sku, voltage, voltage_num, tolerance, dielectric,
                    power, description, unit_price, order_id, order_date, notes,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                comp.category, comp.mpn, comp.clean_mpn, comp.manufacturer, comp.value,
                comp.norm_value, comp.package, comp.package_raw, comp.quantity,
                comp.bin_location, comp.distributor, comp.distributor_sku, comp.voltage,
                comp.voltage_num, comp.tolerance, comp.dielectric, comp.power,
                comp.description, comp.unit_price, comp.order_id, comp.order_date,
                comp.notes, now, now
            ))
            comp_id = cursor.lastrowid
            conn.commit()
            return comp_id

    def update_component(self, comp: Component):
        """Update an existing component."""
        now = datetime.now().isoformat()
        if not comp.clean_mpn:
            comp.clean_mpn = clean_mpn(comp.mpn)

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE components SET
                    category = ?, mpn = ?, clean_mpn = ?, manufacturer = ?, value = ?,
                    norm_value = ?, package = ?, package_raw = ?, quantity = ?,
                    bin_location = ?, distributor = ?, distributor_sku = ?,
                    voltage = ?, voltage_num = ?, tolerance = ?, dielectric = ?,
                    power = ?, description = ?, unit_price = ?, order_id = ?,
                    order_date = ?, notes = ?, updated_at = ?
                WHERE id = ?
            """, (
                comp.category, comp.mpn, comp.clean_mpn, comp.manufacturer, comp.value,
                comp.norm_value, comp.package, comp.package_raw, comp.quantity,
                comp.bin_location, comp.distributor, comp.distributor_sku, comp.voltage,
                comp.voltage_num, comp.tolerance, comp.dielectric, comp.power,
                comp.description, comp.unit_price, comp.order_id, comp.order_date,
                comp.notes, now, comp.id
            ))
            conn.commit()

    def adjust_quantity(self, comp_id: int, delta: int):
        """Increase or decrease inventory count for a component."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE components SET quantity = MAX(0, quantity + ?), updated_at = ? WHERE id = ?",
                           (delta, datetime.now().isoformat(), comp_id))
            conn.commit()

    def delete_component(self, comp_id: int):
        """Delete component by id."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM components WHERE id = ?", (comp_id,))
            conn.commit()

    def get_component(self, comp_id: int) -> Optional[Component]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM components WHERE id = ?", (comp_id,))
            row = cursor.fetchone()
            return self._row_to_component(row) if row else None

    def list_all(self, limit: int = 500) -> List[Component]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM components ORDER BY category, value, package LIMIT ?", (limit,))
            return [self._row_to_component(r) for r in cursor.fetchall()]

    def search_components(self, query: str = "", category: Optional[str] = None,
                          package: Optional[str] = None, limit: int = 200) -> List[Component]:
        """Fast multi-field search for components."""
        tokens = [t.strip() for t in query.split() if t.strip()]
        
        sql = "SELECT * FROM components WHERE 1=1"
        params: List[Any] = []

        if category and category.lower() != "all":
            sql += " AND category = ?"
            params.append(category.lower())

        if package and package.lower() != "all":
            sql += " AND (package LIKE ? OR package_raw LIKE ?)"
            params.extend([f"%{package}%", f"%{package}%"])

        for token in tokens:
            sql += """ AND (
                mpn LIKE ? OR
                clean_mpn LIKE ? OR
                value LIKE ? OR
                package LIKE ? OR
                distributor_sku LIKE ? OR
                bin_location LIKE ? OR
                description LIKE ? OR
                manufacturer LIKE ?
            )"""
            pattern = f"%{token}%"
            params.extend([pattern] * 8)

        sql += " ORDER BY category, value, package LIMIT ?"
        params.append(limit)

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, params)
            return [self._row_to_component(r) for r in cursor.fetchall()]

    def find_by_sku(self, sku: str) -> List[Component]:
        if not sku:
            return []
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM components WHERE UPPER(distributor_sku) = UPPER(?)", (sku.strip(),))
            return [self._row_to_component(r) for r in cursor.fetchall()]

    def find_by_mpn(self, mpn: str) -> List[Component]:
        if not mpn:
            return []
        c_mpn = clean_mpn(mpn)
        with self.get_connection() as conn:
            cursor = conn.cursor()
            # Try exact clean_mpn match first
            cursor.execute("SELECT * FROM components WHERE clean_mpn = ? OR UPPER(mpn) = UPPER(?)", (c_mpn, mpn.strip()))
            rows = cursor.fetchall()
            if rows:
                return [self._row_to_component(r) for r in rows]
                
            # Fallback to prefix/fuzzy MPN
            cursor.execute("SELECT * FROM components WHERE clean_mpn LIKE ? OR clean_mpn LIKE ?",
                           (f"{c_mpn}%", f"%{c_mpn}%"))
            return [self._row_to_component(r) for r in cursor.fetchall()]

    def find_passives(self, category: str, norm_value: Optional[float], package: str) -> List[Component]:
        """Find passive components matching category and value, with package compatibility check."""
        if norm_value is None:
            return []
            
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM components WHERE category = ?", (category.lower(),))
            rows = cursor.fetchall()

        matched = []
        for r in rows:
            comp = self._row_to_component(r)
            if values_match(comp.norm_value, norm_value):
                # Check package compatibility
                if packages_match(comp.package, package):
                    matched.append(comp)

        return matched

    def find_compatible_passives(self, category: str, norm_value: Optional[float],
                                package: str, min_voltage: Optional[float] = None) -> List[Component]:
        """Find alternatives: same value & package, higher voltage rating or compatible package."""
        if norm_value is None:
            return []
            
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM components WHERE category = ?", (category.lower(),))
            rows = cursor.fetchall()

        compatible = []
        for r in rows:
            comp = self._row_to_component(r)
            if values_match(comp.norm_value, norm_value):
                # Compatible package or higher voltage
                pkg_ok = packages_match(comp.package, package)
                volt_ok = True
                if min_voltage and comp.voltage_num:
                    volt_ok = (comp.voltage_num >= min_voltage)
                if pkg_ok and volt_ok:
                    compatible.append(comp)

        return compatible

    def import_order(self, order_info: Dict[str, Any], items: List[Component]) -> Tuple[int, int]:
        """
        Import or update components from an order.
        If a component with identical MPN or SKU already exists, increment stock.
        Returns: (inserted_count, updated_count)
        """
        now = datetime.now().isoformat()
        inserted = 0
        updated = 0

        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Record order record
            cursor.execute("""
                INSERT INTO orders (distributor, order_id, order_date, total_items, total_cost, imported_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                order_info.get("distributor", "Unknown"),
                order_info.get("order_id", ""),
                order_info.get("order_date", ""),
                len(items),
                order_info.get("total_cost", 0.0),
                now
            ))

            for comp in items:
                if not comp.clean_mpn:
                    comp.clean_mpn = clean_mpn(comp.mpn)

                # Check if this item already exists in stock
                match_id = None
                if comp.distributor_sku:
                    cursor.execute("SELECT id, quantity FROM components WHERE distributor = ? AND distributor_sku = ?",
                                   (comp.distributor, comp.distributor_sku))
                    row = cursor.fetchone()
                    if row:
                        match_id = row["id"]

                if not match_id and comp.clean_mpn:
                    cursor.execute("SELECT id, quantity FROM components WHERE clean_mpn = ? AND package = ?",
                                   (comp.clean_mpn, comp.package))
                    row = cursor.fetchone()
                    if row:
                        match_id = row["id"]

                if match_id:
                    # Update stock quantity
                    cursor.execute("UPDATE components SET quantity = quantity + ?, updated_at = ? WHERE id = ?",
                                   (comp.quantity, now, match_id))
                    updated += 1
                else:
                    # Insert new component
                    cursor.execute("""
                        INSERT INTO components (
                            category, mpn, clean_mpn, manufacturer, value, norm_value,
                            package, package_raw, quantity, bin_location, distributor,
                            distributor_sku, voltage, voltage_num, tolerance, dielectric,
                            power, description, unit_price, order_id, order_date, notes,
                            created_at, updated_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        comp.category, comp.mpn, comp.clean_mpn, comp.manufacturer, comp.value,
                        comp.norm_value, comp.package, comp.package_raw, comp.quantity,
                        comp.bin_location, comp.distributor, comp.distributor_sku, comp.voltage,
                        comp.voltage_num, comp.tolerance, comp.dielectric, comp.power,
                        comp.description, comp.unit_price, comp.order_id, comp.order_date,
                        comp.notes, now, now
                    ))
                    inserted += 1

            conn.commit()

        return inserted, updated

    def get_stats(self) -> Dict[str, Any]:
        """Return high-level inventory statistics."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*), SUM(quantity) FROM components")
            count, total_qty = cursor.fetchone()
            
            cursor.execute("SELECT category, COUNT(*), SUM(quantity) FROM components GROUP BY category")
            by_category = {r[0]: {"unique_parts": r[1], "total_qty": r[2] or 0} for r in cursor.fetchall()}

            cursor.execute("SELECT COUNT(*) FROM orders")
            total_orders = cursor.fetchone()[0]

            return {
                "unique_parts": count or 0,
                "total_quantity": total_qty or 0,
                "total_orders": total_orders or 0,
                "by_category": by_category,
                "db_path": self.db_path
            }

    def clear_all_data(self):
        """Wipe all components and orders (local reset)."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM components")
            cursor.execute("DELETE FROM orders")
            conn.commit()
