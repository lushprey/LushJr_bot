"""
integrations/core_ai/provider.py
─────────────────────────────────
Implementación de AIProvider usando la API de Nvidia (compatible OpenAI).
OPTIMIZADO: una sola llamada por mensaje + streaming para respuesta inmediata.
"""
import json
import logging
from datetime import datetime
from typing import List

from openai import OpenAI

from integrations.base import AIProvider, IntentResult, Tool, ToolCall

logger = logging.getLogger(__name__)

# Prompt unificado: detecta intención Y genera respuesta en una sola llamada.
SYSTEM_UNIFIED_TEMPLATE = """\
Tu nombre es LushJr. Eres un asistente personal en Telegram con acceso a un calendario.
Hoy es {fecha_hoy} ({dia_semana}).

Analiza el mensaje del usuario y responde con SOLO un JSON con esta estructura:
{{
  "tool": "consultar" | "crear" | "editar" | "eliminar" | "chat",
  "params": {{
    "fecha_inicio": "YYYY-MM-DD",
    "fecha_fin": "YYYY-MM-DD",
    "hora_inicio": "HH:MM",
    "hora_fin": "HH:MM",
    "titulo": "nombre del evento",
    "lugar": "lugar del evento",
    "descripcion": "descripción",
    "event_id": "id si el usuario lo menciona",
    "respuesta": "respuesta directa al usuario"
  }}
}}

Reglas:
- Incluye solo los campos relevantes, omite los demás
- "chat": cualquier conversación que no sea sobre el calendario
- Siempre incluye "respuesta" con un mensaje directo para el usuario, incluso si usas una herramienta
- Para fechas relativas usa hoy como referencia
- Si el usuario dice "a las 3pm" → hora_inicio: "15:00"
- Si el usuario dice "de 3pm a 5 pm" → hora_inicio: "15:00", hora_fin: "17:00"
- SOLO devuelve el JSON, sin markdown ni explicaciones
"""


class NvidiaAIProvider(AIProvider):

    def __init__(self, api_key: str, model: str = "meta/llama-3.1-8b-instruct"):
        self.client = OpenAI(
            base_url="https://integrate.api.nvidia.com/v1",
            api_key=api_key,
        )
        self.model = model
        self._system_prompt_cache: dict[str, str] = {}

    def _get_system_prompt(self, base_prompt: str) -> str:
        """Cachea el system prompt con la fecha del día."""
        today = datetime.now().strftime("%Y-%m-%d")
        if today not in self._system_prompt_cache:
            self._system_prompt_cache.clear()  # limpiar días anteriores
            self._system_prompt_cache[today] = SYSTEM_UNIFIED_TEMPLATE.format(
                fecha_hoy=today,
                dia_semana=datetime.now().strftime("%A"),
            )
        return self._system_prompt_cache[today]

    def detect_intent(self, message: str, context: dict) -> IntentResult:
        """Legacy — mantiene compatibilidad."""
        tool_call = self.call_with_tools(message, [], "")
        return IntentResult.from_dict({
            "accion": tool_call.tool_name,
            **tool_call.params,
        })

    def chat(self, message: str, system_prompt: str) -> str:
        """
        Genera respuesta de chat usando streaming para reducir latencia percibida.
        Solo se usa cuando processor necesita post-procesar un resultado de tool.
        """
        chunks = []
        with self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": message},
            ],
            temperature=0.7,
            max_tokens=512,  # reducido de 1024 — respuestas más concisas
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
        OPTIMIZADO: una sola llamada que detecta intención y parámetros.
        Elimina la doble llamada que causaba el retraso.
        """
        unified_prompt = self._get_system_prompt(system_prompt)

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
                return ToolCall(tool_name="chat", params={})

            data = json.loads(raw)
            return ToolCall(
                tool_name=data.get("tool", "chat"),
                params=data.get("params", {}),
            )

        except json.JSONDecodeError as e:
            logger.warning(f"JSON parse error: {e}. Defaulting to chat.")
            return ToolCall(tool_name="chat", params={})
        except Exception as e:
            logger.error(f"AI call failed: {e}")
            return ToolCall(tool_name="chat", params={"respuesta": f"❌ Error: {e}"})