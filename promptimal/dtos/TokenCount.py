# Standard library
from dataclasses import dataclass


@dataclass
class TokenCount:
    input: int
    output: int

    def __add__(self, other):
        if not isinstance(other, TokenCount):
            return NotImplemented

        return TokenCount(self.input + other.input, self.output + other.output)
