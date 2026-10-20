"""Tests of the AI assistant logic without llama-cpp-python and Qt."""
import json
import os

import cryspy
import pytest

from cryspy_editor.widgets import llm_local
from cryspy_editor.widgets.llm_local import LLMLocal, take_json_object


class FakeLlama:
    """Returns prepared replies instead of running a model."""

    def __init__(self, replies, n_ctx=4096):
        self.replies = list(replies)
        self.l_messages = []
        self._n_ctx = n_ctx

    def n_ctx(self):
        return self._n_ctx

    def tokenize(self, text: bytes, add_bos=True):
        # about 4 characters per token, as for real models on English text
        return list(range((len(text) + 3) // 4))

    def create_chat_completion(self, messages, max_tokens=512, **kwargs):
        self.l_messages.append(messages)
        n_prompt = sum(len(self.tokenize(m["content"].encode())) + 8
                       for m in messages)
        if n_prompt + max_tokens > self._n_ctx:
            raise ValueError(
                f"Requested tokens ({n_prompt + max_tokens}) exceed context "
                f"window of {self._n_ctx}")
        return {"choices": [{"message": {"content": self.replies.pop(0)}}]}


def make_llm(replies):
    llm = LLMLocal.__new__(LLMLocal)
    llm.model_path = "fake.gguf"
    llm.llm = FakeLlama(replies)
    llm.history = []
    return llm


RCIF = """
global_

data_cell
_cell_length_a 5.0()
_cell_length_b 5.0
_cell_length_c 5.0
_cell_angle_alpha 90
_cell_angle_beta 90
_cell_angle_gamma 90
"""


def test_take_json_object():
    assert take_json_object('Sure! {"action": "none", "answer": "a {b}"} ok') == \
        {"action": "none", "answer": "a {b}"}
    assert take_json_object('{"a": {"b": 1}}') == {"a": {"b": 1}}
    assert take_json_object("{bad} then {\"a\": 1}") == {"a": 1}
    assert take_json_object("no json") is None


def reply(tool="none", answer="", **arguments):
    return json.dumps({"tool": tool, "arguments": arguments, "answer": answer})


def test_answer_without_tool():
    llm = make_llm([reply(answer="Bragg law")])
    result = llm.answer("What is Bragg law?", None)
    assert result["text"] == "Bragg law"
    assert result["flag_object_changed"] is False
    assert len(llm.history) == 2


def test_invalid_json_is_answer():
    llm = make_llm(["plain text"])
    result = llm.answer("hello", None)
    assert result["tools"] == []
    assert result["text"] == "plain text"


def test_old_action_key_is_accepted():
    llm = make_llm([json.dumps({"action": "none", "answer": "ok"})])
    assert llm.answer("hi", None)["text"] == "ok"


def test_unknown_tool_is_reported_to_model():
    llm = make_llm([reply("rm_rf"), reply(answer="Sorry.")])
    result = llm.answer("delete", None)
    assert "unknown tool" in result["text"]
    # the error went back to the model as the result of the call
    assert "unknown tool" in llm.llm.l_messages[-1][-1]["content"]


def test_tool_without_object():
    llm = make_llm([reply("show_model"), reply(answer="Open a file.")])
    assert "no CrysPy object" in llm.answer("show", None)["text"]


def test_help_from_cryspy():
    llm = make_llm([reply("get_help", query="multipoles"),
                    reply(answer="Use atom_rho_multipole.")])
    l_called = []
    result = llm.answer("как описать мультиполи?", None,
                        callback_action=l_called.append)
    assert l_called == ["get_help"]
    # the help page itself is shown to the user, then the answer
    assert "_atom_rho_multipole" in result["text"] or \
        "atom_rho_multipole" in result["text"]
    assert result["text"].endswith("Use atom_rho_multipole.")
    assert result["flag_object_changed"] is False


def test_refine_parameters_and_fix():
    obj = cryspy.str_to_globaln(RCIF)
    llm = make_llm([
        reply("list_parameters", refined_only=True),
        reply(answer="length_a is refined."),
        reply("fix_parameters"),
        reply(answer="Done."),
        reply("refine_parameters", pattern="cell.length_b"),
        reply(answer="ok"),
    ])
    text = llm.answer("which parameters are refined?", obj)["text"]
    assert "cell.length_a" in text
    result = llm.answer("fix everything", obj)
    assert result["flag_object_changed"] is True
    assert len(obj.get_variable_names()) == 0
    llm.answer("refine b", obj)
    assert len(obj.get_variable_names()) == 1
    # history is sent back to the model
    assert len(llm.llm.l_messages[-2]) == 1 + 4 + 1


def test_number_of_tool_calls_is_limited():
    obj = cryspy.str_to_globaln(RCIF)
    llm = make_llm([reply("summarize_object")] * 10)
    result = llm.answer("loop", obj)
    assert result["tools"] == ["summarize_object"] * llm_local.MAX_TOOL_CALLS


def test_missing_llama_cpp(monkeypatch, tmp_path):
    monkeypatch.setattr(llm_local, "flag_llama_cpp", False)
    with pytest.raises(ImportError):
        LLMLocal(os.path.join(tmp_path, "model.gguf"))


def test_take_settings():
    settings = llm_local.take_settings({"n_ctx": "8192", "unknown": 1})
    assert settings["n_ctx"] == 8192
    assert "unknown" not in settings
    assert settings["n_gpu_layers"] == llm_local.DEFAULT_SETTINGS["n_gpu_layers"]
    assert llm_local.take_settings(None) == llm_local.DEFAULT_SETTINGS


@pytest.mark.parametrize("memory, index", [
    (None, None), (4, 0), (7.6, 1), (8, 1), (16, 2), (24, 2), (64, 3)])
def test_take_recommended_index(memory, index):
    assert llm_local.take_recommended_index(memory) == index


def test_total_memory():
    memory = llm_local.get_total_memory_gb()
    assert memory is None or memory > 0.1


def test_settings_reach_model():
    llm = make_llm([reply(answer="ok")])
    llm.settings = llm_local.take_settings({"max_tokens": 100, "temperature": 0.5})
    llm.answer("hi", None)
    # FakeLlama ignores kwargs; check them by wrapping
    calls = []
    llm.llm.create_chat_completion = lambda messages, **kw: (
        calls.append(kw) or {"choices": [{"message": {"content": "{}"}}]})
    llm.answer("hi", None)
    assert calls[0]["max_tokens"] == 100
    assert calls[0]["temperature"] == 0.5


def test_long_result_fits_context():
    """A message much longer than the context is cut, not sent whole."""
    llm = make_llm(["The fit is good."])
    llm.settings = llm_local.take_settings({"max_tokens": 512})
    long_result = "chi_sq = 1.2\n" + "x" * 40000
    assert llm.chat([{"role": "system", "content": "s"},
                     {"role": "user", "content": long_result}]) == \
        "The fit is good."
    sent = llm.llm.l_messages[-1]
    assert "[...cut...]" in sent[-1]["content"]
    assert sent[-1]["content"].startswith("chi_sq = 1.2")


def test_long_history_is_dropped():
    llm = make_llm([json.dumps({"action": "none", "answer": "ok"})])
    llm.history = [{"role": "user", "content": "y" * 3000},
                   {"role": "assistant", "content": "z" * 3000}] * 5
    assert llm.answer("hi", None)["text"] == "ok"
    sent = llm.llm.l_messages[-1]
    assert sent[0]["role"] == "system"
    assert sent[-1]["content"] == "hi"


def test_answer_length_larger_than_context():
    llm = make_llm(["unused"])
    llm.settings = llm_local.take_settings({"max_tokens": 5000})
    with pytest.raises(ValueError, match="Increase the context"):
        llm.chat([{"role": "user", "content": "hi"}])
