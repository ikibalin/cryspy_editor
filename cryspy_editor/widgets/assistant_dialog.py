"""Questions of the AI assistant to the user, without Qt.

A tool that lacks information (unit cell, space group, wavelength...)
says which values to ask (in CrysPy Editor: the key "missing" of the
result of a CrysPy tool, see assistant_tools.form_dialog); the assistant
asks the questions one by one in a Dialog, the answers of the user are
read here without the model, and when all values are known the action is
finished with them.

The same module is in PyColl5 (assistant_dialog.py): keep them identical.
"""
import re
from dataclasses import dataclass
from typing import Any, Callable, Optional

# the first word of the answer (English, Russian, French, German)
YES_WORDS = frozenset((
    "yes", "y", "yeah", "yep", "ok", "okay", "sure", "right", "correct", "true",
    "да", "ага", "ок", "верно", "правильно", "конечно",
    "oui", "ouais", "d'accord", "exact", "exactement",
    "ja", "jawohl", "genau", "richtig", "stimmt"))
NO_WORDS = frozenset((
    "no", "n", "nope", "wrong", "false", "incorrect",
    "нет", "неверно", "неправильно",
    "non", "faux",
    "nein", "falsch"))
ALL_INFORMATION = "Now I have all the information to perform the calculations."
CANCEL_WORDS = frozenset((
    "cancel", "stop", "abort", "quit", "exit",
    "отмена", "отменить", "отмени", "стоп", "хватит",
    "annuler", "annule", "arrêter", "arrête", "arrêt",
    "abbrechen", "abbruch", "stopp", "halt"))


def take_first_word(text: str) -> str:
    l_word = re.findall(r"[\w']+", str(text).lower())
    return l_word[0] if l_word else ""


def is_yes(text: str) -> bool:
    return take_first_word(text) in YES_WORDS


def is_no(text: str) -> bool:
    return take_first_word(text) in NO_WORDS


def is_cancel(text: str) -> bool:
    return take_first_word(text) in CANCEL_WORDS


@dataclass
class Question:
    """One value asked from the user.

    key: name of the value in Dialog.values;
    text: what is asked, e.g. "the unit cell parameters";
    read(answer) -> value: raises ValueError (TypeError, KeyError) when the
    answer is not understood;
    proposal: value known already (e.g. from the data), the user confirms it
    with "yes"; s_proposal: its text, describe(proposal) if empty;
    hint: the format of the answer, e.g. "a b c alpha beta gamma";
    skip(values) -> True when the question is not needed;
    describe(value) -> text of the value in the replies."""

    key: str
    text: str
    read: Callable[[str], Any]
    proposal: Any = None
    s_proposal: str = ""
    hint: str = ""
    skip: Optional[Callable[[dict], bool]] = None
    describe: Callable[[Any], str] = str

    def is_skipped(self, values: dict) -> bool:
        if self.skip is None:
            return False
        try:
            return bool(self.skip(values))
        except (KeyError, TypeError):
            return False


class Dialog:
    """Questions of an action: asked one by one, then
    finish(values) -> result text of the action."""

    def __init__(self, name: str, questions: list, finish: Callable[[dict], str],
                 intro: str = "", values: Optional[dict] = None):
        self.name = name
        self.questions = list(questions)
        self._finish = finish
        self.intro = intro
        self.values = dict(values) if values else {}
        self.n_asked = 0  # answered questions: the number of the current one is n_asked + 1
        self.l_dropped = []  # keys of the proposals refused by the user

    def _l_left(self) -> list:
        return [question for question in self.questions
                if question.key not in self.values and not question.is_skipped(self.values)]

    def current(self) -> Optional[Question]:
        l_left = self._l_left()
        return l_left[0] if l_left else None

    def is_done(self) -> bool:
        return self.current() is None

    def n_left(self) -> int:
        return len(self._l_left())

    def _proposal(self, question: Question):
        if question.key in self.l_dropped:
            return None
        return question.proposal

    def start(self) -> str:
        s_intro = f"{self.intro}\n" if self.intro else ""
        return (f"{s_intro}I understood, but some information is missing. I have {self.n_left()} questions; "
                f"reply to them one by one ('cancel' to stop).\n{self.prompt()}")

    def prompt(self) -> str:
        question = self.current()
        if question is None:
            return ""
        n = self.n_asked + 1
        proposal = self._proposal(question)
        if proposal is not None:
            s_proposal = question.s_proposal or question.describe(proposal)
            s_hint = f" ({question.hint})" if question.hint else ""
            return (f"Q{n}: Am I right that {question.text} is {s_proposal}? "
                    f"Answer yes or give the correct value{s_hint}.")
        s_hint = f" ({question.hint})" if question.hint else ""
        return f"Q{n}: What is {question.text}{s_hint}?"

    def answer(self, text: str) -> tuple:
        """(flag_taken, message): flag_taken is False when the answer is not
        understood and the same question is asked again."""
        question = self.current()
        if question is None:
            return False, "No question is asked."
        proposal = self._proposal(question)
        if proposal is not None and is_yes(text):
            value = proposal
            message = f"Ok: {question.text} is {question.describe(value)}."
        else:
            try:
                value = question.read(text)
            except (ValueError, TypeError, KeyError, IndexError) as e:
                if proposal is not None and is_no(text):
                    self.l_dropped.append(question.key)
                    return False, "Then give the correct value."
                return False, f"Not understood: {e}"
            message = f"Thank you: {question.text} is {question.describe(value)}."
        self.values[question.key] = value
        self.n_asked += 1
        if self.is_done():
            message += f"\n{ALL_INFORMATION}"
        return True, message

    def finish(self):
        return self._finish(dict(self.values))
