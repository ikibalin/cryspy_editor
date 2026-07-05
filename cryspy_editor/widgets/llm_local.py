# local_llm.py

from llama_cpp import Llama
import json
import cryspy
from typing import List, Dict


def substring_from_char(s: str, ch: str) -> str:
    idx = s.find(ch)
    if idx == -1:
        return ""
    return s[idx:]

def substring_until_char(s: str, ch: str) -> str:
    idx = s.find(ch)
    if idx == -1:
        return s
    return s[:idx+1]

def get_json_part(s:str) -> str:
    return substring_until_char(substring_from_char(s, "{"), "}") 


class LLMLocal:
    def __init__(self, model_path: str, n_ctx: int = 4096, n_threads: int = 4):
        self.llm = Llama(
            model_path=model_path,
            n_ctx=n_ctx,
            n_threads=n_threads,
            verbose=False
        )
        self.history: List[Dict[str, str]] = []  # [{"role": "user"/"assistant", "content": "..."}]

    def _build_history_prompt(self) -> str:
        lines = []
        for turn in self.history[-10:]:  # last 10 turns
            lines.append(f"{turn['role'].upper()}: {turn['content']}")
        return "\n".join(lines)

    def ask(self, prompt: str, max_tokens: int = 512) -> str:
        history_text = self._build_history_prompt()
        history_text = ""
        full_prompt = history_text + ("\n" if history_text else "") + f"USER: {prompt}\nASSISTANT:"
        result = self.llm(
            full_prompt,
            max_tokens=max_tokens,
            stop=["</s>"],
            echo=False
        )
        answer = result["choices"][0]["text"].strip()
        self.history.append({"role": "user", "content": prompt})
        self.history.append({"role": "assistant", "content": answer})
        return answer

    def decide_if_action_required(self, question: str):
        system_prompt = """
You decide whether the user wants to perform an action on a CrysPy object
or just ask for general information.

If the user wants to modify or operate on the crystallographic model,
set requires_action = true. Also set requires_action = true if the user wants to display or show the crystallographic model or any part of this model. For all situation given in 'Possible actions' list given below set requires_action = true.

If the user is asking for general information (crystallography theory,
symmetry explanation, unit cell concepts, diffraction, or unrelated topics),
set requires_action = false.

Possible actions (even if not supported yet):
- refine
- fix_all_parameters
- show_refine_parameters
- show_model
- add_atoms
- delete_atoms
- modify_atom
- symmetry
- get_cell
- export_cif
- none

Respond ONLY with JSON:
{
  "requires_action": true/false,
  "action": "...",
  "explanation": "..."
}
"""
        full_prompt = system_prompt + "\nUser question: " + question
        raw = get_json_part(self.ask(full_prompt))
        try:
            decision = json.loads(raw)
        except Exception:
            return {
                "requires_action": False,
                "action": "none",
                "explanation": f"Invalid JSON: {raw}"
            }
        return decision

    def decide_and_execute(self, question: str, cryspy_obj):
        system_prompt = """
You choose ONE crystallographic action for CrysPy.

Allowed actions:
- refine
- fix_all_parameters
- show_refine_parameters
- show_model
- none
- ask_user

Respond ONLY with JSON:
{
  "action": "...",
  "explanation": "..."
}
"""
        full_prompt = system_prompt + "\nUser question: " + question
        raw = get_json_part(self.ask(full_prompt))
        try:
            decision = json.loads(raw)
        except Exception:
            return f"Model returned invalid JSON: {raw}"

        action = decision.get("action", "none")
        explanation = decision.get("explanation", "")

        if action == "refine":
            result = cryspy.rhochi_rietveld_refinement(cryspy_obj)
            explanation_2 = self.ask(f'The result of Rietveld refinement is given in dictionary as  {result:}. Please provide a small analysis of this refinement. Is it some parameters are correlated or chi_sq probably is not so good. ')
            return f"[Action: refine]\n{explanation}\n\nResult:\n{result}\n\n{explanation_2:}"
        elif action == "fix_all_parameters":
            cryspy_obj.fix_variables()
            return f"[Action: fix_all]\n{explanation}\n\nAll parameters fixed."
        elif action == "show_refine_parameters":
            l_names = [hh[-1] for hh in cryspy_obj.get_variable_names()]
            explanation_2 = self.ask(f'In my model the following paraemeters are refined  {l_names:}. Please rewrite it in markdown table. The first value is name and the second one (if exist), it is subindex.')
            return f"[Action: show_refine_parameters]\n{explanation}\n\n{explanation_2}."
        elif action == "show_model":
            result = cryspy_obj.to_cif()
            explanation_2 = self.ask(f'Base on this model in CIF format  provide a short resume about the model: {result:}.')
            return f"[Action: show_model]\n{explanation}\n\n{explanation_2}."
        elif action == "ask_user":
            return (
                f"[Action: ask_user]\n{explanation}\n\n"
                "Please clarify what you want to do with the current crystallographic object."
            )
        else:
            return f"[Action: none]\n{explanation}\n\nNo crystallographic operation executed."
