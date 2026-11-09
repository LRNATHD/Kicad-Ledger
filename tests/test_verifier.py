"""End-to-end verification engine tests."""

import os
import tempfile
import unittest

from stockcheck.db import Database
from stockcheck.importers import import_order_file
from stockcheck.kicad_parser import KiCadParser
from stockcheck.verifier import BoardVerifier


class TestBoardVerifier(unittest.TestCase):

    def setUp(self):
        self.temp_db_fd, self.temp_db_path = tempfile.mkstemp(suffix=".db")
        os.close(self.temp_db_fd)
        self.db = Database(self.temp_db_path)

        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.sample_order = os.path.join(base_dir, "examples", "sample_orders", "lcsc_sample_order.csv")
        self.sample_mouser = os.path.join(base_dir, "examples", "sample_orders", "mouser_sample_order.csv")
        self.board_file = os.path.join(base_dir, "examples", "sample_board", "demo_board.kicad_pcb")

        # Import sample orders into test database
        meta1, items1 = import_order_file(self.sample_order)
        self.db.import_order(meta1, items1)

        meta2, items2 = import_order_file(self.sample_mouser)
        self.db.import_order(meta2, items2)

    def tearDown(self):
        if os.path.exists(self.temp_db_path):
            try:
                os.remove(self.temp_db_path)
            except OSError:
                pass

    def test_board_verification(self):
        items = KiCadParser.parse_file(self.board_file)
        self.assertGreater(len(items), 0)

        verifier = BoardVerifier(self.db)
        report = verifier.verify_board(items)

        self.assertGreater(report["total_components"], 10)
        self.assertGreater(report["in_stock_groups"], 0)

        groups = report["groups"]
        
        # 10k 0805 should be IN_STOCK (needed 4, stock 100)
        g_10k = next(g for g in groups if g.category == "resistor" and g.value == "10k")
        self.assertEqual(g_10k.status, "IN_STOCK")
        self.assertEqual(g_10k.needed_qty, 4)
        self.assertGreaterEqual(g_10k.available_qty, 4)

        # 100nF 0805 should be IN_STOCK
        g_100n = next(g for g in groups if g.category == "capacitor" and g.value == "100nF")
        self.assertEqual(g_100n.status, "IN_STOCK")

        # 220k resistor R8 is not in our orders, so it MUST be MISSING
        g_220k = next(g for g in groups if g.category == "resistor" and g.value == "220k")
        self.assertEqual(g_220k.status, "MISSING")
        self.assertEqual(g_220k.available_qty, 0)

        # AMS1117-3.3 should be IN_STOCK
        g_ams = next(g for g in groups if "AMS1117" in g.value)
        self.assertEqual(g_ams.status, "IN_STOCK")


if __name__ == "__main__":
    unittest.main()
