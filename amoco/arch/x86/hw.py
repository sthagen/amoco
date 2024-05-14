from amoco.cas.expressions import top
from amoco.arch.io import *

with DefineIO(0x20,"PIC1 Cmd") as io:
    @io.In
    def In(io,env,dl):
        logger.info("%s IN"%str(io))
        return top(dl*8)

    @io.Out
    def Out(io,env,src):
        logger.info("%s OUT (src=%s)"%(io,src))

with DefineIO(0x21,"PIC1 Data") as io:
    @io.In
    def In(io,env,dl):
        logger.info("%s IN"%str(io))
        return top(dl*8)

    @io.Out
    def Out(io,env,src):
        logger.info("%s OUT (src=%s)"%(io,src))

