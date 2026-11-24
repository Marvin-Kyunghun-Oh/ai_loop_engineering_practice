import csv
import os
import tempfile
import unittest

from src.presets import load_presets, save_presets


class PresetsTestCase(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmpdir.cleanup)
        self.path = os.path.join(self._tmpdir.name, "presets.csv")


class SaveThenLoadTests(PresetsTestCase):
    def test_save_then_load_returns_same_values(self):
        save_presets(self.path, {"집중": "25m", "휴식": "5m", "긴휴식": "1h30m"})
        self.assertEqual(
            load_presets(self.path),
            {"집중": 1500, "휴식": 300, "긴휴식": 5400},
        )


class InvalidValueTests(PresetsTestCase):
    def test_invalid_value_raises_value_error(self):
        with self.assertRaises(ValueError):
            save_presets(self.path, {"집중": "25m", "잘못": "abc"})

    def test_invalid_value_does_not_create_file(self):
        with self.assertRaises(ValueError):
            save_presets(self.path, {"잘못": "abc"})
        self.assertFalse(os.path.exists(self.path))

    def test_invalid_value_does_not_change_existing_file(self):
        save_presets(self.path, {"집중": "25m"})
        with open(self.path, "rb") as f:
            before = f.read()
        with self.assertRaises(ValueError):
            save_presets(self.path, {"새것": "25m", "잘못": "abc"})
        with open(self.path, "rb") as f:
            after = f.read()
        self.assertEqual(before, after)


class MissingFileTests(PresetsTestCase):
    def test_missing_file_returns_empty_dict(self):
        self.assertFalse(os.path.exists(self.path))
        self.assertEqual(load_presets(self.path), {})


class DuplicateNameTests(PresetsTestCase):
    def test_duplicate_name_in_file_raises_value_error(self):
        with open(self.path, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["name", "duration"])
            writer.writerow(["집중", "25m"])
            writer.writerow(["집중", "10m"])
        with self.assertRaises(ValueError):
            load_presets(self.path)


class MalformedCsvTests(PresetsTestCase):
    def _write_rows(self, rows):
        with open(self.path, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f)
            for row in rows:
                writer.writerow(row)

    def test_missing_duration_column_raises_value_error(self):
        self._write_rows([["name", "length"], ["집중", "25m"]])
        with self.assertRaises(ValueError) as ctx:
            load_presets(self.path)
        self.assertIn("duration", str(ctx.exception))

    def test_missing_name_column_raises_value_error(self):
        self._write_rows([["title", "duration"], ["집중", "25m"]])
        with self.assertRaises(ValueError) as ctx:
            load_presets(self.path)
        self.assertIn("name", str(ctx.exception))

    def test_empty_duration_value_raises_value_error_with_row(self):
        self._write_rows([["name", "duration"], ["집중", "25m"], ["휴식", ""]])
        with self.assertRaises(ValueError) as ctx:
            load_presets(self.path)
        self.assertIn("3", str(ctx.exception))

    def test_empty_name_raises_value_error(self):
        self._write_rows([["name", "duration"], ["", "25m"]])
        with self.assertRaises(ValueError):
            load_presets(self.path)

    def test_short_row_raises_value_error_not_key_error(self):
        self._write_rows([["name", "duration"], ["집중"]])
        with self.assertRaises(ValueError):
            load_presets(self.path)


if __name__ == "__main__":
    unittest.main()
