"""
Unit tests for file_utils.py (atomic JSON writes).
"""

import os
import json
import sys
import tempfile
import unittest

tests_dir = os.path.dirname(os.path.abspath(__file__))
if tests_dir not in sys.path:
    sys.path.insert(0, tests_dir)

import helpers  # noqa: F401 - ensures code/ is on sys.path
from common.file_utils import atomic_write_json, atomic_write_text


class FileUtilsTests(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="news_agg_test_file_utils_")

    def tearDown(self):
        import shutil
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_atomic_write_json_creates_valid_file(self):
        target = os.path.join(self.test_dir, "data.json")
        data = {"hello": "world", "items": [1, 2, 3]}

        atomic_write_json(target, data)

        self.assertTrue(os.path.exists(target))
        with open(target, "r", encoding="utf-8") as f:
            content = f.read()
            loaded = json.loads(content)

        self.assertEqual(loaded, data)
        self.assertTrue(content.endswith("\n"))

    def test_atomic_write_json_creates_parent_directories(self):
        target = os.path.join(self.test_dir, "sub", "dir", "nested.json")
        data = {"nested": True}

        atomic_write_json(target, data)

        self.assertTrue(os.path.exists(target))
        with open(target, "r", encoding="utf-8") as f:
            self.assertEqual(json.load(f), data)

    def test_atomic_write_json_overwrites_cleanly(self):
        target = os.path.join(self.test_dir, "data.json")
        data_v1 = {"version": 1}
        data_v2 = {"version": 2, "updated": True}

        atomic_write_json(target, data_v1)
        with open(target, "r", encoding="utf-8") as f:
            self.assertEqual(json.load(f), data_v1)

        atomic_write_json(target, data_v2)
        with open(target, "r", encoding="utf-8") as f:
            self.assertEqual(json.load(f), data_v2)

        # Ensure no lingering temp files
        files = os.listdir(self.test_dir)
        self.assertEqual(files, ["data.json"])

    def test_atomic_write_json_preserves_target_on_failure(self):
        target = os.path.join(self.test_dir, "data.json")
        data_original = {"safe": "content"}
        atomic_write_json(target, data_original)

        # Attempt to write non-serializable object (e.g. a set)
        with self.assertRaises(TypeError):
            atomic_write_json(target, {"invalid": {1, 2, 3}})

        # Target file content must be completely untouched
        with open(target, "r", encoding="utf-8") as f:
            self.assertEqual(json.load(f), data_original)

        # No temporary files left behind
        files = os.listdir(self.test_dir)
        self.assertEqual(files, ["data.json"])

    def test_atomic_write_text_creates_valid_file(self):
        target = os.path.join(self.test_dir, "output.html")
        html = "<html><body>Hello World</body></html>"

        atomic_write_text(target, html)

        self.assertTrue(os.path.exists(target))
        with open(target, "r", encoding="utf-8") as f:
            self.assertEqual(f.read(), html)

    def test_atomic_write_text_overwrites_existing(self):
        target = os.path.join(self.test_dir, "output.html")
        atomic_write_text(target, "<h1>Version 1</h1>")
        atomic_write_text(target, "<h1>Version 2</h1>")

        with open(target, "r", encoding="utf-8") as f:
            self.assertEqual(f.read(), "<h1>Version 2</h1>")

        files = os.listdir(self.test_dir)
        self.assertEqual(files, ["output.html"])


if __name__ == "__main__":
    unittest.main()
