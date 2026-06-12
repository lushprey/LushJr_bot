"""
integrations/nvidia_ai.py
──────────────────────────
Implementación de AIProvider usando la API de Nvidia (compatible OpenAI).
"""
import json
import logging
from datetime import datetime

from openai import OpenAI

from core.ai_provider import AIProvider, IntentResult

logger = logging.getLogger(__name__)

SYSTEM_INTENT_TEMPLATE = """\
Tu nombre es LushJr.
Eres el cerebro de un asistente personal en Telegram conectado a un calendario.
Hoy es {fecha_hoy} ({dia_semana}).

Tu única tarea es analizar el mensaje del usuario y devolver un JSON con esta estructura exacta:

{{
  "accion": "consultar" | "crear" | "editar" | "eliminar" | "chat",
  "fecha_inicio": "YYYY-MM-DD",
  "fecha_fin": "YYYY-MM-DD",
  "hora_inicio": "HH:MM",
  "hora_fin": "HH:MM",
  "titulo": "nombre del evento",
  "lugar": "lugar del evento",
  "descripcion": "descripción del evento",
  "event_id": "id de notion si el usuario lo menciona",
  "respuesta_directa": "texto solo si accion es chat"
}}

Reglas:
- Incluye solo los campos relevantes al mensaje, omite los demás
- "consultar": el usuario pregunta por eventos
- "crear": el usuario quiere agendar, agregar o crear un evento
- "editar": el usuario quiere modificar un evento existente
- "eliminar": el usuario quiere borrar o cancelar un evento
- "chat": cualquier otra pregunta o conversación
- Para fechas relativas usa la fecha de hoy como referencia
- Para "esta semana" usa fecha_fin = hoy + 6 días
- Si el usuario dice "a las 3pm" → hora_inicio: "15:00"
- Si el usuario dice "de 2 a 4" → hora_inicio: "14:00", hora_fin: "16:00"
- SOLO devuelve el JSON, sin explicaciones ni markdown
"""


class NvidiaAIProvider(AIProvider):

    def __init__(self, api_key: str, model: str = "meta/llama-3.3-70b-instruct"):
        self.client = OpenAI(
            base_url="https://integrate.api.nvidia.com/v1",
            api_key=api_key,
        )
        self.model = model

    def detect_intent(self, message: str, context: dict) -> IntentResult:
        system_prompt = SYSTEM_INTENT_TEMPLATE.format(
            fecha_hoy=context.get("fecha_hoy", datetime.now().strftime("%Y-%m-%d")),
            dia_semana=context.get("dia_semana", datetime.now().strftime("%A")),
        )

        completion = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": message},
            ],
            temperature=0.2,
            max_tokens=300,
        )

        raw = completion.choices[0].message.content.strip()
        raw = raw.replace("```json", "").replace("```", "").strip()

        data = json.loads(raw)
        return IntentResult.from_dict(data)

    def chat(self, message: str, system_prompt: str) -> str:
        completion = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": message},
            ],
            temperature=0.7,
            max_tokens=1024,
        )
        return completion.choices[0].message.content.strip()