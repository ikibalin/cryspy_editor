"""Tests of the agent loop of the AI assistant (one action at a time)
without llama-cpp-python."""
import json

import cryspy
import pytest

from cryspy_editor.widgets import assistant_agent
from cryspy_editor.widgets.assistant import take_json_object
from cryspy_editor.widgets.assistant_agent import Agent, form_step_schema, take_step_reply
from cryspy_editor.widgets.assistant_tools import D_TOOLS

from test_assistant import RCIF, make_assistant, reply

pytestmark = pytest.mark.skipif("get_recipe" not in D_TOOLS, reason="CrysPy without recipes")


def step(action, arguments=None, thought="next"):
    """Reply of the model in the agent loop."""
    return json.dumps({"thought": thought, "action": action, "arguments": arguments or {}})


def final(answer, thought="done"):
    return json.dumps({"thought": thought, "action": "final", "answer": answer})


def test_take_step_reply():
    assert take_step_reply(step("refine"), take_json_object)["action"] == "refine"
    assert take_step_reply(final("ok"), take_json_object) == \
        {"thought": "done", "action": "final", "arguments": {}, "answer": "ok"}
    assert take_step_reply("no json", take_json_object)["answer"] == "no json"
    assert take_step_reply('{"action": "none", "answer": "hi"}', take_json_object)["action"] == "final"


def test_schema_allows_only_known_actions():
    schema = form_step_schema(["refine", "calculate"])
    assert schema["properties"]["action"]["enum"] == ["refine", "calculate", "final"]
    assert schema["required"] == ["thought", "action"]


def test_recipe_starts_the_loop():
    obj = cryspy.str_to_globaln(RCIF)
    assistant = make_assistant([
        reply(("get_recipe", {"name": "refine_structure"})),
        step("fix_parameters", thought="The recipe starts with all parameters fixed."),
        step("list_parameters", {"refined_only": True}),
        final("All parameters are fixed; the file has no experiment to refine."),
    ])
    l_called = []
    result = assistant.ask("refine the structure step by step", obj, on_action=l_called.append)
    assert l_called == ["get_recipe", "fix_parameters", "list_parameters"]
    l_messages = assistant.model.llm.l_messages
    # the steps of the recipe and each result reach the model before its next action
    assert "Recipe refine_structure" in l_messages[1][-1]["content"]
    assert "Result of fix_parameters" in l_messages[2][-1]["content"]
    assert "action" in l_messages[1][0]["content"] and "final" in l_messages[1][0]["content"]
    assert "Step 2: The recipe starts with all parameters fixed." in result["text"]
    assert result["text"].endswith("no experiment to refine.")
    assert result["flag_object_changed"] is True
    assert len(obj.get_variable_names()) == 0


def test_error_goes_back_and_is_corrected():
    obj = cryspy.str_to_globaln(RCIF)
    assistant = make_assistant([
        reply(("work_step_by_step", {})),
        step("set_parameter", {"path": "nothing", "value": 1}),
        step("set_parameter", {"path": "cell.length_b", "value": 6}),
        final("b is 6 Å now."),
    ])
    result = assistant.ask("set b to 6 and check", obj)
    assert "Error" in assistant.model.llm.l_messages[2][-1]["content"]
    assert [action for action, _, _ in result["actions"]] == ["set_parameter", "set_parameter"]
    assert float(obj.items[0].cell.length_b) == 6.


class CountingModel:
    def __init__(self, replies):
        self.replies = list(replies)
        self.l_schema = []

    def chat(self, messages, flag_json=False, schema=None):
        self.l_schema.append(schema)
        return self.replies.pop(0) if self.replies else final("end")


def fake_run_tool(name, cryspy_object, arguments):
    if name == "fail":
        return "Error: it fails.", False
    return f"{name} {json.dumps(arguments)} done", True


def test_the_same_call_is_refused_after_the_limit():
    model = CountingModel([step("calc")] * 3 + [final("ok")])
    out = Agent(model, fake_run_tool, ["calc"], take_json_object).run("system", [], "go")
    l_result = [result for _, _, _, result in out["steps"]]
    assert l_result[:2] == ["calc {} done"] * 2
    assert l_result[2].startswith("Error: this action with these arguments was already done")
    assert out["answer"] == "ok"
    assert model.l_schema[0]["properties"]["action"]["enum"] == ["calc", "final"]


def test_number_of_actions_is_limited():
    model = CountingModel([step("calc", {"i": ind}) for ind in range(30)])
    out = Agent(model, fake_run_tool, ["calc"], take_json_object).run("system", [], "go")
    assert len(out["steps"]) == assistant_agent.MAX_AGENT_STEPS
    assert "limit" in out["stopped"]


def test_errors_in_a_row_stop_the_loop():
    model = CountingModel([step("fail", {"i": ind}) for ind in range(10)])
    out = Agent(model, fake_run_tool, ["fail"], take_json_object).run("system", [], "go")
    assert len(out["steps"]) == assistant_agent.MAX_ERRORS_IN_ROW
    assert out["flag_object_changed"] is False


def test_stop_request_ends_the_loop():
    model = CountingModel([step("calc", {"i": ind}) for ind in range(10)])
    l_step = []
    out = Agent(model, fake_run_tool, ["calc"], take_json_object).run(
        "system", [], "go", on_action=l_step.append, should_stop=lambda: len(l_step) >= 2)
    assert len(out["steps"]) == 2
    assert out["stopped"].startswith("Stopped by the user")


def test_old_observations_are_shortened():
    long_result = "x" * 2000
    model = CountingModel([step("calc", {"i": ind}) for ind in range(4)])
    l_messages = []

    def chat(messages, flag_json=False, schema=None):
        l_messages.append([dict(message) for message in messages])
        return CountingModel.chat(model, messages, flag_json, schema)
    model.chat = chat
    Agent(model, lambda *args: (long_result, False), ["calc"], take_json_object).run("system", [], "go")
    last = l_messages[-1]
    l_length = [len(message["content"]) for message in last if message["role"] == "user"][1:]
    assert max(l_length[:-2]) < 400 < min(l_length[-2:])


def test_stop_button(qapp):
    from cryspy_editor.widgets.ui_assistant import AssistantWindow
    window = AssistantWindow()
    try:
        assert not window.button_stop.isEnabled()
        window.on_stop()  # no running request: nothing happens
        assert not window.button_stop.isEnabled()
    finally:
        window.close()


def test_request_stop_is_reset_for_the_next_request():
    obj = cryspy.str_to_globaln(RCIF)
    assistant = make_assistant([reply(("work_step_by_step", {})), final("ok")])
    assistant.request_stop()
    result = assistant.ask("go", obj)
    assert result["text"] == "ok"
