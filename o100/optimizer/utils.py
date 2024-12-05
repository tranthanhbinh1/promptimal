# Standard library
import json
import random
from typing import List, Optional, Tuple
from statistics import mean

# Third party
import json_repair
from openai import AsyncOpenAI

# Local
# from o100.dtos import PromptCandidate, TokenCount
# from o100.optimizer.prompts import INIT_POPULATION_PROMPT, EVAL_PROMPT, CROSSOVER_PROMPT
from dtos import PromptCandidate, TokenCount
from optimizer.prompts import (
    INFER_TASK_PROMPT,
    INIT_POPULATION_PROMPT,
    EVAL_PROMPT,
    CROSSOVER_PROMPT,
)


def get_xml_content(output: str, tag: str) -> str:
    start = output.find(f"<{tag}>") + len(f"<{tag}>")
    end = output.find(f"</{tag}>")
    end = end if end != -1 else len(output)
    content = output[start:end].strip()
    return content


async def infer_task_description(
    prompt: str, task_description: Optional[str], openai: AsyncOpenAI
) -> Tuple[str, TokenCount]:
    if task_description.strip():
        return task_description, TokenCount(0, 0)

    system_message = {"role": "system", "content": INFER_TASK_PROMPT}
    user_message = {
        "role": "user",
        "content": f"Describe the task that the following prompt is used for:\n\n<prompt>\n{prompt}\n</prompt>",
    }
    response = await openai.chat.completions.create(
        messages=[system_message, user_message], model="gpt-4o", temperature=1.0
    )
    output = response.choices[0].message.content
    task_description = get_xml_content(output, "task_description")

    return task_description, TokenCount(
        response.usage.prompt_tokens, response.usage.completion_tokens
    )


async def init_population(
    prompt: str, task_description: str, population_size: int, openai: AsyncOpenAI
) -> Tuple[List[PromptCandidate], TokenCount]:
    """
    Initializes a population of candidate prompts.
    """

    system_message = {
        "role": "system",
        "content": INIT_POPULATION_PROMPT.format(
            population_size=population_size, task_description=task_description
        ),
    }
    user_message = {
        "role": "user",
        "content": f"Generate {population_size} better versions of the following prompt:\n\n<prompt>\n{prompt}\n</prompt>",
    }
    response = await openai.chat.completions.create(
        messages=[system_message, user_message],
        model="gpt-4o",
        temperature=1.0,
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "better_prompts",
                "strict": True,
                "schema": {
                    "type": "object",
                    "properties": {
                        "prompts": {
                            "type": "array",
                            "items": {
                                "type": "string",
                                "description": "A better version of the provided prompt.",
                            },
                            "description": f"A list of {population_size} prompts that are better versions of the provided prompt.",
                        }
                    },
                    "required": ["prompts"],
                    "additionalProperties": False,
                },
            },
        },
    )
    output = json_repair.loads(response.choices[0].message.content)
    population = [PromptCandidate(prompt) for prompt in output["prompts"]]
    population = [PromptCandidate(prompt)] + population  # Add initial prompt

    return population, TokenCount(
        response.usage.prompt_tokens, response.usage.completion_tokens
    )


async def evaluate_fitness(
    candidate: PromptCandidate,
    task_description: str,
    initial_prompt: PromptCandidate,
    openai: AsyncOpenAI,
    num_samples=5,
) -> Tuple[PromptCandidate, TokenCount]:
    """
    Evaluates a prompt candidate using a LLM + self-consistency.
    """

    # Elite, already evaluated from the previous generation
    if candidate.fitness:
        return candidate, TokenCount(0, 0)

    # Generate `n_samples` self-evaluations
    response = await openai.chat.completions.create(
        messages=[
            {
                "role": "system",
                "content": EVAL_PROMPT.format(task_description=task_description),
            },
            {"role": "user", "content": initial_prompt.prompt},
            {
                "role": "assistant",
                "content": json.dumps(
                    {
                        "evaluation": initial_prompt.reflection,
                        "score": initial_prompt.fitness,
                    }
                ),
            },
            {"role": "user", "content": candidate.prompt},
        ],
        model="gpt-4o",
        temperature=1.0,
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "evaluation",
                "strict": True,
                "schema": {
                    "type": "object",
                    "properties": {
                        "evaluation": {
                            "type": "string",
                            "description": "Justification for your score.",
                        },
                        "score": {
                            "type": "number",
                            "description": "A score between 1-10 for the prompt. A lower score indicates a worse prompt, and a higher score a better prompt.",
                        },
                    },
                    "required": ["evaluation", "score"],
                    "additionalProperties": False,
                },
            },
        },
        n=num_samples,
    )
    outputs = (choice.message.content for choice in response.choices)
    outputs = [json_repair.loads(output) for output in outputs]

    # Consolidate results
    candidate.fitness = mean(output["score"] for output in outputs) / 10
    candidate.reflection = outputs[0]["evaluation"]  # 1st evaluation is best

    return candidate, TokenCount(
        response.usage.prompt_tokens, response.usage.completion_tokens
    )


def select_parent(
    population: List[PromptCandidate], tournament_size=3
) -> PromptCandidate:
    tournament = random.sample(population, tournament_size)
    return max(tournament, key=lambda candidate: candidate.fitness)


async def crossover(
    parent1: PromptCandidate,
    parent2: PromptCandidate,
    task_description: str,
    openai: AsyncOpenAI,
) -> Tuple[PromptCandidate, TokenCount]:
    system_message = {
        "role": "system",
        "content": CROSSOVER_PROMPT.format(task_description=task_description),
    }
    user_message = {
        "role": "user",
        "content": f"Combine the following prompts into a better one:\n\n<prompt_1>\n{parent1.prompt}\n</prompt_1>\n\n<prompt_2>\n{parent2.prompt}\n</prompt_2>",
    }
    response = await openai.chat.completions.create(
        messages=[system_message, user_message],
        model="gpt-4o",
        temperature=1.0,
    )
    output = response.choices[0].message.content
    prompt = get_xml_content(output, "combined_prompt")

    return PromptCandidate(prompt), TokenCount(
        response.usage.prompt_tokens, response.usage.completion_tokens
    )
