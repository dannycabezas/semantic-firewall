import logging
from typing import Any

import httpx
from core.exceptions import BackendError

logger = logging.getLogger(__name__)


class BackendProxyService:
    """
    Proxy service to the backend.

    Responsibility: Manage communication with the backend.
    """

    def __init__(self, backend_url: str, timeout: float = 30.0) -> None:
        """
        Initialize the proxy service.

        Args:
            backend_url: Backend URL
            timeout: Timeout for the requests (default: 30.0)
        """
        self._backend_url = backend_url
        self._timeout = timeout

    async def send_chat_message(self, message: str) -> dict[str, Any]:
        """
        Send a message to the backend and return the response.

        Args:
            message: Message to send

        Returns:
            Backend response as a dictionary

        Raises:
            BackendError: If there is an error in the communication
        """
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                logger.info(f"Sending message to the backend: {self._backend_url}")
                response = await client.post(
                    f"{self._backend_url}/api/chat", json={"message": message}
                )
                response.raise_for_status()
                data = response.json()
                logger.info(f"Backend response received: {response.status_code}")
                return data

        except httpx.HTTPError as e:
            logger.error(f"HTTP error from the backend: {e}")
            raise BackendError(
                message="Error communicating with the backend",
                details={"error": str(e), "backend_url": self._backend_url},
            ) from e
        except Exception as e:
            logger.error(f"Unexpected error contacting the backend: {e}")
            raise BackendError(
                message="Unexpected error communicating with the backend",
                details={"error": str(e)},
            ) from e
