from src.utils.general.GeminiApiCall import GeminiClient


def create_client() -> GeminiClient:
    """Create the default low-cost transcription client."""
    return GeminiClient(
        model="gemini-3.5-flash-lite",
        max_output_tokens=8192,
        timeout=120.0,
    )
