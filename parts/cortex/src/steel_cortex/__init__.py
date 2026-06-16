"""steel-cortex — the chassis: permission-aware procurement semantic layer.

Entities + chunked documents carry tenant and role ACLs; retrieval enforces both in SQL,
below the LLM. Refusals are first-class results. The retrieval contract (RetrievalResult)
is what agents consume — through dependency injection, never imports.
"""

from steel_cortex.acl import ROLE_TYPES, allowed_types
from steel_cortex.cortex import Cortex
from steel_cortex.models import ChunkHit, Citation, RetrievalResult

__version__ = "0.1.0"

__all__ = [
    "ROLE_TYPES",
    "ChunkHit",
    "Citation",
    "Cortex",
    "RetrievalResult",
    "allowed_types",
]
