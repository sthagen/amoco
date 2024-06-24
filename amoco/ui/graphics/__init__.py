from amoco.logger import Log

logger = Log(__name__)
logger.debug("loading module")


from .rich_ import engine as rich_engine


class Engine(object):
    """
    This class acts as the base class for all views
    and is just a placeholder that allows to define
    a common engine module available to all instances.
    """

    engine = rich_engine


from amoco.config import conf


def load_engine(engine=None):
    if isinstance(engine, str):
        conf.UI.graphics = engine
        engine = None

    if engine is None:
        if conf.UI.graphics == "gtk":
            from amoco.ui.graphics.gtk_ import engine as gtk_engine

            engine = gtk_engine

        elif conf.UI.graphics == "qt":
            from amoco.ui.graphics.qt_ import engine as qt_engine

            engine = qt_engine

        elif conf.UI.graphics == "textual":
            from amoco.ui.graphics.textual_ import engine as textual_engine

            engine = textual_engine

        else:
            engine = rich_engine

    Engine.engine = engine
