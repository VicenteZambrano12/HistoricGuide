from pathlib import Path

import yaml
from src.utils.general.cloud import prompt_text

from src.utils.AgentSystem.Orchestrator.dataclasses.types import Category

from .dataclasses.GenerationPrompt import GenerationPrompt


PROMPT_DIRECTORY = Path(__file__).resolve().parents[3] / "config" / "prompts"


def load_prompt(category: Category) -> GenerationPrompt:
    """Load and validate the generation prompt associated with a routing category.

    Args:
        category (Literal["historic", "restaurant"]): Topic selecting the prompt filename.

    Returns:
        GenerationPrompt: Configuration containing a nonblank system instruction.

    Raises:
        KeyError: The caller supplies an unsupported category.
        pydantic.ValidationError: The YAML shape, prompt text, or extra fields are invalid.
        ValueError: Environment or storage configuration is invalid.
        OSError: The local prompt or credentials file cannot be read.
        UnicodeDecodeError: Prompt contents are not valid UTF-8.
        yaml.YAMLError: Prompt contents are not valid YAML.
        google.api_core.exceptions.GoogleAPIError: Cloud prompt retrieval fails.
    """
    filename = {"historic": "historic.yaml", "restaurant": "restaurant.yaml"}[category]
    return GenerationPrompt.model_validate(yaml.safe_load(prompt_text(PROMPT_DIRECTORY / filename)))
