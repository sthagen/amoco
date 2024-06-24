# -*- coding: utf-8 -*-

from amoco.cas.expressions import composer, cst, tst


def byte_select(x, s):
    return x.bytes(s, s + 1)


def reflect(x, n):
    L = [x[b : b + 1] for b in range(n)]
    return composer(L)


def reverse16(x):
    return reflect(x, 16)


def reverse_and_invert(x):
    L = [~(x[b : b + 1]) for b in range(32)]
    return composer(L)


def cdc_decrement():
    pass


def round16(x):
    return composer([cst(0, 16), (x + 0x8000)[16:32]])


def ssov(x, y):
    max_pos = cst((1 << (y - 1)) - 1, y)
    max_neg = cst(1, y) << (y - 1)
    return tst(x > max_pos, max_pos, tst(x < max_neg, max_neg, x))


def suov(x, y):
    max_pos = cst((1 << y) - 1, y)
    return tst(x > max_pos, max_pos, tst(x < 0, cst(0, x.size), x))
