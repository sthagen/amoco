from textual.screen import Screen
from textual import widgets as tw


class HelpScreen(Screen):
    def compose(self):
        self.border = tw.Static("Help")
        self.border.styles.border = ("round", "grey")
        self.border.styles.center = True
        yield self.border
        yield tw.Footer()
        yield tw.Static("hello")
