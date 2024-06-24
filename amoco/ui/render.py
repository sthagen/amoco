# -*- coding: utf-8 -*-

# This code is part of Amoco
# Copyright (C) 2006-2011 Axel Tillequin (bdcht3@gmail.com)
# published under GPLv2 license

"""
render.py
=========

This module implements amoco's rich interface to allow pretty printed
outputs of rich renderables built from vltable instances.
The rendered texts are used as main inputs for graphic engines to build
their own views' objects.

A token is a tuple (t,s) where t is a style and s is a python string.
The engine's pp function is reponsible for applying the style to the string.
"""

from amoco.config import conf

from amoco.logger import Log

logger = Log(__name__)
logger.debug("loading module")

from pygments.token import Token


def TokenListJoin(j, lst):
    """
    insert token j (Literal if j is str) between elements of lst.
    If lst[0] is a list, it is updated with following elements, else
    a new list is returned.

    Arguments:
        j (token or str): the token tuple (Token.type, str) or
                          the str used as (Token.Literal, str) "join".
        lst (list)      : the list of token tuples to "join" with j.

    Returns:
        lst[0] updated with joined lst[1:] iff lst[0] is a list,
        or a new list joined from elements of lst otherwise.
    """
    # define join token:
    if isinstance(j, str):
        j = (Token.Literal, j)
    # init output list:
    res = lst[0] if len(lst) > 0 else []
    if not isinstance(res, list):
        res = [res]
    for x in lst[1:]:
        res.append(j)
        if isinstance(x, list):
            res.extend(x)
        else:
            res.append(x)
    return res


def LambdaTokenListJoin(j, f):
    """
    returns a lambda that takes instruction i and returns the TokenListJoin
    build from join argument j and lst argument f(i).
    """
    return lambda i: TokenListJoin(j, f(i))


class vltable:
    """
    A variable length table relies on pygments to pretty print tabulated data.

    Arguments:
        rows (list): optional argument with initial list of tokenrows.
        formatter (Formatter): optional pygment's formatter to use
                               (defaults to conf.UI.formatter.)
        outfile (file): optional output file passed to the formatter
                               (defaults to StringIO.)

    Attributes:
        rows (list of tokenrow): lines of the table, with tabulated data.
        rowparams (dict): parameters associated with a line.
        maxlength: maximum number of lines (default to infinity).
        hidden_r (set): rows that should be hidden.
        squash_r (bool): row is removed if True or empty if False.
        hidden_c (set): columns that should be hidden.
        squash_c (bool): column is removed if True or empty if False.
        colsize  (dict): mapping column index to its required width.
        width (int): total width of the table.
        height (int): total heigth of the table.
        nrows (int): total number of rows (lines).
        ncols (int): total number of columns.
        header (str): table header line (empty by default).
        footer (str): table footer line (empty by default).
    """

    def __init__(self, rows=None, formatter=None, outfile=None):
        if rows is None:
            rows = []
        self.rows = rows
        self.rowparams = {
            "colsize": {},
            "hidden_c": set(),
            "squash_c": True,
            "formatter": formatter,
            "outfile": outfile,
        }
        self.maxlength = float("inf")
        self.hidden_r = set()
        self.hidden_c = self.rowparams["hidden_c"]
        self.squash_r = True
        self.colsize = self.rowparams["colsize"]
        self.update()
        self.header = ""
        self.footer = ""

    def update(self, *rr):
        "recompute the column width over rr range of rows, and update colsize array"
        for c in range(self.ncols):
            cz = self.colsize.get(c, 0) if len(rr) > 0 else 0
            self.colsize[c] = max(cz, self.getcolsize(c, rr, squash=False))

    def getcolsize(self, c, rr=None, squash=True):
        "compute the given column width (over rr list of row indices if not None.)"
        cz = 0
        if not rr:
            rr = range(self.nrows)
        for i in rr:
            if self.rowparams["squash_c"] and (i in self.hidden_r):
                if squash:
                    continue
            cz = max(cz, self.rows[i].colsize(c))
        return cz

    @property
    def width(self):
        sep = self.rowparams.get("sep", "")
        cs = self.ncols * len(sep)
        return sum(self.colsize.values(), cs)

    def setcolsize(self, c, value):
        "set column size to value"
        i = range(self.ncols)[c]
        self.colsize[i] = value

    def addcolsize(self, c, value):
        "set column size to value"
        i = range(self.ncols)[c]
        self.colsize[i] += value

    def addrow(self, toks):
        "add row of given list of tokens and update table"
        self.rows.append(tokenrow(toks))
        self.update()
        return self

    def addcolumn(self, lot, c=None):
        "add column with provided toks (before index c if given) and update table"
        if c is None:
            c = self.ncols
        for ir, toks in enumerate(lot):
            if ir < self.nrows:
                r = self.rows[ir]
                for _ in range(r.ncols, c):
                    r.cols.append([(Token.Column, "")])
                toks.insert(0, (Token.Column, ""))
                r.cols.insert(c, toks)
            else:
                logger.warning("addcolumn: to much rows in provided list of tokens")
                break
        self.update()
        return self

    def hiderow(self, n):
        "hide given row"
        self.hidden_r.add(n)

    def showrow(self, n):
        "show given row"
        self.hidden_r.remove(n)

    def hidecolumn(self, n):
        "hide given column"
        self.hidden_c.add(n)

    def showcolumn(self, n):
        "show given column"
        self.hidden_c.remove(n)

    def showall(self):
        "remove all hidden rows/cols"
        self.hidden_r = set()
        self.rowparams["hidden_c"] = set()
        self.hidden_c = self.rowparams["hidden_c"]
        return self

    def grep(self, regex, col=None, invert=False):
        "search for a regular expression in the table"
        from re import search

        L = set()
        R = range(self.nrows)
        for i in R:
            if i in self.hidden_r:
                continue
            C = self.rows[i].rawcols(col)
            for c, s in enumerate(C):
                if c in self.hidden_c:
                    continue
                if search(regex, s):
                    L.add(i)
                    break
        if not invert:
            L = set(R) - L
        for n in L:
            self.hiderow(n)
        return self

    @property
    def nrows(self):
        return len(self.rows)

    @property
    def ncols(self):
        if self.nrows > 0:
            return max((r.ncols for r in self.rows))
        else:
            return 0


class tokenrow(object):
    """
    A vltable row (line) of tabulated data tokens.

    Attributes:
        toks (list): list of tokens tuple (Token.Type, str).
        maxwidth: maximum authorized width of this row.
        align (str): left/center/right aligment indicator (default to "<" left).
        fill (str): fill character used for padding to required size.
        separator (str): character used for separation of columns.
        cols (list): list of columns of tokens.
        ncols (int): number of columns in this row.
    """

    def __init__(self, toks=None):
        if toks is None:
            toks = []
        self.label = None
        self.maxwidth = float("inf")
        self.align = "<"
        self.fill = " "
        self.separator = ""
        toks = [(t, "%s" % s) for (t, s) in toks]
        self.cols = self.cut(toks)

    def cut(self, toks):
        "cut the raw list of tokens into a list of column of tokens"
        C = []
        c = []
        for t in toks:
            c.append(t)
            if t[0] == Token.Column:
                C.append(c)
                c = []
        C.append(c)
        return C

    def addcolumn(self, index=None, col=None):
        c = col or []
        c.append((Token.Column, ""))
        self.cols.insert(index, c)

    def colsize(self, c):
        "return the column size (width)"
        if c >= len(self.cols):
            return 0
        return sum((len(t[1]) for t in self.cols[c] if t[0] != Token.Column))

    @property
    def ncols(self):
        return len(self.cols)

    def rawcols(self, j=None):
        "return the raw (undecorated) string of this row (j-th column if given)"
        r = []
        cols = self.cols
        if j is not None:
            cols = self.cols[j : j + 1]
        for c in cols:
            r.append("".join([t[1] for t in c]))
        return r

    def has_tokentype(self, tt):
        alltt = set()
        for c in self.cols:
            alltt.update(set(x[0] for x in c))
        if isinstance(tt, Token):
            return tt in alltt
        else:
            return any(((tt in list(x)) for x in alltt))


class Icons:
    sep = " | "
    dots = "..."
    tri = " > "
    lar = " <- "
    dbl = "="
    hor = "-"
    ver = "|"
    top = "T"
    bot = "_"
    usep = " \u2502 "
    udots = "\u2504 "
    utri = " \u25b6 "
    ular = " \u21fd "
    udbl = "\u2550"
    uhor = "\u2500"
    uver = "\u2502"
    utop = "\u22a4"
    ubot = "\u22a5"
    mop = {}

    def __getattribute__(self, a):
        if a not in ("mop", "op") and conf.UI.unicode:
            return super().__getattribute__("u" + a)
        else:
            return super().__getattribute__(a)

    def op(self, symbol):
        if conf.Cas.unicode:
            return self.mop.get(symbol, symbol)
        else:
            return symbol


icons = Icons()
# define operator unicode symbols:
icons.mop["S"] = "\u2211"  # Sigma
icons.mop["-"] = "\u2212"
icons.mop["**"] = "\u2217"
icons.mop["&"] = "\u2227"
icons.mop["|"] = "\u2228"
icons.mop["^"] = "\u2295"
icons.mop["~"] = "\u2310"
icons.mop["=="] = "\u225f"
icons.mop["!="] = "\u2260"
icons.mop["<="] = "\u2264"
icons.mop[">="] = "\u2265"
icons.mop[">=."] = "\u22dd"
icons.mop["<."] = "\u22d6"
icons.mop["<<"] = "\u226a"
icons.mop[">>"] = "\u226b"
icons.mop[".>>"] = "\u00b1\u226b"
icons.mop["<<<"] = "\u22d8"
icons.mop[">>>"] = "\u22d9"


def replace_mnemonic_token(l, value):
    for i in range(len(l)):
        tn, tv = l[i]
        if tn == Token.Mnemonic:
            tv = value.ljust(len(tv))
        l[i] = (tn, tv)


def replace_opn_token(l, n, value):
    index = 1 + (2 * n)
    if value is None:
        if index + 1 < len(l):
            l.pop(index + 1)
            l.pop(index)
    else:
        tn, tv = l[index]
        if isinstance(value, tuple):
            l[index] = value
        else:
            l[index] = (tn, value)
