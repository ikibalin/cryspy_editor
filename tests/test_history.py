"""History of the rcif object: going back after a failed change."""
import os

from cryspy_editor.history import RcifHistory

DIR_EXAMPLES = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "examples")


def test_history_keeps_last_ten_and_skips_equal_states():
    history = RcifHistory()
    history.push("first", "a")
    assert not history.push("second", "a")
    assert [e.label for e in history.entries] == ["second"]
    for ind in range(15):
        history.push(f"run {ind}", f"text {ind}")
    assert len(history) == 10
    assert history.entries[-1].text == "text 14"
    assert history.entries[0].text == "text 5"


def test_go_back_after_run(qapp, monkeypatch, tmp_path):
    from cryspy_editor.ceditor import CMainWindow
    monkeypatch.chdir(tmp_path)
    window = CMainWindow()
    try:
        window.d_setup["data_file_name"] = os.path.join(
            DIR_EXAMPLES, "Fe3O4_5T_powder_1d", "main.rcif")
        window.take_rcif_object_from_d_setup()
        assert len(window.history) == 0

        def change_cell(rcif_object):
            for data in rcif_object.items:
                if data.is_attribute("cell"):
                    data.cell.length_a = 9.0

        window.cthread.function = change_cell
        window.cthread.arguments = (window.rcif_object, )
        window.cthread.start()
        assert window.cthread.wait(10000)
        assert "_cell_length_a 9.0" in window.rcif_object.to_cif()
        assert len(window.history) == 1
        assert window.history.entries[0].label == "change cell"

        window.update_menu_history()
        actions = window.menu_history.actions()
        assert len(actions) == 1 and "before change cell" in actions[0].text()
        actions[0].trigger()
        assert "_cell_length_a 8.454" in window.rcif_object.to_cif()
        # going back is kept too and can be undone
        assert len(window.history) == 2
        assert "_cell_length_a 9.0" in window.history.entries[-1].text
    finally:
        window.close()
