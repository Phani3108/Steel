"""jai-foundry — deterministic synthetic-data factory for Borealis Manufacturing.

Borealis Manufacturing is a fictional $800M industrial manufacturer whose data grounds
every JAI demo and eval. Generation is pure seeded templates + curated vocabulary — no
LLM calls — so output is byte-reproducible for a given seed.
"""

from jai_foundry.generate import BASE_DATE, DEFAULT_SEED, generate
from jai_foundry.load import ensure_schema, load

__version__ = "0.1.0"

__all__ = ["BASE_DATE", "DEFAULT_SEED", "ensure_schema", "generate", "load"]
