from textual.screen import Screen
from textual import widgets as tw


class DBScreen(Screen):
    def compose(self):
        yield tw.Static("dbscreen...")
