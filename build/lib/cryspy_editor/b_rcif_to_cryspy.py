import pycifstar
import os
import copy


L_ITEM_CLASS = []
L_LOOP_CLASS = []
L_DATA_CLASS = []
L_GLOBAL_CLASS = []

try:
    FLAG_CRYSPY = True

    from cryspy.common.cl_global_constr import GlobalConstr
    from cryspy.common.cl_data_constr import DataConstr

    from cryspy.cif_like.cl_crystal import Crystal
    from cryspy.cif_like.cl_pd import Pd
    from cryspy.cif_like.cl_pd2d import Pd2d
    from cryspy.cif_like.cl_diffrn import Diffrn

    from cryspy.pd2dcif_like.cl_pd2d_meas import Pd2dMeas
    from cryspy.pd2dcif_like.cl_pd2d_proc import Pd2dProc

    from cryspy.cif_like.cl_chi2 import Chi2 
    from cryspy.cif_like.cl_diffrn_radiation import DiffrnRadiation 
    from cryspy.cif_like.cl_extinction import Extinction 
    from cryspy.cif_like.cl_range import Range 
    from cryspy.cif_like.cl_setup import Setup 
    from cryspy.cif_like.cl_texture import Texture 
    from cryspy.cif_like.cl_diffrn_refln import DiffrnRefln, DiffrnReflnL 
    from cryspy.cif_like.cl_exclude import Exclude, ExcludeL 
    from cryspy.cif_like.cl_phase import Phase, PhaseL 

    from cryspy.corecif.cl_atom_site import AtomSiteL
    from cryspy.corecif.cl_atom_site_aniso import AtomSiteAnisoL
    from cryspy.corecif.cl_atom_type import AtomTypeL
    from cryspy.corecif.cl_cell import Cell
    from cryspy.corecif.cl_diffrn_orient_matrix import DiffrnOrientMatrix
    from cryspy.corecif.cl_refine_ls import RefineLs
    from cryspy.corecif.cl_refln import ReflnL

    from cryspy.magneticcif.cl_atom_site_moment import AtomSiteMomentL
    from cryspy.magneticcif.cl_atom_site_scat import AtomSiteScatL
    from cryspy.magneticcif.cl_atom_site_susceptibility import AtomSiteSusceptibilityL
    from cryspy.magneticcif.cl_atom_type_scat import AtomTypeScatL
    from cryspy.magneticcif.cl_refln_susceptibility import ReflnSusceptibilityL

    from cryspy.symcif.cl_space_group import SpaceGroup
    from cryspy.symcif.cl_space_group_symop import SpaceGroupSymop, SpaceGroupSymopL
    from cryspy.symcif.cl_space_group_wyckoff import SpaceGroupWyckoff, SpaceGroupWyckoffL

    from cryspy.pd1dcif_like.cl_pd_background import PdBackground, PdBackgroundL
    from cryspy.pd1dcif_like.cl_pd_instr_reflex_asymmetry import PdInstrReflexAsymmetry
    from cryspy.pd1dcif_like.cl_pd_instr_resolution import PdInstrResolution
    from cryspy.pd1dcif_like.cl_pd_peak import PdPeak, PdPeakL
    from cryspy.pd1dcif_like.cl_pd_meas import PdMeas, PdMeasL
    from cryspy.pd1dcif_like.cl_pd_proc import PdProc, PdProcL

    from cryspy import AtomLocalAxes, AtomLocalAxesL
    from cryspy import AtomRhoOrbitalRadialSlater, AtomRhoOrbitalRadialSlaterL
    from cryspy import AtomElectronConfiguration, AtomElectronConfigurationL


    from cryspy.scripts.cl_rhochi import RhoChi
    L_ITEM_CLASS.extend([PdInstrResolution, PdInstrReflexAsymmetry,
                         PdProc, PdPeak, PdMeas, PdBackground,
                         SpaceGroup, SpaceGroupSymop, SpaceGroupWyckoff,
                         Pd2dMeas, Pd2dProc,
                         Chi2, DiffrnRadiation, 
                         Extinction, Range, Setup,
                         Texture, Cell, DiffrnOrientMatrix,
                         RefineLs, DiffrnRefln, Exclude, Phase,
                         AtomLocalAxes, AtomRhoOrbitalRadialSlater, AtomElectronConfiguration
                         ])

    L_LOOP_CLASS.extend([PdProcL, PdPeakL, PdMeasL, PdBackgroundL, SpaceGroupSymopL, SpaceGroupWyckoffL, 
                         AtomSiteMomentL, AtomSiteScatL, AtomSiteSusceptibilityL,
                         AtomTypeScatL, ReflnSusceptibilityL, DiffrnReflnL, ExcludeL, 
                         PhaseL, AtomSiteL, AtomSiteAnisoL,
                         AtomTypeL,ReflnL,
                         AtomLocalAxesL, AtomRhoOrbitalRadialSlaterL, AtomElectronConfigurationL])

    L_DATA_CLASS.extend([Crystal, Pd, Pd2d, Diffrn])

    L_GLOBAL_CLASS.append(RhoChi)

except ImportError:
    FLAG_CRYSPY = False

try:
    FLAG_MAGREF = True

    from magref.classes.cl_cryst_field import CrystField
    from magref.classes.cl_coefficient_stevens import CoefficientStevens
    from magref.classes.cl_coefficient_wybourne import CoefficientWybourne
    from magref.classes.cl_inelastic_parameter import InelasticParameter
    from magref.classes.cl_ion_type import IonType
    from magref.classes.cl_inelastic_background import InelasticBackgroundL
    from magref.classes.cl_meas_elastic import MeasElasticL
    from magref.classes.cl_meas_inelastic import MeasInelasticL
    from magref.classes.cl_meas_inelastic_peak import MeasInelasticPeakL
    from magref.classes.cl_point_site import PointSiteL
    from magref.classes.cl_point_type import PointTypeL
    from magref.classes.cl_refinement import RefinementL
    from magref.scripts.cl_cryst_ref import CrystRef

    L_ITEM_CLASS.extend([CoefficientStevens, CoefficientWybourne, InelasticParameter, IonType])
    L_LOOP_CLASS.extend([InelasticBackgroundL, MeasElasticL, MeasInelasticL, MeasInelasticPeakL, 
                         PointSiteL, PointTypeL, RefinementL])
    L_DATA_CLASS.extend([CrystField])
    L_GLOBAL_CLASS.append(CrystRef)

except ImportError:
    FLAG_MAGREF = False


try:
    FLAG_MEM = True

    from lib_mem.mem.cl_density_points_number import DensityPointsNumber
    from lib_mem.mem.cl_density_point import DensityPointL
    from lib_mem.mem.cl_density import Density
    from lib_mem.mem.cl_compting_parameters import ComputingParameters

    from lib_mem.scripts.cl_mem_tensor import MemTensor

    L_ITEM_CLASS.extend([ComputingParameters, DensityPointsNumber])
    L_LOOP_CLASS.extend([DensityPointL])
    L_DATA_CLASS.extend([Density])
    L_GLOBAL_CLASS.append(MemTensor)
except ImportError:
    FLAG_MEM = False


def is_in_rcif_block(rcif_block, cryspy_obj):
    ls_cryspy = cryspy_obj.to_cif.split("\n")
    l_name = [_.strip().split()[0] for _ in ls_cryspy if _.startswith("_")]
    l_flag = [rcif_block.is_value(_name) for _name in l_name]
    return any(l_flag), all(l_flag)
    

def rcif_to_cryspy(rcif):
    l_global_obj = []
    l_defined_classes = []

    if len(rcif.items)+len(rcif.loops) > 0:
        str_rcif_items = str(rcif.items)
        l_optional_classes = []
        for _item_class in L_ITEM_CLASS:
            item_obj = _item_class.from_cif(str_rcif_items)
            if item_obj is not None:
                l_optional_classes.append(_item_class)
                l_global_obj.append(item_obj)
                if _item_class not in l_defined_classes:
                    l_defined_classes.append(_item_class)
        for _loop_obj in rcif.loops:
            for _loop_class in L_LOOP_CLASS:
                loop_obj = _loop_class.from_cif(str(_loop_obj))
                
                if loop_obj is None:
                    pass
                elif len(loop_obj) != 0:
                    l_optional_classes.append(_loop_class)
                    l_global_obj.append(loop_obj)
                    if _loop_class not in l_defined_classes:
                        l_defined_classes.append(_loop_class)

    for _data in rcif.datas:
        flag = False
        
        str_data = str(_data)
        for _data_class in L_DATA_CLASS:
            data_obj = _data_class.from_cif(str_data)
            if data_obj is not None:
                l_global_obj.append(data_obj)
                if not(_data_class in l_defined_classes):
                    l_defined_classes.append(_data_class)
                flag = True
        if not(flag):
            str_data_items = str(_data.items)
            l_data_item_obj, l_data_loop_obj = [], []
            l_optional_classes = []
            for _item_class in L_ITEM_CLASS:
                item_obj = _item_class.from_cif(str_data_items)
                if item_obj is not None:
                    l_optional_classes.append(_item_class)
                    l_data_item_obj.append(item_obj)
            for _loop_obj in _data.loops:
                for _loop_class in L_LOOP_CLASS:
                    loop_obj = _loop_class.from_cif(str(_loop_obj))

                    if loop_obj is None:
                        pass
                    elif len(loop_obj) != 0:
                        l_optional_classes.append(_loop_class)
                        l_data_loop_obj.extend(loop_obj)

            if ((len(l_data_item_obj) != 0) | (len(l_data_loop_obj) != 0)):
                _data_class = DataConstr
                data_obj = DataConstr(data_name=_data.name, optional_classes=list(set(l_optional_classes)))
                data_obj.optional_objs = l_data_item_obj + l_data_loop_obj
                l_global_obj.append(data_obj)
                l_defined_classes.append(_data_class)
            
    global_constr = GlobalConstr(global_name="", mandatory_classes=l_defined_classes)
    global_constr.mandatory_objs = l_global_obj 
    return global_constr


