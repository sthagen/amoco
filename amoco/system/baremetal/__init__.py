from amoco.system.core import DefineLoader, logger
from amoco.system import elf


@DefineLoader("elf-baremetal", elf.EM_AVR)
def loader_avr(p):
    from amoco.system.baremetal.avr import ELF

    logger.info("baremetal/avr firmware loading...")
    return ELF(p)


@DefineLoader("elf-baremetal", elf.EM_SPARC)
def loader_sparc(p):
    from amoco.system.baremetal.leon2 import ELF

    logger.info("baremetal/leon2 firmware loading...")
    return ELF(p)


@DefineLoader("elf-baremetal", elf.EM_RISCV)
def loader_riscv(p):
    from amoco.system.baremetal.riscv import ELF

    logger.info("baremetal/riscv firmware loading...")
    return ELF(p)


@DefineLoader("elf-baremetal", elf.EM_TRICORE)
def loader_tricore(p):
    from amoco.system.baremetal.tricore import SSW

    logger.info("baremetal/tricore firmware loading...")
    return SSW.loader(p)


@DefineLoader("baremetal-x86")
def loader_386(p):
    from amoco.system.baremetal.x86 import BSC

    logger.info("baremetal/x86 firmware loading...")
    return BSC(p)


@DefineLoader("baremetal-x86-legacy")
def loader_386_legacy(p):
    from amoco.system.baremetal.x86 import BSC

    logger.info("baremetal/x86 legacy firmware loading...")
    return BSC(p, legacy=True)
