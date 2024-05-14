from amoco.system.structs import *

# from linux/arch/x86/include/asm/desc_defs.h:

@StructDefine("""
H : limit
I : base
""",packed=True)
class struct_gdtr(StructFormatter):
    def __init__(self,data=None,offset=0):
        self.address_formatter("base")
        if data is not None:
            self.unpack(data,offset)

@StructDefine("""
H : limit0
H : base0
H * #8/4/1/2/1 : base1/type/s/dpl/p
H * #4/1/1/1/1/8 : limit1/avl/l/d/g/base2
""",packed=True)
class gdt_entry_t(StructFormatter):
    def __init__(self,data=None,offset=0):
        self.address_formatter("base0","base1","base2")
        self.name_formatter("s","type")
        if data is not None:
            self.unpack(data,offset)

    @property
    def alt(self):
        if self._v.s==1:
            return "segment"
        return None

    def limit(self):
        return self.limit0+(self.limit1<<16)

    def base(self):
        return self.base0+(self.base1<<16)+(self.base2<<24)

with Consts("s"):
    DESC_SYSTEM  = 0x0
    DESC_SEGMENT = 0x1
with Consts("type"):
    NULL_ENTRY     = 0x0
    DESC_TSS16_OK  = 0x1
    DESC_LDT       = 0x2
    DESC_TSS16_KO  = 0x3
    GATE_CALL16    = 0x4
    GATE_TASK      = 0x5
    DESC_TSS32_OK  = 0x9
    DESC_TSS32_KO  = 0xb
    GATE_CALL32    = 0xc
with Consts("segment.type"):
    SEG_RO     = 0x0
    SEG_RO_a   = 0x1
    SEG_RW     = 0x2
    SEG_RW_a   = 0x3
    SEG_RO_e   = 0x4
    SEG_RO_ea  = 0x5
    SEG_RW_e   = 0x6
    SEG_RW_ea  = 0x7
    SEG_XO     = 0x8
    SEG_XO_a   = 0x9
    SEG_XR     = 0xa
    SEG_XR_a   = 0xb
    SEG_XO_e   = 0xc
    SEG_XO_ea  = 0xd
    SEG_XR_e   = 0xe
    SEG_XR_ea  = 0xf

@StructDefine("""
H : offset0
H : selector
H * #8/4/1/2/1 : param/type/s/dpl/p
H : offset1
""",packed=True)
class call_gate_t(StructFormatter):
    def __init__(self,data=None,offset=0):
        self.address_formatter("offset0","offset1")
        self.name_formatter("s","type")
        if data is not None:
            self.unpack(data,offset)
    def offset(self):
        return self.offset0+(self.offset1<<16)

@StructDefine("""
H : offset0
H : selector
H * #8/4/1/2/1 : param/type/s/dpl/p
H : offset1
I : offset2
I : reserved
""",packed=True)
class call_gate_64_t(StructFormatter):
    def __init__(self,data=None,offset=0):
        self.address_formatter("offset0","offset1","offset2")
        self.name_formatter("s","type")
        if data is not None:
            self.unpack(data,offset)
    def offset(self):
        return self.offset0+(self.offset1<<16)+(self.offset2<<32)

@StructDefine("""
H : limit
I : base
""",packed=True)
class struct_idtr(StructFormatter):
    def __init__(self,data=None,offset=0):
        self.address_formatter("base")
        if data is not None:
            self.unpack(data,offset)

@StructDefine("""
H : offset0
H : selector
H * #8/4/1/2/1 : reserved/type/s/dpl/p
H : offset1
""",packed=True)
class idt_entry_t(StructFormatter):
    def __init__(self,data=None,offset=0):
        self.address_formatter("offset0","offset1")
        self.name_formatter("type")
        if data is not None:
            self.unpack(data,offset)
    def offset(self):
        return self.offset0+(self.offset1<<16)

with Consts("idt_entry_t.type"):
    GATE_TASK        = 0x5
    GATE_INTERRUPT16 = 0x6
    GATE_TRAP16      = 0x7
    GATE_INTERRUPT32 = 0xe
    GATE_TRAP32      = 0xf

@StructDefine("""
H : link
H : SP0
H : SS0
H : SP1
H : SS1
H : SP2
H : SS2
H : IP
H : FLAG
H : AX
H : CX
H : DX
H : BX
H : SP
H : BP
H : SI
H : DI
H : ES
H : CS
H : SS
H : DS
H : LDTR
""",packed=True)
class tss16_entry_t(StructFormatter):
    def __init__(self,data=None,offset=0):
        self.address_formatter("IP","SP","BP","LDTR")
        if data is not None:
            self.unpack(data,offset)

@StructDefine("""
H : link
H : reserved
I : ESP0
H : SS0
H : reserved2
I : ESP1
H : SS1
H : reserved3
I : ESP2
H : SS2
H : reserved4
I : CR3
I : EIP
I : EFLAGS
I : EAX
I : ECX
I : EDX
I : EBX
I : ESP
I : EBP
I : ESI
I : EDI
H : ES
H : reserved5
H : CS
H : reserved6
H : SS
H : reserved7
H : DS
H : reserved8
H : FS
H : reserved9
H : GS
H : reserved10
H : LDTR
H : reserved11
B : T
B : reserved12
H : IOMAP
""",packed=True)
class tss32_entry_t(StructFormatter):
    def __init__(self,data=None,offset=0):
        self.address_formatter("EIP","ESP","EBP","LDTR")
        if data is not None:
            self.unpack(data,offset)


# 32-bit pagging structures:
#===========================

@StructDefine("""
I * #3/1/1/7/20: reserved0/PWT/PCD/reserved1/address
""",packed=True)
class CR3(StructFormatter):
    def __init__(self,data=None,offset=0):
        self.address_formatter("address")
        if data is not None:
            self.unpack(data,offset)

@StructDefine("""
I * #1/1/1/1/1/1/1/1/4/20 : present/RW/US/PWT/PCD/A/Ign/z/reserved0/address
""")
class PDE(StructFormatter):
    def __init__(self,data=None,offset=0):
        self.address_formatter("address")
        if data is not None:
            self.unpack(data,offset)

PageDirectory = TypeDefine("PageDirectory","PDE*1024")

@StructDefine("""
I * #1/1/1/1/1/1/1/1/1/3/20 : present/RW/US/PWT/PCD/A/D/PAT/G/reserved0/address
""")
class PTE(StructFormatter):
    def __init__(self,data=None,offset=0):
        self.address_formatter("address")
        if data is not None:
            self.unpack(data,offset)

PageTable = TypeDefine("PageTable","PTE*1024")

