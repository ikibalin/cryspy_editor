"""Commands of the AI assistant typed by the user, without Qt.

'@name' runs a recipe of CrysPy or an action (tool) directly, without the
model choosing it:

    @refine_structure                      the recipe, step by step
    @refine_flip_ratio_nuclear refine Ho1  the recipe with a remark for the model
    @refine_parameters scale               an action with its only argument
    @set_parameter path=cell.length_a value=5.43
    @list_parameters {"refined_only": true}

Without a model a recipe runs literally (cryspy.run_recipe). The input line
proposes the names after '@' (form_completions). A question such as "what
can you do?", also after a greeting, is answered from the recipes and the
actions (is_capability_question, form_capabilities_text), with or without a
model; a greeting alone without a model by GREETING_TEXT (is_greeting).
"""
import json
import re
import shlex
from typing import List, Optional, Tuple

from cryspy_editor.widgets.assistant_tools import D_TOOLS

COMMAND_PREFIX = "@"
RE_COMMAND = re.compile(r"^@([A-Za-z_][A-Za-z0-9_]*)\s*(.*)$", re.DOTALL)
# a greeting before a question ("Hi, what can you do?") or alone ("Hello!")
S_GREETING = (r"(hi|hello|hey|good (morning|afternoon|evening)|greetings|"
              r"привет(ствую)?|здравствуй(те)?|добрый (день|вечер)|доброе утро|"
              r"bonjour|salut|hallo|guten tag)")
S_PLEASE = r"((please|пожалуйста|s'il te pla[iî]t|bitte)\s*[,.!]?\s*)?"
S_CAPABILITY = (
    r"what (else )?(can|could) you do( for me)?|what (else )?you (can|could) do|"
    r"what are you able to do|what do you (know|do)|what are your (capabilities|skills|functions|abilities)|"
    r"what can i (ask|do with) you|what can you help( me)?( with)?|how can you help( me)?|"
    r"who are you|tell me (about yourself|what you can do)|help|\?|@|"
    r"что (ты )?(еще |ещё )?(умеешь|можешь)( делать)?|что ты (еще |ещё )?(умеешь|можешь)( делать)?|"
    r"что умеет ассистент|какие у тебя (есть )?(возможности|функции)|чем (ты )?(можешь )?помочь|"
    r"кто ты|расскажи,? что (ты )?умеешь|помощь|"
    r"que (sais|peux)-tu faire|qu'est-ce que tu (sais|peux) faire|was kannst du( tun| machen)?")
S_TARGET = r"(\s+(in|with|в|dans) (cryspy editor|cryspy|this program|этой программе))?"
RE_CAPABILITY = re.compile(
    rf"^\s*({S_GREETING}\s*[,.!]*\s*)?{S_PLEASE}({S_CAPABILITY}){S_TARGET}\s*[?!.]*\s*$", re.IGNORECASE)
RE_GREETING = re.compile(rf"^\s*{S_GREETING}(\s+(there|all|everyone|всем))?\s*[,.!)]*\s*$", re.IGNORECASE)
N_MAX_DESCRIPTION = 90


def take_recipes() -> list:
    """The recipes of CrysPy (and of the user)."""
    from cryspy.procedure_assistant.recipes import take_recipes as take_cryspy_recipes
    return take_cryspy_recipes()


def take_recipe_names() -> List[str]:
    return [recipe.name for recipe in take_recipes()]


def parse_command(text: str) -> Optional[Tuple[str, str]]:
    """(name, the rest of the text) of '@name ...', else None."""
    match = RE_COMMAND.match(text.strip())
    if match is None:
        return None
    return match.group(1), match.group(2).strip()


def parse_command_arguments(name: str, text: str) -> dict:
    """Arguments of an action written after its name: a JSON object,
    key=value pairs, or the value of its only (or only required) argument.
    Raises ValueError for text that is none of them."""
    text = text.strip()
    if text == "":
        return {}
    if text.startswith("{"):
        try:
            arguments = json.loads(text)
        except json.JSONDecodeError as error:
            raise ValueError(f"the arguments are not JSON: {error.msg}") from None
        if not isinstance(arguments, dict):
            raise ValueError("the arguments are not a JSON object")
        return arguments
    if re.match(r"^[A-Za-z_][A-Za-z0-9_]*\s*=", text):
        arguments = {}
        for word in shlex.split(text):
            if "=" not in word:
                raise ValueError(f"'{word}' is not key=value")
            key, value = word.split("=", 1)
            arguments[key.strip()] = value
        return arguments
    tool = D_TOOLS[name]
    l_parameter = list(getattr(tool, "parameters", {}) or {})
    l_name = list(getattr(tool, "required", []) or []) or l_parameter
    if len(l_name) != 1:
        raise ValueError(f"{name} has several arguments: write them as key=value "
                         f"({', '.join(l_parameter)})")
    return {l_name[0]: text}


def shorten(text: str, n_max: int = N_MAX_DESCRIPTION) -> str:
    text = " ".join(str(text).split())
    return text if len(text) <= n_max else text[:n_max - 3].rstrip() + "..."


def form_completions() -> List[Tuple[str, str]]:
    """('@name', short description) of the recipes, then of the actions,
    for the hints of the input line."""
    l_out = [(f"{COMMAND_PREFIX}{recipe.name}", f"recipe: {shorten(recipe.title)}")
             for recipe in take_recipes()]
    l_recipe = [name for name, _ in l_out]
    l_out.extend((f"{COMMAND_PREFIX}{name}", shorten(getattr(tool, "description", "")))
                 for name, tool in D_TOOLS.items() if f"{COMMAND_PREFIX}{name}" not in l_recipe)
    return l_out


def is_capability_question(text: str) -> bool:
    """A question about the assistant itself ("what can you do?", also after
    a greeting: "Hi, what you can do?"): answered by form_capabilities_text,
    not by the model (small models look for it in the documentation)."""
    return RE_CAPABILITY.match(text) is not None


def is_greeting(text: str) -> bool:
    """Only a greeting ("Hi!", "Привет"): answered by GREETING_TEXT."""
    return RE_GREETING.match(text) is not None


GREETING_TEXT = ("Hello! I am the assistant of CrysPy Editor: I work on the opened rcif file (parameters, "
                 "refinement, recipes of CrysPy...). Ask in your own words, write "
                 "\"what can you do?\" for the list of my actions and recipes, or type @ to choose one.")


def form_capabilities_text() -> str:
    """The recipes and the actions with short descriptions."""
    ls_out = ["I work on the opened rcif file with the actions of CrysPy. Ask in your own words, "
              "or type @name to run a recipe or an action directly (the names are proposed "
              "after @)."]
    l_recipe = take_recipes()
    if l_recipe:
        ls_out.append("\nRecipes (typical analyses, done step by step):")
        for recipe in l_recipe:
            s_kind = f" [for: {', '.join(recipe.kinds)}]" if recipe.kinds else ""
            ls_out.append(f"  @{recipe.name}: {recipe.title}{s_kind}")
    ls_out.append("\nActions:")
    ls_out.extend(f"  @{name}: {shorten(getattr(tool, 'description', ''))}" for name, tool in D_TOOLS.items())
    ls_out.append("\nExamples: @refine_parameters scale; @set_parameter path=cell.length_a value=5.43")
    return "\n".join(ls_out)
