import numpy

def check_same_hkl(np_hkl_1, np_hkl_2):
    return numpy.all(np_hkl_1 == np_hkl_2)


def check_friedel(np_hkl_1, np_hkl_2):
    return numpy.all(np_hkl_1 == (-1 * np_hkl_2)) or numpy.all(np_hkl_1 == np_hkl_2)


def check_ortho(np_hkl_1, np_hkl_2):
    flag_h = (np_hkl_1[0] == np_hkl_2[0]) or (np_hkl_1[0] == -1 * np_hkl_2[0])
    flag_k = (np_hkl_1[1] == np_hkl_2[1]) or (np_hkl_1[1] == -1 * np_hkl_2[1])
    flag_l = (np_hkl_1[2] == np_hkl_2[2]) or (np_hkl_1[2] == -1 * np_hkl_2[2])
    return flag_h and flag_k and flag_l 


def check_tetra(np_hkl_1, np_hkl_2):
    flag = check_ortho(np_hkl_1, np_hkl_2)
    if not flag:
        flag_h = (np_hkl_1[0] == np_hkl_2[1]) or (np_hkl_1[0] == -1 * np_hkl_2[1])
        flag_k = (np_hkl_1[1] == np_hkl_2[0]) or (np_hkl_1[1] == -1 * np_hkl_2[0])
        flag_l = (np_hkl_1[2] == np_hkl_2[2]) or (np_hkl_1[2] == -1 * np_hkl_2[2])
        flag = flag_h and flag_k and flag_l 
    return flag


def check_hexagonal(np_hkl_1, np_hkl_2):
    hh = -(np_hkl_2[0] + np_hkl_2[1])
    l_hkl = [
        (np_hkl_2[0], np_hkl_2[1], np_hkl_2[2]), 
        (np_hkl_2[1], hh, np_hkl_2[2]), 
        (hh, np_hkl_2[0], np_hkl_2[2]), 
        (np_hkl_2[0], np_hkl_2[1], -np_hkl_2[2]), 
        (np_hkl_2[1], hh, -np_hkl_2[2]), 
        (hh, np_hkl_2[0], -np_hkl_2[2]), 
        (-np_hkl_2[0], -np_hkl_2[1], -np_hkl_2[2]), 
        (-np_hkl_2[1], -hh, -np_hkl_2[2]), 
        (-hh, -np_hkl_2[0], -np_hkl_2[2]), 
        (-np_hkl_2[0], -np_hkl_2[1], np_hkl_2[2]), 
        (-np_hkl_2[1], -hh, np_hkl_2[2]), 
        (-hh, -np_hkl_2[0], np_hkl_2[2])]
    return (np_hkl_1[0], np_hkl_1[1], np_hkl_1[2]) in l_hkl


def check_cubic(np_hkl_1, np_hkl_2):
    l_hkl = [
        (np_hkl_2[0], np_hkl_2[1], np_hkl_2[2]), 
        (-np_hkl_2[0], -np_hkl_2[1], -np_hkl_2[2]), 
        (-np_hkl_2[0], np_hkl_2[1], np_hkl_2[2]), 
        (np_hkl_2[0], -np_hkl_2[1], np_hkl_2[2]), 
        (np_hkl_2[0], np_hkl_2[1], -np_hkl_2[2]), 
        (-np_hkl_2[0], -np_hkl_2[1], np_hkl_2[2]), 
        (np_hkl_2[0], -np_hkl_2[1], -np_hkl_2[2]), 
        (-np_hkl_2[0], np_hkl_2[1], -np_hkl_2[2]), 
        (np_hkl_2[1], np_hkl_2[0], np_hkl_2[2]), 
        (-np_hkl_2[1], -np_hkl_2[0], -np_hkl_2[2]), 
        (-np_hkl_2[1], np_hkl_2[0], np_hkl_2[2]), 
        (np_hkl_2[1], -np_hkl_2[0], np_hkl_2[2]), 
        (np_hkl_2[1], np_hkl_2[0], -np_hkl_2[2]), 
        (-np_hkl_2[1], -np_hkl_2[0], np_hkl_2[2]), 
        (np_hkl_2[1], -np_hkl_2[0], -np_hkl_2[2]), 
        (-np_hkl_2[1], np_hkl_2[0], -np_hkl_2[2]), 
        (np_hkl_2[2], np_hkl_2[1], np_hkl_2[0]), 
        (-np_hkl_2[2], -np_hkl_2[1], -np_hkl_2[0]), 
        (-np_hkl_2[2], np_hkl_2[1], np_hkl_2[0]), 
        (np_hkl_2[2], -np_hkl_2[1], np_hkl_2[0]), 
        (np_hkl_2[2], np_hkl_2[1], -np_hkl_2[0]), 
        (-np_hkl_2[2], -np_hkl_2[1], np_hkl_2[0]), 
        (np_hkl_2[2], -np_hkl_2[1], -np_hkl_2[0]), 
        (-np_hkl_2[2], np_hkl_2[1], -np_hkl_2[0]), 
        (np_hkl_2[0], np_hkl_2[2], np_hkl_2[1]), 
        (-np_hkl_2[0], -np_hkl_2[2], -np_hkl_2[1]), 
        (-np_hkl_2[0], np_hkl_2[2], np_hkl_2[1]), 
        (np_hkl_2[0], -np_hkl_2[2], np_hkl_2[1]), 
        (np_hkl_2[0], np_hkl_2[2], -np_hkl_2[1]), 
        (-np_hkl_2[0], -np_hkl_2[2], np_hkl_2[1]), 
        (np_hkl_2[0], -np_hkl_2[2], -np_hkl_2[1]), 
        (-np_hkl_2[0], np_hkl_2[2], -np_hkl_2[1])]
    return (np_hkl_1[0], np_hkl_1[1], np_hkl_1[2]) in l_hkl

