from pathlib import Path

import yaml

from .dataclasses.OrchestratorPrompt import OrchestratorPrompt


PROMPT_PATH = (
    Path(__file__).resolve().parents[3] / "config" / "prompts" / "orchestrator.yaml"
)


def load_prompt() -> OrchestratorPrompt:
    with PROMPT_PATH.open(encoding="utf-8") as stream:
        return OrchestratorPrompt.model_validate(yaml.safe_load(stream))
