# -*- coding: utf-8 -*-

# This code is part of Amoco
# Copyright (C) 2006-2011 Axel Tillequin (bdcht3@gmail.com)
# published under GPLv2 license

"""
logger.py
=========

This module defines amoco logging facilities.
The ``Log`` class inherits from a standard :py:class:`logging.Logger`,
with minor additional features like a ``'VERBOSE'`` level introduced between
``'INFO'`` and ``'DEBUG'``
levels, and a progress method that can be useful for time consuming activities.
See below for details.

Most amoco modules start by creating their local ``logger`` object used to
provide various feedback.
Users can thus focus on messages from selected amoco modules by adjusting their
level independently, or use the ``set_quiet()``, ``set_debug()`` or
``set_log_all(level)`` functions to adjust all loggers at once.

Examples:

    Setting the mapper module to ``'VERBOSE'`` level:

.. code-block:: python

        In [1]: import amoco
        In [2]: amoco.cas.mapper.logger.setlevel('VERBOSE')

    Setting all modules loggers to ``'ERROR'`` level:

.. code-block:: python

        In [2]: amoco.logger.set_quiet()

Note:
All loggers can be configured to log both to *stderr* with selected level
and to a unique temporary file with ``'DEBUG'`` level. See configuration.
"""

import logging

VERBOSE = 15
logging.addLevelName(VERBOSE, "VERBOSE")
# logging.captureWarnings(True)


from amoco.config import conf

default_format = logging.Formatter(
    "[%(asctime)s] %(levelname)-8s %(name)s: %(message)s", datefmt="%X"
)
default_handler = logging.StreamHandler()

from rich.console import Console
from rich.logging import RichHandler

default_format = logging.Formatter("%(name)s: %(message)s")
default_handler = RichHandler(
    show_path=False,
    console=Console(stderr=True),
    log_time_format="[%X]",
    rich_tracebacks=True,
)

# setting logfile global. Static definition here, see below for traits observer.

logfile = None


def set_file_logging(filename, level):
    global logfile
    if not filename and conf.Log.tempfile:
        import tempfile

        filename = tempfile.mkstemp(".log", prefix="amoco-")[1]
    if filename:
        logfile = logging.FileHandler(filename, mode="w")
        logfile.setFormatter(default_format)
        logfile.setLevel(level)
    else:
        logfile = None


# By default, we log at INFO level in console, and VERBOSE in file:
set_file_logging(conf.Log.filename, VERBOSE)


class Log(logging.Logger):
    """
    This class is intended to allow amoco activities to be logged
    simultaneously to the *stderr* output with an adjusted level and to
    a temporary file with full verbosity.

    All instanciated Log objects are tracked by the Log class attribute
    ``Log.loggers`` which maps their names with associated instances.

    The recommended way to create a Log object is to add, near the begining
    of amoco modules:

    .. code-block:: python

        from amoco.logger import Log
        logger = Log(__name__)

    """

    loggers = {}

    def __init__(self, name, handler=default_handler):
        super().__init__(name)
        handler.setFormatter(default_format)
        self.addHandler(handler)
        self.setLevel(conf.Log.level)
        if logfile:
            self.addHandler(logfile)
        self.register(name, self)

    def verbose(self, msg, *args, **kargs):
        return self.log(VERBOSE, msg, *args, **kargs)

    def setLevel(self, lvl):
        return super().setLevel(lvl)

    @classmethod
    def register(cls, name, self):
        if name in self.loggers:
            raise KeyError
        else:
            cls.loggers[name] = self


def set_quiet():
    """set all loggers to ``'ERROR'`` level"""
    set_log_all(logging.ERROR)


def set_debug():
    """set all loggers to ``'DEBUG'`` level"""
    set_log_all(logging.DEBUG)


def set_log_all(level):
    """set all loggers to specified level

    Args:
        level (int): level value as an integer.
    """
    for l in Log.loggers.values():
        l.setLevel(level)


def set_log_module(name, level):
    if name in Log.loggers:
        Log.loggers[name].setLevel(level)


def log_level_observed(change):
    level = change["new"]
    set_log_all(level)


conf.Log.observe(log_level_observed, names=["level"])


def reset_log_file(filename, level=logging.DEBUG):
    """set DEBUG log file for all loggers.

    Args:
        filename (str): filename for the FileHandler added
                         to all amoco loggers
    """
    global logfile
    if logfile is not None:
        logfile.close()
        unset_log_file()
    set_file_logging(filename, level)
    for l in Log.loggers.values():
        l.addHandler(logfile)


def unset_log_file():
    global logfile
    if logfile:
        for l in Log.loggers.values():
            l.removeHandler(logfile)
        logfile = None


def log_tempfile_observed(change):
    if not conf.Log.filename:
        if change["new"] is True:
            if not logfile:
                reset_log_file("", VERBOSE)
        else:
            unset_log_file()


conf.Log.observe(log_tempfile_observed, names=["tempfile"])


def log_filename_observed(change):
    reset_log_file(change["new"])


conf.Log.observe(log_filename_observed, names=["filename"])
