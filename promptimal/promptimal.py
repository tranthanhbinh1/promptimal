# Standard library
import os
import argparse
import subprocess
from typing import Optional, Tuple, Callable

# Local
try:
    from promptimal.app import App
    from promptimal.dtos import PromptCandidate, TokenCount
except ImportError:
    from app import App
    from dtos import PromptCandidate, TokenCount


#########
# HELPERS
#########


def generate_evaluator(
    evaluator_path: Optional[str], evaluator_python_path: Optional[str]
) -> Optional[Callable]:
    if not evaluator_path:
        return None

    if not evaluator_python_path:
        # Fallback to current Python interpreter if not specified
        import sys

        evaluator_python_path = sys.executable

    async def evaluator(
        candidate: PromptCandidate, *args
    ) -> Tuple[PromptCandidate, TokenCount]:
        if candidate.fitness != None:
            return candidate, TokenCount(0, 0)

        try:
            print("\n" + "=" * 50)
            print(f"Running evaluator with prompt:\n{candidate.prompt}")
            print("=" * 50)

            result = subprocess.run(
                [
                    str(evaluator_python_path),
                    str(evaluator_path),
                    "--prompt",
                    candidate.prompt,
                ],
                capture_output=True,
                text=True,
                check=False,
            )

            # Always print stdout if there is any
            if result.stdout:
                print("\nEvaluator stdout:")
                print("-" * 20)
                print(result.stdout.strip())

            # Always print stderr if there is any
            if result.stderr:
                print("\nEvaluator stderr:")
                print("-" * 20)
                print(result.stderr.strip())

            if result.returncode != 0:
                print(f"\nEvaluator failed with return code: {result.returncode}")
                candidate.fitness = 0.0
            else:
                # Get the last non-empty line from stdout
                output_lines = [
                    line.strip() for line in result.stdout.split("\n") if line.strip()
                ]
                if not output_lines:
                    print("\nNo output from evaluator")
                    candidate.fitness = 0.0
                else:
                    try:
                        # Try to convert the last line to float
                        candidate.fitness = float(output_lines[-1])
                        print(f"\nExtracted fitness score: {candidate.fitness}")
                    except ValueError:
                        print(
                            f"\nCould not convert evaluator output to float: {output_lines[-1]}"
                        )
                        candidate.fitness = 0.0

            print("=" * 50 + "\n")

        except Exception as e:
            print(f"Exception in evaluator: {str(e)}")
            candidate.fitness = 0.0

        return candidate, TokenCount(0, 0)

    return evaluator


######
# MAIN
######


def main():
    parser = argparse.ArgumentParser(
        description="Optimize your prompts using a genetic algorithm."
    )
    parser.add_argument(
        "--prompt",
        default="",
        required=False,
        type=str,
        help="Initial prompt to optimize.",
    )
    parser.add_argument(
        "--improve",
        default="",
        required=False,
        type=str,
        help="Description of what you want to improve about the prompt.",
    )
    parser.add_argument(
        "--num_iters",
        default=5,
        required=False,
        type=int,
        help="Number of iterations to run the optimization loop for.",
    )
    parser.add_argument(
        "--num_samples",
        default=3,
        required=False,
        type=int,
        help="Number of prompts to generate in each iteration.",
    )
    parser.add_argument(
        "--threshold",
        default=1.0,
        required=False,
        type=float,
        help="Score threshold to stop the optimization loop.",
    )
    parser.add_argument(
        "--google_ai_api_key",
        default="",
        required=False,
        type=str,
        help="Google AI API key.",
    )
    parser.add_argument(
        "--evaluator",
        default="",
        required=False,
        type=str,
        help="Path to your custom evaluator script.",
    )
    parser.add_argument(
        "--evaluator_python_path",
        default="",
        required=False,
        type=str,
        help="Path to the Python interpreter to use for the evaluator script (e.g. /path/to/venv/bin/python).",
    )
    args = parser.parse_args()

    # if not os.getenv("OPENAI_API_KEY", None) or args.openai_api_key:
    #     print("\033[1;31mOpenAI API key not found.\033[0m")
    #     return

    init_prompt = (
        input("\033[1;90mInitial prompt (use \\n for newlines):\033[0m\n\n")
        if not args.prompt
        else args.prompt
    ).replace("\\n", "\n")
    improvement_request = (
        input("\n\033[1;90mWhat do you want to improve:\033[0m\n\n")
        if not args.improve
        else args.improve
    ).replace("\\n", "\n")

    app = App(init_prompt)
    optimized_prompt, is_finished = app.start(
        improvement_request=improvement_request,
        num_iters=args.num_iters,
        population_size=args.num_samples,
        threshold=args.threshold,
        api_key=args.google_ai_api_key,
        evaluator=generate_evaluator(args.evaluator, args.evaluator_python_path),
    )

    if args.prompt:
        print(f"\033[1;90mInitial prompt:\033[0m\n\n{init_prompt}")
    if args.improve:
        print(
            f"\n\033[1;90mWhat do you want to improve:\033[0m\n\n{improvement_request}"
        )
    if is_finished:
        print(
            f"\n🧬 \033[1;35mOPTIMIZED PROMPT\033[0m 🧬\n\n\033[35m{optimized_prompt}\033[0m"
        )
    else:
        print(f"\n\033[1;31mOptimization loop terminated.\033[0m")
