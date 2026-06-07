"""Retrieval ablation configurations for systematic comparison."""

ABLATION_CONFIGS = {
    "dense_only": {
        "description": "Dense retrieval only (no BM25, no reranker)",
        "use_sparse": False,
        "use_reranker": False,
        "top_k": 10,
    },
    "sparse_only": {
        "description": "BM25 sparse retrieval only",
        "use_sparse": True,
        "use_reranker": False,
        "top_k": 10,
        "dense_weight": 0.0,
    },
    "hybrid_no_rerank": {
        "description": "Dense + BM25 fusion, no reranker",
        "use_sparse": True,
        "use_reranker": False,
        "top_k": 10,
    },
    "hybrid_with_rerank": {
        "description": "Dense + BM25 + cross-encoder reranker",
        "use_sparse": True,
        "use_reranker": True,
        "top_k": 10,
    },
    "hybrid_rerank_decompose": {
        "description": "Hybrid + reranker + multi-query decomposition",
        "use_sparse": True,
        "use_reranker": True,
        "top_k": 10,
        "multi_query": True,
    },
}

CHUNK_SIZE_ABLATIONS = [200, 400, 600, 800]
OVERLAP_ABLATIONS = [0, 50, 100]
TOP_K_ABLATIONS = [5, 10, 20, 50]

SYSTEM_COMPARISONS = {
    "A_llm_only": "LLM only, no retrieval",
    "B_single_agent_dense": "Single-agent dense RAG",
    "C_single_agent_hybrid": "Single-agent hybrid RAG",
    "D_multi_agent_hybrid": "Multi-agent hybrid RAG",
    "E_multi_agent_with_verifier": "Multi-agent RAG with verifier",
}
