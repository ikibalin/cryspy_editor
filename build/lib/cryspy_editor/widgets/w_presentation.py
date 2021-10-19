"""Functions to create docks for dock-area."""
import numpy
from PyQt5 import QtWidgets, QtCore

from cryspy import AtomSiteL, Crystal, Cell, SpaceGroup, \
    PdInstrResolution, Diffrn, \
    PdBackgroundL, Pd, PdMeasL, RhoChi, Chi2, \
    Pd2dMeas, Pd2dProc, Pd2d, TOF, \
    Setup, PhaseL, Range, DiffrnRadiation, Pd2dBackground, \
    Pd2dInstrResolution, DiffrnOrientMatrix, DiffrnReflnL, Phase, \
    AtomElectronConfigurationL, MEM, AtomSiteScatL, \
    InversedHessian

from cryspy.A_functions_base.function_2_crystallography_base import \
    calc_atoms_in_unit_cell
from cryspy.A_functions_base.function_2_mem import \
    calc_index_atom_symmetry_closest_to_fract_xyz

from cryspy.B_parent_classes.cl_1_item import ItemN
from cryspy.B_parent_classes.cl_2_loop import LoopN
from cryspy.B_parent_classes.cl_3_data import DataN
from cryspy.B_parent_classes.cl_4_global import GlobalN

from cryspy.D_functions_item_loop.function_1_section_from_density_point \
    import calc_section_from_density_point

import matplotlib.pyplot as plt


def define_tool_buttons(obj, thread: QtCore.QThread) -> tuple:
    """Give actions."""
    w_actions = ()
    if isinstance(obj, RhoChi):
        w_actions = action_rhochi(obj, thread)
    elif isinstance(obj, MEM):
        w_actions = action_mem(obj, thread)
    elif isinstance(obj, Crystal):
        w_actions = action_crystal(obj, thread)
    elif isinstance(obj, Pd):
        w_actions = action_pd(obj, thread)
    elif isinstance(obj, Pd2d):
        w_actions = action_pd2d(obj, thread)
    elif isinstance(obj, TOF):
        w_actions = action_tof(obj, thread)
    elif isinstance(obj, Diffrn):
        w_actions = action_diffrn(obj, thread)
    elif isinstance(obj, AtomSiteScatL):
        w_actions = action_atom_site_scat_l(obj, thread)
    elif isinstance(obj, PdInstrResolution):
        w_actions = action_pd_instr_resolution(obj, thread)
    elif isinstance(obj, Pd2dMeas):
        w_actions = action_pd2d_meas(obj, thread)
    elif isinstance(obj, Pd2dProc):
        w_actions = action_pd2d_proc(obj, thread)
    elif isinstance(obj, Cell):
        w_actions = action_cell(obj, thread)
    elif isinstance(obj, SpaceGroup):
        w_actions = action_space_group(obj, thread)
    elif isinstance(obj, DiffrnOrientMatrix):
        w_actions = action_diffrn_orient_matrix(obj, thread)
    elif isinstance(obj, DiffrnReflnL):
        w_actions = action_diffrn_refln_l(obj, thread)
    elif isinstance(obj, AtomSiteL):
        w_actions = action_atom_site_l(obj, thread)
    elif isinstance(obj, InversedHessian):
        w_actions = action_inversed_hessian(obj, thread)
    # l_action = list(w_actions)
    # l_action.extend(action_plots(obj))
    return w_actions


def action_atom_site_l(obj: AtomSiteL, thread: QtCore.QThread):
    """Give actions for AtomSiteL."""
    w_actions = []
    if obj.is_attribute("type_symbol"):
        qtb_1 = QtWidgets.QToolButton()
        qtb_1.setText("Show b_scat")
        qtb_1.clicked.connect(lambda: run_function(
            obj.report, (), thread))
        w_actions.append(qtb_1)
    return w_actions


def action_inversed_hessian(obj: InversedHessian, thread: QtCore.QThread):
    """Give actions for AtomSiteL."""
    w_actions = []
    if obj.is_defined():
        qtb_1 = QtWidgets.QToolButton()
        qtb_1.setText("Show correlation")
        qtb_1.clicked.connect(lambda: run_function(
            obj.report, (), thread))
        w_actions.append(qtb_1)
    return w_actions


def action_plots(obj):
    w_actions = []
    if not(isinstance(obj, (ItemN, LoopN, DataN, GlobalN))):
        return w_actions

    qtb_1 = QtWidgets.QToolButton()
    qtb_1.setText("Plots")

    def func_plot(obj):
        plots = obj.plots()
        for plot in plots:
            fig, ax = plot
            fig.show()
        return
    qtb_1.clicked.connect(lambda: func_plot(obj))
    w_actions.append(qtb_1)
    return w_actions


def action_atom_site_scat_l(obj: AtomSiteScatL, thread: QtCore.QThread):
    """Plot form factor."""
    w_actions = []
    if (obj.is_attribute("atom_type_scat") |
            obj.is_attribute("type_symbol")):
        qtb_1 = QtWidgets.QToolButton()
        qtb_1.setText("Plot form factors")
        sthovl = numpy.linspace(0, 2, 100)

        def func_plot(obj, sthovl, flag):
            fig, ax = obj.plot_form_factor()
            fig.show()
            return (fig, ax)
        qtb_1.clicked.connect(lambda: func_plot(obj, sthovl, False))
        w_actions.append(qtb_1)
    return w_actions


def action_pd_instr_resolution(obj: PdInstrResolution, thread: QtCore.QThread):
    """Plot resolution."""
    w_actions = []
    if (obj.is_defined()):
        qtb_1 = QtWidgets.QToolButton()
        qtb_1.setText("Plot resolution")
        ttheta = numpy.linspace(0, 140, 100)

        def func_plot(obj, ttheta):
            h_pv, eta, h_g, h_l, a_g, b_g, a_l, b_l = obj.calc_resolution(
                ttheta)
            plt.plot(ttheta, h_g, label="h_g")
            plt.plot(ttheta, h_l, label="h_l")
            plt.plot(ttheta, h_pv, label="h_pv")
            plt.legend(loc='upper right')
            plt.show()
            return
        qtb_1.clicked.connect(lambda: func_plot(obj, ttheta))
        w_actions.append(qtb_1)
    return w_actions


def action_cell(obj: Cell, thread: QtCore.QThread):
    """Plot resolution."""
    w_actions = []
    if (obj.is_defined()):
        qtb_1 = QtWidgets.QToolButton()
        qtb_1.setText("Cell report")
        qtb_1.clicked.connect(lambda: run_function(
            obj.report, (), thread))
        w_actions.append(qtb_1)
    return w_actions


def action_diffrn_orient_matrix(obj: DiffrnOrientMatrix,
                                thread: QtCore.QThread):
    """Plot resolution."""
    w_actions = []
    if (obj.is_defined()):
        qtb_1 = QtWidgets.QToolButton()
        qtb_1.setText("Show U matrix")

        def func_temp(obj):
            s_out = f"""Orientation matrix U:
          a* [c,  a*]        c
 X: {obj.u_11: 8.5f} {obj.u_12: 8.5f} {obj.u_13: 8.5f}
 Y: {obj.u_21: 8.5f} {obj.u_22: 8.5f} {obj.u_23: 8.5f}
 Z: {obj.u_31: 8.5f} {obj.u_32: 8.5f} {obj.u_33: 8.5f}

axis 'X' is along incident beam;
axis 'Z' is vertical direction."""
            return s_out

        qtb_1.clicked.connect(lambda: run_function(
            func_temp, (obj, ), thread))
        w_actions.append(qtb_1)
    return w_actions


def action_diffrn_refln_l(obj: DiffrnReflnL, thread: QtCore.QThread):
    """Give actions diffrn_refln."""
    w_actions = []
    if (obj.is_defined()):
        qtb_1 = QtWidgets.QToolButton()
        qtb_1.setText("Report experimental agreement factors")
        qtb_1.clicked.connect(lambda: run_function(
            obj.report_agreement_factor_exp, (), thread))
        w_actions.append(qtb_1)

        if (obj.is_attribute("fr") & obj.is_attribute("fr_sigma") &
                obj.is_attribute("fr_calc")):
            qtb_1 = QtWidgets.QToolButton()
            qtb_1.setText("Report chi_sq exp.")
            qtb_1.clicked.connect(lambda: run_function(
                obj.report_chi_sq_exp, (), thread))
            w_actions.append(qtb_1)

            qtb_1 = QtWidgets.QToolButton()
            qtb_1.setText("Plot FR_exp/FR_mod")

            def func_plot(obj):
                plt.errorbar(obj.fr_calc, obj.fr, yerr=obj.fr_sigma, fmt=".")
                plt.plot(obj.fr, obj.fr)
                # plt.legend(loc='upper right')
                plt.show()
                return
            qtb_1.clicked.connect(lambda: func_plot(obj))

            w_actions.append(qtb_1)
    return w_actions


def action_space_group(obj: SpaceGroup, thread: QtCore.QThread):
    """Plot resolution."""
    w_actions = []
    if (obj.is_defined()):
        qtb_1 = QtWidgets.QToolButton()
        qtb_1.setText("Space Group report")
        qtb_1.clicked.connect(lambda: run_function(
            obj.report_space_group, (), thread))
        w_actions.append(qtb_1)
    return w_actions


def action_rhochi(obj: RhoChi, thread: QtCore.QThread):
    """Dock for RhoChi object."""
    w_actions = []
    crystals = obj.crystals()
    experiments = obj.experiments()

    flag_crystals = len(crystals) != 0
    flag_experiments = len(experiments) != 0
    flag_diffrn = any([isinstance(exp, Diffrn) for exp in experiments])

    # for experiment in experiments:
    #     if isinstance(experiment, Pd):
    #         w_actions_t = action_pd(experiment, thread)
    #         w_actions.extend(w_actions_t)
    #     elif isinstance(experiment, Pd2d):
    #         w_actions_t = action_pd2d(experiment, thread)
    #         w_actions.extend(w_actions_t)
    #     elif isinstance(experiment, Diffrn):
    #         w_actions_t = action_diffrn(experiment, thread)
    #         w_actions.extend(w_actions_t)

    # Action doc
    if (flag_crystals & flag_experiments & obj.is_defined()):
        qtb_1 = QtWidgets.QToolButton()
        qtb_1.setText("Calc. Chi square")
        qtb_1.clicked.connect(lambda: run_function(
            obj.calc_chi_sq, (True, ), thread))
        w_actions.append(qtb_1)

        qtb_1 = QtWidgets.QToolButton()
        qtb_1.setText("Refine")
        qtb_1.clicked.connect(lambda: run_function(
            obj.refine, (False, "BFGS",), thread))
        w_actions.append(qtb_1)

        qtb_1 = QtWidgets.QToolButton()
        qtb_1.setText("Estimate Inversed Hessian")
        qtb_1.clicked.connect(lambda: run_function(
            obj.estimate_inversed_hessian, (), thread))
        w_actions.append(qtb_1)

    elif not(flag_crystals & flag_experiments):
        if not flag_crystals:
            qtb_1 = QtWidgets.QToolButton()
            qtb_1.setText("Add crystal")
            qtb_1.clicked.connect(lambda: add_items(obj, [
                Crystal(data_name="phase")], thread))
            w_actions.append(qtb_1)

        if not flag_experiments:
            qtb_1 = QtWidgets.QToolButton()
            qtb_1.setText("Add diffrn")
            qtb_1.clicked.connect(lambda: add_items(obj, [
                Diffrn(data_name="mono")], thread))
            w_actions.append(qtb_1)

            qtb_1 = QtWidgets.QToolButton()
            qtb_1.setText("Add pd")
            qtb_1.clicked.connect(lambda: add_items(obj, [
                Pd(data_name="powder1d")], thread))
            w_actions.append(qtb_1)

            qtb_1 = QtWidgets.QToolButton()
            qtb_1.setText("Add pd2d")
            qtb_1.clicked.connect(lambda: add_items(obj, [
                Pd2d(data_name="powder2d")], thread))
            w_actions.append(qtb_1)
    else:
        qlabel = QtWidgets.QLabel(
            "To run calculations all items should be defined.")
        w_actions.append(qlabel)
        # layout_actions.addWidget(qlabel)
    if (flag_diffrn & flag_crystals):
        qtb_1 = QtWidgets.QToolButton()
        qtb_1.setText("Estimate F_M")
        qtb_1.clicked.connect(lambda: run_function(
            obj.estimate_f_mag_for_diffrn, (), thread))
        w_actions.append(qtb_1)
    if obj.is_attribute("inversed_hessian"):
        w_actions_t = action_inversed_hessian(obj.inversed_hessian, thread)
        w_actions.extend(w_actions_t)
    return w_actions


def action_mem(obj: MEM, thread: QtCore.QThread):
    """Dock for MEM object."""
    w_actions = []
    crystals = obj.crystals()
    experiments = obj.experiments()

    flag_crystals = len(crystals) != 0
    flag_experiments = len(experiments) != 0

    # for experiment in experiments:
    #     w_actions_temp = action_diffrn(experiment, thread)
    #     w_actions.extend(w_actions_temp)

    # Action doc
    if (flag_crystals & flag_experiments & obj.is_defined()):
        if flag_crystals:
            crystal = crystals[0]
            if not(crystal.is_attribute("atom_electron_configuration")):
                qtb_1 = QtWidgets.QToolButton()
                qtb_1.setText("Create AtomElectronConfiguration")
                qtb_1.clicked.connect(lambda: crystal.add_items([
                    AtomElectronConfigurationL()]))
                qtb_1.clicked.connect(lambda: run_function(pass_func, (),
                                                           thread))
                w_actions.append(qtb_1)

        qtb_1 = QtWidgets.QToolButton()
        qtb_1.setText("Create prior density")
        qtb_1.clicked.connect(lambda: run_function(
            obj.create_prior_density, (), thread))
        w_actions.append(qtb_1)

        qtb_1 = QtWidgets.QToolButton()
        qtb_1.setText("Calculate FR")
        qtb_1.clicked.connect(lambda: run_function(obj.calc_fr, (),
                                                   thread))
        w_actions.append(qtb_1)

        qtb_1 = QtWidgets.QToolButton()
        qtb_1.setText("Maximize entropy")
        qtb_1.clicked.connect(lambda: run_function(obj.maximize_entropy, (),
                                                   thread))
        w_actions.append(qtb_1)

        qtb_1 = QtWidgets.QToolButton()
        qtb_1.setText("Chi refinement")
        qtb_1.clicked.connect(lambda: run_function(obj.refine_susceptibility,
                                                   (), thread))
        w_actions.append(qtb_1)

        qtb_1 = QtWidgets.QToolButton()
        qtb_1.setText("Run cycle")
        qtb_1.clicked.connect(lambda: run_function(obj.make_cycle, (),
                                                   thread))
        w_actions.append(qtb_1)

        qtb_1 = QtWidgets.QToolButton()
        qtb_1.setText("Save to '.den' files")
        qtb_1.clicked.connect(lambda: run_function(obj.save_to_file_den, (),
                                                   thread))
        w_actions.append(qtb_1)

        if obj.is_attribute("section"):
            qtb_1 = QtWidgets.QToolButton()
            qtb_1.setText("Plot sections")
    
            def func_plot(obj):
                crystal = obj.crystals()[0]
                space_group = crystal.space_group
                f_s_g_s = space_group.full_space_group_symop
                r_11 = numpy.array(f_s_g_s.r_11, dtype=float)
                r_12 = numpy.array(f_s_g_s.r_12, dtype=float)
                r_13 = numpy.array(f_s_g_s.r_13, dtype=float)
                r_21 = numpy.array(f_s_g_s.r_21, dtype=float)
                r_22 = numpy.array(f_s_g_s.r_22, dtype=float)
                r_23 = numpy.array(f_s_g_s.r_23, dtype=float)
                r_31 = numpy.array(f_s_g_s.r_31, dtype=float)
                r_32 = numpy.array(f_s_g_s.r_32, dtype=float)
                r_33 = numpy.array(f_s_g_s.r_33, dtype=float)
    
                r_ij = (r_11, r_12, r_13, r_21, r_22, r_23, r_31, r_32, r_33)
    
                b_1 = numpy.array(f_s_g_s.b_1, dtype=float)
                b_2 = numpy.array(f_s_g_s.b_2, dtype=float)
                b_3 = numpy.array(f_s_g_s.b_3, dtype=float)
    
                b_i = (b_1, b_2, b_3)
    
                atom_site = crystal.atom_site
                fract_x = atom_site.numpy_fract_x
                fract_y = atom_site.numpy_fract_y
                fract_z = atom_site.numpy_fract_z
                fract_xyz = (fract_x, fract_y, fract_z)
    
                atom_label = atom_site.numpy_label
    
                fract_uc_x, fract_uc_y, fract_uc_z, label_uc = \
                    calc_atoms_in_unit_cell(r_ij, b_i, fract_xyz, atom_label)
    
                cell = crystal.cell
                atom_site_susceptibility = crystal.atom_site_susceptibility
    
                section = obj.section[0]
                density_point = obj.density_point
                mem_parameters = obj.mem_parameters
    
                atom_x, atom_y, atom_label = section.calc_atoms(
                    cell, atom_site, f_s_g_s, distance_min=0.3)
    
                den_chi_section, den_b_section = \
                    calc_section_from_density_point(
                    section, density_point, mem_parameters, cell, f_s_g_s,
                    atom_site, atom_site_susceptibility)
    
                fract_atom_xyz = numpy.array(fract_xyz, dtype=float
                                             ).transpose()

                fract_sec_xyz = section.calc_fractions(cell, atom_site)
                fract_sec_xyz = numpy.transpose(numpy.array(fract_sec_xyz,
                                                            dtype=float))
    
                n_atom_index, n_symmetry, distance = \
                    calc_index_atom_symmetry_closest_to_fract_xyz(
                        fract_sec_xyz, fract_atom_xyz, r_ij, b_i, cell)
                n_at_2d = numpy.transpose(n_atom_index.reshape(
                    section.points_x, section.points_y))
    
                fig, (ax1, ax2) = plt.subplots(ncols=2, figsize=(4.2, 4.2),
                                               dpi=300)
                plt.set_cmap('Accent')
                ax1.imshow(n_at_2d, interpolation='bilinear',
                           extent=(-0.5*section.size_x, 0.5*section.size_x,
                                   -0.5*section.size_y, 0.5*section.size_y),
                           alpha=0.1, origin="lower")
    
                den_x = numpy.linspace(-0.5*section.size_x, 0.5*section.size_x,
                                       section.points_x)
                den_y = numpy.linspace(-0.5*section.size_y, 0.5*section.size_y,
                                       section.points_y)
    
                blk = '#000000'
                ax1.contour(den_x, den_y, den_chi_section.transpose(),
                            levels=[0.1, 0.5, 1., 5., 10., 50.],
                            colors=[blk, blk, blk, blk, blk, blk],
                            linewidths=0.5)
    
                ax1.plot(atom_x, atom_y, 'ko', ms=3)
                for _1, _2, _3 in zip(atom_x, atom_y, atom_label):
                    ax1.text(_1, _2, _3)
                ax1.set_title(
                    f"Tensor. Max is {den_chi_section.max():.1f}")
    
                # plt.set_cmap('RdBu')
                ax2.imshow(n_at_2d, interpolation='bilinear',
                           extent=(-0.5*section.size_x, 0.5*section.size_x,
                                   -0.5*section.size_y, 0.5*section.size_y),
                           alpha=0.1, origin="lower")
    
                hh = numpy.abs(den_b_section).max()
                rd = '#FF0000'
                ax2.contour(den_x, den_y, den_b_section.transpose(),
                            levels=[-50., -10., -5., -1., -0.5, -0.1, 
                                    0.1, 0.5, 1., 5., 10., 50.],
                            colors=[rd, rd, rd, rd, rd, rd,
                                    blk, blk, blk, blk, blk, blk],
                            linewidths=0.5)
                # ax2.imshow(den_b_section, interpolation='bilinear',
                #            extent=(-0.5*section.size_x, 0.5*section.size_x,
                #                    -0.5*section.size_y, 0.5*section.size_y),
                #            vmin=-hh, vmax=hh,
                #            alpha=1., origin="lower")
                ax2.set_title(f"2channel. Max is {hh:.1f}")
                ax2.plot(atom_x, atom_y, 'ko', ms=3)
                for _1, _2, _3 in zip(atom_x, atom_y, atom_label):
                    ax2.text(_1, _2, _3)
    
                plt.show()
    
                return
            qtb_1.clicked.connect(lambda: func_plot(obj))
            w_actions.append(qtb_1)

    elif not(flag_crystals & flag_experiments):
        if not flag_crystals:
            qtb_1 = QtWidgets.QToolButton()
            qtb_1.setText("Add crystal")
            qtb_1.clicked.connect(lambda: add_items(obj, [
                Crystal(data_name="phase")], thread))
            w_actions.append(qtb_1)

        if not flag_experiments:
            qtb_1 = QtWidgets.QToolButton()
            qtb_1.setText("Add diffrn")
            qtb_1.clicked.connect(lambda: add_items(obj, [
                Diffrn(data_name="mono")], thread))
            w_actions.append(qtb_1)

    else:
        qlabel = QtWidgets.QLabel(
            "To run calculations all items should be defined.")
        qlabel.setSizePolicy(QtWidgets.QSizePolicy.Expanding,
                             QtWidgets.QSizePolicy.Expanding)
        w_actions.append(qlabel)

    return w_actions


def pass_func():
    """Pass function."""
    return


def add_items(obj, l_item, thread: QtCore.QThread):
    """Add items."""
    obj.add_items(l_item)
    thread.function = pass_func
    thread.arguments = ()
    thread.start()


def run_function(func, args, thread: QtCore.QThread):
    """Run function."""
    thread.function = func
    thread.arguments = args
    thread.start()


def action_pd(obj: Pd, thread: QtCore.QThread):
    """Form dock_pd.

    Based on
    --------
        - dock_proc
        - dock_meas
        - dock_chi2
        - dock_refine_ls
        - dock_peak
    """
    w_actions = []
    f_meas = obj.is_attribute("pd_meas")
    f_chi2 = obj.is_attribute("chi2")
    f_phase = obj.is_attribute("phase")

    l_pd_peak = []
    if f_phase:
        phase = obj.phase
        for item in phase.items:
            try:
                pd_peak = getattr(obj, f"pd_peak_{item.label.lower():}")
                l_pd_peak.append(pd_peak)
            except AttributeError:
                pass

    f_setup = obj.is_attribute("setup")
    f_pd_instr_resolution = obj.is_attribute("pd_instr_resolution")
    f_pd_background = obj.is_attribute("pd_background")
    f_range = obj.is_attribute("range")

    if not(f_chi2 & f_meas & f_setup & f_pd_instr_resolution & f_phase &
           f_pd_background & f_range):
        if not f_chi2:
            qtb_1 = QtWidgets.QToolButton()
            qtb_1.setText("Add chi2")
            qtb_1.clicked.connect(lambda: add_items(obj, [Chi2()], thread))
            w_actions.append(qtb_1)

        if not f_meas:
            qtb_1 = QtWidgets.QToolButton()
            qtb_1.setText("Add pd_meas")
            qtb_1.clicked.connect(lambda: add_items(obj, [PdMeasL()], thread))
            w_actions.append(qtb_1)

        if not f_setup:
            qtb_1 = QtWidgets.QToolButton()
            qtb_1.setText("Add setup")
            qtb_1.clicked.connect(lambda: add_items(obj, [Setup()], thread))
            w_actions.append(qtb_1)

        if not f_pd_instr_resolution:
            qtb_1 = QtWidgets.QToolButton()
            qtb_1.setText("Add pd_instr_resolution")
            qtb_1.clicked.connect(lambda: add_items(obj, [PdInstrResolution()],
                                                    thread))
            w_actions.append(qtb_1)

        if not f_phase:
            qtb_1 = QtWidgets.QToolButton()
            qtb_1.setText("Add phase")
            vv = PhaseL()
            vv.items = [Phase(label="phase", igsize=0., scale=1.)]
            qtb_1.clicked.connect(lambda: add_items(obj, [vv], thread))
            w_actions.append(qtb_1)

        if not f_pd_background:
            qtb_1 = QtWidgets.QToolButton()
            qtb_1.setText("Add pd_background")
            qtb_1.clicked.connect(lambda: add_items(obj, [PdBackgroundL()],
                                                    thread))
            w_actions.append(qtb_1)

        if not f_range:
            qtb_1 = QtWidgets.QToolButton()
            qtb_1.setText("Add range")
            qtb_1.clicked.connect(lambda: add_items(obj, [Range(
                ttheta_min=2, ttheta_max=100.)], thread))
            w_actions.append(qtb_1)
    return w_actions


def action_tof(obj: TOF, thread: QtCore.QThread):
    """Form dock_pd.

    Based on
    --------
        - dock_proc
        - dock_meas
        - dock_chi2
        - dock_refine_ls
        - dock_peak
    """
    w_actions = []
    # f_meas = obj.is_attribute("pd_meas")
    # f_chi2 = obj.is_attribute("chi2")
    # f_phase = obj.is_attribute("phase")

    # l_pd_peak = []
    # if f_phase:
    #     phase = obj.phase
    #     for item in phase.items:
    #         try:
    #             pd_peak = getattr(obj, f"pd_peak_{item.label.lower():}")
    #             l_pd_peak.append(pd_peak)
    #         except AttributeError:
    #             pass

    # f_setup = obj.is_attribute("setup")
    # f_pd_instr_resolution = obj.is_attribute("pd_instr_resolution")
    # f_pd_background = obj.is_attribute("pd_background")
    # f_range = obj.is_attribute("range")

    # if not(f_chi2 & f_meas & f_setup & f_pd_instr_resolution & f_phase &
    #        f_pd_background & f_range):
    #     if not f_chi2:
    #         qtb_1 = QtWidgets.QToolButton()
    #         qtb_1.setText("Add chi2")
    #         qtb_1.clicked.connect(lambda: add_items(obj, [Chi2()], thread))
    #         w_actions.append(qtb_1)

    return w_actions


def action_crystal(obj: Crystal, thread: QtCore.QThread):
    """Docks for crystal."""
    w_actions = []
    if not(obj.is_attribute("cell")):
        qtb_1 = QtWidgets.QToolButton()
        qtb_1.setText("Add cell")
        qtb_1.clicked.connect(lambda: add_items(obj, [Cell()], thread))
        w_actions.append(qtb_1)
    else:
        cell = obj.cell
        w_actions.extend(action_cell(cell, thread))

    if not(obj.is_attribute("space_group")):
        qtb_1 = QtWidgets.QToolButton()
        qtb_1.setText("Add space group")
        qtb_1.clicked.connect(lambda: add_items(obj, [SpaceGroup(
            name_hm_alt="P 1")], thread))
        w_actions.append(qtb_1)
    else:
        space_group = obj.space_group
        w_actions.extend(action_space_group(space_group, thread))

    if not(obj.is_attribute("atom_site")):
        qtb_1 = QtWidgets.QToolButton()
        qtb_1.setText("Add atom site")
        qtb_1.clicked.connect(lambda: add_items(obj, [AtomSiteL()],
                                                thread))
        w_actions.append(qtb_1)
    else:
        atom_site = obj.atom_site
        w_actions.extend(action_atom_site_l(atom_site, thread))

    if obj.is_attribute("atom_site_susceptibility"):
        qtb_1 = QtWidgets.QToolButton()
        qtb_1.setText("Report main axes of magn.ellipsoids")
        qtb_1.clicked.connect(lambda: run_function(
            obj.report_main_axes_of_magnetization_ellipsoids, (), thread))
        w_actions.append(qtb_1)

    if obj.is_attribute("atom_site_scat"):
        atom_site_scat = obj.atom_site_scat
        w_actions.extend(action_atom_site_scat_l(atom_site_scat, thread))

    return w_actions


def action_pd2d(obj: Pd2d, thread: QtCore.QThread):
    """Actions for pd2d."""
    w_actions = []
    f_meas = obj.is_attribute("pd2d_meas")
    f_proc = obj.is_attribute("pd2d_proc")
    f_chi2 = obj.is_attribute("chi2")
    f_phase = obj.is_attribute("phase")

    f_setup = obj.is_attribute("setup")
    f_pd2d_instr_resolution = obj.is_attribute("pd2d_instr_resolution")
    f_phase = obj.is_attribute("phase")
    f_pd2d_background = obj.is_attribute("pd2d_background")
    f_range = obj.is_attribute("range")

    if not(f_chi2 & f_meas & f_setup & f_pd2d_instr_resolution & f_phase &
           f_pd2d_background & f_range):

        if not f_chi2:
            qtb_1 = QtWidgets.QToolButton()
            qtb_1.setText("Add chi2")
            qtb_1.clicked.connect(lambda: add_items(obj, [Chi2()], thread))
            w_actions.append(qtb_1)

        if not f_meas:
            qtb_1 = QtWidgets.QToolButton()
            qtb_1.setText("Add pd2d_meas")
            qtb_1.clicked.connect(lambda: add_items(obj, [Pd2dMeas()], thread))
            w_actions.append(qtb_1)

        if not f_setup:
            qtb_1 = QtWidgets.QToolButton()
            qtb_1.setText("Add setup")
            qtb_1.clicked.connect(lambda: add_items(obj, [Setup()], thread))
            w_actions.append(qtb_1)

        if not f_pd2d_instr_resolution:
            qtb_1 = QtWidgets.QToolButton()
            qtb_1.setText("Add pd2d_instr_resolution")
            qtb_1.clicked.connect(lambda: add_items(obj, [
                Pd2dInstrResolution()], thread))
            w_actions.append(qtb_1)

        if not f_phase:
            qtb_1 = QtWidgets.QToolButton()
            qtb_1.setText("Add phase")
            vv = PhaseL()
            vv.items = [Phase(label="phase", igsize=0., scale=1.)]
            qtb_1.clicked.connect(lambda: add_items(obj, [vv], thread))
            w_actions.append(qtb_1)

        if not f_pd2d_background:
            qtb_1 = QtWidgets.QToolButton()
            qtb_1.setText("Add pd2d_background")
            qtb_1.clicked.connect(lambda: add_items(obj, [Pd2dBackground()],
                                                    thread))
            w_actions.append(qtb_1)

        if not f_range:
            qtb_1 = QtWidgets.QToolButton()
            qtb_1.setText("Add range")
            qtb_1.clicked.connect(lambda: add_items(obj, [Range(
                ttheta_min=4., ttheta_max=80., phi_min=-10., phi_max=20.)],
                thread))
            w_actions.append(qtb_1)
    if (f_proc | f_meas):
        if f_proc:
            w_actions.extend(action_pd2d_proc(obj.pd2d_proc, thread))
        elif f_meas:
            w_actions.extend(action_pd2d_proc(obj.pd2d_meas, thread))

    return w_actions


def action_pd2d_meas(obj: Pd2dMeas, thread: QtCore.QThread):
    """Actions for Pd2dMeas objects."""
    w_actions = []
    qtb_1 = QtWidgets.QToolButton()
    qtb_1.setText("Plot gamma-nu")

    def func_plot_gn(obj):
        fig, ax = obj.plot_gamma_nu()
        fig.show()
        return (fig, ax)

    qtb_1.clicked.connect(lambda: func_plot_gn(obj))
    w_actions.append(qtb_1)

    qtb_1 = QtWidgets.QToolButton()
    qtb_1.setText("Plot 2theta-phi")

    def func_plot_tp(obj):
        fig, ax = obj.plot_ttheta_phi()
        fig.show()
        return (fig, ax)

    qtb_1.clicked.connect(lambda: func_plot_tp(obj))
    w_actions.append(qtb_1)
    return w_actions


def action_pd2d_proc(obj: Pd2dProc, thread: QtCore.QThread):
    """Actions for Pd2dMeas objects."""
    w_actions = []
    qtb_1 = QtWidgets.QToolButton()
    qtb_1.setText("Plot gamma-nu")

    def func_plot_gn(obj):
        fig, ax = obj.plot_gamma_nu()
        fig.show()
        return (fig, ax)

    qtb_1.clicked.connect(lambda: func_plot_gn(obj))
    w_actions.append(qtb_1)

    qtb_1 = QtWidgets.QToolButton()
    qtb_1.setText("Plot 2theta-phi")

    def func_plot_tp(obj):
        fig, ax = obj.plot_ttheta_phi()
        fig.show()
        return (fig, ax)

    qtb_1.clicked.connect(lambda: func_plot_tp(obj))
    w_actions.append(qtb_1)
    return w_actions


def action_diffrn(obj: Diffrn, thread: QtCore.QThread):
    """Actions for Diffrn objects."""
    w_actions = []

    f_setup = obj.is_attribute("setup")
    f_diffrn_radiation = obj.is_attribute("diffrn_radiation")
    f_diffrn_orient_matrix = obj.is_attribute("diffrn_orient_matrix")
    f_diffrn_refln = obj.is_attribute("diffrn_refln")
    f_phase = obj.is_attribute("phase")

    if not(f_setup & f_diffrn_radiation & f_diffrn_orient_matrix &
           f_diffrn_refln & f_phase):
        if not(f_setup):
            qtb_1 = QtWidgets.QToolButton()
            qtb_1.setText("Add setup")
            qtb_1.clicked.connect(lambda: add_items(obj, [Setup()], thread))
            w_actions.append(qtb_1)

        if not(f_diffrn_radiation):
            qtb_1 = QtWidgets.QToolButton()
            qtb_1.setText("Add diffrn_radiation")
            qtb_1.clicked.connect(lambda: add_items(
                obj, [DiffrnRadiation()], thread))
            w_actions.append(qtb_1)

        if not(f_diffrn_orient_matrix):
            qtb_1 = QtWidgets.QToolButton()
            qtb_1.setText("Add diffrn_orient_matrix")
            qtb_1.clicked.connect(lambda: add_items(obj, [DiffrnOrientMatrix(
                ub_11=1., ub_12=0., ub_13=0., ub_21=0., ub_22=1., ub_23=0.,
                ub_31=0., ub_32=0., ub_33=1.,)], thread))
            w_actions.append(qtb_1)

        if not(f_diffrn_refln):
            qtb_1 = QtWidgets.QToolButton()
            qtb_1.setText("Add diffrn_refln")
            qtb_1.clicked.connect(lambda: add_items(
                obj, [DiffrnReflnL()], thread))
            w_actions.append(qtb_1)

        if not(f_phase):
            qtb_1 = QtWidgets.QToolButton()
            qtb_1.setText("Add phase")
            qtb_1.clicked.connect(lambda: add_items(obj, [
                Phase(label="phase")], thread))
            w_actions.append(qtb_1)

    if f_diffrn_refln:
        diffrn_refln = obj.diffrn_refln
        w_actions.extend(action_diffrn_refln_l(diffrn_refln, thread))
    if f_diffrn_orient_matrix:
        diffrn_orient_matrix = obj.diffrn_orient_matrix
        w_actions.extend(action_diffrn_orient_matrix(
            diffrn_orient_matrix, thread))
    return w_actions
