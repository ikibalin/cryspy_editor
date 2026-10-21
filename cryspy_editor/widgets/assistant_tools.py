"""Actions of the AI assistant, without Qt.

The actions are the tools of CrysPy (cryspy.call_assistant_tool): CrysPy
Editor keeps no tools of its own. This module is the counterpart of
assistant_tools.py of PyColl5, where the actions work on the list of scans.
"""
from typing import Dict

import cryspy
from cryspy import call_assistant_tool
from cryspy.procedure_assistant.tools import L_ASSISTANT_TOOLS, AssistantTool

from cryspy_editor.widgets.assistant_dialog import Dialog, Question

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


def is_request_tool(name: str) -> bool:
    """True if the action takes the request of the user (argument
    "request"), e.g. to find the values given in it."""
    return bool(getattr(D_TOOLS.get(name), "flag_request", False))


def describe_value(value) -> str:
    """Text of an answer: lists without brackets ("5 6 4 90 90 90")."""
    if isinstance(value, (list, tuple)):
        return " ".join(describe_value(item) for item in value)
    if isinstance(value, float):
        return f"{value:g}"
    return str(value)


def form_dialog(name: str, cryspy_object, arguments: dict, result: dict) -> Dialog:
    """Dialog of the arguments of the action that CrysPy asks from the user
    (result["missing"], as MCP elicitation): CrysPy gives the questions and
    checks the answers (cryspy.convert_assistant_answer); when all are
    known, the action is called again with them."""
    l_question = [
        Question(d_missing["name"], d_missing.get("question", d_missing["name"]),
                 lambda text, d_missing=d_missing: cryspy.convert_assistant_answer(d_missing, text),
                 proposal=d_missing.get("proposal"), s_proposal=str(d_missing.get("s_proposal", "")),
                 hint=str(d_missing.get("hint", "")), describe=describe_value)
        for d_missing in result["missing"]]
    # the text is the message of the tool and "<name> needs to know: ..."
    l_line = str(result["text"]).split("\n")
    intro = "\n".join(l_line[:-1])

    def finish(values: dict):
        # text, or the next Dialog when the tool needs more values; without
        # the request: a tool that proposes values found in it would propose
        # them again instead of taking the answers
        d_argument = {key: value for key, value in arguments.items() if key != "request"}
        return run_tool(name, cryspy_object, dict(d_argument, **values))[0]
    return Dialog(name, l_question, finish, intro=intro)


def run_tool(name: str, cryspy_object, arguments: dict) -> tuple:
    """(result, flag_object_changed) of the action. The result is text;
    errors start with "Error", so that the model can correct the call and
    the answer never reports a failed action as done.

    When CrysPy asks values from the user (key "missing"), the result is a
    Dialog with its questions (form_dialog)."""
    result = call_assistant_tool(cryspy_object, name, arguments)
    if result.get("missing"):
        return form_dialog(name, cryspy_object, arguments, result), False
    text = str(result["text"])
    if result.get("flag_error", False) and not text.startswith("Error"):
        text = f"Error: {text}"
    return text, bool(result["flag_object_changed"])
