# -*- coding: utf-8 -*-

import sys
import os
os.environ.setdefault('PYTHONIOENCODING', 'utf-8')

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget,
    QVBoxLayout, QHBoxLayout, QTabWidget,
    QLabel, QStatusBar, QFrame
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont

from modules.ui_calc       import CalcPanel
from modules.ui_simulation import SimPanel
from modules.ui_control    import ControlPanel
from modules.ui_knowledge  import KnowledgePanel


# ─── 全局样式─────────────────────────
APP_STYLE = """
QWidget {
    background-color: #1a1a2e;
    color: #e0e0f0;
    font-family: 'Microsoft YaHei', 'SimHei', sans-serif;
    font-size: 13px;
}
QMainWindow { background-color: #12121f; }

QTabWidget::pane {
    border: 1px solid #2e2e4e;
    background: #1e1e30;
    border-radius: 4px;
}
QTabBar::tab {
    background: #252540;
    color: #9090b8;
    padding: 10px 24px;
    border: none;
    border-bottom: 3px solid transparent;
    margin-right: 2px;
    font-size: 13px;
    font-weight: bold;
}
QTabBar::tab:selected {
    background: #1e1e30;
    color: #7ec8e3;
    border-bottom: 3px solid #7ec8e3;
}
QTabBar::tab:hover:!selected {
    background: #2a2a45;
    color: #a0c0d8;
}

QGroupBox {
    border: 1px solid #2e2e55;
    border-radius: 6px;
    margin-top: 10px;
    padding-top: 6px;
    font-weight: bold;
    color: #9090c8;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 6px;
    color: #a0a0d8;
}

QPushButton {
    background-color: #2e2e55;
    color: #d0d0f0;
    border: 1px solid #40406e;
    border-radius: 5px;
    padding: 6px 14px;
    font-weight: bold;
}
QPushButton:hover {
    background-color: #3e3e70;
    color: #ffffff;
    border: 1px solid #7ec8e3;
}
QPushButton:pressed {
    background-color: #7ec8e3;
    color: #12121f;
}
QPushButton:disabled {
    background-color: #1e1e35;
    color: #555580;
}

QDoubleSpinBox, QSpinBox, QComboBox, QLineEdit {
    background-color: #252542;
    border: 1px solid #40406e;
    border-radius: 4px;
    padding: 3px 6px;
    color: #d0d0f0;
    selection-background-color: #7ec8e3;
    selection-color: #12121f;
}
QDoubleSpinBox:focus, QSpinBox:focus,
QComboBox:focus, QLineEdit:focus {
    border: 1px solid #7ec8e3;
}
QComboBox::drop-down {
    border: none;
    width: 24px;
}
QComboBox QAbstractItemView {
    background-color: #252542;
    border: 1px solid #40406e;
    selection-background-color: #3e3e70;
    color: #d0d0f0;
}

QTextEdit {
    background-color: #12121f;
    border: 1px solid #2e2e55;
    border-radius: 4px;
    color: #b0f0b0;
    font-family: Consolas, monospace;
    selection-background-color: #3e3e70;
}

QTableWidget {
    background-color: #1a1a2e;
    alternate-background-color: #20203a;
    border: 1px solid #2e2e55;
    gridline-color: #2e2e55;
    selection-background-color: #3a3a6e;
    color: #d0d0f0;
}
QTableWidget QHeaderView::section {
    background-color: #252540;
    color: #9090c8;
    border: none;
    border-right: 1px solid #2e2e55;
    padding: 4px;
    font-weight: bold;
}

QProgressBar {
    border: 1px solid #40406e;
    border-radius: 4px;
    background: #1a1a2e;
    text-align: center;
    color: #d0d0f0;
}
QProgressBar::chunk {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
        stop:0 #7ec8e3, stop:1 #a29bfe);
    border-radius: 3px;
}

QScrollBar:vertical {
    background: #1a1a2e;
    width: 10px;
    margin: 0;
}
QScrollBar::handle:vertical {
    background: #3e3e6e;
    border-radius: 5px;
    min-height: 20px;
}
QScrollBar::handle:vertical:hover {
    background: #7ec8e3;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }

QStatusBar {
    background-color: #12121f;
    color: #7090a0;
    border-top: 1px solid #2e2e4e;
    font-size: 11px;
}

QSplitter::handle {
    background: #2e2e4e;
    width: 3px;
}

QListWidget {
    background-color: #1a1a2e;
    border: 1px solid #2e2e55;
    border-radius: 4px;
    color: #c0c0e0;
}
QListWidget::item:selected {
    background-color: #3a3a6e;
    color: #7ec8e3;
}
QListWidget::item:hover {
    background-color: #25254a;
}
"""


# ─── 标题栏 Widget ────────────────────────────────
class TitleBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(64)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 0, 20, 0)

        # 左：图标 + 标题
        icon_lbl = QLabel('⚡')
        icon_lbl.setFont(QFont('Segoe UI Emoji', 22))
        icon_lbl.setStyleSheet('color:#7ec8e3;')
        layout.addWidget(icon_lbl)

        title_lbl = QLabel('高压线巡检机器人  设计与仿真分析平台')
        title_lbl.setFont(QFont('Microsoft YaHei', 15, QFont.Bold))
        title_lbl.setStyleSheet('color:#e8e8ff; letter-spacing:1px;')
        layout.addWidget(title_lbl)
        layout.addStretch()

        # 右：副标题
        sub_lbl = QLabel('基于《轮抱式高压线巡检机器人的机构设计与研究》')
        sub_lbl.setFont(QFont('Microsoft YaHei', 9))
        sub_lbl.setStyleSheet('color:#6060a0;')
        layout.addWidget(sub_lbl)

        self.setStyleSheet('background-color:#16162a; border-bottom:2px solid #2e2e55;')


# ─── 主窗口 ───────────────────────────────────────
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('高压线巡检机器人 · 设计与仿真分析平台')
        self.resize(1400, 860)
        self.setMinimumSize(1100, 700)
        self._build_ui()
        self._start_status_timer()

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # 标题栏
        root.addWidget(TitleBar())

        # 分隔线
        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet('background:#2e2e55;')
        root.addWidget(sep)

        # 主内容：Tab 导航
        self.main_tabs = QTabWidget()
        self.main_tabs.setDocumentMode(True)
        self.main_tabs.setMovable(False)

        # ── 四大功能模块 Tab ──
        tab_icons = ['📐', '🔬', '🎮', '📚']
        tab_names = [
            '  参数化设计与计算  ',
            '  运动仿真与分析  ',
            '  样机测试与控制  ',
            '  知识库与方案管理  ',
        ]
        tab_widgets = [
            CalcPanel(),
            SimPanel(),
            ControlPanel(),
            KnowledgePanel(),
        ]
        for icon, name, widget in zip(tab_icons, tab_names, tab_widgets):
            self.main_tabs.addTab(widget, icon + name)

        root.addWidget(self.main_tabs)

        # 状态栏
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self._perm_lbl = QLabel('就绪')
        self._perm_lbl.setStyleSheet('color:#7ec8e3;')
        self.status_bar.addPermanentWidget(self._perm_lbl)
        self.status_bar.showMessage(
            '欢迎使用高压线巡检机器人设计与仿真分析平台  |  '
            '论文依据：《轮抱式高压线巡检机器人的机构设计与研究》'
        )

    def _start_status_timer(self):
        """定时更新状态栏时钟"""
        from datetime import datetime
        self._timer = QTimer(self)
        self._timer.timeout.connect(
            lambda: self._perm_lbl.setText(
                datetime.now().strftime('%Y-%m-%d  %H:%M:%S')
            )
        )
        self._timer.start(1000)


# ─── 程序入口 ─────────────────────────────────────
def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    app.setStyleSheet(APP_STYLE)

    # 设置全局字体
    font = QFont('Microsoft YaHei', 10)
    app.setFont(font)

    win = MainWindow()
    win.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
