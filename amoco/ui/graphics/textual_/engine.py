# -*- coding: utf-8 -*-

# This code is part of Amoco
# Copyright (C) 2024 Axel Tillequin
# published under GPLv2 license

from amoco.logger import Log

logger = Log(__name__)
logger.debug("loading module")

from textual.app import App

from .dbscreen import DBScreen
from .configscreen import ConfigScreen
from .helpscreen import HelpScreen


class Amoco(App):
    CSS_PATH = "amoco.tcss"
    MODES = {
        "session": DBScreen(),
        "config": ConfigScreen(),
        "help": HelpScreen(),
    }
    BINDINGS = [
        ("s", "switch_mode('session')", "Session"),
        ("c", "switch_mode('config')", "Config"),
        ("h", "switch_mode('help')", "Help"),
    ]

    def on_mount(self):
        self.switch_mode("session")

    def show(self):
        self.run()


app = Amoco()


def get_formatter(name=None):
    return app


def builder(view):
    """
    Implements the main API that allows view instances to
    build their graphic object for display.
    """
    t = view.__class__.__name__
    try:
        return DefineBuilder.All[t](view)
    except KeyError:
        logger.error("no builder defined for %s" % t)
        return None


class DefineBuilder(object):
    """
    A generic decorator that associates the view class name
    with its builder function.
    """

    All = {}

    def __init__(self, name):
        self.name = name

    def __call__(self, f):
        self.All[self.name] = f


# -----------------------------------------------------------------------------
from .emulscreen import EmulScreen


@DefineBuilder("emulView")
def emulView_builder(view):
    name = "emul"
    app.install_screen(EmulScreen(view, name=name, id="emulView"), name=name)
    app.MODES["session"] = "emul"
    return app
