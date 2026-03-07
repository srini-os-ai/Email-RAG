from __future__ import annotations

import argparse

from app.config import settings
from app.db import connect, init_db
from app.ingest import ingest_source


def main() -> None:
    parser = argparse.ArgumentParser(description="Incrementally ingest mailbox into SQLite + vector index")
    parser.add_argument("--source", required=True, help="Path to .mbox or .txt file")
    parser.add_argument("--type", choices=["mbox", "text"], default="mbox")
    args = parser.parse_args()

    conn = connect(settings.db_path)
    init_db(conn)
    job_id = ingest_source(conn, args.source, args.type)
    print(f"Ingestion completed. job_id={job_id}")


if __name__ == "__main__":
    main()
