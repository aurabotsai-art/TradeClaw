from __future__ import annotations

"""
Vector database wrapper for financial memory (Pinecone + Gemini embeddings).

Provides:
  - embed_text(text) -> list[float]
  - upsert_memory(id, text, metadata) -> None
  - query_similar(query_text, symbol=None, top_k=5, namespace=None) -> list[dict]

Namespaces (recommended):
  - "filings"
  - "news_events"
  - "trade_reasoning"
  - "earnings"
"""

from typing import Any, Dict, List, Optional

from dine_trade.config.settings import GEMINI_API_KEY, PINECONE_API_KEY, PINECONE_INDEX_NAME

try:
    from pinecone import Pinecone  # type: ignore[import]
except ImportError:  # pragma: no cover - optional dependency
    Pinecone = None  # type: ignore[assignment]

try:
    from google import genai  # type: ignore[import]
except ImportError:  # pragma: no cover
    genai = None


_pc_client: Optional["Pinecone"] = None
_pc_index = None


def _get_pinecone_index():
    """Return a Pinecone index instance or raise RuntimeError if not configured."""
    global _pc_client, _pc_index
    if _pc_index is not None:
        return _pc_index

    if Pinecone is None:
        raise RuntimeError("pinecone package is not installed; pip install pinecone-client")
    if not PINECONE_API_KEY or not PINECONE_INDEX_NAME:
        raise RuntimeError("PINECONE_API_KEY or PINECONE_INDEX_NAME not configured.")

    _pc_client = Pinecone(api_key=PINECONE_API_KEY)
    _pc_index = _pc_client.Index(PINECONE_INDEX_NAME)
    return _pc_index


def embed_text(text: str) -> List[float]:
    """
    Embed text using Gemini embedding-001 model.

    Returns the embedding vector as a list[float].
    """
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY not set for embeddings.")
    if genai is None:
        raise RuntimeError("google-genai is not installed; pip install google-genai")

    client = genai.Client(api_key=GEMINI_API_KEY)
    # embedding-001 is the financial memory embedding backbone
    resp = client.models.embed_content(
        model="embedding-001",
        contents=text,
    )

    # The google-genai client returns an embeddings list; take the first vector.
    emb = getattr(resp, "embeddings", None)
    if isinstance(emb, list) and emb:
        vec = getattr(emb[0], "values", None) or getattr(emb[0], "embedding", None)
    else:
        # Fallback to top-level values attribute if present
        vec = getattr(resp, "values", None)

    if not isinstance(vec, list):
        raise RuntimeError("Unexpected embedding response format from Gemini.")

    return [float(x) for x in vec]


def _infer_namespace(metadata: Dict[str, Any]) -> str:
    """
    Infer Pinecone namespace from metadata.

    Priority:
      - explicit metadata["namespace"]
      - event_type mapping:
          * 'SEC_FILING'    -> 'filings'
          * 'NEWS'          -> 'news_events'
          * 'EARNINGS'      -> 'earnings'
          * 'TRADE_REASON'  -> 'trade_reasoning'
      - default: 'general'
    """
    ns = str(metadata.get("namespace") or "").strip()
    if ns:
        return ns

    event_type = str(metadata.get("event_type") or "").upper()
    if event_type == "SEC_FILING":
        return "filings"
    if event_type == "NEWS":
        return "news_events"
    if event_type == "EARNINGS":
        return "earnings"
    if event_type == "TRADE_REASON":
        return "trade_reasoning"

    return "general"


def upsert_memory(
    id: str,
    text: str,
    metadata: Dict[str, Any],
) -> None:
    """
    Upsert a memory vector into Pinecone.

    Args:
        id: unique identifier (e.g., filing_id, trade_run_id, news_id).
        text: raw text to embed (reasoning, SEC summary, news, earnings analysis).
        metadata: dict including at least:
            - symbol: str
            - event_type: str
            - date: ISO date or datetime string
            - outcome / pnl: optional numeric or string
            - namespace: optional, to override inferred namespace
    """
    index = _get_pinecone_index()
    vector = embed_text(text)
    namespace = _infer_namespace(metadata)

    index.upsert(
        vectors=[
            {
                "id": id,
                "values": vector,
                "metadata": metadata,
            }
        ],
        namespace=namespace,
    )


def query_similar(
    query_text: str,
    symbol: Optional[str] = None,
    top_k: int = 5,
    namespace: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Query similar memories from Pinecone for retrieval-augmented reasoning.

    Args:
        query_text: description of current situation (natural language).
        symbol: optional symbol filter.
        top_k: number of matches to return.
        namespace: optional namespace override (filings, news_events, trade_reasoning, earnings).

    Returns:
        List of dicts with keys:
          - id
          - score
          - metadata
    """
    index = _get_pinecone_index()
    vector = embed_text(query_text)

    flt: Dict[str, Any] = {}
    if symbol:
        flt["symbol"] = symbol.upper()

    ns = namespace or "general"

    res = index.query(
        vector=vector,
        top_k=int(top_k),
        include_metadata=True,
        filter=flt or None,
        namespace=ns,
    )

    matches = getattr(res, "matches", None) or getattr(res, "results", None) or []
    out: List[Dict[str, Any]] = []
    for m in matches:
        out.append(
            {
                "id": getattr(m, "id", None) or m.get("id"),
                "score": getattr(m, "score", None) or m.get("score"),
                "metadata": getattr(m, "metadata", None) or m.get("metadata", {}),
            }
        )
    return out


# ---------------------------------------------------------------------------
# Trade feedback loop (Phase 14.5)
# ---------------------------------------------------------------------------

TRADE_REASONING_NAMESPACE = "trade_reasoning"


def upsert_trade_memory(
    trade_id: str,
    reasoning_text: str,
    pnl: float,
    regime: str,
    symbol: str,
    *,
    extra_metadata: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Store a closed trade's decision context and outcome in vector DB for feedback.

    Call after each trade closes. Embeds reasoning_text and stores pnl/regime/symbol
    in metadata so similar situations can be retrieved before future trades.

    Args:
        trade_id: unique id for this trade (e.g. order_id or uuid).
        reasoning_text: agent reasoning + market state summary to embed.
        pnl: realized PnL for this trade.
        regime: market regime at time of trade (e.g. trending, ranging).
        symbol: ticker/symbol.
        extra_metadata: optional extra keys (e.g. side, asset_class, exit_time).
    """
    metadata: Dict[str, Any] = {
        "event_type": "TRADE_REASON",
        "symbol": str(symbol).upper(),
        "pnl": float(pnl),
        "regime": str(regime or "unknown"),
        "namespace": TRADE_REASONING_NAMESPACE,
    }
    if extra_metadata:
        metadata.update(extra_metadata)
    upsert_memory(trade_id, reasoning_text, metadata)


def query_similar_trades(
    query_text: str,
    symbol: Optional[str] = None,
    top_k: int = 10,
) -> List[Dict[str, Any]]:
    """
    Query similar past trade situations by decision context.

    Returns matches with id, score, and metadata (including pnl, regime, symbol).
    Use for feedback loop: if similar trades had negative avg PnL, downweight signal.
    """
    return query_similar(
        query_text,
        symbol=symbol,
        top_k=int(top_k),
        namespace=TRADE_REASONING_NAMESPACE,
    )

