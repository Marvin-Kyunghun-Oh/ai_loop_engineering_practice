import unittest

from src.durations import format_duration, parse_duration, total_minutes


class ParseDurationNormalTests(unittest.TestCase):
    def test_hours_and_minutes(self):
        self.assertEqual(parse_duration("1h30m"), 5400)

    def test_seconds_only(self):
        self.assertEqual(parse_duration("90s"), 90)

    def test_hours_only(self):
        self.assertEqual(parse_duration("2h"), 7200)

    def test_surrounding_whitespace_is_stripped(self):
        self.assertEqual(parse_duration(" 45m "), 2700)

    def test_surrounding_whitespace_around_hour_is_stripped(self):
        self.assertEqual(parse_duration(" 1h "), 3600)

    def test_hours_minutes_seconds(self):
        self.assertEqual(parse_duration("1h1m1s"), 3661)

    def test_minutes_only(self):
        self.assertEqual(parse_duration("10m"), 600)

    def test_hours_and_seconds_skipping_minutes(self):
        self.assertEqual(parse_duration("2h5s"), 7205)


class ParseDurationErrorTests(unittest.TestCase):
    def _assert_rejects(self, text):
        with self.assertRaises(ValueError) as ctx:
            parse_duration(text)
        self.assertIn(repr(text), str(ctx.exception))

    def test_empty_string_raises(self):
        self._assert_rejects("")

    def test_whitespace_only_raises(self):
        self._assert_rejects("  ")

    def test_negative_value_raises(self):
        self._assert_rejects("-5m")

    def test_duplicate_unit_raises(self):
        self._assert_rejects("1h1h")

    def test_units_out_of_order_raises(self):
        self._assert_rejects("30m1h")

    def test_number_without_unit_raises(self):
        self._assert_rejects("90")

    def test_unknown_unit_raises(self):
        self._assert_rejects("5d")

    def test_uppercase_unit_raises(self):
        self._assert_rejects("1H")

    def test_internal_whitespace_raises(self):
        self._assert_rejects("1h 30m")


class TotalMinutesTests(unittest.TestCase):
    def test_hours_and_minutes(self):
        self.assertEqual(total_minutes("1h30m"), 90)

    def test_seconds_under_one_minute_is_zero(self):
        self.assertEqual(total_minutes("59s"), 0)

    def test_truncates_remaining_seconds(self):
        self.assertEqual(total_minutes("1h1m1s"), 61)

    def test_minutes_only(self):
        self.assertEqual(total_minutes("25m"), 25)

    def test_invalid_input_propagates_value_error(self):
        with self.assertRaises(ValueError) as ctx:
            total_minutes("5d")
        self.assertIn(repr("5d"), str(ctx.exception))


class FormatDurationTests(unittest.TestCase):
    def test_zero_is_zero_seconds(self):
        self.assertEqual(format_duration(0), "0s")

    def test_sixty_seconds_is_one_minute(self):
        self.assertEqual(format_duration(60), "1m")

    def test_one_hour(self):
        self.assertEqual(format_duration(3600), "1h")

    def test_hours_and_minutes(self):
        self.assertEqual(format_duration(5400), "1h30m")

    def test_hours_minutes_seconds(self):
        self.assertEqual(format_duration(3661), "1h1m1s")

    def test_round_trip_values(self):
        for n in (0, 59, 60, 3600, 5400, 86399):
            with self.subTest(n=n):
                self.assertEqual(parse_duration(format_duration(n)), n)

    def test_negative_value_raises(self):
        with self.assertRaises(ValueError) as ctx:
            format_duration(-1)
        self.assertIn(repr(-1), str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
