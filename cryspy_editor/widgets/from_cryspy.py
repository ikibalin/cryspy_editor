import numpy

def calc_sthovl_by_unit_cell_parameters(index_hkl, unit_cell_parameters):
    """
    Calculate sin(theta)/lambda for given reflections h, k, l
    and unit cell parameters defined as a, b, c, cos(alpha), cos(beta), cos(gamma).
    """
    inv_d = calc_inv_d_by_unit_cell_parameters(index_hkl, unit_cell_parameters)
    sthovl = 0.5*inv_d
    return sthovl



def calc_inv_d_by_unit_cell_parameters(index_hkl, unit_cell_parameters):
    """
    Calculate 1/d for given reflections hkl
    and unit cell parameters defined as [a, b, c, alpha, beta, gamma].
    """
    a, b = unit_cell_parameters[0], unit_cell_parameters[1]
    c = unit_cell_parameters[2]
    c_a = numpy.cos(unit_cell_parameters[3])
    c_b = numpy.cos(unit_cell_parameters[4])
    c_g = numpy.cos(unit_cell_parameters[5])
    c_a_sq, c_b_sq = numpy.square(c_a), numpy.square(c_b)
    c_g_sq = numpy.square(c_g)
    s_a_sq, s_b_sq, s_g_sq = (1.-c_a_sq), (1.-c_b_sq), (1.-c_g_sq)

    A = (1.-c_a_sq-c_b_sq-c_g_sq+2.*c_a*c_b*c_g)
    h = index_hkl[0]
    k = index_hkl[1]
    l = index_hkl[2]
    B1 = s_a_sq*numpy.square(h*1./a)+\
         s_b_sq*numpy.square(k*1./b)+\
         s_g_sq*numpy.square(l*1./c)
    B2 = 2.*(k*l*(c_a-c_b*c_g))/(b*c)+\
         2.*(h*l*(c_b-c_a*c_g))/(a*c)+\
         2.*(h*k*(c_g-c_a*c_b))/(a*b)
    B = B1-B2
    inv_d = numpy.sqrt(B*1./A)
    return inv_d




def calc_index_hkl_in_range(sthovl_min, sthovl_max, unit_cell_parameters):
    a, b, c = unit_cell_parameters[0], unit_cell_parameters[1], unit_cell_parameters[2]
    h_max = int(2.*a*sthovl_max)
    k_max = int(2.*b*sthovl_max)
    l_max = int(2.*c*sthovl_max)
    
    index_h = numpy.arange(-h_max, h_max+1, 1, dtype=int)
    index_k = numpy.arange(-k_max, k_max+1, 1, dtype=int)
    index_l = numpy.arange(-l_max, l_max+1, 1, dtype=int)

    index_h, index_k, index_l = numpy.meshgrid(index_h, index_k, index_l, indexing="ij")
    index_h, index_k, index_l = index_h.flatten(), index_k.flatten(), index_l.flatten()
    index_hkl_full = numpy.stack([index_h, index_k, index_l], axis=0)
    
    index_hkl_unique = numpy.unique(index_hkl_full, axis=1)

    index_hkl = index_hkl_unique
    sthovl = calc_sthovl_by_unit_cell_parameters(index_hkl, unit_cell_parameters)

    arg_sort_sthovl = numpy.argsort(sthovl)
    index_hkl_sort = index_hkl[:, arg_sort_sthovl]
    sthovl_sort = sthovl[arg_sort_sthovl]
    
    flag = numpy.logical_and(sthovl_sort>= sthovl_min, sthovl_sort <= sthovl_max)
    index_hkl_out = index_hkl_sort[:, flag]
    return index_hkl_out



def calc_unit_cell_parameters_and_u_by_ub(m_ub):
    v_b_1 = numpy.stack([m_ub[0], m_ub[3], m_ub[6]], axis=0)
    v_b_2 = numpy.stack([m_ub[1], m_ub[4], m_ub[7]], axis=0)
    v_b_3 = numpy.stack([m_ub[2], m_ub[5], m_ub[8]], axis=0)

    b_1 = float(numpy.sqrt(((v_b_1*v_b_1).sum(axis=0))))
    b_2 = float(numpy.sqrt(((v_b_2*v_b_2).sum(axis=0))))
    b_3 = float(numpy.sqrt(((v_b_3*v_b_3).sum(axis=0))))
    c_i_g = (v_b_1*v_b_2).sum(axis=0)/(b_1*b_2)
    c_i_b = (v_b_1*v_b_3).sum(axis=0)/(b_1*b_3)
    c_i_a = (v_b_2*v_b_3).sum(axis=0)/(b_2*b_3)
    i_a, i_b = numpy.arccos(c_i_a), numpy.arccos(c_i_b)
    i_g = numpy.arccos(c_i_g)
    s_i_a, s_i_b, s_i_g = numpy.sin(i_a), numpy.sin(i_b), numpy.sin(i_g)
    i_vol = b_1*b_2*b_3*numpy.sqrt(1-c_i_a**2-c_i_b**2-c_i_g**2+2.*c_i_a*c_i_b*c_i_g)
    c_a = (c_i_b*c_i_g-c_i_a)/(s_i_b*s_i_g)
    c_b = (c_i_a*c_i_g-c_i_b)/(s_i_a*s_i_g)
    c_g = (c_i_a*c_i_b-c_i_g)/(s_i_a*s_i_b)
    a_1 = b_2*b_3*s_i_a/i_vol
    a_2 = b_1*b_3*s_i_b/i_vol
    a_3 = b_1*b_2*s_i_g/i_vol
    alpha, beta = numpy.arccos(c_a), numpy.arccos(c_b)
    gamma = numpy.arccos(c_g)

    unit_cell_parameters = numpy.stack([a_1, a_2, a_3, alpha, beta, gamma], axis=0)
    m_inv_b = calc_m_inv_b_by_unit_cell_parameters(unit_cell_parameters)
    m_u = calc_m1_m2(m_ub, m_inv_b)
    return unit_cell_parameters, m_u 

def calc_m_inv_b_by_unit_cell_parameters(unit_cell_parameters):
    a, b = unit_cell_parameters[0], unit_cell_parameters[1]
    c = unit_cell_parameters[2]
    alpha, beta = unit_cell_parameters[3], unit_cell_parameters[4]
    gamma = unit_cell_parameters[5]
    c_a, c_b, c_g = numpy.cos(alpha), numpy.cos(beta), numpy.cos(gamma)
    s_a, s_b, s_g = numpy.sin(alpha), numpy.sin(beta), numpy.sin(gamma)

    phi = calc_phi_by_unit_cell_parameters(unit_cell_parameters) 

    zeros = numpy.zeros_like(unit_cell_parameters[0])

    m_inv_b_ij = numpy.stack([
        (a*phi)/s_a, a*(c_g-c_a*c_b)/s_a, a*c_b,
              zeros,               b*s_a, b*c_a,
              zeros,               zeros, c], axis=0)
    return m_inv_b_ij

def calc_phi_by_unit_cell_parameters(
        unit_cell_parameters):
    """
    Calculate phi
    phi = (1 - cos^2 alpha - cos^2 beta - cos^2 gamma - 2 cos alpha cos beta cos gamma)^0.5
    """
    phi_sq = calc_phi_sq_by_unit_cell_parameters(unit_cell_parameters)
    phi = numpy.sqrt(phi_sq)
    return phi

def calc_phi_sq_by_unit_cell_parameters(
        unit_cell_parameters):
    """
    Calculate phi_sq
    phi_sq = 1 - cos^2 alpha - cos^2 beta - cos^2 gamma - 2 cos alpha cos beta cos gamma
    """
    alpha, beta = unit_cell_parameters[3], unit_cell_parameters[4]
    gamma = unit_cell_parameters[5]
    c_a, c_b, c_g = numpy.cos(alpha), numpy.cos(beta), numpy.cos(gamma)
    phi_sq =  (
        1. - numpy.square(c_a) - numpy.square(c_b) - numpy.square(c_g) +
        2.*c_a*c_b*c_g)
    return phi_sq

def calc_m1_m2(m1_ij, m2_ij):
    """
    m1, m2 are matrix m_11, m_12, m_13, m_21, m_22, m_23, m_31, m_32, m_33

    Output is matrix o = M1 * M2
    """
    m1_11, m1_12, m1_13 = m1_ij[0], m1_ij[1], m1_ij[2]
    m1_21, m1_22, m1_23 = m1_ij[3], m1_ij[4], m1_ij[5]
    m1_31, m1_32, m1_33 = m1_ij[6], m1_ij[7], m1_ij[8]

    m2_11, m2_12, m2_13 = m2_ij[0], m2_ij[1], m2_ij[2]
    m2_21, m2_22, m2_23 = m2_ij[3], m2_ij[4], m2_ij[5]
    m2_31, m2_32, m2_33 = m2_ij[6], m2_ij[7], m2_ij[8]

    o_11 = m1_11*m2_11 + m1_12*m2_21 + m1_13*m2_31
    o_12 = m1_11*m2_12 + m1_12*m2_22 + m1_13*m2_32
    o_13 = m1_11*m2_13 + m1_12*m2_23 + m1_13*m2_33
    o_21 = m1_21*m2_11 + m1_22*m2_21 + m1_23*m2_31
    o_22 = m1_21*m2_12 + m1_22*m2_22 + m1_23*m2_32
    o_23 = m1_21*m2_13 + m1_22*m2_23 + m1_23*m2_33
    o_31 = m1_31*m2_11 + m1_32*m2_21 + m1_33*m2_31
    o_32 = m1_31*m2_12 + m1_32*m2_22 + m1_33*m2_32
    o_33 = m1_31*m2_13 + m1_32*m2_23 + m1_33*m2_33
    o_ij = numpy.stack([o_11, o_12, o_13, o_21, o_22, o_23, o_31, o_32, o_33], axis=0)
    return o_ij
