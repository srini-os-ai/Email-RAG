from __future__ import annotations

import time

import requests
import streamlit as st


API_BASE = st.sidebar.text_input("API Base URL", value="http://127.0.0.1:8000")
page = st.sidebar.radio("Page", ["Ingest", "Search", "Ask"])

st.title("Email RAG MVP")


def render_confidence(value: float) -> None:
    st.progress(int(max(0.0, min(1.0, value)) * 100), text=f"Confidence: {value:.2f}")


def show_results(data: dict) -> None:
    st.subheader("Original Emails (Primary)")
    for r in data.get("results", []):
        with st.expander(f"{r['subject']} | {r['sender']} | {r['date']}"):
            st.caption(f"Source: {r['source_ref']}")
            st.write(r["snippet"])
            cols = st.columns(3)
            cols[0].metric("Retrieval", f"{r['retrieval_score']:.2f}")
            cols[1].metric("Coverage", f"{r['coverage_score']:.2f}")
            cols[2].metric("Confidence", f"{r['confidence']:.2f}")
            render_confidence(r["confidence"])

    if data.get("answer"):
        st.subheader("LLM Answer (Secondary)")
        st.write(data["answer"])

    st.subheader("Overall Confidence")
    render_confidence(data.get("overall_confidence", 0.0))


if page == "Ingest":
    st.header("Ingestion")
    source_path = st.text_input("Mailbox Path", value="data/sample.mbox")
    source_type = st.selectbox("Type", ["mbox", "text"], index=0)
    if st.button("Start Ingestion"):
        resp = requests.post(
            f"{API_BASE}/ingest/start",
            json={"source_path": source_path, "source_type": source_type},
            timeout=15,
        )
        if resp.ok:
            st.success("Ingestion started")
        else:
            st.error(resp.text)

    if st.button("Refresh Status"):
        st.rerun()

    try:
        status = requests.get(f"{API_BASE}/ingest/status", timeout=10).json()
        st.json(status)
        total = max(1, status.get("total_bytes", 1))
        done = status.get("processed_bytes", 0)
        st.progress(min(100, int(done * 100 / total)), text=f"ETA: {status.get('eta_seconds', 0)}s")
    except Exception as exc:
        st.warning(f"Status unavailable: {exc}")

elif page == "Search":
    st.header("Search Emails")
    query = st.text_input("Search query")
    top_k = st.slider("Top K", 1, 20, 5)
    if st.button("Search") and query.strip():
        resp = requests.post(
            f"{API_BASE}/query",
            json={"query": query, "mode": "search", "top_k": top_k},
            timeout=30,
        )
        if resp.ok:
            show_results(resp.json())
        else:
            st.error(resp.text)

else:
    st.header("Ask Questions")
    query = st.text_area("Question")
    top_k = st.slider("Top K", 1, 20, 5)
    if st.button("Ask") and query.strip():
        with st.spinner("Thinking..."):
            resp = requests.post(
                f"{API_BASE}/query",
                json={"query": query, "mode": "ask", "top_k": top_k},
                timeout=60,
            )
        if resp.ok:
            show_results(resp.json())
        else:
            st.error(resp.text)
