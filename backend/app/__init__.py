"""ResearchMate AI backend package."""
import os

# Prevent `transformers` from importing TensorFlow/Flax. If TF is present in the
# environment, importing it can deadlock (Abseil "mutex.cc Lock blocking") and hang the
# embedding/reranker model load. We only ever use the PyTorch backend, so opt out.
# Set before any submodule imports sentence-transformers/transformers.
os.environ.setdefault("USE_TF", "0")
os.environ.setdefault("USE_FLAX", "0")
os.environ.setdefault("TRANSFORMERS_NO_ADVISORY_WARNINGS", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

__version__ = "0.1.0"
