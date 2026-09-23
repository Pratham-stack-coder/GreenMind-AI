"""
Knowledge & Context Retrieval for GreenMind AI Copilot.
Contains architectural rules, cloud sustainability best practices, and optimization guides.
Integrates with ChromaDB when installed, with safe in-memory fallback.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

DOCUMENTS = [
    {
        "id": "doc-01",
        "title": "Cloud Right-Sizing Guidelines",
        "topic": "cost",
        "content": (
            "Right-sizing EC2/VM instances involves selecting the optimal instance family and size based on p95 utilization. "
            "Instances with sustained CPU < 25% and memory < 40% are prime candidates for 1-step downsizing (e.g., m5.xlarge -> m5.large), "
            "typically cutting compute cost by ~50% with zero SLO degradation."
        ),
    },
    {
        "id": "doc-02",
        "title": "Carbon-Aware Workload Time-Shifting",
        "topic": "sustainability",
        "content": (
            "Electricity grids experience dynamic carbon intensity variation based on renewable availability. "
            "In regions like us-east and eu-west, carbon intensity peaks during evening ramp (6-9 PM) and reaches minima "
            "during early morning (1-5 AM). Deferring non-urgent batch jobs and data processing to green windows cuts emissions by 20-40%."
        ),
    },
    {
        "id": "doc-03",
        "title": "Predictive Auto-Scaling Best Practices",
        "topic": "performance",
        "content": (
            "Reactive auto-scaling triggers after thresholds are breached (e.g. 75% CPU for 5 minutes), exposing users to latency spikes. "
            "GreenMind ML forecasting models project resource demand 60 minutes ahead, enabling pre-warming and proactive scale-out 15 minutes before peak traffic."
        ),
    },
    {
        "id": "doc-04",
        "title": "Storage Lifecycle & Idle Resource Termination",
        "topic": "cost",
        "content": (
            "Unattached EBS volumes, orphan snapshots older than 90 days, and idle load balancers contribute significantly to wasted spend. "
            "Migrating Infrequent Access objects to S3 Glacier or cold tier reduces storage cost by up to 70%."
        ),
    },
]


def search_knowledge(query: str, top_k: int = 2) -> list[dict[str, Any]]:
    """Retrieve relevant optimization documentation based on keywords or vector search."""
    # Try ChromaDB if available
    try:
        import chromadb
        client = chromadb.Client()
        collection = client.get_or_create_collection(name="greenmind_knowledge")
        if collection.count() == 0:
            for doc in DOCUMENTS:
                collection.add(
                    ids=[doc["id"]],
                    documents=[doc["content"]],
                    metadatas=[{"title": doc["title"], "topic": doc["topic"]}],
                )
        results = collection.query(query_texts=[query], n_results=top_k)
        docs = []
        if results and results.get("documents"):
            for i, text in enumerate(results["documents"][0]):
                meta = results["metadatas"][0][i] if results.get("metadatas") else {}
                docs.append({"title": meta.get("title", ""), "content": text})
            return docs
    except Exception:
        pass

    # In-memory keyword fallback
    query_lower = query.lower()
    scored = []
    for doc in DOCUMENTS:
        score = sum(1 for word in query_lower.split() if word in doc["content"].lower() or word in doc["title"].lower())
        if score > 0:
            scored.append((score, doc))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [item[1] for item in scored[:top_k]]
