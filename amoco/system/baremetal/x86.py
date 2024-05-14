from amoco.system.structs import struct, Consts, StructFormatter, StructDefine
from amoco.arch.x86 import cpu_x86 as cpu
from amoco.system.core import DataIO, CoreExec

class BSC(CoreExec):

    def __init__(self, program, legacy=False):
        super().__init__(program,cpu)
        # use segmentation to compute addresses:
        self.cpu.internals['seg'] = True
        # set mode to 16 bit (unreal mode)
        self.cpu.internals['mode'] = 16
        # set initial ring to 0
        self.cpu.internals['ring'] = 0
        self.OS = OS()
        stepping = 1
        # assume arbitrary read returns 0:
        self.state.meminit0 = True
        # define initial state of x86:
        self.state[cpu.eax] = cpu.cst(0,32)
        self.state[cpu.edx] = cpu.cst(0o500+stepping,32)
        self.state[cpu.ecx] = cpu.cst(0,32)
        self.state[cpu.ebx] = cpu.cst(0,32)
        self.state[cpu.esp] = cpu.cst(0,32)
        self.state[cpu.ebp] = cpu.cst(0,32)
        self.state[cpu.esi] = cpu.cst(0,32)
        self.state[cpu.edi] = cpu.cst(0,32)
        self.state[cpu.eflags] = cpu.cst(2,32)
        self.state[cpu.eip] = cpu.cst(0xfff0,32)
        # initial state for segment selectors:
        self.state[cpu.cs] = cpu.cst(0xf000,16)
        self.state[cpu.segbase(cpu.cs)] = cpu.cst(0xffff0000,32)
        self.state[cpu.ds] = cpu.cst(0x0,16)
        self.state[cpu.segbase(cpu.ds)] = cpu.cst(0x0,32)
        self.state[cpu.es] = cpu.cst(0x0,16)
        self.state[cpu.segbase(cpu.es)] = cpu.cst(0x0,32)
        self.state[cpu.fs] = cpu.cst(0x0,16)
        self.state[cpu.segbase(cpu.fs)] = cpu.cst(0x0,32)
        self.state[cpu.gs] = cpu.cst(0x0,16)
        self.state[cpu.segbase(cpu.gs)] = cpu.cst(0x0,32)
        self.state[cpu.ss] = cpu.cst(0x0,16)
        self.state[cpu.segbase(cpu.ss)] = cpu.cst(0x0,32)
        # initial state for GDTR/LDTR:
        self.state[cpu.GDTR] = cpu.cst(0xffff00000000,48)
        self.state[cpu.LDTR] = cpu.cst(0x0,16)
        self.state[cpu.segbase(cpu.LDTR)] = cpu.cst(0x0,32)
        self.state[cpu.seglimit(cpu.LDTR)] = cpu.cst(0xffff,16)
        # inital state for control/debug regs:
        self.state[cpu.cr0] = cpu.cst(0x60000010,32)
        self.state[cpu.cr2] = cpu.cst(0,32)
        self.state[cpu.cr3] = cpu.cst(0,32)
        self.state[cpu.cr4] = cpu.cst(0,32)
        self.state[cpu.dr0] = cpu.cst(0,32)
        self.state[cpu.dr1] = cpu.cst(0,32)
        self.state[cpu.dr2] = cpu.cst(0,32)
        self.state[cpu.dr3] = cpu.cst(0,32)
        self.state[cpu.dr6] = cpu.cst(0xffff0ff0,32)
        self.state[cpu.dr7] = cpu.cst(0x400,32)
        # map program to the end of the address space:
        sz = program.dataio.size()
        vaddr = 0x100000000-sz
        data = program.dataio.read()
        self.state.mmap.write(vaddr,data)
        # if legacy is True, map the firmware also in the
        # BIOS legacy area as if running on an old i8086 cpu...
        if legacy:
            if len(data)>0x10000:
                # write BIOS from extended system area up to FFFF.
                self.state.mmap.write(0x000e0000,data[-0x20000:])
            else:
                # write 64KB BIOS in legacy area
                self.state.mmap.write(0x000f0000,data[-0x10000:])

    def title_info(self):
        infos = ["%s:%s"%(k,v) for (k,v) in self.cpu.internals.items()]
        if self.state(cpu.PE)==cpu.bit1:
            infos.append("PE")
        if self.state(cpu.PG)==cpu.bit1:
            infos.append("PG")
        return infos

    # helper method for how the stack is defined,
    # most notably used by emulView.frame_stack() to
    # display the stack. Here we can handle the fact
    # that the stack is always using the ss segment
    # (or we could deal with a stack growing up.)
    def helper_stack(self,sp=None,delta=0):
        cur = self.state(self.cpu.esp)
        bas = self.state(self.cpu.ebp)
        seg = self.cpu.ss
        if sp is None:
            sp = [cur,bas]
        sz = self.cpu.internals['mode']
        if not (sp[0]._is_cst and sp[0].value==0):
            sp[0] = self.cpu.mem(sp[0],sz,seg=seg)
        if delta == 0:
            delta = bas-cur
        ssbase = self.state(self.cpu.segbase(seg))
        info = "ss_base: %s"%ssbase
        return (sp[0],delta,sz//8,info)

    # helper method for emulView.frame_code
    # allows to enhance the output with arch-specific
    # informations like cs_base, cpu.internals, etc.
    def helper_code(self):
        info_cs_base = self.state(self.cpu.segbase(self.cpu.cs))
        infos = {'cs_base': "%s"%info_cs_base}
        return infos

class OS:
    symbols = {}
    abi = None
