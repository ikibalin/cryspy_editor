"""Actions of the AI assistant, without Qt.

The actions are the tools of CrysPy (cryspy.call_assistant_tool): CrysPy
Editor keeps no tools of its own. This module is the counterpart of
assistant_tools.py of PyColl5, where the actions work on the list of scans.
"""
import inspect
import re
from typing import Dict

import cryspy
from cryspy import call_assistant_tool
from cryspy.procedure_assistant.recipes import recipes_as_text
from cryspy.procedure_assistant.tools import L_ASSISTANT_TOOLS, AssistantTool

from cryspy_editor.widgets.assistant_dialog import Dialog, Question

D_TOOLS: Dict[str, AssistantTool] = {tool.name: tool for tool in L_ASSISTANT_TOOLS}
# CrysPy reports the progress of long actions (newer than 0.17)
FLAG_PROGRESS = "progress" in inspect.signature(call_assistant_tool).parameters

# Actions that return information rather than change the object: the model
# answers the request from their results. calculate and refine (also
# refine_one_by_one) change the object but their chi-square and refined
# values are what the user asks for.
SET_ANSWER_ACTIONS = {"calculate", "refine", "refine_one_by_one"}


def is_answer_tool(name: str) -> bool:
    """True if the model answers from the result of the action."""
    tool = D_TOOLS.get(name)
    if tool is None:
        return False
    return (not tool.flag_object_changed) or name in SET_ANSWER_ACTIONS


# the system prompt must fit the context of small models (4096 tokens) with the
# history: an action is described by the first sentence of its description,
# at most MAX_DESCRIPTION characters
MAX_DESCRIPTION = 90
RE_SENTENCE_END = re.compile(r"(?<!\be\.g)(?<!\bi\.e)\.\s|;\s")


def shorten_description(text: str, max_length: int = MAX_DESCRIPTION) -> str:
    """The first sentence (or the part before ';'), cut at a word."""
    text = RE_SENTENCE_END.split(text.strip(), maxsplit=1)[0].rstrip(".")
    if len(text) <= max_length:
        return text
    return text[:max_length].rsplit(" ", 1)[0].rstrip(",:(") + " ..."


def form_tool_line(tool: AssistantTool) -> str:
    """'- name(argument, optional?): description' for the system prompt."""
    l_argument = [name if name in tool.required else f"{name}?" for name in tool.parameters]
    return f"- {tool.name}({', '.join(l_argument)}): {shorten_description(tool.description)}"


def form_tools_text() -> str:
    """The actions with their arguments for the system prompt (short: the
    model gets the whole description of an action from its error text or
    from list_methods/get_help when it needs more)."""
    return "\n".join(form_tool_line(tool) for tool in L_ASSISTANT_TOOLS)


# words of a recipe ('For:' of the recipe file) given in the system prompt
MAX_RECIPE_WORDS = 3


def form_recipes_text() -> str:
    """The recipes of CrysPy (typical algorithms) for the system prompt: the
    name, the title and the first requests they are for."""
    try:
        from cryspy.procedure_assistant.recipes import take_recipes
    except ImportError:  # older CrysPy
        return recipes_as_text()
    ls_out = []
    for recipe in take_recipes():
        l_when = [when.strip() for when in str(recipe.when).split(",") if when.strip()]
        s_when = f" (for: {', '.join(l_when[:MAX_RECIPE_WORDS])})" if l_when else ""
        ls_out.append(f"- {recipe.name}: {recipe.title}{s_when}")
    return "\n".join(ls_out)


def form_object_recipes_text(cryspy_object) -> str:
    """The kinds of the experiments of the object and their recipes
    (tool suggest_recipes of CrysPy); empty without experiments."""
    if cryspy_object is None:
        return ""
    result = call_assistant_tool(cryspy_object, "suggest_recipes")
    if result["flag_error"]:
        return ""
    return str(result["text"])


def form_request_methods_text(cryspy_object, request: str) -> str:
    """The methods of the object that fit the request (CrysPy
    form_matching_methods_text, newer than 0.17); empty when none fits:
    small models answer "cannot do" without looking the methods up."""
    if cryspy_object is None or "call_method" not in D_TOOLS:
        return ""
    try:
        from cryspy.procedure_assistant.methods import form_matching_methods_text
    except ImportError:  # older CrysPy
        return ""
    return form_matching_methods_text(cryspy_object, request)


def add_request_methods(question: str, cryspy_object) -> str:
    """The request with the methods that fit it after it."""
    text = form_request_methods_text(cryspy_object, question)
    return f"{question}\n\n({text})" if text else question


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


# buttons of one question: more are typed
MAX_OPTIONS = 5
# progress(info) of long actions (refinement iterations) while an action
# runs; returning False stops it (set_progress)
D_PROGRESS = {"callback": None}


def set_progress(callback=None):
    """Call callback(info) after every iteration of a long action (CrysPy
    with progress in call_assistant_tool); None: no progress."""
    D_PROGRESS["callback"] = callback


def take_options(d_missing: dict) -> tuple:
    """Possible answers of a question of CrysPy shown as buttons: its
    options, else the allowed values (enum), else yes/no for a boolean."""
    l_option = d_missing.get("options") or []
    if not l_option and 0 < len(d_missing.get("enum") or []) <= MAX_OPTIONS:
        l_option = d_missing["enum"]
    if not l_option and d_missing.get("type") == "boolean":
        l_option = ["yes", "no"]
    return tuple(str(option) for option in l_option[:MAX_OPTIONS])


def form_dialog(name: str, cryspy_object, arguments: dict, result: dict) -> Dialog:
    """Dialog of the arguments of the action that CrysPy asks from the user
    (result["missing"], as MCP elicitation): CrysPy gives the questions and
    checks the answers (cryspy.convert_assistant_answer); when all are
    known, the action is called again with them."""
    l_question = [
        Question(d_missing["name"], d_missing.get("question", d_missing["name"]),
                 lambda text, d_missing=d_missing: cryspy.convert_assistant_answer(d_missing, text),
                 proposal=d_missing.get("proposal"), s_proposal=str(d_missing.get("s_proposal", "")),
                 hint=str(d_missing.get("hint", "")), describe=describe_value,
                 options=take_options(d_missing))
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


def run_tool(name: str, cryspy_object, arguments: dict, flag_user: bool = False) -> tuple:
    """(result, flag_object_changed) of the action. The result is text;
    errors start with "Error", so that the model can correct the call and
    the answer never reports a failed action as done.

    When CrysPy asks values from the user (key "missing"), the result is a
    Dialog with its questions (form_dialog). flag_user: the user typed the
    action ('@name'), so the required arguments not given are asked too."""
    if D_PROGRESS["callback"] is not None and FLAG_PROGRESS:
        result = call_assistant_tool(cryspy_object, name, arguments, ask_required=flag_user,
                                     progress=D_PROGRESS["callback"])
    else:
        result = call_assistant_tool(cryspy_object, name, arguments, ask_required=flag_user)
    if result.get("missing"):
        return form_dialog(name, cryspy_object, arguments, result), False
    text = str(result["text"])
    if result.get("flag_error", False) and not text.startswith("Error"):
        text = f"Error: {text}"
    return text, bool(result["flag_object_changed"])


def suggest_requests(cryspy_object) -> list:
    """[(label, request)] proposed as buttons on an empty chat: made by
    CrysPy from the object (cryspy.suggest_assistant_requests), or the
    same few for every object with an older CrysPy."""
    suggest = getattr(cryspy, "suggest_assistant_requests", None)
    if suggest is not None:
        try:
            return [(str(item["label"]), str(item["request"])) for item in suggest(cryspy_object)]
        except Exception:  # a proposal must never break the chat
            pass
    return [("Summarize the data", "@summarize_object"), ("What can you do?", "What can you do?")]
