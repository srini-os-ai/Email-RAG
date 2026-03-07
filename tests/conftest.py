from __future__ import annotations

import os
from pathlib import Path

import pytest

from app.db import connect, init_db


@pytest.fixture()
def temp_db(tmp_path):
    db_path = tmp_path / "test.db"
    conn = connect(str(db_path))
    init_db(conn)
    return conn


@pytest.fixture()
def sample_mbox(tmp_path: Path) -> Path:
    path = tmp_path / "emails.mbox"
    path.write_text(
        """From a@example.com Sat Jan  1 00:00:00 2026
Subject: Budget planning
From: A <a@example.com>
Date: Sat, 01 Jan 2026 09:00:00 -0500

Budget is approved for Q1 hiring plan.

From b@example.com Sat Jan  2 00:00:00 2026
Subject: Hiring update
From: B <b@example.com>
Date: Sun, 02 Jan 2026 10:00:00 -0500

We hired two engineers for the platform team.
""",
        encoding="utf-8",
    )
    return path
