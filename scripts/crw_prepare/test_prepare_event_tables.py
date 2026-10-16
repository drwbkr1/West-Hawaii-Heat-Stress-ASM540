import unittest
from prepare_event_tables import prepare_row


def row(dhw, mask="0"):
    return ["2015-09-01T12:00:00Z", "18.875", "-156.125", "28.5", str(dhw), mask]


class DailyPreparationTests(unittest.TestCase):
    def test_inclusive_threshold_boundaries(self):
        for dhw, flags in [(0, [0, 0]), (3.99, [0, 0]), (4, [1, 0]),
                           (7.99, [1, 0]), (8, [1, 1]), (12, [1, 1])]:
            with self.subTest(dhw=dhw):
                converted = prepare_row(row(dhw), [4, 8])
                self.assertEqual(converted[7:], [1, *flags])

    def test_all_nonwater_masks_exclude_even_numeric_dhw(self):
        for mask in ["1", "2", "4", "NaN", "-5", "251"]:
            with self.subTest(mask=mask):
                self.assertEqual(prepare_row(row(12, mask), [4, 8])[6:], [None, 0, None, None])

    def test_missing_water_dhw_is_not_heat_free(self):
        for missing in ["NaN", "", "-327.68"]:
            self.assertEqual(prepare_row(row(missing), [4, 8])[6:], [None, 0, None, None])

    def test_zero_dhw_is_valid(self):
        self.assertEqual(prepare_row(row(0), [4, 8])[6:], [0.0, 1, 0, 0])

    def test_key_coordinate_order(self):
        self.assertEqual(prepare_row(row(4), [4, 8])[1], "18.875_-156.125")

    def test_thresholds_are_configured(self):
        self.assertEqual(prepare_row(row(6), [2, 6, 10])[8:], [1, 1, 0])

    def test_invalid_mask_and_time_rejected(self):
        with self.assertRaises(ValueError):
            prepare_row(row(4, "5"), [4, 8])
        modified = row(4)
        modified[0] = "2015-09-01T00:00:00Z"
        with self.assertRaises(ValueError):
            prepare_row(modified, [4, 8])

    def test_nonfinite_value_rejected(self):
        with self.assertRaises(ValueError):
            prepare_row(row("inf"), [4, 8])


if __name__ == "__main__":
    unittest.main()
