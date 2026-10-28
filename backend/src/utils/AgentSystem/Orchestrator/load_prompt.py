from pathlib import Path

import yaml
from src.utils.general.cloud import prompt_text

from .dataclasses.OrchestratorPrompt import OrchestratorPrompt


PROMPT_PATH = (
    Path(__file__).resolve().parents[3] / "config" / "prompts" / "orchestrator.yaml"
)


def load_prompt() -> OrchestratorPrompt:
    return OrchestratorPrompt.model_validate(yaml.safe_load(prompt_text(PROMPT_PATH)))
