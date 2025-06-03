# Standard library
import time
import asyncio
from typing import List, Optional, Tuple
from loguru import logger as logging

# Third party - Remove urwid and pyperclip since we're removing UI
# import urwid
# import pyperclip

# Local
try:
    from promptimal.optimizer import optimize
    from promptimal.dtos import ProgressStep
except ImportError:
    from optimizer import optimize
    from dtos import ProgressStep

#########
# HELPERS
#########

# Remove all UI classes: ScrollableListBox, PromptBox, ProgressBox, Footer

######
# MAIN
######


class App:
    def __init__(self, init_prompt: str):
        # State
        self.is_finished = False
        self.prompt = init_prompt
        self.score = None
        self.steps = [
            ProgressStep(
                index=0,
                value=0.0,
                message="Starting optimization",
                best_prompt=init_prompt,
                start_time=time.time(),
            )
        ]

        logging.info("=== Prompt Optimization Started ===")
        logging.info(f"Initial prompt: {init_prompt}")

    def _format_elapsed_time(
        self, start_time: float, end_time: Optional[float] = None
    ) -> str:
        if not end_time:
            return "--:--:--"

        elapsed_seconds = int(end_time - start_time)
        hours, remainder = divmod(elapsed_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours:02}:{minutes:02}:{seconds:02}"

    def _log_progress(self, step: ProgressStep):
        """Log progress information instead of updating UI"""
        elapsed = self._format_elapsed_time(step.start_time, step.end_time)
        progress_pct = f"{step.value * 100:.1f}%" if step.value else "0.0%"

        if step.is_terminal:
            logging.info(f"✓ {step.message}")
        else:
            logging.info(f"[{progress_pct}] {step.message} (Elapsed: {elapsed})")

        # Log token usage and cost if available
        if step.token_count:
            input_toks = step.token_count.input
            output_toks = step.token_count.output
            total_toks = input_toks + output_toks
            cost = (input_toks * (2.50 / 1000000)) + (output_toks * (10.0 / 1000000))
            logging.info(
                f"   Tokens: {total_toks} | Cost: ${cost:.4f} | Prompts evaluated: {step.num_prompts}"
            )

    def _log_score_update(self, score: float):
        """Log score updates"""
        score_pct = score * 100
        if score <= 0.33:
            level = "LOW"
        elif score >= 0.67:
            level = "HIGH"
        else:
            level = "MED"

        logging.info(f"📊 Score updated: {score_pct:.2f}% ({level})")

    async def optimize(self, **kwargs):
        async for step in optimize(self.prompt, **kwargs):
            # Update state
            old_prompt = self.prompt
            self.prompt = step.best_prompt.replace("\\n", "\n")

            # Log score changes
            if step.best_score != self.score:
                self.score = step.best_score
                if self.score is not None:
                    self._log_score_update(self.score)

            # Update or add step
            existing_step = next((s for s in self.steps if s.index == step.index), None)
            if existing_step:
                existing_step.value = step.value
                existing_step.message = step.message
                existing_step.token_count = step.token_count
                existing_step.num_prompts = step.num_prompts
                existing_step.end_time = step.end_time
                self._log_progress(existing_step)
            else:
                self.steps.append(step)
                self._log_progress(step)

            # Log prompt changes
            if self.prompt != old_prompt:
                logging.info("🔄 Prompt updated:")
                logging.info(f"   New prompt: {self.prompt}")

        self.is_finished = True
        logging.info("=== Optimization Complete ===")
        logging.info(f"Final prompt: {self.prompt}")
        if self.score is not None:
            logging.info(f"Final score: {self.score * 100:.2f}%")

    def start(self, **kwargs) -> Tuple[str, bool]:
        # Run optimization without UI
        asyncio.run(self.optimize(**kwargs))
        return self.prompt, self.is_finished
