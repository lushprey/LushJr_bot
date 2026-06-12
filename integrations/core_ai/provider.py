"""
integrations/core_ai/provider.py
──────────────────────────────────────────
"""
import json
import logging
from datetime import datetime, timedelta
from typing import List

import locale
from openai import OpenAI

from integrations.base import AIProvider, IntentResult, Tool, ToolCall

logger = logging.getLogger(__name__)

# Día de la semana en inglés — no depende del locale del sistema
_WEEKDAYS_EN = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

SYSTEM_TEMPLATE = """\
Your name is LushJr. You are a personal assistant on Telegram with access to a calendar.
Today is {today} ({weekday}).
Tomorrow is {tomorrow}.
End of this week (6 days from today): {end_of_week}.
End of this month: {end_of_month}.

{directive_prompt}

Respond ONLY with a JSON object with this exact structure:
{{
  "tool": "<tool_name>",
  "params": {{ <parameters for the chosen tool> }}
}}

Date rules:
- Always use ISO format "YYYY-MM-DD" for dates
- Use today ({today}) as reference for relative dates
- "tomorrow" / "mañana" → {tomorrow}
- "this week" / "esta semana" → date_start: {today}, date_end: {end_of_week}
- "this month" / "este mes" → date_start: {today}, date_end: {end_of_month}
- "3pm" / "3 p.m." / "15h" → time_start: "15:00"
- "from 2 to 4" / "de 2 a 4" → time_start: "14:00", time_end: "16:00"

Available tools:
{tools_schema}

For the "chat" tool, include a "response" key in params with your direct reply to the user (in the same language the user wrote).
Return ONLY the JSON, no markdown, no extra text.
"""


def _calculate_end_of_month(today: datetime) -> str:
    if today.month == 12:
        end = today.replace(year=today.year + 1, month=1, day=1) - timedelta(days=1)
    else:
        end = today.replace(month=today.month + 1, day=1) - timedelta(days=1)
    return end.strftime("%Y-%m-%d")


class NvidiaAIProvider(AIProvider):

    def __init__(self, api_key: str, model: str = "meta/llama-3.1-8b-instruct"):
        self.client = OpenAI(
            base_url="https://integrate.api.nvidia.com/v1",
            api_key=api_key,
        )
        self.model = model
        self._prompt_cache: dict = {}

    def _build_tools_schema(self, tools: List[Tool]) -> str:
        lines = []
        for t in tools:
            required = ", ".join(t.required_params) if t.required_params else "none"
            lines.append(f'- "{t.name}": {t.description} | required params: {required}')
        return "\n".join(lines)

    def _build_system_prompt(self, tools: List[Tool], directive_prompt: str) -> str:
        today = datetime.now()
        today_str = today.strftime("%Y-%m-%d")

        cache_key = (today_str, id(directive_prompt))
        if cache_key in self._prompt_cache:
            return self._prompt_cache[cache_key]

        tomorrow_str = (today + timedelta(days=1)).strftime("%Y-%m-%d")
        end_of_week_str = (today + timedelta(days=6)).strftime("%Y-%m-%d")
        end_of_month_str = _calculate_end_of_month(today)
        weekday_str = _WEEKDAYS_EN[today.weekday()]  # siempre en inglés

        prompt = SYSTEM_TEMPLATE.format(
            today=today_str,
            weekday=weekday_str,
            tomorrow=tomorrow_str,
            end_of_week=end_of_week_str,
            end_of_month=end_of_month_str,
            directive_prompt=directive_prompt.strip(),
            tools_schema=self._build_tools_schema(tools),
        )

        self._prompt_cache.clear()  # limpiar días anteriores
        self._prompt_cache[cache_key] = prompt
        return prompt

    def detect_intent(self, message: str, context: dict) -> IntentResult:
        """Legacy — mantiene compatibilidad."""
        tool_call = self.call_with_tools(message, [], "")
        return IntentResult.from_dict({"accion": tool_call.tool_name, **tool_call.params})

    def chat(self, message: str, system_prompt: str) -> str:
        """Post-procesa resultados de tools que devuelven datos crudos (ej: query_events)."""
        chunks = []
        with self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": message},
            ],
            temperature=0.7,
            max_tokens=512,
            stream=True,
        ) as stream:
            for chunk in stream:
                delta = chunk.choices[0].delta.content
                if delta:
                    chunks.append(delta)
        return "".join(chunks).strip()

    def call_with_tools(
        self,
        message: str,
        tools: List[Tool],
        system_prompt: str,
    ) -> ToolCall:
        """
        Una sola llamada: detecta tool + params usando los nombres reales.
        El prompt se construye dinámicamente desde las tools registradas.
        """
        unified_prompt = self._build_system_prompt(tools, system_prompt)

        try:
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": unified_prompt},
                    {"role": "user", "content": message},
                ],
                temperature=0.2,
                max_tokens=400,
            )

            raw = completion.choices[0].message.content or ""
            raw = raw.replace("```json", "").replace("```", "").strip()

            if not raw:
                logger.warning("AI returned empty response, defaulting to chat.")
                return ToolCall(tool_name="chat", params={})

            data = json.loads(raw)
            tool_name = data.get("tool", "chat")

            valid_names = {t.name for t in tools} | {"chat"}
            if tool_name not in valid_names:
                logger.warning(f"Unknown tool '{tool_name}', defaulting to chat.")
                tool_name = "chat"

            return ToolCall(tool_name=tool_name, params=data.get("params", {}))

        except json.JSONDecodeError as e:
            logger.warning(f"JSON parse error: {e} | raw: {raw!r}")
            return ToolCall(tool_name="chat", params={})
        except Exception as e:
            logger.error(f"AI call failed: {e}")
            return ToolCall(tool_name="chat", params={"response": f"❌ Error: {e}"})