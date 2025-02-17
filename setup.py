from setuptools import setup, find_packages

long_descr = """
Amoco is a python package dedicated to the (static) analysis of binaries.

It features:

- a generic framework for decoding instructions, developed to reduce
  the time needed to implement support for new architectures.
  For example the decoder for most IA32 instructions (general purpose)
  fits in less than 800 lines of Python.
  The full SPARCv8 RISC decoder (or the ARM THUMB-1 set as well) fits
  in less than 350 lines. The ARMv8 instruction set decoder is less than
  650 lines.
- a **symbolic** algebra module which allows to describe the semantics of
  every instructions and compute a functional representation of instruction
  blocks.
- a generic execution model wich provides an abstract memory model to deal
  with concrete or symbolic values transparently, and other system-dependent
  features.
- various classes implementing usual disassembly techniques like linear sweep,
  recursive traversal, or more elaborated techniques like path-predicate
  which relies on SAT/SMT solvers to proceed with discovering the control
  flow graph or even to implement techniques like DARE (Directed Automated
  Random Exploration).
- various generic "helpers" and arch-dependent pretty printers to allow
  custom look-and-feel configurations (think AT&T vs. Intel syntax,
  absolute vs. relative offsets, decimal or hex immediates, etc).
"""

setup(
    name="amoco",
    version="2.9.11",
    description="yet another binary analysis framework",
    long_description=long_descr,
    # Metadata
    author="Axel Tillequin",
    license="GPLv2",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        'License :: OSI Approved :: GNU General Public License v2 or later (GPL-2.0-or-later)',
        "Programming Language :: Python :: 3",
        "Topic :: Scientific/Engineering :: Information Analysis",
        "Topic :: Security",
        "Topic :: Software Development :: Disassemblers",
        "Topic :: Software Development :: Interpreters",
    ],
    keywords="binary analysis symbolic execution",
    packages=find_packages(exclude=["doc", "tests*"]),
    setup_requires=[
        "pytest-runner",
    ],
    tests_require=[
        "pytest",
    ],
    install_requires=[
        "grandalf>=0.8",
        "crysp>=1.2",
        "pyparsing",
        "traitlets",
        "pygments",
        "rich",
    ],
    entry_points={
        "console_scripts": ["amoco=amoco.ui.app:cli [app]"],
    },
    extras_require={
        "app": [
            "click",
            "sqlalchemy",
            "z3-solver",
            "ccrawl>=1.9",
            "PySide6",
            "IPython",
            "textual",
            "prompt_toolkit>=3.0.28",
        ],
    },
    package_data={
        "amoco.ui.graphics.qt_": ["*.qml", "*.qss"],
        "amoco.ui.graphics.textual_": ["*.tcss"],
    },
    data_files=[],
)
