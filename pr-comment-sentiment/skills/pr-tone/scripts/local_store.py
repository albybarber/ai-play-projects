"""Private, transactional cache and process locks for local pr-tone evidence."""

from __future__ import annotations

import json
import os
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterator


@dataclass(frozen=True)
class Cached:
    data: dict
    fetched_at: str


class RunBusy(RuntimeError):
    pass


class Store:
    def __init__(self, home: Path) -> None:
        path = home / "cache.sqlite3"
        fd = os.open(path, os.O_CREAT | os.O_RDWR, 0o600)
        os.close(fd)
        path.chmod(0o600)
        self.db = sqlite3.connect(path, timeout=30)
        self.db.execute(
            "CREATE TABLE IF NOT EXISTS cache ("
            "kind TEXT NOT NULL, key TEXT NOT NULL, data TEXT NOT NULL, fetched_at TEXT NOT NULL,"
            "PRIMARY KEY (kind, key))"
        )
        self.db.commit()

    def get(self, kind: str, key: str, max_age_hours: int | None = None) -> Cached | None:
        row = self.db.execute(
            "SELECT data, fetched_at FROM cache WHERE kind = ? AND key = ?", (kind, key)
        ).fetchone()
        if row is None:
            return None
        if max_age_hours is not None:
            age = datetime.now(timezone.utc) - datetime.fromisoformat(row[1])
            if age < timedelta(0) or age >= timedelta(hours=max_age_hours):
                return None
        return Cached(json.loads(row[0]), row[1])

    def put(self, kind: str, key: str, data: dict, fetched_at: str | None = None) -> str:
        stamp = fetched_at or datetime.now(timezone.utc).isoformat(timespec="seconds")
        with self.db:
            self.db.execute(
                "INSERT INTO cache VALUES (?, ?, ?, ?) ON CONFLICT(kind, key) DO UPDATE SET "
                "data = excluded.data, fetched_at = excluded.fetched_at",
                (kind, key, json.dumps(data), stamp),
            )
        return stamp

    def close(self) -> None:
        self.db.close()


@contextmanager
def run_lock(directory: Path) -> Iterator[None]:
    """OS locks release on interruption; a leftover lock file never blocks a resume."""
    fd = os.open(directory / ".lock", os.O_CREAT | os.O_RDWR, 0o600)
    try:
        os.chmod(directory / ".lock", 0o600)
        if os.name == "nt":
            import msvcrt

            if os.fstat(fd).st_size == 0:
                os.write(fd, b"\0")
            os.lseek(fd, 0, os.SEEK_SET)
            try:
                msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
            except OSError as exc:
                raise RunBusy(f"run {directory.name} is already being written") from exc
        else:
            import fcntl

            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as exc:
                raise RunBusy(f"run {directory.name} is already being written") from exc
        yield
    finally:
        os.close(fd)
