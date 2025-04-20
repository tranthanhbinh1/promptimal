import random
from statistics import mean
from typing import List, Tuple
import instructor
from pydantic import BaseModel, Field

# Local
try:
    from promptimal.dtos import PromptCandidate, TokenCount
    from promptimal.optimizer.prompts import (
        INIT_POPULATION_PROMPT,
        EVAL_PROMPT,
        CROSSOVER_PROMPT,
    )
except ImportError:
    from dtos import PromptCandidate, TokenCount
    from optimizer.prompts import (
        INIT_POPULATION_PROMPT,
        EVAL_PROMPT,
        CROSSOVER_PROMPT,
    )

from google import genai


# Pydantic models for structured output
class BetterPrompts(BaseModel):
    prompts: List[str] = Field(
        description="A list of prompts that are better versions of the provided prompt."
    )


class PromptEvaluation(BaseModel):
    evaluation: str = Field(description="Justification for your score.")
    score: float = Field(
        description="A score between 1-10 for the prompt, with 10 being the highest."
    )


class PromptCrossover(BaseModel):
    analysis: str = Field(description="Your step-by-step analysis of the two prompts.")
    prompt: str = Field(description="The combined and improved prompt.")


async def init_population(
    prompt: str, improvement_request: str, population_size: int, genai: genai.Client
) -> Tuple[List[PromptCandidate], TokenCount]:
    """
    Initializes a population of candidate prompts.
    """
    # Create a patched client with instructor
    client = instructor.from_genai(genai, use_async=True)

    system_message = {
        "role": "system",
        "content": INIT_POPULATION_PROMPT.format(
            population_size=population_size, improvement_request=improvement_request
        ),
    }
    user_message = {
        "role": "user",
        "content": f"Generate {population_size} better versions of the following prompt:\n\n<prompt>\n{prompt}\n</prompt>",
    }

    # Use instructor to handle the structured output
    response = await client.chat.completions.create(
        messages=[system_message, user_message],
        model="gemini-2.0-flash",
        # temperature=1.0,
        response_model=BetterPrompts,
    )

    # Directly use the validated model
    population = [PromptCandidate(prompt) for prompt in response.prompts]
    population = [PromptCandidate(prompt)] + population  # Add initial prompt

    # Get token usage from instructor response
    token_usage = getattr(response, "usage", None)
    if token_usage:
        token_count = TokenCount(
            token_usage.prompt_tokens, token_usage.completion_tokens
        )
    else:
        token_count = TokenCount(0, 0)

    return population, token_count


async def evaluate_fitness(
    candidate: PromptCandidate,
    initial_prompt: PromptCandidate,
    improvement_request: str,
    genai: genai.Client,
    num_samples=5,
) -> Tuple[PromptCandidate, TokenCount]:
    """
    Evaluates a prompt candidate using a LLM + self-consistency.
    """
    # Elite, already evaluated from the previous generation
    if candidate.fitness:
        return candidate, TokenCount(0, 0)

    # Create a patched client with instructor
    client = instructor.from_genai(genai, use_async=True)

    # Generate `n_samples` self-evaluations
    messages = [
        {
            "role": "system",
            "content": EVAL_PROMPT.format(
                initial_prompt=initial_prompt,
                improvement_request=improvement_request,
            ),
        },
        {
            "role": "user",
            "content": f"Evaluate the following prompt:\n\n<prompt>\n{candidate.prompt}\n</prompt>",
        },
    ]

    evaluations = []
    total_prompt_tokens = 0
    total_completion_tokens = 0

    # We need to call the API multiple times to get multiple samples
    for _ in range(num_samples):
        eval_response = await client.chat.completions.create(
            messages=messages,
            model="gemini-2.0-flash",
            # temperature=1.0,
            response_model=PromptEvaluation,
        )

        evaluations.append(eval_response)

        # Accumulate token usage
        token_usage = getattr(eval_response, "usage", None)
        if token_usage:
            total_prompt_tokens += token_usage.prompt_tokens
            total_completion_tokens += token_usage.completion_tokens

    # Consolidate results
    candidate.fitness = mean(eval_response.score for eval_response in evaluations) / 10
    candidate.reflection = evaluations[0].evaluation  # 1st evaluation is best

    return candidate, TokenCount(total_prompt_tokens, total_completion_tokens)


def select_parent(
    population: List[PromptCandidate], tournament_size=3
) -> PromptCandidate:
    tournament = random.sample(population, tournament_size)
    # Use a default value of 0.0 if fitness is None
    return max(tournament, key=lambda candidate: candidate.fitness or 0.0)


async def crossover(
    parent1: PromptCandidate,
    parent2: PromptCandidate,
    initial_prompt: str,
    improvement_request: str,
    genai: genai.Client,
) -> Tuple[PromptCandidate, TokenCount]:
    # Create a patched client with instructor
    client = instructor.from_genai(genai, use_async=True)

    system_message = {
        "role": "system",
        "content": CROSSOVER_PROMPT.format(
            initial_prompt=initial_prompt, improvement_request=improvement_request
        ),
    }
    user_message = {
        "role": "user",
        "content": f"Combine the following prompts into a better one:\n\n<prompt_1>\n{parent1.prompt}\n</prompt_1>\n\n<prompt_2>\n{parent2.prompt}\n</prompt_2>",
    }

    # Use instructor to handle the structured output
    response = await client.chat.completions.create(
        messages=[system_message, user_message],
        model="gemini-2.0-flash",
        # temperature=1.0,
        response_model=PromptCrossover,
    )

    # Get token usage from instructor response
    token_usage = getattr(response, "usage", None)
    if token_usage:
        token_count = TokenCount(
            token_usage.prompt_tokens, token_usage.completion_tokens
        )
    else:
        token_count = TokenCount(0, 0)

    return PromptCandidate(response.prompt), token_count
