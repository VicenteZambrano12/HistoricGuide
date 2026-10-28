from pathlib import Path

import yaml
from src.utils.general.cloud import prompt_text

from src.utils.AgentSystem.Orchestrator.dataclasses.types import Category

from .dataclasses.GenerationPrompt import GenerationPrompt


PROMPT_DIRECTORY = Path(__file__).resolve().parents[3] / "config" / "prompts"


def load_prompt(category: Category) -> GenerationPrompt:
    filename = {"historic": "historic.yaml", "restaurant": "restaurant.yaml"}[category]
    return GenerationPrompt.model_validate(yaml.safe_load(prompt_text(PROMPT_DIRECTORY / filename)))
