Installation
============

Amoco is a pure python package which depends on the following packages:

- grandalf_ used for building, walking and rendering Control Flow Graphs
- crysp_ used by the generic intruction decoder (:mod:`arch.core`)
- traitlets_ used for managing the configuration
- pyparsing_ used for parsing instruction specifications
- rich_ used for terminal ui

Recommended *optional* packages are:

- z3_ used to simplify expressions and solve constraints
- ccrawl_ used to define and import data structures

Some optional features related to UI and persistence require:

- click_ used to define amoco command-line app
- ply_ for parsing *GNU as* files
- sqlalchemy_ for persistence of amoco objects in a database
- pyside6_ for the Qt-based graphical user interface

Installation is straightforward for most packages using pip_.
For a full package, from the amoco directory, just do::

pip install .


.. _grandalf: https://github.com/bdcht/grandalf
.. _crysp: https://github.com/bdcht/crysp
.. _traitlets:  https://pypi.org/project/traitlets/
.. _pyparsing: https://pypi.org/project/pyparsing/
.. _z3: https://github.com/Z3Prover/z3
.. _rich: https://github.com/Textualize/rich
.. _ccrawl: https://github.com/bdcht/ccrawl/
.. _click: https://click.palletsprojects.com/
.. _ply: http://www.dabeaz.com/ply/
.. _sqlalchemy: http://www.sqlalchemy.org/
.. _pyside6: https://doc.qt.io/qtforpython-6/
.. _pip: https://pypi.python.org/pypi/pip
