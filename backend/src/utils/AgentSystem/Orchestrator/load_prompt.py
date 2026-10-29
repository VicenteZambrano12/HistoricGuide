from pathlib import Path

import yaml
from src.utils.general.cloud import prompt_text

from .dataclasses.OrchestratorPrompt import OrchestratorPrompt


PROMPT_PATH = (
    Path(__file__).resolve().parents[3] / "config" / "prompts" / "orchestrator.yaml"
)


def load_prompt() -> OrchestratorPrompt:
    """Load and validate the classifier prompt from the active data source.

    Args:
        None.

    Returns:
        OrchestratorPrompt: Configuration containing a nonblank system instruction.

    Raises:
        pydantic.ValidationError: The YAML shape, prompt text, or extra fields are invalid.
        ValueError: Environment or storage configuration is invalid.
        OSError: The local prompt or credentials file cannot be read.
        UnicodeDecodeError: Prompt contents are not valid UTF-8.
        yaml.YAMLError: Prompt contents are not valid YAML.
        google.api_core.exceptions.GoogleAPIError: Cloud prompt retrieval fails.
    """
    return OrchestratorPrompt.model_validate(yaml.safe_load(prompt_text(PROMPT_PATH)))
