from app.services.rag.retriever import HybridRetriever, _tokenize


def test_tokenize():
    assert _tokenize("Self-Attention is ALL you need!") == [
        "self",
        "attention",
        "is",
        "all",
        "you",
        "need",
    ]


def test_rrf_ranks_by_position():
    scores = HybridRetriever._rrf(["a", "b", "c"])
    assert scores["a"] > scores["b"] > scores["c"]


def test_rrf_fusion_rewards_agreement():
    """A doc ranked highly by both retrievers should beat one ranked by only one."""
    dense = HybridRetriever._rrf(["x", "y", "z"])
    keyword = HybridRetriever._rrf(["x", "w", "y"])

    fused = {}
    for cid in set(dense) | set(keyword):
        fused[cid] = dense.get(cid, 0.0) + keyword.get(cid, 0.0)

    # x is #1 in both lists → must be the top fused result.
    assert max(fused, key=fused.get) == "x"
