# -*- coding: utf-8 -*-

"""
.. _main:

main.py
=======
The main module of amoco.

"""

# This code is part of Amoco
# Copyright (C) 2006-2014 Axel Tillequin (bdcht3@gmail.com)
# published under GPLv2 license

# ruff: noqa: F401

from amoco.config import conf
from amoco.system.core import read_program, load_program
from amoco.emu import emul
