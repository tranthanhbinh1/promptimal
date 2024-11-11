# o100

**o100 is a simple command-line tool for optimizing your prompts.**

It generates and uses synthetic tests to evaluate prompts and iteratively improve them. All you have to do is supply the prompt you want to optimize and a description of the task. o100 will then execute the following loop:

1. An _optimizer LLM_ will use a LLM to generate candidates for a better prompt
2. An _evaluator LLM_ will generate synthetic tests (example I/O pairs) and use them to score each candidate
3. The top-k prompts and their scores are picked and used as context for the optimizer LLM to generate another round of candidates
4. This process is repeated until some termination threshold is reached

Using o100 is dead simple. It takes less than 30 seconds to start optimizing a prompt.
