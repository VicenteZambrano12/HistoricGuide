from typing import Literal


# Internal modes preserve their established spelling independently of public chat modes.
PipelineMode = Literal["STT", "TTS", "full", "only text"]
