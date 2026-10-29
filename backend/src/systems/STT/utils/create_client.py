from src.utils.general.GeminiApiCall import GeminiClient


def create_client() -> GeminiClient:
    """Create the transcription client with an 8192-token limit and 120-second timeout.

    Args:
        None.

    Returns:
        GeminiClient: Client using the gemini-3.5-flash-lite generation model.

    Raises:
        ValueError: API credentials or shared configuration are invalid.
        OSError: Shared configuration cannot be read.
    """
    return GeminiClient(
        model="gemini-3.5-flash-lite",
        max_output_tokens=8192,
        timeout=120.0,
    )
