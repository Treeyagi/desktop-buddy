"""Look tab: shoe colorway picker."""
from settings.tabs.common import *  # noqa: F401,F403


class LookTab:
    def _look_tab(self):
        tab = QWidget()
        outer = QVBoxLayout(tab)
        shoes = QGroupBox("Shoes")
        row = QHBoxLayout(shoes)
        self.shoe_buttons = {}
        group = QButtonGroup(self)
        group.setExclusive(True)
        for style in rig.SHOE_STYLES:
            b = QToolButton()
            b.setCheckable(True)
            b.setIcon(shoe_swatch(style))
            b.setIconSize(QSize(170, 104))
            b.setText(style)
            b.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
            b.clicked.connect(lambda _, st=style: self._queue(shoes=st))
            group.addButton(b)
            row.addWidget(b)
            self.shoe_buttons[style] = b
        row.addStretch(1)
        outer.addWidget(shoes)
        outer.addWidget(self._hint("Chunky 2000s D3-style skate shoes. Hat, hoodie and other outfit "
                                   "options can be added here later."))
        outer.addStretch(1)
        return tab

    def _sync_look(self, s):
        shoe = self.shoe_buttons.get(s.get("shoes", "hot pink"))
        if shoe:
            shoe.setChecked(True)
