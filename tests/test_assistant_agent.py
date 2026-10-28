"""Tests of the agent loop of the AI assistant (one action at a time)
without llama-cpp-python."""
import json

import cryspy

from cryspy_editor.widgets import assistant_agent
from cryspy_editor.widgets.assistant import take_json_object
from cryspy_editor.widgets.assistant_agent import Agent, form_step_schema, take_step_reply

from test_assistant import RCIF, make_assistant, reply


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


def test_steps_of_the_user_are_followed_not_a_recipe():
    """The user describes the algorithm: the agent does it and cannot switch
    to a recipe in the middle (a recipe is chosen only by the first reply)."""
    from cryspy_editor.widgets.assistant import form_system_prompt
    obj = cryspy.str_to_globaln(RCIF)
    assistant = make_assistant([
        reply(("work_step_by_step", {})),
        step("get_recipe", {"name": "refine_structure"}),
        step("list_parameters"),
        final("The parameters are listed."),
    ])
    request = ("take the list of all parameters, refine them one by one and keep each only "
               "if chi_sq gets better")
    result = assistant.ask(request, obj)
    l_messages = assistant.model.llm.l_messages
    assert "never a recipe instead of them" in l_messages[0][0]["content"]
    assert "follow exactly them" in l_messages[1][0]["content"]
    assert "cannot be used here" in l_messages[2][-1]["content"]
    assert "Recipe refine_structure" not in str(l_messages[-1])
    assert [action for action, _, _ in result["actions"]] == ["get_recipe", "list_parameters"]
    assert result["actions"][0][2].startswith("Error")
    assert "keep it only if chi_sq gets better" in form_system_prompt(obj)


def test_recipe_keeps_get_recipe_in_the_schema():
    model = CountingModel([final("ok")])
    assistant = make_assistant([])
    assistant.model = model
    assistant.ask_step_by_step("refine the structure step by step", None,
                               [("get_recipe", {"name": "refine_structure"})])
    assistant.model = CountingModel([final("ok")])
    assistant.ask_step_by_step("my own steps", None, [])
    assert "get_recipe" not in assistant.model.l_schema[0]["properties"]["action"]["enum"]
    assert "get_recipe" in model.l_schema[0]["properties"]["action"]["enum"]


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


def test_number_of_actions_is_a_setting():
    model = CountingModel([step("calc", {"i": ind}) for ind in range(30)])
    out = Agent(model, fake_run_tool, ["calc"], take_json_object, max_steps=20).run("system", [], "go")
    assert len(out["steps"]) == 20 and "limit of 20 actions" in out["stopped"]


def test_assistant_takes_max_steps_from_model_settings():
    l_reply = [reply(("get_recipe", {"name": "refine_structure"}))]
    l_reply += [step("list_parameters", {"pattern": f"p{ind}"}) for ind in range(5)] + [final("done")]
    assistant = make_assistant(l_reply, settings={"max_steps": 3})
    out = assistant.ask("refine the structure step by step", cryspy.str_to_globaln(RCIF))
    assert len(out["actions"]) == 3
    assert "limit of 3 actions" in out["text"]


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


def test_steps_are_shown_as_they_go():
    """Each step reaches the user when it starts and when its result comes;
    the reply then has only the end, the chat history keeps all."""
    obj = cryspy.str_to_globaln(RCIF)
    assistant = make_assistant([
        reply(("get_recipe", {"name": "refine_structure"})),
        step("fix_parameters", thought="Fix all first."),
        final("All parameters are fixed."),
    ])
    l_shown = []
    result = assistant.ask("refine the structure step by step", obj, on_step=l_shown.append)
    assert l_shown[0] == "Step 1:\n[get_recipe] ..."
    assert l_shown[1].startswith("[get_recipe] Recipe refine_structure")
    assert l_shown[2] == "Step 2: Fix all first.\n[fix_parameters] ..."
    assert l_shown[3].startswith("[fix_parameters] ")
    assert len(l_shown) == 4
    assert result["text"] == "All parameters are fixed."
    assert "Step 2: Fix all first." in assistant.history[-1]["content"]


def test_window_shows_a_step(qapp):
    from cryspy_editor.widgets.ui_assistant import AssistantWindow
    window = AssistantWindow()
    try:
        window.append_step("Step 1: Fix all first.\n[fix_parameters] ...")
        assert "Step 1: Fix all first." in window.history_view.toPlainText()
    finally:
        window.close()


def test_max_steps_in_model_settings(qapp):
    from cryspy_editor.widgets.ui_assistant import ModelSettingsDialog
    dialog = ModelSettingsDialog("model.gguf", {"max_steps": 40})
    try:
        assert dialog.settings()["max_steps"] == 40
        dialog.sb_max_steps.setValue(500)  # any number
        assert dialog.settings()["max_steps"] == 500
        dialog.set_defaults()
        assert dialog.settings()["max_steps"] == assistant_agent.MAX_AGENT_STEPS
    finally:
        dialog.close()


def test_recipe_is_kept_in_full_to_the_end():
    """The recipe chosen before the loop is the plan of the whole work: it is
    given in full and never shortened like the results of older actions."""
    obj = cryspy.str_to_globaln(RCIF)
    recipe_text = cryspy.call_assistant_tool(obj, "get_recipe", {"name": "refine_structure"})["text"]
    l_step = [step("list_parameters", {"pattern": pattern}) for pattern in ("cell", "scale", "adp", "b_iso")]
    assistant = make_assistant([reply(("get_recipe", {"name": "refine_structure"}))] + l_step + [final("done")])
    assistant.model.llm._n_ctx = 16384  # the context is not the limit here
    assistant.ask("refine the structure step by step", obj)
    messages = assistant.model.llm.l_messages[-1]
    content = next(message["content"] for message in messages if "Result of get_recipe" in message["content"])
    assert recipe_text in content


def test_fit_messages_cuts_the_system_message_last():
    from cryspy_editor.widgets.assistant import fit_messages
    messages = [{"role": "system", "content": "rules " * 200},
                {"role": "user", "content": "question"},
                {"role": "user", "content": "result " * 400}]
    out = fit_messages(messages, 100, 900, lambda text: len(text) // 4)
    assert out[0]["content"] == messages[0]["content"]
    assert out[-1]["content"].endswith("[...cut...]")


def test_recipe_used_inside_a_recipe_is_kept_in_full():
    """use_recipe (a recipe inside a recipe) gives a plan followed to the
    end: its result is not shortened like the results of other actions."""
    inner = "Recipe brick:\n" + "1. step: " + "x" * 2000

    def run_tool(name, cryspy_object, arguments):
        return (inner, False) if name == "use_recipe" else (f"{name} " + "y" * 600, False)

    class RecordingModel(CountingModel):
        def chat(self, messages, flag_json=False, schema=None):
            self.l_messages = [dict(message) for message in messages]
            return super().chat(messages, flag_json, schema)

    model = RecordingModel([step("use_recipe", {"name": "brick"})] + [step("calc", {"n": n}) for n in range(4)]
                           + [final("ok")])
    Agent(model, run_tool, ["use_recipe", "calc"], take_json_object).run("system", [], "go")
    l_content = [message["content"] for message in model.l_messages if message["role"] == "user"]
    assert any(inner in content for content in l_content)
    assert sum("[...cut...]" in content for content in l_content) >= 2  # older results of calc
