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
can you do?" is answered from the recipes and the actions (is_capability_
question, form_capabilities_text), with or without a model.
"""
import json
import re
import shlex
from typing import List, Optional, Tuple

from cryspy_editor.widgets.assistant_tools import D_TOOLS

COMMAND_PREFIX = "@"
RE_COMMAND = re.compile(r"^@([A-Za-z_][A-Za-z0-9_]*)\s*(.*)$", re.DOTALL)
RE_CAPABILITY = re.compile(
    r"^\s*(what (else )?(can|could) you do|what are you able to do|what do you (know|do)|"
    r"help|\?|@|"
    r"что (ты )?(еще |ещё )?(умеешь|можешь)( делать)?|что умеет ассистент|помощь|"
    r"que (sais|peux)-tu faire|was kannst du)\s*[?!.]*\s*$", re.IGNORECASE)
N_MAX_DESCRIPTION = 90


def take_recipes() -> list:
    """The recipes of CrysPy (and of the user); empty for an older CrysPy."""
    try:
        from cryspy.procedure_assistant.recipes import take_recipes as take_cryspy_recipes
    except ImportError:
        return []
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
    return RE_CAPABILITY.match(text) is not None


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
