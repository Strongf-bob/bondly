import json
from datetime import datetime
from typing import Any

import httpx
from pydantic import ValidationError

from bondly.llm.prompts import EXTRACTION_SYSTEM_PROMPT, INTENT_SYSTEM_PROMPT
from bondly.llm.schemas import ChatIntent, MessageExtraction


class LlmError(RuntimeError):
    pass


class LlmClient:
    def __init__(
        self,
        base_url: str,
        api_key: str,
        model: str,
        timeout_seconds: float = 30.0,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._model = model
        self._timeout_seconds = timeout_seconds

    async def classify_intent(self, message: str) -> ChatIntent:
        payload = await self._chat_completion(
            system_prompt=INTENT_SYSTEM_PROMPT,
            user_prompt=message,
        )
        try:
            return ChatIntent.model_validate_json(payload)
        except ValidationError as exc:
            raise LlmError("LLM returned invalid intent JSON.") from exc

    async def extract_message(
        self,
        message: str,
        now: datetime,
        timezone: str,
    ) -> MessageExtraction:
        user_prompt = (
            f"Current datetime: {now.isoformat()}\n"
            f"Timezone: {timezone}\n"
            f"User message: {message}"
        )
        payload = await self._chat_completion(
            system_prompt=EXTRACTION_SYSTEM_PROMPT,
            user_prompt=user_prompt,
        )
        try:
            return MessageExtraction.model_validate_json(payload)
        except ValidationError as exc:
            raise LlmError("LLM returned invalid extraction JSON.") from exc

    async def _chat_completion(self, system_prompt: str, user_prompt: str) -> str:
        body = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.1,
            "response_format": {"type": "json_object"},
        }
        headers = {"Authorization": f"Bearer {self._api_key}"}
        try:
            async with httpx.AsyncClient(timeout=self._timeout_seconds) as client:
                response = await client.post(
                    f"{self._base_url}/chat/completions",
                    json=body,
                    headers=headers,
                )
        except httpx.RequestError as exc:
            raise LlmError("LLM API request failed before receiving a response.") from exc

        if response.status_code >= 400:
            raise LlmError(f"LLM API request failed with status {response.status_code}.")

        return self._extract_content(response.json())

    def _extract_content(self, payload: dict[str, Any]) -> str:
        try:
            content = payload["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise LlmError("LLM API response does not match chat completions format.") from exc

        if isinstance(content, str):
            return content
        return json.dumps(content, ensure_ascii=False)
