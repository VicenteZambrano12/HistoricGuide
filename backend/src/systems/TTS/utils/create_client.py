from src.utils.general.GeminiApiCall import GeminiClient


def create_client() -> GeminiClient:
    """Create the speech client with an 8192-token limit and 120-second timeout.

    Args:
        None.

    Returns:
        GeminiClient: Client using the gemini-2.5-flash-preview-tts model.

    Raises:
        ValueError: API credentials or shared configuration are invalid.
        OSError: Shared configuration cannot be read.
    """
    return GeminiClient(
        model="gemini-2.5-flash-preview-tts",
        max_output_tokens=8192,
        timeout=120.0,
    )
