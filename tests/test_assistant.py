"""Tests of the AI assistant logic without llama-cpp-python, and of its
window."""
import json
import os

import cryspy
import pytest

from cryspy_editor.widgets import assistant as assistant_module
from cryspy_editor.widgets.assistant import (
    Assistant,
    LocalModel,
    take_decision,
    take_json_object,
)
from cryspy_editor.widgets.assistant_tools import is_answer_tool


class FakeLlama:
    """Returns prepared replies instead of running a model."""

    def __init__(self, replies, n_ctx=4096):
        self.replies = list(replies)
        self.l_messages = []
        self._n_ctx = n_ctx

    def n_ctx(self):
        return self._n_ctx

    def close(self):
        self.flag_closed = True

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


def make_model(replies, settings=None):
    model = LocalModel.__new__(LocalModel)
    model.model_path = "fake.gguf"
    model.settings = assistant_module.take_settings(settings)
    model.llm = FakeLlama(replies)
    return model


def make_assistant(replies, settings=None):
    return Assistant(make_model(replies, settings))


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


def reply(*actions, answer=""):
    """Reply of the model: actions are (name, arguments) pairs."""
    return json.dumps({"actions": [{"action": name, "arguments": arguments}
                                   for name, arguments in actions],
                       "answer": answer})


def test_take_json_object():
    assert take_json_object('Sure! {"action": "none", "answer": "a {b}"} ok') == \
        {"action": "none", "answer": "a {b}"}
    assert take_json_object('{"a": {"b": 1}}') == {"a": {"b": 1}}
    assert take_json_object("{bad} then {\"a\": 1}") == {"a": 1}
    assert take_json_object("no json") is None


def test_take_decision_forms():
    assert take_decision(reply(("refine", {}), answer="ok")) == \
        {"actions": [("refine", {})], "answer": "ok"}
    # a single step, arguments as the other keys, the old "tool" key
    assert take_decision('{"action": "set_parameter", "path": "a", "value": 1}') == \
        {"actions": [("set_parameter", {"path": "a", "value": 1})], "answer": ""}
    assert take_decision('{"tool": "none", "arguments": {}, "answer": "hi"}') == \
        {"actions": [], "answer": "hi"}
    assert take_decision('{"message": "hello"}')["answer"] == "hello"
    assert take_decision("plain text") == {"actions": [], "answer": "plain text"}


def test_answer_without_action():
    assistant = make_assistant([reply(answer="Bragg law")])
    result = assistant.ask("What is Bragg law?", None)
    assert result["text"] == "Bragg law"
    assert result["flag_object_changed"] is False
    assert len(assistant.history) == 2


def test_invalid_json_is_answer():
    assistant = make_assistant(["plain text"])
    result = assistant.ask("hello", None)
    assert result["actions"] == []
    assert result["text"] == "plain text"


def test_unknown_action_is_corrected():
    assistant = make_assistant([reply(("rm_rf", {})),
                                reply(("summarize_object", {})),
                                reply(answer="One data block.")])
    obj = cryspy.str_to_globaln(RCIF)
    result = assistant.ask("what is loaded?", obj)
    # the error went back to the model, which corrected the action
    assert "unknown tool" in assistant.model.llm.l_messages[1][-1]["content"]
    assert [action for action, _, _ in result["actions"]] == ["summarize_object"]
    assert result["text"].endswith("One data block.")


def test_error_stays_after_retries():
    assistant = make_assistant([reply(("show_model", {}))] * 3 + [reply(answer="Open a file.")])
    result = assistant.ask("show", None)
    assert "no CrysPy object" in result["text"]
    assert result["text"].endswith("Open a file.")
    # the first reply, the retries and the answer from the result
    assert len(assistant.model.llm.l_messages) == 1 + assistant_module.MAX_RETRIES + 1


def test_help_from_cryspy():
    assistant = make_assistant([reply(("get_help", {"query": "multipoles"})),
                                reply(answer="Use atom_rho_multipole.")])
    l_called = []
    result = assistant.ask("как описать мультиполи?", None, on_action=l_called.append)
    assert l_called == ["get_help"]
    # the help page itself is shown to the user, then the answer
    assert "atom_rho_multipole" in result["text"]
    assert result["text"].endswith("Use atom_rho_multipole.")
    assert result["flag_object_changed"] is False
    # the answer is made from the result of get_help
    assert "Result of get_help" in assistant.model.llm.l_messages[-1][-1]["content"]


def test_help_without_query_takes_question():
    assistant = make_assistant([reply(("get_help", {})), reply(answer="ok")])
    result = assistant.ask("thermal vibrations", None)
    assert result["actions"][0][1] == {"query": "thermal vibrations"}


def test_several_actions_in_one_reply():
    obj = cryspy.str_to_globaln(RCIF)
    assistant = make_assistant([
        reply(("fix_parameters", {}), ("refine_parameters", {"pattern": "cell.length_b"}),
              answer="Done.")])
    result = assistant.ask("fix everything and refine b", obj)
    assert [action for action, _, _ in result["actions"]] == \
        ["fix_parameters", "refine_parameters"]
    assert result["flag_object_changed"] is True
    assert len(obj.get_variable_names()) == 1
    # only actions that change the object: no second call for the answer
    assert len(assistant.model.llm.l_messages) == 1
    assert result["text"].endswith("Done.")


def test_list_parameters_and_history():
    obj = cryspy.str_to_globaln(RCIF)
    assistant = make_assistant([
        reply(("list_parameters", {"refined_only": True})),
        reply(answer="length_a is refined."),
        reply(answer="ok"),
    ])
    text = assistant.ask("which parameters are refined?", obj)["text"]
    assert "cell.length_a" in text
    assistant.ask("thanks", obj)
    # history is sent back to the model
    assert len(assistant.model.llm.l_messages[-1]) == 1 + 2 + 1


def test_number_of_actions_is_limited():
    obj = cryspy.str_to_globaln(RCIF)
    # ten different patterns, all matching (no match is an error, corrected by the model)
    l_step = [("list_parameters", {"pattern": "cell.length_a"[:ind + 1]}) for ind in range(10)]
    assistant = make_assistant([reply(*l_step), reply(answer="ok")])
    result = assistant.ask("loop", obj)
    assert len(result["actions"]) == assistant_module.MAX_STEPS


def test_repeated_action_is_done_once():
    obj = cryspy.str_to_globaln(RCIF)
    assistant = make_assistant([reply(("summarize_object", {}), ("summarize_object", {})),
                                reply(answer="ok")])
    assert len(assistant.ask("twice", obj)["actions"]) == 1


def test_is_answer_tool():
    assert is_answer_tool("get_help")
    assert is_answer_tool("refine")
    assert not is_answer_tool("set_parameter")
    assert not is_answer_tool("unknown")


def test_system_prompt_names_blocks():
    obj = cryspy.str_to_globaln(RCIF)
    prompt = assistant_module.form_system_prompt(obj)
    assert "1 data blocks: cell" in prompt
    assert "get_help" in prompt and "refine_parameters" in prompt
    assert "No file is opened" in assistant_module.form_system_prompt(None)


def test_missing_llama_cpp(monkeypatch, tmp_path):
    monkeypatch.setattr(assistant_module, "flag_llama_cpp", False)
    with pytest.raises(ImportError):
        LocalModel(os.path.join(tmp_path, "model.gguf"))


def test_take_settings():
    settings = assistant_module.take_settings({"n_ctx": "8192", "unknown": 1})
    assert settings["n_ctx"] == 8192
    assert "unknown" not in settings
    assert settings["n_gpu_layers"] == assistant_module.DEFAULT_SETTINGS["n_gpu_layers"]
    assert assistant_module.take_settings(None) == assistant_module.DEFAULT_SETTINGS


@pytest.mark.parametrize("memory, index", [
    (None, None), (4, 0), (7.6, 1), (8, 1), (16, 2), (24, 2), (64, 2)])
def test_take_recommended_index(memory, index):
    assert assistant_module.take_recommended_index(memory) == index


def test_total_memory():
    memory = assistant_module.get_total_memory_gb()
    assert memory is None or memory > 0.1


def test_settings_reach_model():
    model = make_model([], {"max_tokens": 100, "temperature": 0.5})
    calls = []
    model.llm.create_chat_completion = lambda messages, **kw: (
        calls.append(kw) or {"choices": [{"message": {"content": "{}"}}]})
    Assistant(model).ask("hi", None)
    assert calls[0]["max_tokens"] == 100
    assert calls[0]["temperature"] == 0.5
    assert calls[0]["response_format"] == {"type": "json_object"}


def test_long_result_fits_context():
    """A message much longer than the context is cut, not sent whole."""
    model = make_model(["The fit is good."], {"max_tokens": 512})
    long_result = "chi_sq = 1.2\n" + "x" * 40000
    assert model.chat([{"role": "system", "content": "s"},
                       {"role": "user", "content": long_result}]) == "The fit is good."
    sent = model.llm.l_messages[-1]
    assert "[...cut...]" in sent[-1]["content"]
    assert sent[-1]["content"].startswith("chi_sq = 1.2")


def test_long_history_is_dropped():
    assistant = make_assistant([reply(answer="ok")])
    assistant.history = [{"role": "user", "content": "y" * 3000},
                         {"role": "assistant", "content": "z" * 3000}] * 5
    assert assistant.ask("hi", None)["text"] == "ok"
    sent = assistant.model.llm.l_messages[-1]
    assert sent[0]["role"] == "system"
    assert sent[-1]["content"] == "hi"


def test_answer_length_larger_than_context():
    model = make_model(["unused"], {"max_tokens": 5000})
    with pytest.raises(ValueError, match="Increase the context"):
        model.chat([{"role": "user", "content": "hi"}])


def test_assistant_is_a_window_of_its_own(qapp):
    from PyQt5 import QtCore, QtWidgets
    from cryspy_editor.widgets.ui_assistant import AssistantController
    main_window = QtWidgets.QMainWindow()
    d_setup = {}
    controller = AssistantController(main_window, d_setup, lambda: True, lambda: None, lambda: None)
    try:
        menu = controller.init_menu(main_window.menuBar())
        assert [action.text() for action in menu.actions() if not action.isSeparator()] == \
            ["Load model (GGUF file or Ollama)...", "Show assistant", "Unload model", "CookBook..."]
        window = controller.window
        assert window.windowTitle() == "AI Assistant / CrysPy Editor"
        assert window.windowFlags() & QtCore.Qt.Window
        assert window.parent() is main_window
        controller.show_window()
        window.resize(321, 234)
        window.close()
        assert not window.isVisible()
        controller.show_window()
        # the same window comes back with its size
        assert controller.window is window and window.isVisible()
        assert (window.width(), window.height()) == (321, 234)
        controller.save_window_state()
        assert d_setup["assistant_window_visible"] is True
    finally:
        controller.window.close()
        main_window.close()


def test_model_is_freed_before_exit(qapp):
    """A model left to the interpreter shutdown makes the Metal backend of
    llama.cpp abort; unload and shutdown free it at once."""
    from PyQt5 import QtWidgets

    from cryspy_editor.widgets.ui_assistant import AssistantController, LoadWorker
    main_window = QtWidgets.QMainWindow()
    controller = AssistantController(main_window, {}, lambda: True, lambda: None, lambda: None)
    try:
        window = controller.window
        assistant = make_assistant([])
        llm = assistant.model.llm
        window.on_model_loaded(assistant)
        window.unload_model()
        assert llm.flag_closed and assistant.model.llm is None
        assert window.assistant is None

        assistant = make_assistant([])
        llm = assistant.model.llm
        window.on_model_loaded(assistant)
        controller.shutdown()
        assert llm.flag_closed and window.assistant is None

        # a load that finished, but whose result never reached the window
        worker = LoadWorker("fake.gguf")
        worker.assistant = make_assistant([])
        llm = worker.assistant.model.llm
        window._start_thread(worker, lambda result: None, lambda msg: None)
        controller.shutdown()
        assert llm.flag_closed and not window.is_busy()
        # the signals of the finished thread are not delivered afterwards
        qapp.processEvents()
        controller.shutdown()  # twice: on close and on aboutToQuit
    finally:
        controller.window.close()
        main_window.close()


@pytest.mark.parametrize("answer", ["The cell parameters are refined.", "Done.", "Готово, параметры уточнены.",
                                    "Refinement completed for all parameters."])
def test_answer_without_action_never_reports_a_change(answer):
    """Small models answer "refined" with no action: the user is told that
    nothing is done (as in PyColl5)."""
    result = make_assistant([reply(answer=answer)]).ask("refine the cell", None)
    assert result["text"] == assistant_module.NOTHING_DONE


def test_answer_from_the_results_not_from_the_chat():
    assistant = make_assistant([reply(("summarize_object", {}), answer="It is refined."), reply(answer="")])
    result = assistant.ask("what is loaded?", cryspy.str_to_globaln(RCIF))
    assert "only from these results" in assistant.model.llm.l_messages[1][-1]["content"]
    assert "refined" not in result["text"]
    assert "never write that something is done" in assistant_module.form_system_prompt()


def test_failed_action_is_never_reported_as_done():
    """The TbTe3 session: 'refine scale factor' matched nothing, the model
    wrote 'Scale factor marked for refinement.'"""
    assistant = make_assistant(
        [reply(("refine_parameters", {"pattern": "scale_factor"}),
               answer="Scale factor marked for refinement.")] * 3)
    result = assistant.ask("Refine scale factor", cryspy.str_to_globaln(RCIF))
    assert "Error: no parameters match" in result["text"]
    assert "marked for refinement." not in result["text"]


def test_new_tools_of_cryspy():
    assistant = make_assistant(
        [reply(("calculate_structure_factor", {"hkl": "1 1 1"})),
         reply(answer="F_N = 1.38")])
    obj = cryspy.str_to_globaln("""global_
data_al
_cell_length_a 4.05
_cell_length_b 4.05
_cell_length_c 4.05
_cell_angle_alpha 90
_cell_angle_beta 90
_cell_angle_gamma 90
_space_group_name_H-M_alt "F m -3 m"
loop_
_atom_site_label
_atom_site_type_symbol
_atom_site_fract_x
_atom_site_fract_y
_atom_site_fract_z
_atom_site_adp_type
_atom_site_B_iso_or_equiv
Al Al 0 0 0 Biso 0.0
""")
    result = assistant.ask("Calculate nuclear structure factor for (1 1 1)", obj)
    name, _, text = result["actions"][0]
    assert name == "calculate_structure_factor"
    assert "|F_N| = 1.379" in text  # 4 b(Al)
    assert "add_crystal_from_cod" in assistant_module.form_system_prompt()


def test_window_text_as_in_pycoll5(qapp):
    """The window of PyColl5 and of CrysPy Editor look the same: examples
    in the empty chat, one-line placeholder, "You" for the user."""
    from cryspy_editor.widgets import ui_assistant
    window = ui_assistant.AssistantWindow()
    try:
        assert window.input_line.placeholderText() == "Ask the question or request an action"
        assert window.history_view.placeholderText().startswith("Examples of requests:")
        window.assistant = make_assistant([])
        window._start_thread = lambda worker, on_finished, on_error: None  # no model run
        window.input_line.setText("What is Bragg law?")
        window.on_send()
        assert window.history_view.toPlainText().startswith("You:")
    finally:
        window.close()


def test_no_answer_that_it_is_done_after_an_error():
    """A part of the request failed: the answer written from the results
    that everything is done is not shown (the results say what is done)."""
    bad = ("set_parameter", {"name": "no_such_parameter", "value": 1})
    assistant = make_assistant([reply(bad, ("summarize_object", {})), reply(bad), reply(bad),
                                reply(answer="The parameter is set and the structure is refined.")])
    result = assistant.ask("set no_such_parameter to 1 and say what is loaded", cryspy.str_to_globaln(RCIF))
    assert any(text.startswith("Error") for _, _, text in result["actions"]), result["text"]
    assert "refined" not in result["text"]
