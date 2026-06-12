"""
core/processor.py
──────────────────
OPTIMIZADO: elimina la segunda llamada a la IA tras ejecutar una tool.
Solo hace post-proceso con IA cuando el resultado del tool lo requiere.
"""
import logging

from integrations.base import AIProvider, Directive

logger = logging.getLogger(__name__)

# Tools que NO necesitan post-proceso con IA (su resultado ya es texto listo)
_PASSTHROUGH_TOOLS = {"chat"}


class MessageProcessor:

    def __init__(self, ai: AIProvider, directive: Directive):
        self.ai = ai
        self.directive = directive

    def process(self, message: str) -> str:
        """
        Procesa el mensaje del usuario.

        Flow optimizado:
        1. Una sola llamada a AI (detecta tool + params)
        2. Ejecuta tool
        3. Solo hace segunda llamada a AI si el tool devuelve datos crudos
           que necesitan formateo (ej: lista de eventos de Notion)
        """
        try:
            tools = self.directive.get_tools()
            system_prompt = self.directive.get_system_prompt()

            # Llamada única a la IA
            tool_call = self.ai.call_with_tools(message, tools, system_prompt)
            logger.info(f"Tool elegida: {tool_call.tool_name} | params: {tool_call.params}")

            # chat: respuesta directa sin tool externa
            if tool_call.tool_name == "chat":
                respuesta = tool_call.params.get("respuesta")
                if respuesta:
                    return respuesta  # ya viene en el JSON — 0 llamadas extra
                return self.ai.chat(message, system_prompt)

            # Buscar tool
            tool = next((t for t in tools if t.name == tool_call.tool_name), None)
            if tool is None:
                logger.warning(f"Tool no encontrada: {tool_call.tool_name}")
                return f"❌ Tool no encontrada: {tool_call.tool_name}"

            # Ejecutar tool
            result = tool.execute(tool_call.params)
            r_message = next((x for x in result if isinstance(x, str)), "")
            success = next((x for x in result if isinstance(x, bool)), False)

            if not success:
                logger.warning(f"Tool falló: {r_message}")
                return r_message

            # Post-proceso: solo si el resultado es datos crudos (ej: JSON de Notion)
            # Para "crear", "editar", "eliminar" el mensaje ya es legible → devolver directo
            if tool_call.tool_name == "consultar":
                return self.ai.chat(r_message, system_prompt)
            final_message = r_message if r_message else tool_call.params.get("respuesta")
            return str(final_message)  # crear/editar/eliminar: sin llamada extra

        except Exception as e:
            logger.exception(f"Error procesando mensaje: {e}")
            return f"❌ Error: {str(e)}"