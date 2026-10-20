"""Actions of the AI assistant, without Qt.

The actions are the tools of CrysPy (cryspy.call_assistant_tool): CrysPy
Editor keeps no tools of its own. This module is the counterpart of
assistant_tools.py of PyColl5, where the actions work on the list of scans.
"""
from typing import Dict

from cryspy import call_assistant_tool
from cryspy.procedure_assistant.tools import L_ASSISTANT_TOOLS, AssistantTool

D_TOOLS: Dict[str, AssistantTool] = {tool.name: tool for tool in L_ASSISTANT_TOOLS}

# Actions that return information rather than change the object: the model
# answers the request from their results. calculate and refine change the
# object but their chi-square and refined values are what the user asks for.
SET_ANSWER_ACTIONS = {"calculate", "refine"}


def is_answer_tool(name: str) -> bool:
    """True if the model answers from the result of the action."""
    tool = D_TOOLS.get(name)
    if tool is None:
        return False
    return (not tool.flag_object_changed) or name in SET_ANSWER_ACTIONS


def form_tools_text() -> str:
    """The actions with their arguments for the system prompt."""
    return "\n".join(tool.to_short_text() for tool in L_ASSISTANT_TOOLS)


def run_tool(name: str, cryspy_object, arguments: dict) -> tuple:
    """(result text, flag_object_changed) of the action; errors are text
    starting with "Error", so that the model can correct the call."""
    result = call_assistant_tool(cryspy_object, name, arguments)
    return str(result["text"]), bool(result["flag_object_changed"])
