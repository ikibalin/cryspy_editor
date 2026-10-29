"""Menus of procedures are built from CrysPy functions without changing them."""
import cryspy

from cryspy_editor.widgets.cryspy_objects import (
    check_function_for_procedure, check_function_to_auto_run)


def test_checks_keep_return_annotation():
    func = cryspy.rhochi_no_refinement
    annotations = dict(func.__annotations__)
    assert "return" in annotations
    check_function_for_procedure(func)
    check_function_to_auto_run(func)
    assert func.__annotations__ == annotations
