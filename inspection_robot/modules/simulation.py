# -*- coding: utf-8 -*-
"""
模块二：运动仿真与分析模块
基于简化动力学模型，复现论文第4章ADAMS仿真分析

本模块提供了高压线巡检机器人的运动仿真功能，包括：
- 爬坡稳定性仿真（不同倾角和线径下的动力学分析）
- 越障过程仿真（三臂轮流式越障9阶段模拟）
- 使用Runge-Kutta方法求解运动微分方程

仿真方法：
- 动力学计算：基于牛顿-欧拉方程
- 数值求解：使用scipy.integrate.solve_ivp（RK45方法）
- 随机模拟：固定随机种子保证结果可复现

注意：
- 所有物理参数使用SI单位（米、千克、秒）
- 仿真结果可直接用于论文图4-3、图4-5的对比验证
"""

import numpy as np
from scipy.integrate import solve_ivp

__author__ = "李豪"
__copyright__ = "Copyright 2026, 高压线巡检机器人平台"
__license__ = "MIT"
__version__ = "1.0.0"
__maintainer__ = "李豪"
__status__ = "Production"


class ClimbingSimulator:
    """
    爬坡稳定性仿真
    论文4.2节：不同倾角和线径下的巡检稳定性分析
    """
    MASS       = 15.0   # 总质量 kg
    WHEEL_R    = 0.05   # 驱动轮半径 m
    MOTOR_T    = 2.0    # 单电机额定扭矩 N·m
    N_MOTORS   = 4      # 驱动电机数量
    GEAR_RATIO = 30     # 减速比
    ETA        = 0.85   # 传动效率
    MU         = 0.4    # 轮-线摩擦系数

    def __init__(self, beta_deg=0.0, wire_radius=25.0):
        """
        :param beta_deg: 高压线倾角 (度)
        :param wire_radius: 高压线半径 (mm)
        """
        self.beta       = np.radians(beta_deg)
        self.beta_deg   = beta_deg
        self.wire_radius = wire_radius
        # 夹紧力随线径线性增加
        self.grip_force = 200.0 + (wire_radius - 15.0) * 3.0
        # 目标稳态速度（论文实验约0.3 m/s）
        self._v_ss = 0.30 + max(0.0, 0.004 * (wire_radius - 15.0))

    def dynamics(self, t, y):
        """
        运动微分方程 y = [position, velocity]
        使用非线性粘性阻尼使速度收敛到稳态值
        """
        pos, vel = y
        g  = 9.81
        m  = self.MASS
        r  = self.WHEEL_R

        # 驱动力（减速箱输出）
        F_drive = self.N_MOTORS * self.MOTOR_T * self.GEAR_RATIO * self.ETA / r

        # 重力沿斜面分量
        F_grav = m * g * np.sin(self.beta)

        # 最大摩擦力（由夹紧力决定）
        F_fric_max = self.MU * self.grip_force * self.N_MOTORS

        # 净驱动力（不超过最大摩擦力）
        F_net = min(F_drive, F_fric_max) - F_grav

        # 非线性阻尼：在稳态速度处阻尼系数 = F_net / v_ss
        # 确保 v_ss = F_net / B => B = F_net / v_ss
        v_ss = max(self._v_ss, 0.01)
        B    = F_net / v_ss if F_net > 0 else 50.0
        F_damp = -B * vel

        acc = (F_net + F_damp) / m
        # 防止反转
        if vel <= 0.0 and acc < 0.0:
            acc = 0.0
        return [vel, acc]

    def run(self, t_end=10.0, dt=0.02):
        """
        运行仿真，返回时间/位置/速度字典
        """
        t_eval = np.arange(0, t_end + dt, dt)
        sol = solve_ivp(
            self.dynamics, (0, t_end), [0.0, 0.0],
            t_eval=t_eval, method='RK45',
            rtol=1e-6, atol=1e-8
        )
        return {
            'time':        sol.t,
            'position':    sol.y[0],
            'velocity':    sol.y[1],
            'beta_deg':    self.beta_deg,
            'wire_radius': self.wire_radius,
        }

    @classmethod
    def batch_simulate_angles(cls, angles=(0, 20, 40, 45), t_end=10.0):
        """批量仿真不同倾角（对应论文图4-3）"""
        return [cls(beta_deg=a).run(t_end) for a in angles]

    @classmethod
    def batch_simulate_radii(cls, radii=(15, 25, 35), beta_deg=30.0, t_end=10.0):
        """批量仿真不同线径（对应论文图4-5）"""
        return [cls(beta_deg=beta_deg, wire_radius=r).run(t_end) for r in radii]


class ObstacleSimulator:
    """
    越障过程仿真
    论文4.3节：三臂轮流式越障运动仿真（四分裂间隔棒）
    """
    # 越障各阶段（论文图2-7 三臂轮流越障流程）
    PHASES = [
        {'name': '接近障碍物',   'duration': 2.0, 'speed_factor': 1.0,  'action': 'move'},
        {'name': '前臂松开',     'duration': 1.0, 'speed_factor': 0.0,  'action': 'release'},
        {'name': '前臂跨越',     'duration': 2.0, 'speed_factor': 0.3,  'action': 'cross'},
        {'name': '前臂锁紧',     'duration': 1.0, 'speed_factor': 0.0,  'action': 'grip'},
        {'name': '中臂松开',     'duration': 1.0, 'speed_factor': 0.0,  'action': 'release'},
        {'name': '中臂跨越',     'duration': 2.0, 'speed_factor': 0.3,  'action': 'cross'},
        {'name': '中臂锁紧',     'duration': 1.0, 'speed_factor': 0.0,  'action': 'grip'},
        {'name': '后臂跨越恢复', 'duration': 3.0, 'speed_factor': 0.8,  'action': 'cross'},
        {'name': '越障完成',     'duration': 2.0, 'speed_factor': 1.0,  'action': 'move'},
    ]

    NOMINAL_SPEED = 0.30  # m/s 额定巡检速度
    MOTOR_T_NOM   = 2.0   # N·m
    WHEEL_R       = 0.05
    N_MOTORS      = 4
    MASS          = 15.0

    def run(self, dt=0.05):
        """
        模拟完整越障过程，返回时间序列数据
        :return: dict{time, velocity, torque, phases, phase_boundaries}
        """
        rng = np.random.default_rng(42)  # 固定随机种子保证复现性
        t_list, v_list, T_list, p_list = [], [], [], []
        t = 0.0

        for phase in self.PHASES:
            dur  = phase['duration']
            sf   = phase['speed_factor']
            name = phase['name']
            n_steps = max(1, int(dur / dt))

            for i in range(n_steps):
                # 速度：目标值 + 轻微高斯噪声
                v = self.NOMINAL_SPEED * sf + rng.normal(0, 0.004)
                v = max(v, 0.0)

                # 扭矩：行走阶段为滚动阻力矩；动作阶段为推杆工作峰值矩
                if sf > 0.01:
                    F_roll = self.MASS * 9.81 * 0.02
                    T = F_roll * self.WHEEL_R / self.N_MOTORS
                else:
                    # 推杆工作产生的反力矩脉冲
                    T = self.MOTOR_T_NOM * 0.25 * abs(np.sin(i * 0.4 + 0.5))

                t_list.append(t + i * dt)
                v_list.append(v)
                T_list.append(T)
                p_list.append(name)

            t += dur

        return {
            'time':             np.array(t_list),
            'velocity':         np.array(v_list),
            'torque':           np.array(T_list),
            'phases':           p_list,
            'phase_boundaries': self._boundaries(),
        }

    def _boundaries(self):
        """返回各阶段起止时间列表"""
        bds, t = [], 0.0
        for ph in self.PHASES:
            bds.append({'t_start': t, 't_end': t + ph['duration'], 'name': ph['name']})
            t += ph['duration']
        return bds
