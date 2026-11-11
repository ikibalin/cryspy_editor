"""Menu actions of CrysPy procedures run the procedure of their action.

The old slot took the procedure from self.sender().object. In a lambda slot
the sender is not reliable: the first click on "Estimate absorption" gave
the object panel as sender and AttributeError
'WObjectPanel' object has no attribute 'object'.
"""



def procedure_actions(editor_window):
    l_action = []
    for menu_action in editor_window.menu_bar.actions():
        menu = menu_action.menu()
        if menu is None:
            continue
        l_action.extend(a for a in menu.actions() if hasattr(a, "object"))
    return l_action


def test_each_action_runs_its_procedure(qapp, editor_window, monkeypatch):
    l_run = []
    monkeypatch.setattr(editor_window, "press_procedure", l_run.append)
    l_action = procedure_actions(editor_window)
    assert len(l_action) > 0
    assert any("absorption" in a.text().lower() for a in l_action)
    for action in l_action:
        action.trigger()
    assert l_run == [a.object for a in l_action]


def test_sender_is_the_object_panel(qapp, editor_window, monkeypatch):
    """As after a click in the object panel: the slot must not ask
    self.sender() which action was clicked."""
    l_run = []
    monkeypatch.setattr(editor_window, "press_procedure", l_run.append)
    monkeypatch.setattr(editor_window, "sender", lambda: editor_window.w_object_panel)
    action = next(a for a in procedure_actions(editor_window)
                  if "absorption" in a.text().lower())
    action.trigger()
    assert l_run == [action.object]
