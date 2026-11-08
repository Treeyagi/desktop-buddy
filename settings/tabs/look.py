"""Look tab: shoe colorway picker."""
from settings.tabs.common import *  # noqa: F401,F403


class LookTab:
    def _look_tab(self):
        tab = QWidget()
        outer = QVBoxLayout(tab)
        who = QGroupBox("Character")
        wrow = QHBoxLayout(who)
        self.char_buttons = {}
        cgroup = QButtonGroup(self)
        cgroup.setExclusive(True)
        for key, label, pm in (("cartoon", "Cartoon", self._char_pixmap(False)),
                               ("sprite", "Treeyagi (sprite)", self._char_pixmap(True))):
            b = QToolButton()
            b.setCheckable(True)
            b.setIcon(QIcon(pm))
            b.setIconSize(QSize(120, 150))
            b.setText(label)
            b.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
            b.clicked.connect(lambda _, k=key: self._queue(character=k))
            cgroup.addButton(b)
            wrow.addWidget(b)
            self.char_buttons[key] = b
        wrow.addStretch(1)
        outer.addWidget(who)
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

    @staticmethod
    def _char_pixmap(sprite):
        """A small picture of each look for the picker."""
        if sprite:
            from character.sprite import thumbnail
            return thumbnail().scaled(120, 150, Qt.AspectRatioMode.KeepAspectRatio,
                                      Qt.TransformationMode.SmoothTransformation)
        pm = QPixmap(120, 150)
        pm.fill(QColor(0, 0, 0, 0))
        p = QPainter(pm)
        rig.draw_buddy(p, 60, 145, 1, 0.62, rig.Pose())
        p.end()
        return pm

    def _sync_look(self, s):
        char = self.char_buttons.get(s.get("character", "cartoon"))
        if char:
            char.setChecked(True)
        shoe = self.shoe_buttons.get(s.get("shoes", "hot pink"))
        if shoe:
            shoe.setChecked(True)
