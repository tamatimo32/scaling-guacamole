import unittest

from futures_trading.grids import parse_float_grid, parse_optional_float_grid


class GridParserTests(unittest.TestCase):
    def test_parses_comma_values_and_ranges(self):
        self.assertEqual(
            parse_float_grid("0.002,0.004:0.008:0.002"),
            [0.002, 0.004, 0.006, 0.008],
        )

    def test_optional_grid_accepts_none(self):
        self.assertEqual(parse_optional_float_grid("none"), [None])


if __name__ == "__main__":
    unittest.main()
