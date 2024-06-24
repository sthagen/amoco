# -*- coding: utf-8 -*-

# This code is part of Amoco
# Copyright (C) 2024 Axel Tillequin (bdcht3@gmail.com)
# published under GPLv2 license

from amoco.config import conf
from amoco.logger import Log

logger = Log(__name__)
logger.debug("loading module")

from amoco.ui.render import icons
from rich.console import Console, RenderableType
from rich.theme import Theme
from rich.text import Text
from rich.table import Table, Column
from rich.tree import Tree
from rich.panel import Panel
from rich.markup import escape
from rich import inspect, get_console
from rich.measure import measure_renderables

renderables = [Text, Table, Tree, Panel]


class engine(object):
    @staticmethod
    def get_formatter(name=None):
        formatter = name or Formats.get(conf.UI.formatter, "Null")
        if isinstance(formatter, str):
            formatter = Formats[formatter]
        return formatter

    @classmethod
    def builder(cls, view):
        return cls.RichTable(view._vltable())

    @staticmethod
    def setw(view, w):
        view.obj.width = w

    @staticmethod
    def getw(view):
        try:
            c = view.engine.get_formatter()
            w = measure_renderables(c, c.options, [view.obj])
            return w.maximum
        except Exception:
            return view._vltable().width

    @staticmethod
    def seth(view, h):
        view.obj.height = h

    @staticmethod
    def geth(view):
        try:
            return view.highlighted(view.obj).count("\n") + 1
        except Exception:
            return view._vltable().nrows

    @staticmethod
    def setxy(view, xy):
        pass

    @staticmethod
    def getxy(view):
        return None

    @classmethod
    def pp(cls, view):
        return cls.highlighted(view._vltable())

    @classmethod
    def highlighted(cls, T):
        if not isinstance(T, RenderableType):
            formatter = cls.get_formatter(T.rowparams["formatter"])
            outfile = T.rowparams["outfile"]
            renderable = cls.RichTable(T)
        else:
            formatter = cls.get_formatter(None)
            outfile = None
            renderable = T
        if outfile:
            formatter.file = outfile
            formatter.print(renderable, end="")
            return outfile.getvalue().rstrip("\n")
        with formatter.capture() as output:
            formatter.print(renderable, end="")
        return output.get().rstrip("\n")

    @staticmethod
    def RichTable(T):
        # build the table panel:
        # we make a rich.Table from vltable T:
        wrapflag = T.rowparams.get("wrap", True)
        COLS = [
            Column("", min_width=T.colsize[i], no_wrap=wrapflag) for i in range(T.ncols)
        ]
        if len(COLS) == 0:
            COLS.append(Column("", no_wrap=wrapflag))
        # last column will take all remaining expendable space:
        COLS[-1].ratio = 1
        rT = Table(
            *COLS,
            show_header=False,
            show_footer=False,
            title=None,
            title_style="header",
            title_justify="right",
            box=None,
            pad_edge=False,
            collapse_padding=True,
            expand=True,
        )
        for i in range(T.nrows):
            if i in T.hidden_r:
                if not T.squash_r:
                    rT.add_row(None)
            else:
                if T.rows[i].label:
                    rT.add_row(toks2rich([T.rows[i].label]), style="label")
                rowstyle = "mark" if T.rows[i].has_tokentype("Mark") else None
                rT.add_row(*rtrow(T.rows[i], **T.rowparams), style=rowstyle)
        if rT.row_count > T.maxlength:
            rT.rows = rT.rows[: T.maxlength]
            for col in rT.columns:
                col._cells = col._cells[: T.maxlength - 1]
                col._cells.append("[comment]" + icons.dots)
        P = Panel(
            rT,
            title=escape(T.header),
            style="header",
            title_align="right",
            subtitle=escape(T.footer),
            subtitle_align="right",
            highlight=False,
            expand=True,
        )
        return P

    @staticmethod
    def RichTree(T, title=""):
        fa = "[address]{!s}[address]"
        fc = "[comment]#{}[/comment]"
        # build the tree panel:
        if T is None:
            t = Tree("<empty>")
            T = []
        else:
            f = fa + fc if T.symbol else fa
            t = Tree(f.format(T.entry, T.symbol), expanded=not T.closed)

        def add2tree(t, l):
            for e in l:
                f = fa + fc if e.symbol else fa
                cur = t.add(f.format(e.entry, e.symbol), expanded=not e.closed)
                add2tree(cur, e)

        add2tree(t, T)
        P = Panel(
            t,
            title=title,
            style="header",
            title_align="right",
            highlight=False,
            expand=True,
        )
        return P

    @classmethod
    def highlight(cls, toks, formatter=None, outfile=None):
        renderable = toks2rich(toks)
        formatter = cls.get_formatter(formatter)
        if outfile:
            formatter.file = outfile
            formatter.print(renderable, end="")
            return outfile.getvalue().rstrip("\n")
        with formatter.capture() as output:
            formatter.print(renderable, end="")
        return output.get().rstrip("\n")

    @classmethod
    def inspect(cls, obj):
        inspect(obj, methods=True)


# define default dark theme to match pygments term module:
default_dark = Theme(
    {
        "literal": "white",
        "address": "#ffbb00",
        "constant": "#ff6600",
        "prefix": "#ffffff",
        "mnemonic": "bold #ffffff",
        "register": "#6666ff",
        "memory": "#66ffff",
        "string": "#66ff66",
        "segment": "#888888",
        "comment": "#ff88ff",
        "green": "#88ff88",
        "good": "bold #88ff88",
        "name": "bold",
        "alert": "bold #ff5555",
        "column": "#000000",
        "header": "#888888",
        "mark": "on #333333",
        "taint": "on #442222",
        "hide": "black",
        "label": "bold #ff88ff",
    }
)

default_light = Theme(
    {
        "literal": "black",
        "address": "#cc3300",
        "constant": "#dd0000",
        "prefix": "#000000",
        "mnemonic": "bold #000000",
        "register": "#0000ff",
        "memory": "#00cccc",
        "string": "#008800",
        "segment": "#888888",
        "comment": "#aa33aa",
        "good": "bold #008800",
        "name": "bold",
        "alert": "bold red",
        "column": "#ffffff",
        "header": "#888888",
        "mark": "on #aaaaff",
        "taint": "on #ffaaaa",
        "hide": "white",
        "label": "bold #aa33aa",
    }
)


Formats = {
    "Null": Console(theme=default_dark, color_system=None),
    "TerminalDark": Console(theme=default_dark, color_system="auto", highlight=False),
    "TerminalLight": Console(theme=default_light, color_system="auto", highlight=False),
}

if conf.UI.richtheme:
    try:
        Formats["TerminalDark"].push_theme(Theme.read(conf.UI.richtheme))
    except FileNotFoundError:
        logger.warning("theme '%s' not found" % conf.UI.richtheme)
    except Exception:
        logger.warning("error in theme '%s'" % conf.UI.richtheme)

get_console().__dict__ = engine.get_formatter().__dict__


def rtrow(row, **params):
    sep = params.get("sep", row.separator)
    cols = iter(row.cols)
    r = [toks2rich(next(cols))]
    for c in cols:
        r.append(toks2rich(c, sep))
    return r


def toks2rich(c, sep=""):
    r = "%s" % sep
    for tt, tv in c:
        stt = str(tt)
        if stt == "Token.Column":
            break
        x = "%s" % escape(tv)
        for style in reversed(stt.lower().split(".")[1:]):
            x = "[%s]%s[/]" % (style, x)
        r += x
    return r
