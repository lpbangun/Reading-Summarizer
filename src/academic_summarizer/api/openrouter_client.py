"""OpenRouter API client for generating summaries."""

from typing import Optional

from openai import OpenAI
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

from ..config import Settings
from ..utils.exceptions import APIError
from ..utils.logger import get_logger, mask_api_key
from .prompt_templates import get_system_prompt

logger = get_logger("api_client")


class OpenRouterClient:
    """Client for OpenRouter API using Grok 4.1 Fast model."""

    def __init__(self, settings: Settings):
        """
        Initialize OpenRouter client.

        Args:
            settings: Application settings
        """
        self.settings = settings
        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=settings.openrouter_api_key,
        )

        logger.info(f"Initialized OpenRouter client with model: {settings.model_name}")
        logger.debug(f"API key: {mask_api_key(settings.openrouter_api_key)}")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((APIError, ConnectionError)),
        reraise=True,
    )
    def generate_summary(self, prompt: str) -> str:
        """
        Generate summary by calling OpenRouter API.

        Args:
            prompt: Formatted prompt with reading text and context

        Returns:
            Generated summary text

        Raises:
            APIError: If API call fails after retries
        """
        logger.info("Calling OpenRouter API to generate summary")
        logger.debug(f"Prompt length: {len(prompt)} characters")

        try:
            response = self.client.chat.completions.create(
                model=self.settings.model_name,
                messages=[
                    {"role": "system", "content": get_system_prompt()},
                    {"role": "user", "content": prompt},
                ],
                temperature=self.settings.temperature,
                max_tokens=self.settings.max_tokens,
                timeout=self.settings.request_timeout,
            )

            summary = response.choices[0].message.content

            if not summary:
                raise APIError("API returned empty response")

            # Log token usage if available
            if hasattr(response, "usage"):
                logger.info(
                    f"Token usage - Input: {response.usage.prompt_tokens}, "
                    f"Output: {response.usage.completion_tokens}, "
                    f"Total: {response.usage.total_tokens}"
                )

            logger.info("Successfully generated summary")
            return summary

        except Exception as e:
            error_msg = f"API call failed: {str(e)}"
            logger.error(error_msg)

            # Check for specific error types
            if "401" in str(e) or "unauthorized" in str(e).lower():
                raise APIError(
                    "Authentication failed. Please check your OPENROUTER_API_KEY in .env file",
                    status_code=401,
                )
            elif "429" in str(e) or "rate limit" in str(e).lower():
                raise APIError(
                    "Rate limit exceeded. Please wait and try again.",
                    status_code=429,
                )
            elif "timeout" in str(e).lower():
                raise APIError(
                    "API request timed out. The PDF might be too large or the server is slow.",
                    status_code=408,
                )
            else:
                raise APIError(error_msg, response=str(e))

    def estimate_tokens(self, text: str) -> int:
        """
        Estimate token count for text.

        This is a rough estimate: ~4 characters per token.

        Args:
            text: Text to estimate

        Returns:
            Estimated token count
        """
        return len(text) // 4
