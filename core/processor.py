"""
core/processor.py
──────────────────

Now uses a tool-driven architecture where:
1. Directive provides available tools
2. AI chooses which tool to use
3. Processor executes the tool
4. Result is returned to user
"""
import logging

from integrations.base import AIProvider, Directive

logger = logging.getLogger(__name__)


class MessageProcessor:

    def __init__(self, ai: AIProvider, directive: Directive):
        self.ai = ai
        self.directive = directive

    def process(self, message: str) -> str:
        """
        Process user message using directive tools and AI.
        
        Flow:
        1. Get available tools from directive
        2. Call AI with tools and system prompt
        3. Execute chosen tool
        4. Return result
        """
        try:
            # Get available tools and system prompt from directive
            tools = self.directive.get_tools()
            system_prompt = self.directive.get_system_prompt()
            
            # Call AI with tools (AI chooses which tool to use)
            logger.info(f"Processing: {message}")
            tool_call = self.ai.call_with_tools(message, tools, system_prompt)
            logger.info(f"Tool chosen: {tool_call.tool_name} with params: {tool_call.params}")
            
            # Handle chat tool specially - use the AI's chat method
            if tool_call.tool_name == "chat":
                result = self.ai.chat(message, system_prompt)
                logger.info(f"Chat result: {result}")
                return result
            
            # Find the tool by name
            tool = next((t for t in tools if t.name == tool_call.tool_name), None)
            if tool is None:
                logger.warning(f"Tool not found: {tool_call.tool_name}")
                return f"❌ Tool not found: {tool_call.tool_name}"
            
            # Execute the tool
            result = tool.execute(tool_call.params)
            r_message = next((x for x in result if isinstance(x, str)), "")
            success = next((x for x in result if isinstance(x, bool)), False)

            logger.info(f"Tool result: {r_message}")
            if success is False:
                logger.warning(f"Tool execution failed: {r_message}")
                return r_message
            result = self.ai.chat(r_message, system_prompt)  # Post-process tool response with AI for better formatting
            logger.info(f"Final response: {result}")
            return result
            
        except Exception as e:
            logger.exception(f"Error processing message: {e}")
            return f"❌ Error: {str(e)}"
