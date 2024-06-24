from textual.screen import Screen
from textual import widgets as tw


class ConfigScreen(Screen):
    def compose(self):
        yield tw.Static("configscreen")
