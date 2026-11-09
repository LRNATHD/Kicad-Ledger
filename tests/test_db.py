"""Unit tests for SQLite database manager."""

import os
import tempfile
import unittest

from stockcheck.db import Database
from stockcheck.models import Component


class TestDatabase(unittest.TestCase):

    def setUp(self):
        self.temp_fd, self.temp_path = tempfile.mkstemp(suffix=".db")
        os.close(self.temp_fd)
        self.db = Database(self.temp_path)

    def tearDown(self):
        if os.path.exists(self.temp_path):
            try:
                os.remove(self.temp_path)
            except OSError:
                pass

    def test_crud_operations(self):
        comp = Component(
            category="resistor",
            mpn="CRCW080510K0FKEA",
            value="10k",
            norm_value=10000.0,
            package="0805",
            quantity=100,
            bin_location="Drawer A1",
            distributor="Mouser",
            distributor_sku="71-CRCW080510K0FKEA"
        )
        comp_id = self.db.add_component(comp)
        self.assertIsNotNone(comp_id)

        # Retrieve
        retrieved = self.db.get_component(comp_id)
        self.assertEqual(retrieved.value, "10k")
        self.assertEqual(retrieved.quantity, 100)

        # Adjust quantity
        self.db.adjust_quantity(comp_id, -10)
        self.assertEqual(self.db.get_component(comp_id).quantity, 90)

        # Search
        results = self.db.search_components("10k")
        self.assertEqual(len(results), 1)

        # Delete
        self.db.delete_component(comp_id)
        self.assertIsNone(self.db.get_component(comp_id))


if __name__ == "__main__":
    unittest.main()
