from src.utils.general.GeminiApiCall import GeminiClient


def create_client() -> GeminiClient:
    """Create the default speech-generation client."""
    return GeminiClient(
        model="gemini-2.5-flash-preview-tts",
        max_output_tokens=8192,
        timeout=120.0,
    )
