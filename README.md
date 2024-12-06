# promptimal

**Promptimal is the fastest way to optimize your prompts and boost performance on AI tasks.**

Promptimal automatically refines your prompt for a specific task. _It doesn't require a dataset_ –– all you need is an initial prompt and a description of the task it's used for. Promptimal will then use a genetic algorithm to iteratively modify the prompt until it's better than the original. Behind the scenes, an LLM-as-judge approach is used to evaluate the modified prompts, but you also have the option to define your own evaluation function.

![Demo](./assets/demo.gif)

## Installation

```bash
> pipx install promptimal
```

## Quickstart

First, make sure you have your OpenAI API key added to your environment:

```bash
> export OPENAI_API_KEY="key_goes_here"
```

Then, run the tool from the command-line:

```bash
> promptimal
```

You'll be asked to input your task description and initial prompt. Alternatively, you can specify these inputs as command-line arguments:

```bash
> promptimal \
    --prompt "You will be provided with a piece of code, and your task is to explain it in a concise way." \
    --task_description "The goal is to generate a summary of a code snippet which will then be embedded and used for vector search."
```

Once you're done, a UI will open in your terminal for monitoring the optimization process:

<img src="./assets/demo.png" width="720" />

## Advanced usage

### Hyperparameters

You can control the optimization parameters by passing additional command-line arguments:

```bash
> promptimal --num_iters=10 --num_samples=20 --threshold=0.7
```

1. `num_iters`: Number of iterations to run the optimization loop for. Equivalent to the number of "generations" in an evolutionary algorithm.
2. `num_samples`: Number of candidate prompts to generate in each iteration. Equivalent to the "population size" in an evolutionary algorithm.
3. `threshold`: Termination threshold for the loop. If a candidate prompt gets a score higher than this threshold, the optimization loop will stop. Default is 1.0.

### Custom evaluators

By default, promptimal uses an LLM-as-judge with self-consistency to evaluate prompt candidates. But to boost performance, you may want to evaluate prompts against a dataset or use some other evaluation technique. To do this, first create a Python file called `evaluator.py`. Then define your own evaluation function in that file, like so:

```python
import argparse

def evaluator(prompt: str) -> float:
    # Your code goes here
    # Must return value between 0 and 1

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--prompt", required=True, type=str)
    args = parser.parse_args()

    score = evaluator(args.prompt)
    print(score)

if __name__ == "__main__":
    main()
```

Once finished, run promptimal with the following command-line argument:

```bash
> promptimal --evaluator="path/to/evaluator.py"
```

This file will serve as a script that promptimal can use to evaluate prompts.

## Roadmap

1. Support for other LLM providers, like Anthropic, Groq, etc.
2. Evolve not only the prompts, but the meta-prompts (based on the [PromptBreeder paper](https://arxiv.org/pdf/2309.16797)).
3. Pre-define some mutation operators.
4. Generate synthetic tests as part of the evaluation process.
