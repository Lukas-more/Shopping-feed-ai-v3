from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from openai import OpenAI, APITimeoutError, APIConnectionError, RateLimitError, APIError


@dataclass
class UsageCost:
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0


MODEL_PRICING = {
    "gpt-4o-mini": {"input": 0.15 / 1_000_000, "output": 0.60 / 1_000_000},
    "gpt-4.1-mini": {"input": 0.40 / 1_000_000, "output": 1.60 / 1_000_000},
    "gpt-4.1": {"input": 2.00 / 1_000_000, "output": 8.00 / 1_000_000},
}


def estimate_tokens(text: str) -> int:
    return max(1, int(len(text) / 4))


def estimate_cost(model: str, prompt: str, expected_output_tokens: int = 220) -> UsageCost:
    pricing = MODEL_PRICING.get(model, MODEL_PRICING["gpt-4o-mini"])
    input_tokens = estimate_tokens(prompt)
    output_tokens = expected_output_tokens
    cost = input_tokens * pricing["input"] + output_tokens * pricing["output"]
    return UsageCost(
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cost_usd=cost,
    )


class OpenAIOptimizer:
    def __init__(self, api_key: str, model: str):
        self.client = OpenAI(
            api_key=api_key,
            timeout=90,
            max_retries=4,
        )
        self.model = model

    def optimize_json(self, system_prompt: str, user_prompt: str) -> tuple[dict[str, Any], UsageCost]:
        resp = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.2,
            max_tokens=220,
            timeout=90,
        )

        content = resp.choices[0].message.content or "{}"
        usage = resp.usage
        pricing = MODEL_PRICING.get(self.model, MODEL_PRICING["gpt-4o-mini"])

        cost = 0.0
        if usage is not None:
            cost = (usage.prompt_tokens * pricing["input"]) + (usage.completion_tokens * pricing["output"])

        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            start = content.find("{")
            end = content.rfind("}")
            if start != -1 and end != -1 and end > start:
                data = json.loads(content[start:end + 1])
            else:
                raise ValueError(f"Model nevrátil validní JSON: {content}")

        return data, UsageCost(
            input_tokens=usage.prompt_tokens if usage else 0,
            output_tokens=usage.completion_tokens if usage else 0,
            cost_usd=cost,
        )