# -*- coding: utf-8 -*-
"""
模块三：样机测试与数据采集 UI
虚拟控制面板 + 数据记录
"""

import csv
import os
from datetime import datetime
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QGroupBox, QLabel, QPushButton, QComboBox,
    QLineEdit, QTextEdit, QTableWidget, QTableWidgetItem,
    QFileDialog, QSplitter, QFrame, QProgressBar
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont, QColor
import matplotlib
matplotlib.use('Qt5Agg')
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
import numpy as np

plt.rcParams['font.family'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

from modules.control_interface import get_controller


class ControlPanel(QWidget):
    """样机测试与数据采集面板"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._ctrl = get_controller()
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._refresh_state)
        self._timer.start(200)  # 200ms刷新
        self._build_ui()

    def _build_ui(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(12)

        # ── 左列：连接 + 控制 ───────────────────────
        left = QWidget()
        left.setFixedWidth(300)
        lv = QVBoxLayout(left)
        lv.setSpacing(10)

        # 连接设置
        grp_conn = QGroupBox('硬件连接')
        cv = QGridLayout(grp_conn)
        cv.addWidget(QLabel('串口:'), 0, 0)
        self.combo_port = QComboBox()
        self.combo_port.addItems(['COM1','COM2','COM3','COM4','COM5','COM6','虚拟模式'])
        self.combo_port.setCurrentText('虚拟模式')
        cv.addWidget(self.combo_port, 0, 1)
        self.btn_connect = QPushButton('连接')
        self.btn_connect.clicked.connect(self._toggle_connect)
        cv.addWidget(self.btn_connect, 1, 0, 1, 2)
        self.lbl_mode = QLabel('● 虚拟模式')
        self.lbl_mode.setStyleSheet('color:#55efc4; font-weight:bold;')
        cv.addWidget(self.lbl_mode, 2, 0, 1, 2)
        lv.addWidget(grp_conn)

        # 运动控制
        grp_move = QGroupBox('运动控制')
        mv = QVBoxLayout(grp_move)
        btn_grid = QGridLayout()
        self.btn_fwd  = self._make_ctrl_btn('▲ 前进', 'forward')
        self.btn_bwd  = self._make_ctrl_btn('▼ 后退', 'backward')
        self.btn_stop = self._make_ctrl_btn('■ 停止', 'stop')
        self.btn_sup  = self._make_ctrl_btn('+ 加速', 'speed_up')
        self.btn_sdn  = self._make_ctrl_btn('- 减速', 'speed_down')
        btn_grid.addWidget(self.btn_fwd,  0, 1)
        btn_grid.addWidget(self.btn_sup,  0, 2)
        btn_grid.addWidget(self.btn_stop, 1, 1)
        btn_grid.addWidget(self.btn_bwd,  2, 1)
        btn_grid.addWidget(self.btn_sdn,  2, 2)
        mv.addLayout(btn_grid)
        lv.addWidget(grp_move)

        # 抱紧机构控制
        grp_grip = QGroupBox('抱紧机构')
        gv = QHBoxLayout(grp_grip)
        self.btn_grip_open  = self._make_ctrl_btn('松开', 'grip_open')
        self.btn_grip_close = self._make_ctrl_btn('夹紧', 'grip_close')
        self.btn_grip_open.setStyleSheet(self.btn_grip_open.styleSheet() +
                                         'background:#e17055;')
        self.btn_grip_close.setStyleSheet(self.btn_grip_close.styleSheet() +
                                          'background:#00b894;')
        gv.addWidget(self.btn_grip_open)
        gv.addWidget(self.btn_grip_close)
        lv.addWidget(grp_grip)

        # 越障指令
        grp_obs = QGroupBox('越障控制')
        ov = QVBoxLayout(grp_obs)
        btn_obs = QPushButton('▶ 启动自动越障序列')
        btn_obs.setFixedHeight(36)
        btn_obs.clicked.connect(lambda: self._send('obstacle_seq'))
        ov.addWidget(btn_obs)
        lv.addWidget(grp_obs)

        # 数据记录
        grp_log = QGroupBox('实验数据记录')
        dlv = QVBoxLayout(grp_log)
        row = QHBoxLayout()
        self.btn_start_log = QPushButton('▶ 开始记录')
        self.btn_start_log.clicked.connect(self._start_log)
        self.btn_stop_log  = QPushButton('■ 停止记录')
        self.btn_stop_log.clicked.connect(self._stop_log)
        self.btn_export    = QPushButton('导出 CSV')
        self.btn_export.clicked.connect(self._export_csv)
        row.addWidget(self.btn_start_log)
        row.addWidget(self.btn_stop_log)
        row.addWidget(self.btn_export)
        dlv.addLayout(row)
        self.lbl_log_count = QLabel('已记录: 0 条')
        dlv.addWidget(self.lbl_log_count)
        lv.addWidget(grp_log)
        lv.addStretch()
        root.addWidget(left)

        # ── 中列：状态显示 ──────────────────────────
        mid = QWidget()
        mid.setFixedWidth(220)
        mv2 = QVBoxLayout(mid)
        mv2.setSpacing(10)

        grp_state = QGroupBox('实时状态')
        sv = QGridLayout(grp_state)
        labels = ['速度 (m/s):', '位置 (m):', '电压 (V):', '电流 (A):', '抱紧状态:', '运动方向:']
        self._state_vals = {}
        keys = ['speed', 'position', 'voltage', 'current', 'grip', 'direction']
        for i, (lbl, key) in enumerate(zip(labels, keys)):
            sv.addWidget(QLabel(lbl), i, 0)
            val_lbl = QLabel('—')
            val_lbl.setStyleSheet('color:#7ec8e3; font-weight:bold;')
            val_lbl.setAlignment(Qt.AlignRight)
            sv.addWidget(val_lbl, i, 1)
            self._state_vals[key] = val_lbl
        mv2.addWidget(grp_state)

        # 摄像头模拟
        grp_cam = QGroupBox('摄像头视图 (模拟)')
        camv = QVBoxLayout(grp_cam)
        self.cam_fig = Figure(figsize=(2.5, 2.5), facecolor='#0d0d0d')
        self.cam_ax  = self.cam_fig.add_subplot(111)
        self.cam_ax.set_facecolor('#0d0d0d')
        self.cam_ax.axis('off')
        self.cam_canvas = FigureCanvas(self.cam_fig)
        self.cam_canvas.setFixedHeight(160)
        camv.addWidget(self.cam_canvas)
        self.combo_cam = QComboBox()
        self.combo_cam.addItems(['前摄像头', '后摄像头', '左摄像头', '右摄像头'])
        camv.addWidget(self.combo_cam)
        mv2.addWidget(grp_cam)
        mv2.addStretch()
        root.addWidget(mid)
        self._update_cam_view()

        # ── 右列：数据表格 + 实时曲线 ────────────────
        right = QWidget()
        rv = QVBoxLayout(right)
        rv.setSpacing(8)

        # 实时速度曲线
        self.rt_fig = Figure(figsize=(5, 2.5), facecolor='#1e1e2e')
        self.rt_ax  = self.rt_fig.add_subplot(111)
        self.rt_ax.set_facecolor('#2a2a3e')
        for sp in self.rt_ax.spines.values(): sp.set_color('#555577')
        self.rt_ax.tick_params(colors='#ccccee')
        self.rt_ax.set_title('实时速度曲线', color='#e0e0ff')
        self.rt_ax.set_xlabel('时间 (s)', color='#ccccee')
        self.rt_ax.set_ylabel('速度 (m/s)', color='#ccccee')
        self.rt_canvas = FigureCanvas(self.rt_fig)
        self.rt_canvas.setMinimumHeight(180)
        rv.addWidget(self.rt_canvas)
        self._rt_times = []
        self._rt_speeds = []
        self._rt_t0 = None

        # 数据表格
        grp_tbl = QGroupBox('实验数据表 (论文表5-2)')
        tv = QVBoxLayout(grp_tbl)
        self.data_table = QTableWidget(0, 6)
        self.data_table.setHorizontalHeaderLabels(
            ['时间', '位置(m)', '速度(m/s)', '电压(V)', '电流(A)', '状态'])
        self.data_table.horizontalHeader().setStretchLastSection(True)
        self.data_table.setAlternatingRowColors(True)
        self.data_table.setEditTriggers(QTableWidget.NoEditTriggers)
        tv.addWidget(self.data_table)
        rv.addWidget(grp_tbl)
        root.addWidget(right)

    def _make_ctrl_btn(self, text, cmd):
        btn = QPushButton(text)
        btn.setFixedSize(80, 38)
        btn.setCursor(Qt.PointingHandCursor)
        btn.clicked.connect(lambda: self._send(cmd))
        return btn

    def _send(self, cmd):
        ok = self._ctrl.send_command(cmd)
        status = '✓' if ok else '✗'

    def _toggle_connect(self):
        port = self.combo_port.currentText()
        if port == '虚拟模式':
            self.lbl_mode.setText('● 虚拟模式')
            self.lbl_mode.setStyleSheet('color:#55efc4; font-weight:bold;')
        else:
            ok = self._ctrl.connect_serial(port)
            if ok:
                self.lbl_mode.setText(f'● 已连接 {port}')
                self.lbl_mode.setStyleSheet('color:#00b894; font-weight:bold;')
            else:
                self.lbl_mode.setText(f'✗ 连接失败 → 虚拟模式')
                self.lbl_mode.setStyleSheet('color:#e17055; font-weight:bold;')

    def _refresh_state(self):
        """200ms 定时刷新状态显示"""
        state = self._ctrl.get_state()
        self._state_vals['speed'].setText(f"{state['speed']:.3f}")
        self._state_vals['position'].setText(f"{state['position']:.4f}")
        self._state_vals['voltage'].setText(f"{state['voltage']:.2f}")
        self._state_vals['current'].setText(f"{state['current']:.3f}")
        self._state_vals['grip'].setText(state['grip'])
        self._state_vals['direction'].setText(state['direction'])

        # 实时曲线
        import time
        if self._rt_t0 is None:
            self._rt_t0 = time.time()
        t_now = time.time() - self._rt_t0
        self._rt_times.append(t_now)
        self._rt_speeds.append(state['speed'])
        # 保留最近60秒
        cutoff = t_now - 60.0
        while self._rt_times and self._rt_times[0] < cutoff:
            self._rt_times.pop(0)
            self._rt_speeds.pop(0)
        self.rt_ax.clear()
        self.rt_ax.set_facecolor('#2a2a3e')
        for sp in self.rt_ax.spines.values(): sp.set_color('#555577')
        self.rt_ax.tick_params(colors='#ccccee')
        self.rt_ax.plot(self._rt_times, self._rt_speeds,
                        color='#7ec8e3', linewidth=1.5)
        self.rt_ax.set_title('实时速度曲线', color='#e0e0ff', fontsize=9)
        self.rt_ax.set_xlabel('时间 (s)', color='#ccccee', fontsize=8)
        self.rt_ax.set_ylabel('速度 (m/s)', color='#ccccee', fontsize=8)
        self.rt_ax.grid(True, linestyle='--', alpha=0.2, color='#555577')
        self.rt_fig.tight_layout(pad=1.5)
        self.rt_canvas.draw()

        # 更新数据记录计数
        self.lbl_log_count.setText(f'已记录: {len(self._ctrl.get_log())} 条')
        # 同步表格末行
        log = self._ctrl.get_log()
        if log:
            last = log[-1]
            row = self.data_table.rowCount()
            if row == 0 or self.data_table.item(row-1, 0) is None or \
               self.data_table.item(row-1, 0).text() != last['timestamp'][-8:]:
                self.data_table.insertRow(row)
                vals = [
                    last['timestamp'][-8:],
                    str(last['position']),
                    str(last['speed']),
                    str(last['voltage']),
                    str(last['current']),
                    last['grip'],
                ]
                for col, v in enumerate(vals):
                    self.data_table.setItem(row, col, QTableWidgetItem(v))
                self.data_table.scrollToBottom()

    def _update_cam_view(self):
        """模拟摄像头画面（线条图形代替）"""
        ax = self.cam_ax
        ax.clear()
        ax.set_facecolor('#0d0d0d')
        ax.axis('off')
        # 画一条高压线场景示意
        ax.plot([0.1, 0.9], [0.5, 0.5], color='#aaaaaa', linewidth=3)
        ax.add_patch(plt.Circle((0.5, 0.5), 0.06, color='#4a4a8a', zorder=3))
        ax.text(0.5, 0.15, '摄像头画面模拟', ha='center',
                color='#555577', fontsize=7, transform=ax.transAxes)
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        self.cam_fig.tight_layout(pad=0)
        self.cam_canvas.draw()

    def _start_log(self):
        self._ctrl.start_logging()
        self.data_table.setRowCount(0)
        self.btn_start_log.setStyleSheet('background:#00b894; color:white;')

    def _stop_log(self):
        self._ctrl.stop_logging()
        self.btn_start_log.setStyleSheet('')

    def _export_csv(self):
        log = self._ctrl.get_log()
        if not log:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, '导出CSV', f'experiment_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv',
            'CSV Files (*.csv)')
        if path:
            with open(path, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.DictWriter(f, fieldnames=log[0].keys())
                writer.writeheader()
                writer.writerows(log)

