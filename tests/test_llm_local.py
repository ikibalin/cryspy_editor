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


def test_long_result_fits_context():
    """A refinement result much longer than the context is cut, not sent whole."""
    llm = make_llm(["The fit is good."])
    llm.settings = llm_local.take_settings({"max_tokens": 512})
    long_result = "chi_sq = 1.2\n" + "x" * 40000
    assert llm.comment_result("refine and analyse", "refine", long_result) == \
        "The fit is good."
    sent = llm.llm.l_messages[-1]
    assert "[...cut...]" in sent[-1]["content"]
    assert sent[-1]["content"].startswith("Request: refine and analyse")


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


def test_format_refinement_result():
    obj = cryspy.str_to_globaln(RCIF.replace("_cell_length_b 5.0", "_cell_length_b 5.0()"))
    names = obj.get_variable_names()
    # RhoChi result names come from the dictionary pipeline
    names = [("cell_cell", "unit_cell_parameters", (0,)),
             ("cell_cell", "unit_cell_parameters", (1,))]
    result = {"chi_sq": 1.23456, "parameter_name": names,
              "correlation_matrix": [[1.0, 0.95], [0.95, 1.0]]}
    text = llm_local.format_refinement_result(result, obj)
    assert "chi_sq = 1.2346" in text
    assert "cell.length_a = 5.00000" in text
    assert "cell_cell.unit_cell_parameters[0] - " \
        "cell_cell.unit_cell_parameters[1]: 0.95" in text
    result["correlation_matrix"] = [[1.0, 0.1], [0.1, 1.0]]
    assert "No correlations" in llm_local.format_refinement_result(result, obj)


@pytest.mark.parametrize("name, text", [
    ((("global", ""), ("crystal", "ho2ti2o7"), ("atom_site_susceptibility", ""),
      ("chi_11", 0)), "crystal_ho2ti2o7.atom_site_susceptibility.chi_11[0]"),
    ((("global", ""), ("diffrn", "d"), ("extinction", None), ("radius", None)),
     "diffrn_d.extinction.radius"),
    ((("crystal", "x"), ("cell", None), ("length_a", ())), "crystal_x.cell.length_a"),
    ((("pd", "p"), ("background", ""), ("intensity", (1, 2))),
     "pd_p.background.intensity[1, 2]"),
    (("crystal_x", "atom_para_susceptibility", (3, 0)),
     "crystal_x.atom_para_susceptibility[3, 0]"),
])
def test_format_parameter_name(name, text):
    assert llm_local.format_parameter_name(name) == text
