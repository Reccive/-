# -*- coding: utf-8 -*-
"""
参数化设计与计算模块 UI
对应模块一：抱紧力/推程/扭矩/强度校核

本模块提供了参数化设计的图形用户界面，包括：
- 参数输入区域（线径、倾角、重量等）
- 计算结果显示（数值表格和图表）
- 多功能标签页（抱紧机构、电机选型、强度校核）
- 实时图表更新和交互

UI组件：
- CalcPanel：主计算面板（多标签页布局）
- DoubleSpinBox：带单位的双精度数值输入
- FigureCanvas：matplotlib图表嵌入
- TextEdit：结果文本显示

依赖：
- modules.calculations：核心计算逻辑
- matplotlib：图表绘制
- PyQt5：GUI框架

作者：李豪
创建日期：2026-03-25
"""

__author__ = "李豪"
__copyright__ = "Copyright 2026, 高压线巡检机器人平台"
__license__ = "MIT"
__version__ = "1.0.0"
__maintainer__ = "李豪"
__status__ = "Production"

import numpy as np
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QGroupBox, QLabel, QDoubleSpinBox,
    QPushButton, QTabWidget, QTextEdit
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
import matplotlib
matplotlib.use('Qt5Agg')
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.pyplot as plt

plt.rcParams['font.family'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

from modules.calculations import GripMechanismCalc, DriveMotorCalc, LinkStrengthCalc


def _style_ax(ax):
    """统一深色主题坐标轴样式"""
    ax.set_facecolor('#2a2a3e')
    for spine in ax.spines.values():
        spine.set_color('#555577')
    ax.tick_params(colors='#ccccee')
    ax.xaxis.label.set_color('#ccccee')
    ax.yaxis.label.set_color('#ccccee')
    ax.title.set_color('#e0e0ff')


def _make_figure(nrows=1, ncols=1, proj=None):
    """创建深色主题 Figure"""
    fig = Figure(figsize=(6, 4), facecolor='#1e1e2e')
    if proj:
        ax = fig.add_subplot(111, projection=proj)
    else:
        ax = fig.add_subplot(111)
        _style_ax(ax)
    fig.tight_layout(pad=2.0)
    return fig, ax


class CalcPanel(QWidget):
    """参数化设计与计算面板"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()
        self._run_all_calculations()

    def _build_ui(self):
        root = QHBoxLayout(self)
        root.setSpacing(12)
        root.setContentsMargins(12, 12, 12, 12)

        # ── 左侧：参数输入 + 结果 ──────────────────
        left = QWidget()
        left.setFixedWidth(320)
        lv = QVBoxLayout(left)
        lv.setSpacing(10)

        grp_basic = QGroupBox('基础参数输入')
        g = QGridLayout(grp_basic)
        g.setVerticalSpacing(8)

        params = [
            ('高压线半径 R (mm):',  'spin_R',      10,  50,  25.0, 1.0),
            ('高压线倾角 β (°):',  'spin_beta',    0,  45,  30.0, 5.0),
            ('机器人重量 W (kg):', 'spin_weight',  5,  30,  15.0, 0.5),
        ]
        for row, (label, attr, lo, hi, val, step) in enumerate(params):
            g.addWidget(QLabel(label), row, 0)
            sp = QDoubleSpinBox()
            sp.setRange(lo, hi)
            sp.setValue(val)
            sp.setSingleStep(step)
            sp.setFixedHeight(28)
            setattr(self, attr, sp)
            g.addWidget(sp, row, 1)

        lv.addWidget(grp_basic)

        self.btn_calc = QPushButton('▶  执行计算')
        self.btn_calc.setFixedHeight(42)
        self.btn_calc.setCursor(Qt.PointingHandCursor)
        self.btn_calc.clicked.connect(self._run_all_calculations)
        lv.addWidget(self.btn_calc)

        grp_res = QGroupBox('计算结果')
        rv = QVBoxLayout(grp_res)
        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        self.result_text.setFont(QFont('Consolas', 9))
        self.result_text.setMinimumHeight(280)
        rv.addWidget(self.result_text)
        lv.addWidget(grp_res)
        lv.addStretch()
        root.addWidget(left)

        # ── 右侧：图表 TabWidget ───────────────────
        self.tab_charts = QTabWidget()

        self.fig_rs, self.ax_rs = _make_figure()
        self.canvas_rs = FigureCanvas(self.fig_rs)
        self.tab_charts.addTab(self.canvas_rs, '推程-半径关系')

        self.fig_grip = Figure(figsize=(6, 4), facecolor='#1e1e2e')
        self.ax_grip = self.fig_grip.add_subplot(111, projection='3d')
        self.ax_grip.set_facecolor('#2a2a3e')
        self.canvas_grip = FigureCanvas(self.fig_grip)
        self.tab_charts.addTab(self.canvas_grip, '抱紧力曲面')

        self.fig_torque, self.ax_torque = _make_figure()
        self.canvas_torque = FigureCanvas(self.fig_torque)
        self.tab_charts.addTab(self.canvas_torque, '电机扭矩-倾角')

        self.fig_stress, self.ax_stress = _make_figure()
        self.canvas_stress = FigureCanvas(self.fig_stress)
        self.tab_charts.addTab(self.canvas_stress, '连杆应力分布')

        root.addWidget(self.tab_charts)

    # ── 计算与绘图 ─────────────────────────────────
    def _run_all_calculations(self):
        R_val    = self.spin_R.value()
        beta_val = self.spin_beta.value()
        w_val    = self.spin_weight.value()

        # 推程-半径
        R_arr = np.linspace(10, 50, 300)
        S_arr = GripMechanismCalc.calc_stroke_from_radius(R_arr)
        S_cur = GripMechanismCalc.calc_stroke_from_radius([R_val])[0]

        # 抱紧力
        F_val = GripMechanismCalc.calc_grip_force(R_val, beta_val, w_val)
        R_surf = np.linspace(10, 50, 30)
        B_surf = np.linspace(0, 45, 30)
        Rm, Bm, Fm = GripMechanismCalc.calc_grip_force_surface(R_surf, B_surf)

        # 电机扭矩
        angles, torques = DriveMotorCalc.calc_torque_vs_angle(w_val)
        T_cur  = DriveMotorCalc.calc_torque_slope(w_val, beta_val)
        T_flat = DriveMotorCalc.calc_torque_flat(w_val)

        # 连杆应力
        F_link = F_val * 0.5
        x_link, sigma_link = LinkStrengthCalc.calc_stress_distribution(F_link)
        stress_info = LinkStrengthCalc.calc_link_stress(F_link)

        # 更新图表
        self._plot_rs(R_arr, S_arr, R_val, S_cur)
        self._plot_grip_surface(Rm, Bm, Fm, R_val, beta_val, F_val)
        self._plot_torque(angles, torques * 1000, beta_val, T_cur * 1000, T_flat * 1000)
        self._plot_stress(x_link * 1000, sigma_link / 1e6, stress_info)

        # 文本报告
        safe_str = '✓ 通过' if stress_info['is_safe'] else '✗ 不通过'
        txt = (
            f"{'='*36}\n"
            f"   参数化设计计算结果报告\n"
            f"{'='*36}\n"
            f"■ 输入参数\n"
            f"   线径 R    = {R_val:.1f} mm\n"
            f"   倾角 β    = {beta_val:.1f} °\n"
            f"   重量 W    = {w_val:.1f} kg\n"
            f"{'─'*36}\n"
            f"■ 抱紧机构\n"
            f"   推杆推程  S = {S_cur:.2f} mm\n"
            f"   最小抱紧力 F = {F_val:.2f} N\n"
            f"{'─'*36}\n"
            f"■ 驱动电机选型\n"
            f"   水平行走扭矩 = {T_flat*1000:.3f} mN·m\n"
            f"   爬坡扭矩(β={beta_val:.0f}°) = {T_cur*1000:.3f} mN·m\n"
            f"   建议选型  ≥ {T_cur*1000*1.5:.2f} mN·m (×1.5安全系数)\n"
            f"{'─'*36}\n"
            f"■ 连杆强度校核\n"
            f"   最大弯矩  = {stress_info['bending_moment']:.4f} N·m\n"
            f"   最大应力  = {stress_info['max_stress']/1e6:.3f} MPa\n"
            f"   安全系数  = {stress_info['safety_factor']:.3f}\n"
            f"   校核结论  = {safe_str}\n"
            f"{'='*36}\n"
        )
        self.result_text.setPlainText(txt)

    def _plot_rs(self, R_arr, S_arr, R_cur, S_cur):
        ax = self.ax_rs
        ax.clear()
        _style_ax(ax)
        ax.fill_between(R_arr, S_arr, alpha=0.15, color='#7ec8e3')
        ax.plot(R_arr, S_arr, color='#7ec8e3', linewidth=2.2, label='推程曲线')
        ax.axvline(R_cur, color='#ff9f43', linestyle='--', alpha=0.9, lw=1.5, label=f'当前 R={R_cur:.1f} mm')
        ax.axhline(S_cur, color='#ff9f43', linestyle=':', alpha=0.6, lw=1.2)
        ax.scatter([R_cur], [S_cur], color='#ff6b6b', s=90, zorder=6)
        ax.annotate(f'S={S_cur:.1f}mm', (R_cur, S_cur),
                    textcoords='offset points', xytext=(8, 6),
                    color='#ff9f43', fontsize=8)
        ax.set_xlabel('高压线半径 R (mm)')
        ax.set_ylabel('推杆推程 S (mm)')
        ax.set_title('推杆推程 S 与高压线半径 R 关系曲线')
        ax.legend(facecolor='#2a2a3e', labelcolor='#ccccee', fontsize=8, framealpha=0.8)
        ax.grid(True, linestyle='--', alpha=0.25, color='#555577')
        self.fig_rs.tight_layout(pad=2.0)
        self.canvas_rs.draw()

    def _plot_grip_surface(self, Rm, Bm, Fm, R_cur, beta_cur, F_cur):
        ax = self.ax_grip
        ax.clear()
        ax.set_facecolor('#2a2a3e')
        surf = ax.plot_surface(Rm, Bm, Fm, cmap='plasma', alpha=0.85, linewidth=0)
        ax.scatter([R_cur], [beta_cur], [F_cur], color='#ff6b6b', s=80, zorder=5)
        ax.set_xlabel('R (mm)', color='#ccccee', labelpad=6)
        ax.set_ylabel('β (°)',  color='#ccccee', labelpad=6)
        ax.set_zlabel('F (N)',  color='#ccccee', labelpad=6)
        ax.set_title('最小抱紧力 F(R, β) 曲面', color='#e0e0ff')
        ax.tick_params(colors='#aaaacc')
        self.fig_grip.colorbar(surf, ax=ax, pad=0.1, shrink=0.7)
        self.fig_grip.tight_layout(pad=1.5)
        self.canvas_grip.draw()

    def _plot_torque(self, angles, torques_mn, beta_cur, T_cur_mn, T_flat_mn):
        ax = self.ax_torque
        ax.clear()
        _style_ax(ax)
        ax.fill_between(angles, torques_mn, alpha=0.15, color='#a29bfe')
        ax.plot(angles, torques_mn, color='#a29bfe', linewidth=2.2, label='爬坡扭矩')
        ax.axhline(T_flat_mn, color='#55efc4', linestyle='--', lw=1.5, label=f'水平扭矩={T_flat_mn:.2f} mN·m')
        ax.axvline(beta_cur,  color='#ff9f43', linestyle='--', alpha=0.9, lw=1.5, label=f'当前 β={beta_cur:.1f}°')
        ax.scatter([beta_cur], [T_cur_mn], color='#ff6b6b', s=90, zorder=6)
        ax.set_xlabel('高压线倾角 β (°)')
        ax.set_ylabel('电机扭矩 (mN·m)')
        ax.set_title('驱动电机所需扭矩 vs 线路倾角')
        ax.legend(facecolor='#2a2a3e', labelcolor='#ccccee', fontsize=8, framealpha=0.8)
        ax.grid(True, linestyle='--', alpha=0.25, color='#555577')
        self.fig_torque.tight_layout(pad=2.0)
        self.canvas_torque.draw()

    def _plot_stress(self, x_mm, sigma_mpa, info):
        ax = self.ax_stress
        ax.clear()
        _style_ax(ax)
        yield_mpa = LinkStrengthCalc.MATERIAL_YIELD / 1e6
        allow_mpa = yield_mpa / LinkStrengthCalc.SAFETY_FACTOR
        ax.fill_between(x_mm, sigma_mpa, alpha=0.2, color='#fd79a8')
        ax.plot(x_mm, sigma_mpa, color='#fd79a8', linewidth=2.2, label='弯曲应力')
        ax.axhline(allow_mpa, color='#fdcb6e', linestyle='--', lw=1.5,
                   label=f'许用应力 [{allow_mpa:.1f} MPa]')
        ax.axhline(yield_mpa, color='#e17055', linestyle=':', lw=1.2,
                   label=f'屈服强度 [{yield_mpa:.0f} MPa]')
        ax.set_xlabel('连杆位置 x (mm)')
        ax.set_ylabel('弯曲应力 σ (MPa)')
        ax.set_title(f'连杆弯曲应力分布  (安全系数 = {info["safety_factor"]:.2f})')
        ax.legend(facecolor='#2a2a3e', labelcolor='#ccccee', fontsize=8, framealpha=0.8)
        ax.grid(True, linestyle='--', alpha=0.25, color='#555577')
        self.fig_stress.tight_layout(pad=2.0)
        self.canvas_stress.draw()
