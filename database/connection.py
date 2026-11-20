import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path

DEFAULT_PATH = Path(__file__).resolve().parent / "community.sqlite3"


@contextmanager
def connect(path=None):
    db = Path(path or os.environ.get("SENTO_DB_PATH", DEFAULT_PATH))
    db.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(db, timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys=ON")
    try:
        with connection:
            yield connection
    finally:
        connection.close()
