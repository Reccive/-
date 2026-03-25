# -*- coding: utf-8 -*-
"""
模块四：知识库与项目管理 UI
设计指标 / 研究综述 / 方案管理 / 实验记录
"""

from datetime import datetime
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QGroupBox, QLabel, QPushButton, QTabWidget,
    QTableWidget, QTableWidgetItem, QTextEdit,
    QLineEdit, QListWidget, QListWidgetItem,
    QMessageBox, QHeaderView, QSplitter
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QColor

from modules import knowledge_base as kb


class KnowledgePanel(QWidget):
    """知识库与项目管理面板"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()
        self._load_data()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)

        self.tabs = QTabWidget()
        root.addWidget(self.tabs)

        self.tabs.addTab(self._build_specs_tab(),    '设计指标')
        self.tabs.addTab(self._build_review_tab(),   '研究综述')
        self.tabs.addTab(self._build_schemes_tab(),  '方案管理')
        self.tabs.addTab(self._build_explog_tab(),   '实验记录')

    # ── Tab 1：设计指标（论文表2-1）────────────────
    def _build_specs_tab(self):
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(8, 8, 8, 8)

        lbl = QLabel('论文表2-1  高压线巡检机器人主要设计指标')
        lbl.setFont(QFont('Microsoft YaHei', 11, QFont.Bold))
        lbl.setStyleSheet('color:#7ec8e3; padding:6px 0;')
        v.addWidget(lbl)

        tbl = QTableWidget(len(kb.DESIGN_SPECS), 4)
        tbl.setHorizontalHeaderLabels(['指标项目', '设计值', '单位', '备注'])
        tbl.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        tbl.verticalHeader().setVisible(False)
        tbl.setEditTriggers(QTableWidget.NoEditTriggers)
        tbl.setAlternatingRowColors(True)
        tbl.setSelectionBehavior(QTableWidget.SelectRows)

        for row, spec in enumerate(kb.DESIGN_SPECS):
            for col, key in enumerate(['指标项目', '设计值', '单位', '备注']):
                item = QTableWidgetItem(str(spec[key]))
                item.setTextAlignment(Qt.AlignCenter)
                tbl.setItem(row, col, item)

        v.addWidget(tbl)
        return w

    # ── Tab 2：研究综述 ─────────────────────────────
    def _build_review_tab(self):
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(8, 8, 8, 8)

        lbl = QLabel('国内外高压线巡检机器人研究现状综述')
        lbl.setFont(QFont('Microsoft YaHei', 11, QFont.Bold))
        lbl.setStyleSheet('color:#a29bfe; padding:6px 0;')
        v.addWidget(lbl)

        splitter = QSplitter(Qt.Horizontal)

        # 左：类别列表
        self.review_list = QListWidget()
        for cat in kb.RESEARCH_REVIEW:
            self.review_list.addItem(cat['category'])
        self.review_list.currentRowChanged.connect(self._show_review_detail)
        splitter.addWidget(self.review_list)

        # 右：详情表
        right = QWidget()
        rv = QVBoxLayout(right)
        rv.setContentsMargins(4, 0, 0, 0)
        self.review_table = QTableWidget(0, 3)
        self.review_table.setHorizontalHeaderLabels(['名称', '主要特点', '局限性'])
        self.review_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.review_table.verticalHeader().setVisible(False)
        self.review_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.review_table.setWordWrap(True)
        rv.addWidget(self.review_table)
        splitter.addWidget(right)
        splitter.setSizes([180, 600])

        v.addWidget(splitter)
        return w

    def _show_review_detail(self, idx):
        if idx < 0:
            return
        items = kb.RESEARCH_REVIEW[idx]['items']
        self.review_table.setRowCount(len(items))
        for row, item in enumerate(items):
            self.review_table.setItem(row, 0, QTableWidgetItem(item['name']))
            self.review_table.setItem(row, 1, QTableWidgetItem(item['features']))
            self.review_table.setItem(row, 2, QTableWidgetItem(item['drawback']))
        self.review_table.resizeRowsToContents()

    # ── Tab 3：方案管理 ─────────────────────────────
    def _build_schemes_tab(self):
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(8, 8, 8, 8)

        toolbar = QHBoxLayout()
        lbl = QLabel('设计方案版本管理')
        lbl.setFont(QFont('Microsoft YaHei', 11, QFont.Bold))
        lbl.setStyleSheet('color:#55efc4; padding:6px 0;')
        toolbar.addWidget(lbl)
        toolbar.addStretch()
        btn_new = QPushButton('+ 新建方案')
        btn_new.clicked.connect(self._new_scheme)
        btn_refresh = QPushButton('刷新')
        btn_refresh.clicked.connect(self._load_schemes)
        toolbar.addWidget(btn_new)
        toolbar.addWidget(btn_refresh)
        v.addLayout(toolbar)

        self.scheme_list = QListWidget()
        self.scheme_list.currentRowChanged.connect(self._show_scheme_detail)
        v.addWidget(self.scheme_list)

        grp_detail = QGroupBox('方案详情')
        dv = QVBoxLayout(grp_detail)
        self.scheme_detail = QTextEdit()
        self.scheme_detail.setReadOnly(True)
        self.scheme_detail.setFont(QFont('Consolas', 9))
        self.scheme_detail.setMaximumHeight(160)
        dv.addWidget(self.scheme_detail)
        v.addWidget(grp_detail)
        return w

    def _new_scheme(self):
        name, ok = self._input_dialog('新建方案', '方案名称:')
        if not ok or not name:
            return
        notes, ok2 = self._input_dialog('备注', '方案备注 (可选):')
        params = {
            'R': 25.0, 'beta': 30.0, 'weight': 15.0,
            'created_by': 'user'
        }
        path = kb.save_design_scheme(name, params, notes if ok2 else '')
        self._load_schemes()
        QMessageBox.information(self, '成功', f'方案已保存:\n{path}')

    def _input_dialog(self, title, label):
        from PyQt5.QtWidgets import QInputDialog
        return QInputDialog.getText(self, title, label)

    def _load_schemes(self):
        self.scheme_list.clear()
        self._schemes = kb.load_all_schemes()
        for s in self._schemes:
            ts = s.get('created_at', '')[:19].replace('T', ' ')
            self.scheme_list.addItem(f"{s['name']}  [{ts}]")

    def _show_scheme_detail(self, idx):
        if idx < 0 or idx >= len(self._schemes):
            return
        s = self._schemes[idx]
        txt = (
            f"名称: {s['name']}\n"
            f"创建时间: {s.get('created_at','')[:19]}\n"
            f"备注: {s.get('notes','')}\n"
            f"参数:\n"
        )
        for k, v in s.get('params', {}).items():
            txt += f"  {k} = {v}\n"
        self.scheme_detail.setPlainText(txt)

    # ── Tab 4：实验记录 ─────────────────────────────
    def _build_explog_tab(self):
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(8, 8, 8, 8)

        toolbar = QHBoxLayout()
        lbl = QLabel('实验记录（对应论文表5-2）')
        lbl.setFont(QFont('Microsoft YaHei', 11, QFont.Bold))
        lbl.setStyleSheet('color:#fd79a8; padding:6px 0;')
        toolbar.addWidget(lbl)
        toolbar.addStretch()
        btn_refresh = QPushButton('刷新')
        btn_refresh.clicked.connect(self._load_experiments)
        toolbar.addWidget(btn_refresh)
        v.addLayout(toolbar)

        self.exp_table = QTableWidget(0, 5)
        self.exp_table.setHorizontalHeaderLabels(
            ['保存时间', '实验类型', '数据条数', '备注', '文件'])
        self.exp_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.exp_table.verticalHeader().setVisible(False)
        self.exp_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.exp_table.setAlternatingRowColors(True)
        v.addWidget(self.exp_table)
        return w

    def _load_experiments(self):
        exps = kb.load_all_experiments()
        self.exp_table.setRowCount(len(exps))
        for row, exp in enumerate(exps):
            ts    = exp.get('saved_at', '')[:19].replace('T', ' ')
            etype = exp.get('type', '—')
            count = str(len(exp.get('data', [])))
            notes = exp.get('notes', '—')
            fname = exp.get('file', '—')
            for col, val in enumerate([ts, etype, count, notes, fname]):
                item = QTableWidgetItem(val)
                item.setTextAlignment(Qt.AlignCenter)
                self.exp_table.setItem(row, col, item)

    def _load_data(self):
        """初始化时加载所有数据"""
        self._schemes = []
        self._load_schemes()
        self._load_experiments()
        if self.review_list.count() > 0:
            self.review_list.setCurrentRow(0)
