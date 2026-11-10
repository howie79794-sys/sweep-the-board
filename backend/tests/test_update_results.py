"""Offline regression tests: execute production functions with mocked I/O.

Load only the function AST to avoid application startup, credentials, and live
database/market-provider imports. The function bodies are not copied into tests.
"""
import ast
import json
import logging
import math
import unittest
from datetime import date, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]


def load_function(path, name, namespace):
    tree = ast.parse((ROOT / path).read_text())
    node = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == name)
    node.decorator_list = []  # external retry wrappers are irrelevant for offline unit tests
    exec(compile(ast.Module(body=[node], type_ignores=[]), str(ROOT / path), "exec"), namespace)
    return namespace[name]


class TaskOutcomeTests(unittest.TestCase):
    def setUp(self):
        self.tasks = {"test": {}}
        self.complete = load_function("api/routes.py", "complete_task", {"tasks": self.tasks})

    def outcome(self, flags, **extra):
        result = {"details": [{"result": {"success": flag}} for flag in flags], **extra}
        self.complete("test", result)
        return self.tasks["test"]["status"], result

    def test_all_success(self):
        status, result = self.outcome([True, True])
        self.assertEqual((status, result["success"], result["failed"]), ("success", 2, 0))

    def test_partial_failure(self):
        status, result = self.outcome([True, False])
        self.assertEqual((status, result["success"], result["failed"]), ("partial", 1, 1))

    def test_all_failed_and_empty_are_not_success(self):
        for flags in ([False, False], []):
            with self.subTest(flags=flags):
                self.assertEqual(self.outcome(flags)[0], "failed")

    def test_ranking_error_not_hidden(self):
        self.assertEqual(self.outcome([True], error="rankings failed")[0], "partial")

    def test_selected_assets_normalized(self):
        result = {"results": [{"asset_id": 1, "success": True}, {"asset_id": 2, "success": False}]}
        self.complete("test", result)
        self.assertEqual(self.tasks["test"]["status"], "partial")
        self.assertEqual((result["total"], result["success"], result["failed"]), (2, 1, 1))


class AssetFreshnessTests(unittest.TestCase):
    def setUp(self):
        self.today = date(2026, 11, 10)
        self.db = MagicMock()
        asset = SimpleNamespace(id=1, name="Test", code="SZ001280", asset_type="stock")
        history = SimpleNamespace(date=date(2026, 10, 30), close_price=100,
                                  pe_ratio=10, pb_ratio=1, market_cap=1000, eps_forecast=2)
        asset_query = MagicMock()
        asset_query.filter.return_value.first.return_value = asset
        market_query = MagicMock()
        market_query.filter.return_value.order_by.return_value.first.return_value = history
        market_query.filter.return_value.first.return_value = None
        self.db.query.side_effect = lambda model: asset_query if model is self.asset_model else market_query
        self.asset_model = MagicMock()
        self.provider = MagicMock()
        self.update = load_function("services/market_data.py", "update_asset_data", {
            "Session": object, "Dict": dict, "date": date, "timedelta": timedelta,
            "get_beijing_time": lambda: datetime(2026, 11, 10, 16),
            "BASELINE_DATE": self.today, "Asset": self.asset_model, "MarketData": MagicMock(),
            "is_trading_hours": lambda: False, "fetch_asset_data": self.provider,
            "json": json, "math": math, "traceback": MagicMock(), "print": MagicMock(),
        })

    def test_real_today_data_succeeds_after_commit(self):
        self.provider.return_value = [{"date": self.today.isoformat(), "close_price": 110}]
        result = self.update(1, self.db)
        self.assertTrue(result["success"])
        self.assertTrue(result["today_updated"])
        self.db.add.assert_called_once()
        self.db.commit.assert_called_once()
        self.assertIsNone(self.provider.call_args.kwargs["db"])

    def test_empty_response_does_not_copy_old_price_to_today(self):
        self.provider.return_value = []
        result = self.update(1, self.db)
        self.assertFalse(result["success"])
        self.assertFalse(result["today_updated"])
        self.db.add.assert_not_called()

    def test_old_external_record_is_not_today(self):
        self.provider.return_value = [{"date": "2026-10-30", "close_price": 100}]
        self.assertFalse(self.update(1, self.db)["success"])
        self.db.add.assert_not_called()

    def test_provider_exception_is_failure(self):
        self.provider.side_effect = RuntimeError("offline")
        self.assertFalse(self.update(1, self.db)["success"])
        self.db.add.assert_not_called()

    def test_commit_failure_is_failure(self):
        self.provider.return_value = [{"date": self.today, "close_price": 110}]
        self.db.commit.side_effect = RuntimeError("database unavailable")
        self.assertFalse(self.update(1, self.db)["success"])
        self.db.rollback.assert_called_once()

    def test_invalid_prices_are_not_success(self):
        for price in (None, 0, -1, float("nan"), float("inf")):
            with self.subTest(price=price):
                self.provider.return_value = [{"date": self.today, "close_price": price}]
                self.assertFalse(self.update(1, self.db)["success"])
        self.db.add.assert_not_called()


class ScheduledExitTests(unittest.TestCase):
    def test_exit_status_reflects_partial_and_total_failures(self):
        for total, success, failed, expected in [(2, 2, 0, 0), (2, 1, 1, 1), (2, 0, 2, 1), (0, 0, 0, 1)]:
            with self.subTest(total=total, success=success):
                db = MagicMock()
                main = load_function("scripts/update_scheduled.py", "main", {
                    "SessionLocal": lambda: db,
                    "update_all_assets_data": lambda *a, **kw: {
                        "total": total, "success": success, "failed": failed, "details": []},
                    "save_rankings": MagicMock(), "date": date, "json": json,
                    "logger": MagicMock(spec=logging.Logger),
                })
                self.assertEqual(main(), expected)
                db.close.assert_called_once()


class ProviderDateTests(unittest.TestCase):
    def test_futures_uses_supported_signature_and_filters_dates(self):
        ak = MagicMock()
        ak.futures_zh_daily_sina.return_value = pd.DataFrame({
            "date": ["2026-10-30", "2026-11-10"], "close": [100, 110]})
        fetch = load_function("services/market_data.py", "_ak_futures_zh_daily_sina", {"ak": ak, "pd": pd})
        result = fetch("IF0", "20261110", "20261110")
        ak.futures_zh_daily_sina.assert_called_once_with(symbol="IF0")
        self.assertEqual(result["date"].tolist(), ["2026-11-10"])

    def test_futures_continuous_symbol(self):
        from typing import Optional
        resolve = load_function("services/market_data.py", "resolve_futures_main_contract", {
            "Optional": Optional, "AKSHARE_AVAILABLE": True, "print": MagicMock()})
        for code in ("IF", "IF0", "CF.IF0", "IF=F"):
            self.assertEqual(resolve(code), "IF0")

    def test_realtime_preserves_provider_date(self):
        from typing import Optional
        ticker = MagicMock()
        fetch = load_function("services/market_data.py", "fetch_realtime_price_yfinance", {
            "Optional": Optional, "pd": pd, "YFINANCE_AVAILABLE": True,
            "yf": SimpleNamespace(Ticker=lambda code: ticker),
            "convert_to_yfinance_symbol": lambda code: code,
            "_yf_ticker_history": lambda *a, **kw: pd.DataFrame({"Close": [100]},
                index=pd.DatetimeIndex(["2026-10-30"], name="Date")),
            "print": MagicMock(),
        })
        self.assertEqual(fetch("TEST")["date"].tolist(), ["2026-10-30"])


if __name__ == "__main__":
    unittest.main()
