"""
integrations/core_ai/provider.py
─────────────────────────────────
Implementación de AIProvider usando la API de Nvidia (compatible OpenAI).
Ahora con soporte para function calling (call_with_tools).
"""
import json
import logging
from datetime import datetime
from typing import List, Optional

from openai import OpenAI

from integrations.base import AIProvider, IntentResult, Tool, ToolCall

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

    def __init__(self, api_key: str, model: str = "meta/llama-3.3-8b-instruct"):
        self.client = OpenAI(
            base_url="https://integrate.api.nvidia.com/v1",
            api_key=api_key,
        )
        self.model = model

    def detect_intent(self, message: str, context: dict) -> IntentResult:
        """Legacy method for backward compatibility."""
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
        """Generate freeform chat response."""
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

    def call_with_tools(
        self,
        message: str,
        tools: List[Tool],
        system_prompt: str
    ) -> ToolCall:
        """
        Call AI with available tools and get structured tool call.
        
        The AI will choose which tool to use and what parameters to pass.
        """
        # Build function schema for OpenAI function calling
        functions = []
        for tool in tools:
            function_def = {
                "name": tool.name,
                "description": tool.description,
                "parameters": {
                    "type": "object",
                    "properties": {
                        param: {"type": "string"}
                        for param in tool.required_params
                    },
                    "required": tool.required_params,
                }
            }
            functions.append(function_def)
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": message},
        ]
        
        # For Nvidia API compatibility, try to use function calling if available
        try:
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                functions=functions,
                temperature=0.2,
                max_tokens=500,
            )
            
            # Parse function call from response
            response_message = completion.choices[0].message
            
            if response_message.function_call:
                tool_name = response_message.function_call.name
                params = json.loads(response_message.function_call.arguments)
                return ToolCall(tool_name=tool_name, params=params)
        except Exception as e:
            logger.warning(f"Function calling failed: {e}. Falling back to JSON parsing.")
        
        # Fallback: ask AI to return JSON with tool choice
        tool_descriptions = "\n".join([
            f"- {tool.name}: {tool.description} (params: {', '.join(tool.required_params)})"
            for tool in tools
        ])
        
        fallback_prompt = f"""{system_prompt}

Available tools:
{tool_descriptions}

Respond with ONLY a JSON object like this:
{{
  "tool": "tool_name_here",
  "params": {{"param1": "value1", "param2": "value2"}}
}}
"""
        completion = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": fallback_prompt},
                {"role": "user", "content": message},
            ],
            temperature=0.2,
            max_tokens=500,
        )
        
        raw = completion.choices[0].message.content.strip() if completion.choices[0].message.content else ""
        raw = raw.replace("```json", "").replace("```", "").strip()
        
        # If response is empty or invalid JSON, default to chat tool
        if not raw:
            logger.warning("AI returned empty response, defaulting to chat tool")
            return ToolCall(tool_name="chat", params={})
        
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse JSON response '{raw}': {e}. Defaulting to chat tool.")
            return ToolCall(tool_name="chat", params={})
        
        return ToolCall(
            tool_name=data.get("tool", "chat"),
            params=data.get("params", {})
        )
