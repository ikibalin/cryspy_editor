"""Calculations of the text tables are done by CrysPy."""
import numpy
import pytest

from cryspy_editor.widgets.function_ascii_to_table import (
    transform_lines_to_d_np_table)
from cryspy_editor.widgets.function_table_operation import (
    redefine_inline_parameters)
from cryspy_editor.widgets.procedures import (
    calc_index_hkl_in_range, choose_func_equiv)

UB = "\n".join(
    f"_diffrn_orient_matrix_ub_{ij} {value}" for ij, value in zip(
        ("11", "12", "13", "21", "22", "23", "31", "32", "33"),
        (0.1, 0.02, 0.0, 0.01, 0.15, 0.03, 0.0, 0.01, 0.12)))


def run_table(text: str) -> dict:
    d_np_table = transform_lines_to_d_np_table(text.split("\n"))
    redefine_inline_parameters(d_np_table)
    return d_np_table


@pytest.mark.parametrize("name, number", [
    ("friedel", 2), ("orto", 8), ("tetra", 16), ("hex", 12), ("cubic", 48)])
def test_number_of_equivalent_hkl(name, number):
    assert len(set(choose_func_equiv(name)((1, 2, 3)))) == number


def test_cubic_average_takes_cyclic_permutations():
    d_np_table = run_table(
        "aver_hkl cubic\n\n H K L Intensity sIntensity\n"
        " 1 2 3 10 1\n 3 1 2 11 1\n 2 3 1 12 1\n -1 -2 -3 10 1\n")
    assert d_np_table["H"].size == 1
    assert d_np_table["Intensity"][0] == pytest.approx(10.75)


def test_cell_by_ub_and_generated_hkl():
    d_np_table = run_table(UB + "\nwavelength : 1.5\ngenerate_hkl 2theta 10 40\n")
    # a, b, c, alpha, beta, gamma of this UB (Busing-Levy, columns b*)
    assert [d_np_table[name][0] for name in ("a", "b", "c")] == pytest.approx(
        [10.23599, 7.11763, 8.49604], abs=1e-5)
    assert [d_np_table[name][0] for name in ("alpha", "beta", "gamma")] == \
        pytest.approx([107.85400, 87.17854, 103.49764], abs=1e-5)
    assert d_np_table["H"].size == 222
    assert numpy.all(numpy.diff(d_np_table["sthovl"]) >= 0.)
    assert d_np_table["2Theta"].min() >= 10. and d_np_table["2Theta"].max() <= 40.


def test_index_hkl_in_range_has_no_symmetry():
    unit_cell_parameters = numpy.array(
        [5., 6., 7., numpy.pi/2, numpy.radians(100.), numpy.pi/2])
    index_hkl = calc_index_hkl_in_range(0.05, 0.3, unit_cell_parameters)
    assert index_hkl.shape == (3, 182)
    l_hkl = [tuple(hkl) for hkl in index_hkl.T.tolist()]
    assert (1, 0, 0) in l_hkl and (-1, 0, 0) in l_hkl
