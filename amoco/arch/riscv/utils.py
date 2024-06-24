# -*- coding: utf-8 -*-
from amoco.cas.expressions import slc


def hi(r):
    return slc(r, 10, 22)


def lo(r):
    return slc(r, 0, 10)
