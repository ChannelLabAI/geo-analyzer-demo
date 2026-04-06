"""Tests for brand-score job endpoints in serve.py.

Uses the internal helpers directly (no real subprocess — mocked).
"""

from __future__ import annotations

import json
import sys
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add parent dir so we can import serve.py internals
sys.path.insert(0, str(Path(__file__).parent.parent))

import serve


class TestJobStore(unittest.TestCase):
    """Tests for _JOBS dict operations: create, read, expiry, thread safety."""

    def setUp(self):
        with serve._JOBS_LOCK:
            serve._JOBS.clear()

    def tearDown(self):
        with serve._JOBS_LOCK:
            serve._JOBS.clear()

    def test_create_job_returns_id(self):
        """POST brand-score creates a job and returns a 16-char hex ID."""
        with patch("serve._run_brand_score_job"):  # don't actually run subprocess
            job_id = serve._create_brand_score_job("https://example.com", "TestBrand")
        self.assertEqual(len(job_id), 16)
        self.assertRegex(job_id, r"^[a-f0-9]{16}$")

    def test_create_job_initial_state(self):
        """Newly created job starts in pending state."""
        with patch("threading.Thread") as mock_thread:
            mock_thread.return_value = MagicMock()
            job_id = serve._create_brand_score_job("https://example.com", "TestBrand")
        with serve._JOBS_LOCK:
            job = serve._JOBS[job_id]
        self.assertEqual(job["status"], "pending")
        self.assertEqual(job["progress"], 0)
        self.assertIsNone(job["result"])
        self.assertIsNone(job["error"])
        self.assertEqual(job["estimated_total"], 45.0)

    def test_create_job_spawns_thread(self):
        """_create_brand_score_job spawns exactly one daemon thread."""
        spawned = []
        original_thread = threading.Thread

        def capture_thread(*args, **kwargs):
            t = original_thread(*args, **kwargs)
            spawned.append(t)
            return t

        with patch("serve.threading.Thread", side_effect=capture_thread):
            with patch("serve._run_brand_score_job"):
                serve._create_brand_score_job("https://example.com", "TestBrand")

        self.assertEqual(len(spawned), 1)
        self.assertTrue(spawned[0].daemon)

    def test_job_not_found_returns_none(self):
        """Non-existent job_id returns None from _JOBS dict."""
        with serve._JOBS_LOCK:
            result = serve._JOBS.get("nonexistent_id")
        self.assertIsNone(result)

    def test_job_ttl_cleanup(self):
        """_cleanup_expired_jobs removes entries older than TTL."""
        old_job_id = "abcdef1234567890"
        recent_job_id = "fedcba0987654321"
        now = time.time()
        with serve._JOBS_LOCK:
            serve._JOBS[old_job_id] = {
                "status": "done", "progress": 100, "result": {}, "error": None,
                "created_at": now - serve._JOB_TTL - 1,  # expired
                "estimated_total": 45.0,
            }
            serve._JOBS[recent_job_id] = {
                "status": "done", "progress": 100, "result": {}, "error": None,
                "created_at": now - 60,  # 1 minute old, within TTL
                "estimated_total": 45.0,
            }

        cutoff = time.time() - serve._JOB_TTL
        with serve._JOBS_LOCK:
            expired = [jid for jid, j in serve._JOBS.items() if j["created_at"] < cutoff]
            for jid in expired:
                del serve._JOBS[jid]

        with serve._JOBS_LOCK:
            self.assertNotIn(old_job_id, serve._JOBS)
            self.assertIn(recent_job_id, serve._JOBS)

    def test_concurrent_creates_thread_safe(self):
        """Multiple concurrent _create_brand_score_job calls produce unique IDs."""
        ids = []
        errors = []

        def create_one():
            try:
                with patch("threading.Thread") as mock_t:
                    mock_t.return_value = MagicMock()
                    jid = serve._create_brand_score_job("https://example.com", "Brand")
                    ids.append(jid)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=create_one) for _ in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(len(errors), 0)
        self.assertEqual(len(ids), 20)
        self.assertEqual(len(set(ids)), 20)  # all unique


class TestRunBrandScoreJob(unittest.TestCase):
    """Tests for _run_brand_score_job thread target."""

    def setUp(self):
        with serve._JOBS_LOCK:
            serve._JOBS.clear()

    def tearDown(self):
        with serve._JOBS_LOCK:
            serve._JOBS.clear()

    def _seed_job(self, job_id: str):
        with serve._JOBS_LOCK:
            serve._JOBS[job_id] = {
                "status": "pending", "progress": 0, "result": None, "error": None,
                "created_at": time.time(), "estimated_total": 45.0,
            }

    def test_successful_run_sets_done(self):
        """Successful subprocess sets status=done and stores result."""
        job_id = "aabb1122ccdd3344"
        self._seed_job(job_id)
        mock_result = {"brand": "TestBrand", "overall_score": 72.0, "grade": "B"}

        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = json.dumps(mock_result)
        mock_proc.stderr = ""

        with patch("serve.subprocess.run", return_value=mock_proc):
            serve._run_brand_score_job(job_id, "https://example.com", "TestBrand")

        with serve._JOBS_LOCK:
            job = serve._JOBS[job_id]
        self.assertEqual(job["status"], "done")
        self.assertEqual(job["progress"], 100)
        self.assertEqual(job["result"], mock_result)
        self.assertIsNone(job["error"])

    def test_subprocess_failure_sets_error(self):
        """Non-zero returncode sets status=error with stderr message."""
        job_id = "1122334455667788"
        self._seed_job(job_id)

        mock_proc = MagicMock()
        mock_proc.returncode = 1
        mock_proc.stdout = ""
        mock_proc.stderr = "ImportError: No module named geo"

        with patch("serve.subprocess.run", return_value=mock_proc):
            serve._run_brand_score_job(job_id, "https://example.com", "TestBrand")

        with serve._JOBS_LOCK:
            job = serve._JOBS[job_id]
        self.assertEqual(job["status"], "error")
        self.assertIn("ImportError", job["error"])

    def test_timeout_sets_error(self):
        """subprocess.TimeoutExpired sets status=error with timeout message."""
        job_id = "aabbccdd11223344"
        self._seed_job(job_id)

        with patch("serve.subprocess.run", side_effect=serve.subprocess.TimeoutExpired("cmd", 180)):
            serve._run_brand_score_job(job_id, "https://example.com", "TestBrand")

        with serve._JOBS_LOCK:
            job = serve._JOBS[job_id]
        self.assertEqual(job["status"], "error")
        self.assertIn("180", job["error"])

    def test_invalid_json_sets_error(self):
        """Invalid stdout JSON sets status=error."""
        job_id = "deadbeefcafebabe"
        self._seed_job(job_id)

        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = "not json {{{"
        mock_proc.stderr = ""

        with patch("serve.subprocess.run", return_value=mock_proc):
            serve._run_brand_score_job(job_id, "https://example.com", "TestBrand")

        with serve._JOBS_LOCK:
            job = serve._JOBS[job_id]
        self.assertEqual(job["status"], "error")

    def test_running_status_set_at_start(self):
        """Job transitions from pending → running before subprocess starts."""
        job_id = "1234567890abcdef"
        self._seed_job(job_id)

        statuses_seen = []

        def slow_subprocess(*args, **kwargs):
            with serve._JOBS_LOCK:
                statuses_seen.append(serve._JOBS[job_id]["status"])
            mock_proc = MagicMock()
            mock_proc.returncode = 0
            mock_proc.stdout = json.dumps({"brand": "X"})
            mock_proc.stderr = ""
            return mock_proc

        with patch("serve.subprocess.run", side_effect=slow_subprocess):
            serve._run_brand_score_job(job_id, "https://example.com", "TestBrand")

        self.assertIn("running", statuses_seen)


class TestBrandGEOScoreModels(unittest.TestCase):
    """Tests for BrandGEOScore.to_dict() serialization."""

    def test_to_dict_all_fields(self):
        """BrandGEOScore.to_dict() includes all required fields for the API."""
        sys.path.insert(0, str(Path(__file__).parent.parent.parent / "geo-analyzer"))
        from geo.models import BrandGEOScore, WebsiteScore, ActionItem, DataConfidence

        ws = WebsiteScore(
            url="https://example.com",
            technical_score=70.0,
            content_score=65.0,
            authority_score=50.0,
            overall_score=62.5,
        )
        ai = ActionItem(
            title="建立 llms.txt",
            description="加 llms.txt",
            estimated_score_gain=8.0,
            difficulty="easy",
            estimated_hours="< 1h",
        )
        score = BrandGEOScore(
            brand="TestBrand",
            url="https://example.com",
            website=ws,
            overall_score=62.5,
            grade="C",
            data_confidence=DataConfidence.MEDIUM,
            action_items=[ai],
        )
        d = score.to_dict()

        # Top-level required fields
        for key in ("brand", "url", "overall_score", "grade", "grade_label",
                    "data_confidence", "action_items", "generated_at", "website"):
            self.assertIn(key, d)

        # Enum serialized as string
        self.assertEqual(d["data_confidence"], "medium")

        # Datetime serialized as ISO string
        self.assertIsInstance(d["generated_at"], str)
        self.assertTrue(d["generated_at"].endswith("Z"))

        # Nested website dict
        ws_d = d["website"]
        for key in ("url", "technical_score", "content_score", "authority_score", "overall_score"):
            self.assertIn(key, ws_d)

        # Action items list
        self.assertEqual(len(d["action_items"]), 1)
        ai_d = d["action_items"][0]
        for key in ("title", "description", "estimated_score_gain", "difficulty",
                    "estimated_hours", "category"):
            self.assertIn(key, ai_d)

    def test_to_dict_json_serializable(self):
        """BrandGEOScore.to_dict() can be passed to json.dumps without error."""
        sys.path.insert(0, str(Path(__file__).parent.parent.parent / "geo-analyzer"))
        from geo.models import BrandGEOScore, WebsiteScore, DataConfidence

        ws = WebsiteScore(url="https://example.com")
        score = BrandGEOScore(
            brand="X", url="https://example.com", website=ws,
            overall_score=50.0, grade="C", data_confidence=DataConfidence.LOW,
        )
        # Should not raise
        serialized = json.dumps(score.to_dict(), ensure_ascii=False)
        self.assertIsInstance(serialized, str)


if __name__ == "__main__":
    unittest.main()
