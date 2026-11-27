"""Claude as the judge model for DeepEval metrics.

DeepEval's built-in Anthropic model sends a temperature, which current Claude models reject,
so we plug our own client in through DeepEval's custom model interface.
When a metric asks for structured output (schema), we use the API's structured outputs.
The model is settings.judge_model (env var JUDGE_MODEL, Haiku by default).
"""
import anthropic
from deepeval.models import DeepEvalBaseLLM

from config import settings

# $ per million tokens (input, output), only to estimate the cost of a run
PRICES = {
    "claude-haiku-5-5": (0.10, 0.50),
    "claude-sonnet-5-5": (2.00, 10.00),
    "claude-opus-5-5": (4.00, 20.00),
}


def estimate_cost(model, usage):
    """Cost in dollars of the given token usage, or None for a model missing from PRICES."""
    if model not in PRICES:
        return None
    input_price, output_price = PRICES[model]
    return (usage["input_tokens"] * input_price + usage["output_tokens"] * output_price) / 1_000_000


class ClaudeJudge(DeepEvalBaseLLM):
    def __init__(self, model=None, effort="low"):
        self.model_id = model or settings.judge_model
        self.effort = effort
        self.client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        self.async_client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
        # Running total of this judge's calls, read by the tests to log the cost of each question
        self.usage = {"calls": 0, "input_tokens": 0, "output_tokens": 0}
        super().__init__(self.model_id)

    def _track(self, response):
        self.usage["calls"] += 1
        self.usage["input_tokens"] += response.usage.input_tokens
        self.usage["output_tokens"] += response.usage.output_tokens
        return response

    def load_model(self):
        return self.client

    def get_model_name(self):
        return self.model_id

    def _params(self, prompt):
        return {
            "model": self.get_model_name(),
            "max_tokens": 16000,
            "output_config": {"effort": self.effort},
            "messages": [{"role": "user", "content": prompt}],
        }

    @staticmethod
    def _text(response):
        return "".join(block.text for block in response.content if block.type == "text")

    def generate(self, prompt, schema=None):
        if schema is not None:
            try:
                return self._track(self.client.messages.parse(**self._params(prompt), output_format=schema)).parsed_output
            except anthropic.BadRequestError:
                pass  # schema not supported by structured outputs: DeepEval will parse the JSON text itself
        return self._text(self._track(self.client.messages.create(**self._params(prompt))))

    async def a_generate(self, prompt, schema=None):
        if schema is not None:
            try:
                response = await self.async_client.messages.parse(**self._params(prompt), output_format=schema)
                return self._track(response).parsed_output
            except anthropic.BadRequestError:
                pass
        return self._text(self._track(await self.async_client.messages.create(**self._params(prompt))))
