from __future__ import annotations

import email
import hashlib
import os
import re
import time
from email import policy
from email.parser import BytesParser
from pathlib import Path

from app.db import (
    create_ingest_job,
    finish_ingest_job,
    get_mailbox_state,
    update_ingest_job,
    update_mailbox_state,
    insert_email,
    upsert_embedding,
)
from app.embedding import Embedder


FROM_SPLIT = re.compile(br"(?m)^From .*$")


def _decode_payload(msg: email.message.Message) -> str:
    if msg.is_multipart():
        parts = []
        for part in msg.walk():
            ctype = part.get_content_type()
            if ctype == "text/plain":
                payload = part.get_payload(decode=True) or b""
                charset = part.get_content_charset() or "utf-8"
                parts.append(payload.decode(charset, errors="replace"))
        return "\n".join(parts).strip()
    payload = msg.get_payload(decode=True)
    if payload is None:
        return (msg.get_payload() or "").strip()
    charset = msg.get_content_charset() or "utf-8"
    return payload.decode(charset, errors="replace").strip()


def _parse_mbox_chunk(raw_bytes: bytes, base_offset: int) -> list[dict]:
    matches = list(FROM_SPLIT.finditer(raw_bytes))
    starts = [0] if not raw_bytes.startswith(b"From ") else []
    starts.extend([m.start() for m in matches])
    starts = sorted(set(starts))
    if not starts:
        starts = [0]
    ends = starts[1:] + [len(raw_bytes)]

    out = []
    for idx, (s, e) in enumerate(zip(starts, ends)):
        blob = raw_bytes[s:e].strip()
        if not blob:
            continue
        if blob.startswith(b"From "):
            nl = blob.find(b"\n")
            blob = blob[nl + 1 :] if nl > -1 else b""
        if not blob:
            continue
        msg = BytesParser(policy=policy.default).parsebytes(blob)
        body = _decode_payload(msg)
        subject = str(msg.get("subject", "(no subject)"))
        sender = str(msg.get("from", "unknown"))
        dt = str(msg.get("date", ""))
        out.append(
            {
                "source_ref": f"offset:{base_offset + s}:{idx}",
                "subject": subject.strip() or "(no subject)",
                "sender": sender.strip() or "unknown",
                "date": dt.strip(),
                "body": body,
            }
        )
    return out


def _estimate_total_emails(new_bytes: bytes, sample_size: int = 10) -> tuple[int, float]:
    sample = _parse_mbox_chunk(new_bytes[: min(len(new_bytes), 256_000)], 0)
    if not sample:
        return 0, 0.0
    avg_bytes = max(1.0, min(len(new_bytes), 256_000) / len(sample))
    est_total = int(len(new_bytes) / avg_bytes)
    return max(est_total, len(sample)), avg_bytes


def ingest_source(conn, source_path: str, source_type: str = "mbox") -> int:
    job_id = create_ingest_job(conn, source_path, source_type)
    started = time.time()
    embedder = Embedder()
    try:
        state = get_mailbox_state(conn, source_path, source_type)
        offset = int(state["processed_offset"])
        prev_count = int(state["processed_emails"])

        p = Path(source_path)
        if not p.exists():
            raise FileNotFoundError(f"Source file not found: {source_path}")

        total_bytes = p.stat().st_size
        if total_bytes < offset:
            offset = 0

        with p.open("rb") as f:
            f.seek(offset)
            new_bytes = f.read()

        est_total_emails, _ = _estimate_total_emails(new_bytes)
        update_ingest_job(
            conn,
            job_id,
            total_bytes=total_bytes,
            processed_bytes=offset,
            total_emails_estimate=prev_count + est_total_emails,
            message="estimating",
        )

        parsed = (
            _parse_mbox_chunk(new_bytes, offset)
            if source_type == "mbox"
            else _parse_text_file(new_bytes, offset)
        )

        processed = 0
        for item in parsed:
            body = item["body"].strip()
            if not body:
                continue
            digest = hashlib.sha256(
                (item["subject"] + "\n" + item["sender"] + "\n" + body).encode("utf-8")
            ).hexdigest()
            email_id = insert_email(
                conn=conn,
                source_type=source_type,
                source_path=source_path,
                source_ref=item["source_ref"],
                subject=item["subject"],
                sender=item["sender"],
                date=item["date"],
                body=body,
                body_preview=body[:280],
                body_hash=digest,
            )
            if email_id is not None:
                vector = embedder.embed(
                    f"Subject: {item['subject']}\nFrom: {item['sender']}\nDate: {item['date']}\n{body}"
                )
                upsert_embedding(conn, email_id, vector)
                processed += 1

            elapsed = max(0.001, time.time() - started)
            throughput = processed / elapsed
            consumed = min(total_bytes, offset + len(new_bytes))
            done_est = prev_count + processed
            remaining = max(0, (prev_count + est_total_emails) - done_est)
            eta = remaining / throughput if throughput > 0 else 0.0
            update_ingest_job(
                conn,
                job_id,
                processed_emails=done_est,
                processed_bytes=consumed,
                throughput_eps=round(throughput, 3),
                eta_seconds=round(eta, 1),
                message="indexing",
            )

        new_offset = offset + len(new_bytes)
        update_mailbox_state(conn, source_path, new_offset, prev_count + processed)
        update_ingest_job(
            conn,
            job_id,
            processed_emails=prev_count + processed,
            processed_bytes=new_offset,
            throughput_eps=round(processed / max(0.001, time.time() - started), 3),
            eta_seconds=0.0,
            message="completed",
        )
        finish_ingest_job(conn, job_id, "completed", f"indexed {processed} new emails")
        return job_id
    except Exception as exc:
        finish_ingest_job(conn, job_id, "failed", str(exc))
        raise


def _parse_text_file(raw_bytes: bytes, base_offset: int) -> list[dict]:
    text = raw_bytes.decode("utf-8", errors="replace")
    if not text.strip():
        return []
    return [
        {
            "source_ref": f"offset:{base_offset}",
            "subject": "Text Email",
            "sender": "unknown",
            "date": "",
            "body": text,
        }
    ]
