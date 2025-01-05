# Standard library
from dataclasses import dataclass
from typing import Optional

# Local
try:
    from promptimal.dtos.TokenCount import TokenCount
except ImportError:
    from dtos.TokenCount import TokenCount


@dataclass
class ProgressStep:
    index: int
    message: str
    best_prompt: str
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    value: Optional[float] = None
    best_score: Optional[float] = None
    token_count: Optional[TokenCount] = None
    num_prompts: Optional[int] = 0
    is_terminal: Optional[bool] = False
