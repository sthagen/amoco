# -*- coding: utf-8 -*-
from amoco.arch.x86.asm import *

# expose "microarchitecture" (instructions semantics)
uarch = dict(filter(lambda kv: kv[0].startswith("i_"), locals().items()))

from amoco.arch.core import instruction, disassembler

instruction_x86 = type("instruction_x86", (instruction,), {})
instruction_x86.set_uarch(uarch)

from amoco.arch.x86.formats import *

from amoco.arch.x86 import spec_ia32

disassemble = disassembler([spec_ia32], iclass=instruction_x86)
disassemble.maxlen = 15

# evaluating a ptr expression that has a segment expression
# will ultimately use this handler to adjust the final base address
# while taking care of segment base and also pagination (if activated)
# to transform the logical base address provided in 'bd' (base, disp)
# into a physical base address.
# Segmentation translates the logical address into a linear address.
# Pagination (if active) transform a linear address into a physical address.
# (if not active, the linear address is the physical address).
def segment_handler(cls, fmap, s, bd):
    base, disp = bd
    # handle segmentation assuming unreal or protected mode:
    if internals['seg'] and (s is not None):
        sbase = segbase(s).eval(fmap)
        base = sbase + base.zeroextend(sbase.size)
        s = None
    # now handle pagination. It is important to note that:
    # if no segment is provided, we still take care of pagination
    # which means that a GDTR register (which holds the linear address of
    # the GDT) can in fact contain the "virtual address" of the GDT!
    if fmap(PG)==bit1:
        if base._is_cst:
            paddr = mmu_get_paddr(fmap,base.v+disp)
            base = cst(paddr-disp,base.size)
    return ptr(base, s, disp)

ptr.segment_handler = segment_handler

from amoco.arch.x86 import structs

def get_gdt(state):
    gdtr = state(GDTR)
    try:
        s_gdtr = structs.struct_gdtr(gdtr.to_bytes())
        loc = ptr(cst(s_gdtr.base,32))
        sz  = s_gdtr.limit+1
        data = state(mem(loc,sz*8)).to_bytes()
        offset = 0
        res = []
        while offset<sz:
            e = structs.gdt_entry_t(data,offset)
            res.append(e)
            offset += e.size()
    except:
        res = None
    return res

def get_idt(state):
    idtr = state(IDTR)
    try:
        s_idtr = structs.struct_idtr(idtr.to_bytes())
        loc = ptr(cst(s_idtr.base,32))
        sz  = s_idtr.limit+1
        data = state(mem(loc,sz*8)).to_bytes()
        offset = 0
        res = []
        while offset<sz:
            e = structs.idt_entry_t(data,offset)
            res.append(e)
            offset += e.size()
    except:
        res = None
    return res

def concretize(data):
    res = b''
    for x in data:
        if isinstance(x,bytes):
            res += x
        else:
            res += b'\0'*x.length
    return res

mmu_cache = {}

def mmu_get_info(state,laddr):
    if not state(PG)==bit1:
        return (None,None,None)
    pd_base = state(cr3)
    if pd_base in mmu_cache:
        pd_ = mmu_cache[pd_base]
    else:
        data = state.mmap.read(pd_base,structs.PageDirectory.size())
        pd_ = structs.PageDirectory().unpack(concretize(data))
        mmu_cache[pd_base] = pd_
    pde = pd_[laddr>>22]
    if not pde.present:
        return (pd_,None,None)
    pt_base = pde.address<<12
    if pt_base in mmu_cache:
        pt_ = mmu_cache[pt_base]
    else:
        data = state.mmap.read(pt_base,structs.PageTable.size())
        pt_ = structs.PageTable().unpack(concretize(data))
        mmu_cache[pt_base] = pt_
    pte = pt_[(laddr>>12)&0x3ff]
    return (pd_,pt_,pte)

def mmu_get_paddr(state,laddr):
    pte = mmu_get_info(state,laddr)[2]
    try:
        if pte.present:
            return (pte.address<<12)+(laddr&0xfff)
        else:
            raise MemoryError
    except:
        return laddr

def mmu_get_v2p_dict(state):
    G = {}
    if state(PG)==bit1:
        for a in range(0,0x100000000,1<<22):
            pd_,pt_,_ = mmu_get_info(state,a)
            if pt_ is not None:
                for i,pte in enumerate(pt_):
                    if pte.present:
                        G[a|(i<<12)] = pte.address<<12
    return G

def mmu_show_mapping_from_dict(G):
    zones = []
    M = iter(G.items())
    vdeb,rdeb = next(M)
    n = 0
    for v,r in M:
        n += 1
        if r!=(rdeb+(n<<12)):
            zones.append(([vdeb,v-1],[rdeb,rdeb+(v-1)-vdeb]))
            vdeb = v
            rdeb = r
            n = 0
    if n>0:
        zones.append(([vdeb,v-1],[rdeb,rdeb+(v-1)-vdeb]))
    for z in zones:
        print("[%08x,%08x] -> [%08x,%08x]"%(z[0][0],z[0][1],z[1][0],z[1][1]))
    return zones

def mmu_show_mapping(state):
    mmu_show_mapping_from_dict(mmu_get_v2p_dict(state))

def PC(state=None):
    return eip if state is None else state(ptr(eip,seg=cs))


def get_data_endian():
    return 1  # LE


def configure(**kargs):
    from amoco.config import conf

    # asm format:
    f = kargs.get("format", conf.Arch.format_x86)
    if f in ("AT&T", "at&t", "ATT", "att"):
        instruction_x86.set_formatter(IA32_ATT)
    elif f in ("Intel", "INTEL", "intel"):
        instruction_x86.set_formatter(IA32_Intel)


configure()
