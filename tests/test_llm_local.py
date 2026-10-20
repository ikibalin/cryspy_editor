"""Tests of the AI assistant logic without llama-cpp-python and Qt."""
import json
import os

import cryspy
import pytest

from cryspy_editor.widgets import llm_local
from cryspy_editor.widgets.llm_local import LLMLocal, take_json_object


class FakeLlama:
    """Returns prepared replies instead of running a model."""

    def __init__(self, replies):
        self.replies = list(replies)
        self.l_messages = []

    def create_chat_completion(self, messages, **kwargs):
        self.l_messages.append(messages)
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


def test_answer_without_action():
    llm = make_llm([json.dumps({"action": "none", "answer": "Bragg law"})])
    result = llm.answer("What is Bragg law?", None)
    assert result["text"] == "Bragg law"
    assert result["flag_object_changed"] is False
    assert len(llm.history) == 2


def test_unknown_action_is_none():
    llm = make_llm([json.dumps({"action": "rm -rf", "answer": "no"})])
    assert llm.answer("delete", None)["action"] == "none"


def test_invalid_json_is_answer():
    llm = make_llm(["plain text"])
    result = llm.answer("hello", None)
    assert result["action"] == "none"
    assert result["text"] == "plain text"


def test_action_without_object():
    llm = make_llm([json.dumps({"action": "show_model", "answer": ""})])
    assert "Open a file first" in llm.answer("show", None)["text"]


def test_show_and_fix_parameters():
    obj = cryspy.str_to_globaln(RCIF)
    llm = make_llm([
        json.dumps({"action": "show_refined_parameters", "answer": ""}),
        json.dumps({"action": "fix_all_parameters", "answer": "Done."}),
        json.dumps({"action": "show_refined_parameters", "answer": ""}),
    ])
    text = llm.answer("which parameters are refined?", obj)["text"]
    assert "length_a" in text
    result = llm.answer("fix everything", obj)
    assert result["flag_object_changed"] is True
    assert len(obj.get_variable_names()) == 0
    assert "No parameters" in llm.answer("and now?", obj)["text"]
    # history is sent back to the model
    assert len(llm.llm.l_messages[-1]) == 1 + 4 + 1


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
    llm = make_llm([json.dumps({"action": "none", "answer": "ok"})])
    llm.settings = llm_local.take_settings({"max_tokens": 100, "temperature": 0.5})
    llm.answer("hi", None)
    # FakeLlama ignores kwargs; check them by wrapping
    calls = []
    llm.llm.create_chat_completion = lambda messages, **kw: (
        calls.append(kw) or {"choices": [{"message": {"content": "{}"}}]})
    llm.answer("hi", None)
    assert calls[0]["max_tokens"] == 100
    assert calls[0]["temperature"] == 0.5
