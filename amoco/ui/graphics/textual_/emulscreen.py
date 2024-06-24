from textual.screen import Screen
from textual import widgets as tw
from rich.text import Text


class EmulScreen(Screen):
    BINDINGS = [("escape", "app.quit", "Quit session")]

    def __init__(self, source, *args, **kargs):
        self.source = source
        super().__init__(*args, **kargs)

    def compose(self):
        yield tw.Footer()
        info = Text.from_ansi(str(self.source.of.task.view.title()))
        yield tw.Collapsible(tw.Static(info), collapsed=False, title="bin")
