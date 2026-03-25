# -*- coding: utf-8 -*-
"""
仿真分析模块 UI
对应模块二：爬坡稳定性仿真 + 越障过程仿真
"""

import numpy as np
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QGroupBox, QLabel, QDoubleSpinBox,
    QPushButton, QTabWidget, QComboBox,
    QProgressBar, QSplitter, QTextEdit, QListWidget
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont
import matplotlib
matplotlib.use('Qt5Agg')
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

plt.rcParams['font.family'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

from modules.simulation import ClimbingSimulator, ObstacleSimulator

COLOR_PALETTE = ['#7ec8e3', '#ff9f43', '#a29bfe', '#ff6b6b', '#55efc4', '#fd79a8']


def _style_ax(ax):
    ax.set_facecolor('#2a2a3e')
    for sp in ax.spines.values():
        sp.set_color('#555577')
    ax.tick_params(colors='#ccccee')
    ax.xaxis.label.set_color('#ccccee')
    ax.yaxis.label.set_color('#ccccee')
    ax.title.set_color('#e0e0ff')


class SimWorker(QThread):
    """后台仿真线程，避免UI卡顿"""
    finished = pyqtSignal(dict)
    progress = pyqtSignal(int)

    def __init__(self, sim_type, params):
        super().__init__()
        self.sim_type = sim_type
        self.params   = params

    def run(self):
        self.progress.emit(15)
        if self.sim_type == 'climb_angles':
            angles  = self.params.get('angles', [0, 20, 40, 45])
            t_end   = self.params.get('t_end', 10.0)
            results = ClimbingSimulator.batch_simulate_angles(angles, t_end)
            self.progress.emit(85)
            self.finished.emit({'type': 'climb_angles', 'results': results})

        elif self.sim_type == 'climb_radii':
            radii  = self.params.get('radii', [15, 25, 35])
            beta   = self.params.get('beta', 30.0)
            t_end  = self.params.get('t_end', 10.0)
            results = ClimbingSimulator.batch_simulate_radii(radii, beta, t_end)
            self.progress.emit(85)
            self.finished.emit({'type': 'climb_radii', 'results': results})

        elif self.sim_type == 'obstacle':
            sim    = ObstacleSimulator()
            result = sim.run()
            self.progress.emit(85)
            self.finished.emit({'type': 'obstacle', 'result': result})

        self.progress.emit(100)


class SimPanel(QWidget):
    """仿真分析面板"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._worker = None
        self._build_ui()

    def _build_ui(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(12)

        # ── 左侧：控制面板 ──────────────────────────
        left = QWidget()
        left.setFixedWidth(300)
        lv = QVBoxLayout(left)
        lv.setSpacing(10)

        # 仿真类型选择
        grp_type = QGroupBox('仿真类型')
        tv = QVBoxLayout(grp_type)
        self.combo_type = QComboBox()
        self.combo_type.addItems([
            '爬坡稳定性 - 不同倾角对比',
            '爬坡稳定性 - 不同线径对比',
            '越障过程仿真'
        ])
        self.combo_type.currentIndexChanged.connect(self._on_type_changed)
        tv.addWidget(self.combo_type)
        lv.addWidget(grp_type)

        # 参数组（倾角仿真）
        self.grp_angles = QGroupBox('倾角设置 (°)')
        av = QGridLayout(self.grp_angles)
        self.angle_spins = []
        for i, val in enumerate([0, 20, 40, 45]):
            av.addWidget(QLabel(f'倾角 {i+1}:'), i, 0)
            sp = QDoubleSpinBox()
            sp.setRange(0, 45)
            sp.setValue(val)
            sp.setSingleStep(5)
            av.addWidget(sp, i, 1)
            self.angle_spins.append(sp)
        lv.addWidget(self.grp_angles)

        # 参数组（线径仿真）
        self.grp_radii = QGroupBox('线径设置 (mm)')
        rv = QGridLayout(self.grp_radii)
        self.radii_spins = []
        self.radii_beta_spin = QDoubleSpinBox()
        self.radii_beta_spin.setRange(0, 45)
        self.radii_beta_spin.setValue(30)
        rv.addWidget(QLabel('固定倾角 β (°):'), 0, 0)
        rv.addWidget(self.radii_beta_spin, 0, 1)
        for i, val in enumerate([15, 25, 35]):
            rv.addWidget(QLabel(f'线径 {i+1}:'), i+1, 0)
            sp = QDoubleSpinBox()
            sp.setRange(10, 50)
            sp.setValue(val)
            sp.setSingleStep(5)
            rv.addWidget(sp, i+1, 1)
            self.radii_spins.append(sp)
        self.grp_radii.hide()
        lv.addWidget(self.grp_radii)

        # 仿真时长
        grp_time = QGroupBox('仿真时长')
        tiv = QGridLayout(grp_time)
        tiv.addWidget(QLabel('仿真时长 t (s):'), 0, 0)
        self.spin_tend = QDoubleSpinBox()
        self.spin_tend.setRange(2, 60)
        self.spin_tend.setValue(10)
        self.spin_tend.setSingleStep(2)
        tiv.addWidget(self.spin_tend, 0, 1)
        lv.addWidget(grp_time)

        # 进度条
        self.progress = QProgressBar()
        self.progress.setValue(0)
        lv.addWidget(self.progress)

        # 运行按钮
        self.btn_run = QPushButton('▶  开始仿真')
        self.btn_run.setFixedHeight(42)
        self.btn_run.setCursor(Qt.PointingHandCursor)
        self.btn_run.clicked.connect(self._run_simulation)
        lv.addWidget(self.btn_run)

        # 仿真日志
        grp_log = QGroupBox('仿真日志')
        lgv = QVBoxLayout(grp_log)
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont('Consolas', 8))
        self.log_text.setMaximumHeight(160)
        lgv.addWidget(self.log_text)
        lv.addWidget(grp_log)
        lv.addStretch()
        root.addWidget(left)

        # ── 右侧：图表 ──────────────────────────────
        self.tab_charts = QTabWidget()

        # 速度曲线图
        self.fig_vel = Figure(figsize=(7, 4), facecolor='#1e1e2e')
        self.ax_vel  = self.fig_vel.add_subplot(111)
        _style_ax(self.ax_vel)
        self.canvas_vel = FigureCanvas(self.fig_vel)
        self.tab_charts.addTab(self.canvas_vel, '质心速度曲线')

        # 位移曲线图
        self.fig_pos = Figure(figsize=(7, 4), facecolor='#1e1e2e')
        self.ax_pos  = self.fig_pos.add_subplot(111)
        _style_ax(self.ax_pos)
        self.canvas_pos = FigureCanvas(self.fig_pos)
        self.tab_charts.addTab(self.canvas_pos, '质心位移曲线')

        # 越障扭矩图
        self.fig_obs = Figure(figsize=(7, 4), facecolor='#1e1e2e')
        self.ax_obs1 = self.fig_obs.add_subplot(211)
        self.ax_obs2 = self.fig_obs.add_subplot(212)
        _style_ax(self.ax_obs1)
        _style_ax(self.ax_obs2)
        self.canvas_obs = FigureCanvas(self.fig_obs)
        self.tab_charts.addTab(self.canvas_obs, '越障过程分析')

        root.addWidget(self.tab_charts)

    def _on_type_changed(self, idx):
        self.grp_angles.setVisible(idx == 0)
        self.grp_radii.setVisible(idx == 1)

    def _run_simulation(self):
        """启动后台仿真线程"""
        if self._worker and self._worker.isRunning():
            return
        self.btn_run.setEnabled(False)
        self.progress.setValue(0)
        idx   = self.combo_type.currentIndex()
        t_end = self.spin_tend.value()

        if idx == 0:
            angles = [sp.value() for sp in self.angle_spins]
            params = {'angles': angles, 't_end': t_end}
            sim_type = 'climb_angles'
        elif idx == 1:
            radii = [sp.value() for sp in self.radii_spins]
            beta  = self.radii_beta_spin.value()
            params = {'radii': radii, 'beta': beta, 't_end': t_end}
            sim_type = 'climb_radii'
        else:
            params   = {}
            sim_type = 'obstacle'

        self._worker = SimWorker(sim_type, params)
        self._worker.progress.connect(self.progress.setValue)
        self._worker.finished.connect(self._on_sim_finished)
        self._worker.start()
        self._log(f'开始仿真：{self.combo_type.currentText()}')

    def _on_sim_finished(self, data):
        self.btn_run.setEnabled(True)
        t = data['type']
        if t in ('climb_angles', 'climb_radii'):
            self._plot_climbing(data['results'], t)
        elif t == 'obstacle':
            self._plot_obstacle(data['result'])
        self._log('仿真完成 ✓')

    def _plot_climbing(self, results, sim_type):
        """绘制爬坡速度/位移曲线"""
        for ax, fig, canvas in [
            (self.ax_vel, self.fig_vel, self.canvas_vel),
            (self.ax_pos, self.fig_pos, self.canvas_pos)
        ]:
            ax.clear()
            _style_ax(ax)

        for i, res in enumerate(results):
            color = COLOR_PALETTE[i % len(COLOR_PALETTE)]
            if sim_type == 'climb_angles':
                label = f'β={res["beta_deg"]}°'
            else:
                label = f'R={res["wire_radius"]}mm'

            self.ax_vel.plot(res['time'], res['velocity'], color=color,
                             linewidth=2.0, label=label)
            self.ax_pos.plot(res['time'], res['position'], color=color,
                             linewidth=2.0, label=label)

        for ax, fig, canvas, ylabel, title in [
            (self.ax_vel, self.fig_vel, self.canvas_vel,
             '质心速度 (m/s)', '检测箱质心速度曲线'),
            (self.ax_pos, self.fig_pos, self.canvas_pos,
             '质心位移 (m)',   '检测箱质心位移曲线'),
        ]:
            ax.set_xlabel('时间 t (s)')
            ax.set_ylabel(ylabel)
            ax.set_title(title)
            ax.legend(facecolor='#2a2a3e', labelcolor='#ccccee',
                      fontsize=8, framealpha=0.8)
            ax.grid(True, linestyle='--', alpha=0.25, color='#555577')
            fig.tight_layout(pad=2.0)
            canvas.draw()

        # 切换到速度曲线标签
        self.tab_charts.setCurrentIndex(0)
        self._log_results(results, sim_type)

    def _plot_obstacle(self, result):
        """绘制越障过程速度和扭矩曲线"""
        t   = result['time']
        vel = result['velocity']
        trq = result['torque']
        boundaries = result['phase_boundaries']

        for ax in (self.ax_obs1, self.ax_obs2):
            ax.clear()
            _style_ax(ax)

        # 速度曲线
        self.ax_obs1.plot(t, vel, color='#7ec8e3', linewidth=1.8, label='质心速度')
        self.ax_obs1.set_ylabel('速度 (m/s)')
        self.ax_obs1.set_title('越障过程质心速度曲线')
        self.ax_obs1.grid(True, linestyle='--', alpha=0.2, color='#555577')

        # 扭矩曲线
        self.ax_obs2.plot(t, trq, color='#ff9f43', linewidth=1.8, label='驱动扭矩')
        self.ax_obs2.set_xlabel('时间 t (s)')
        self.ax_obs2.set_ylabel('扭矩 (N·m)')
        self.ax_obs2.set_title('越障过程驱动轮扭矩曲线')
        self.ax_obs2.grid(True, linestyle='--', alpha=0.2, color='#555577')

        # 绘制阶段分割线和标注
        colors_phase = ['#a29bfe', '#55efc4', '#fd79a8', '#ffeaa7',
                        '#74b9ff', '#00cec9', '#e17055', '#dfe6e9', '#b2bec3']
        for idx, bd in enumerate(boundaries):
            xm = (bd['t_start'] + bd['t_end']) / 2
            for ax in (self.ax_obs1, self.ax_obs2):
                ax.axvspan(bd['t_start'], bd['t_end'],
                           alpha=0.08, color=colors_phase[idx % len(colors_phase)])
                ax.axvline(bd['t_start'], color='#555577', linestyle=':', lw=0.8)
            # 阶段名称标注（只在上图）
            y_max = max(vel) if len(vel) > 0 else 1.0
            self.ax_obs1.text(xm, y_max * 0.88, bd['name'],
                              ha='center', va='top', fontsize=6.5,
                              color='#aaaacc', rotation=90)

        self.fig_obs.tight_layout(pad=2.0)
        self.canvas_obs.draw()
        self.tab_charts.setCurrentIndex(2)

        self._log(f'越障总时长: {t[-1]:.1f}s | 阶段数: {len(boundaries)}')

    def _log(self, msg):
        self.log_text.append(msg)

    def _log_results(self, results, sim_type):
        for res in results:
            v_ss = res['velocity'][-1] if len(res['velocity']) > 0 else 0
            if sim_type == 'climb_angles':
                tag = f"β={res['beta_deg']}°"
            else:
                tag = f"R={res['wire_radius']}mm"
            self._log(f'  {tag}: 稳态速度 = {v_ss:.4f} m/s')
