# Standard library
from dataclasses import dataclass
from typing import Optional


@dataclass
class PromptCandidate:
    prompt: str
    fitness: Optional[float] = None
    reflection: Optional[str] = None
