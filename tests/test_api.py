#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HADRON-55 — Flask API test suite
Run: py tests/test_api.py

Атакует /filter как QA: плохие форматы, пустые запросы, инъекции в имя файла,
одновременные запросы, несуществующие эндпоинты, утечка temp-файлов.
Импортирует реальный Flask app из bot.py (aiogram мокируется).
"""

import io
import os
import sys
import glob
import tempfile
import threading
import unittest
from unittest.mock import MagicMock

# ── Mock aiogram до импорта bot.py ──────────────────────────────────────────
for _mod in [
    "aiogram", "aiogram.types", "aiogram.filters",
    "aiogram.filters.command",
]:
    sys.modules[_mod] = MagicMock()

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import bot  # noqa: E402  (после моков)

app = bot.app
app.config["TESTING"] = True

# ── Хелперы ─────────────────────────────────────────────────────────────────

TARGET_LABELS = bot.TARGET_LABELS
GOOD_NUMS = "100 200 150 300 250 180 220 170 190 210"
SH_GOOD = "scinti : high sensitivity : 50 80 90 100 120 30 40 60 70 110"
SM_GOOD = "scinti : midi sensitivity : 10 20 15 25 30 12 18 22 14 16"


def make_dat(n: int = 1) -> bytes:
    event = (
        "|EVENT: 2101011200\n"
        f"{SH_GOOD}\n{SM_GOOD}\n"
        + "".join(f"{lbl} {GOOD_NUMS}\n" for lbl in TARGET_LABELS)
        + "#\n"
    )
    return (event * n).encode("utf-8")


def post_dat(client, data: bytes, filename: str = "test.dat"):
    return client.post(
        "/filter",
        data={"file": (io.BytesIO(data), filename)},
        content_type="multipart/form-data",
    )


# ── Тесты ───────────────────────────────────────────────────────────────────

class TestHealth(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_health_ok(self):
        r = self.client.get("/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.get_json()["status"], "ok")

    def test_nonexistent_endpoint(self):
        self.assertEqual(self.client.get("/nonexistent").status_code, 404)

    def test_nonexistent_post(self):
        self.assertEqual(self.client.post("/nonexistent").status_code, 404)


class TestFilterBadRequests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_no_file_in_request(self):
        r = self.client.post("/filter", data={}, content_type="multipart/form-data")
        self.assertEqual(r.status_code, 400)
        self.assertIn("error", r.get_json())

    def test_empty_body(self):
        r = self.client.post("/filter", data=b"", content_type="application/octet-stream")
        self.assertEqual(r.status_code, 400)

    def test_wrong_extension_txt(self):
        r = post_dat(self.client, b"some content", filename="data.txt")
        self.assertEqual(r.status_code, 400)

    def test_wrong_extension_csv(self):
        r = post_dat(self.client, b"a,b,c", filename="data.csv")
        self.assertEqual(r.status_code, 400)

    def test_wrong_extension_no_ext(self):
        r = post_dat(self.client, b"content", filename="datafile")
        self.assertEqual(r.status_code, 400)

    def test_wrong_method_get(self):
        self.assertEqual(self.client.get("/filter").status_code, 405)

    def test_wrong_method_delete(self):
        self.assertEqual(self.client.delete("/filter").status_code, 405)

    def test_wrong_method_put(self):
        self.assertEqual(self.client.put("/filter").status_code, 405)


class TestFilterValidRequests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_valid_dat_returns_200(self):
        r = post_dat(self.client, make_dat(1))
        self.assertEqual(r.status_code, 200)

    def test_response_headers_present(self):
        r = post_dat(self.client, make_dat(3))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.headers["X-Total-Events"], "3")
        self.assertEqual(r.headers["X-Kept-Events"], "3")
        self.assertEqual(r.headers["X-Dropped-Events"], "0")

    def test_cors_header_present(self):
        r = post_dat(self.client, make_dat(1))
        self.assertEqual(r.headers.get("Access-Control-Allow-Origin"), "*")

    def test_empty_dat_file(self):
        r = post_dat(self.client, b"")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.headers["X-Total-Events"], "0")
        self.assertEqual(r.headers["X-Kept-Events"], "0")

    def test_whitespace_only_dat(self):
        r = post_dat(self.client, b"   \n\n   \n")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.headers["X-Kept-Events"], "0")

    def test_binary_garbage_in_dat(self):
        garbage = bytes(range(256)) * 100
        r = post_dat(self.client, garbage)
        self.assertEqual(r.status_code, 200)

    def test_all_calibration_events_dropped(self):
        calibr = b"|EVENT: 2101011200\ncalibration run 000\n#\n" * 5
        r = post_dat(self.client, calibr)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.headers["X-Kept-Events"], "0")
        self.assertEqual(r.headers["X-Total-Events"], "5")

    def test_options_preflight(self):
        r = self.client.options("/filter")
        self.assertEqual(r.status_code, 200)

    def test_stress_500_events(self):
        r = post_dat(self.client, make_dat(500))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.headers["X-Kept-Events"], "500")


class TestFilenameSanitization(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_path_traversal_in_filename(self):
        # os.path.basename() срезает ../ — в disposition не должно быть слешей и ..
        r = post_dat(self.client, make_dat(1), filename="../../etc/passwd.dat")
        self.assertEqual(r.status_code, 200)
        disposition = r.headers.get("Content-Disposition", "")
        self.assertNotIn("..", disposition)
        self.assertNotIn("/", disposition)
        self.assertIn("passwd.dat", disposition)

    def test_newline_injection_in_filename(self):
        # werkzeug обрезает filename на \r → итоговое имя не оканчивается на .dat → 400
        # либо имя нормальное → 200 без инжекции — оба варианта приемлемы
        r = post_dat(self.client, make_dat(1), filename="evil\r\nX-Evil: injected.dat")
        self.assertNotIn("X-Evil", str(r.headers))

    def test_spaces_in_filename(self):
        r = post_dat(self.client, make_dat(1), filename="my data file.dat")
        self.assertEqual(r.status_code, 200)

    def test_unicode_filename(self):
        r = post_dat(self.client, make_dat(1), filename="данные.dat")
        self.assertEqual(r.status_code, 200)

    def test_no_temp_files_created(self):
        # Flask endpoint теперь возвращает Response напрямую — temp файлы не создаются
        tmp_dir = tempfile.gettempdir()
        before = set(glob.glob(os.path.join(tmp_dir, "filtered_*.dat")))
        for _ in range(5):
            post_dat(self.client, make_dat(2))
        after = set(glob.glob(os.path.join(tmp_dir, "filtered_*.dat")))
        self.assertEqual(after - before, set(), "Flask endpoint создал temp-файлы")


class TestConcurrentRequests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_concurrent_10_requests(self):
        results = []
        errors = []

        def worker():
            try:
                r = post_dat(self.client, make_dat(5))
                results.append(r.status_code)
            except Exception as e:
                errors.append(str(e))

        threads = [threading.Thread(target=worker) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(errors, [], f"Ошибки в потоках: {errors}")
        self.assertTrue(all(s == 200 for s in results),
                        f"Не все ответы 200: {results}")


# ── Запуск ───────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    unittest.main(verbosity=2)
