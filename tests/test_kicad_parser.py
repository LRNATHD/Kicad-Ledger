"""Unit tests for KiCad board parser."""

import os
import unittest
from stockcheck.kicad_parser import KiCadParser


class TestKiCadParser(unittest.TestCase):

    def setUp(self):
        self.base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.board_file = os.path.join(self.base_dir, "examples", "sample_board", "demo_board.kicad_pcb")

    def test_parse_demo_board(self):
        items = KiCadParser.parse_file(self.board_file)
        self.assertGreater(len(items), 10)

        # Check references are extracted
        refs = {i.reference for i in items}
        self.assertIn("R1", refs)
        self.assertIn("R2", refs)
        self.assertIn("C1", refs)
        self.assertIn("U1", refs)
        self.assertIn("U2", refs)
        self.assertIn("D1", refs)

        # Check package normalization on board
        r1 = next(i for i in items if i.reference == "R1")
        self.assertEqual(r1.value, "10k")
        self.assertEqual(r1.package, "0805")
        self.assertEqual(r1.category, "resistor")

        u1 = next(i for i in items if i.reference == "U1")
        self.assertEqual(u1.value, "STM32F401CEU6")
        self.assertEqual(u1.category, "ic")


if __name__ == "__main__":
    unittest.main()
