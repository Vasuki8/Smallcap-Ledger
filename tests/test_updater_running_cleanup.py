"""Updater lifecycle must never leave a kind stuck as running after DB failures."""
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tracker import db
from tracker.sync import Updater


class UpdaterRunningCleanupTests(unittest.TestCase):
    def test_job_setup_failure_clears_in_memory_running_state(self):
        updater=Updater()
        updater.running["benchmark"]={"detail":"Starting update","started_at":db.now()}
        with patch("tracker.sync.db.connect",side_effect=sqlite3.OperationalError("database is locked")), \
             patch("tracker.sync.traceback.print_exc"):
            updater.run("benchmark")
        self.assertEqual(updater.status(),{})

    def test_scheduler_survives_one_iteration_failure(self):
        updater=Updater()
        class StopAfterTwoTicks:
            def __init__(self):self.ticks=0
            def is_set(self):return self.ticks>=2
            def wait(self,_seconds):self.ticks+=1
        updater.stop=StopAfterTwoTicks()
        with patch.object(
            updater,"schedule_once",
            side_effect=[sqlite3.OperationalError("database is locked"),None],
        ) as once, patch("tracker.sync.traceback.print_exc"):
            updater.schedule()
        self.assertEqual(once.call_count,2)
        self.assertEqual(updater.stop.ticks,2)

    def test_final_status_write_failure_still_clears_running_state(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(db,"DATA",Path(tmp)):
            db.init()
            updater=Updater()
            updater.running["benchmark"]={"detail":"Starting update","started_at":db.now()}
            real_connect=db.connect
            calls=0

            def flaky_connect():
                nonlocal calls
                calls+=1
                if calls==2:
                    raise sqlite3.OperationalError("disk I/O error")
                return real_connect()

            with patch("tracker.sync.db.connect",side_effect=flaky_connect), \
                 patch("tracker.sync.providers.fetch_benchmark",return_value="benchmark ok"), \
                 patch("tracker.sync.traceback.print_exc"):
                updater.run("benchmark")

            self.assertEqual(updater.status(),{})
            row=db.one("SELECT status,finished_at FROM jobs WHERE kind='benchmark' ORDER BY id DESC LIMIT 1")
            self.assertEqual(row["status"],"running")
            self.assertIsNone(row["finished_at"])


if __name__=="__main__":
    unittest.main()
