# -*- coding: utf-8 -*-
"""
模块一：参数化设计与计算模块
实现论文第3章核心数学模型（公式3-1 ~ 3-45）

本模块提供了高压线巡检机器人机构设计的核心计算功能，包括：
- 抱紧机构的推程计算
- 最小抱紧力计算（考虑防滑和支撑条件）
- 驱动电机选型计算（水平和爬坡工况）
- 关键部件（连杆）强度校核

所有计算结果均基于论文中的数学公式，参数单位已统一为SI单位制。
"""

import numpy as np

__author__ = "李豪"
__copyright__ = "Copyright 2026, 高压线巡检机器人平台"
__license__ = "MIT"
__version__ = "1.0.0"
__maintainer__ = "李豪"
__email__ = "your_email@example.com"
__status__ = "Production"  # "Production" or "Development"


class GripMechanismCalc:
    """
    抱紧机构计算类

    论文3.2节：抱紧机构参数计算
    实现基于四连杆机构的推杆行程和抱紧力计算

    功能：
    - 计算推杆行程S与高压线半径R的关系
    - 计算不同工况下的最小抱紧力（考虑防滑和支撑条件）
    - 生成抱紧力随半径和倾角变化的曲面数据

    注意：
    - 所有长度参数单位：mm（毫米）
    - 角度参数单位：度（°）
    - 力的单位：N（牛顿）

    示例：
    >>> # 计算R=25mm时的推程
    >>> stroke = GripMechanismCalc.calc_stroke_from_radius(25.0)
    >>> # 计算R=25mm, β=30°时的抱紧力
    >>> F = GripMechanismCalc.calc_grip_force(25.0, 30.0)
    >>> # 生成抱紧力曲面
    >>> R_mesh, B_mesh, F_mesh = GripMechanismCalc.calc_grip_force_surface(
    ...     range(15, 36, 5),
    ...     range(0, 46, 5)
    ... )
    """
    # 机构固定参数（单位：mm）
    L1 = 80.0      # 连杆1长度（从转轴到推杆铰点）
    L2 = 100.0     # 连杆2长度（驱动臂，从转轴到接触点）
    L3 = 60.0      # 连杆3长度
    L4 = 90.0      # 连杆4长度
    D  = 40.0      # 推杆安装偏距（推杆轴线到转轴的水平距离）
    WHEEL_R = 50.0 # 驱动轮半径（与导线接触的轮子半径）

    @classmethod
    def calc_stroke_from_radius(cls, R_values):
        """
        计算推杆推程S与高压线半径R的关系
        论文公式3-1 ~ 3-8
        几何关系：机器人夹持导线时，连杆张开角度随线径变化
        接触条件：L2 * sin(theta) = R + WHEEL_R
        推程 S = 2 * L1 * (cos(theta_min) - cos(theta))
        :param R_values: 高压线半径数组 (mm)
        :return: 推程S数组 (mm)
        """
        R = np.asarray(R_values, dtype=float)
        R_min = 10.0  # 最小线径，对应推程零点
        # 张开角由接触几何决定
        ratio = np.clip((R + cls.WHEEL_R) / cls.L2, -1.0, 1.0)
        theta = np.arcsin(ratio)
        ratio_min = np.clip((R_min + cls.WHEEL_R) / cls.L2, -1.0, 1.0)
        theta_min = np.arcsin(ratio_min)
        # 推程 = 连杆水平投影变化量 * 2（两侧对称）
        S = 2.0 * cls.L1 * (np.cos(theta_min) - np.cos(theta))
        return np.clip(S, 0, None)

    @classmethod
    def calc_grip_force(cls, R, beta_deg, weight=15.0, g=9.81):
        """
        计算最小抱紧力
        论文公式3-15 ~ 3-22
        平衡条件：沿线方向 n*mu*F_n >= W*sin(beta)
                 垂直方向 n*F_n >= W*cos(beta)
        :param R: 高压线半径 (mm)
        :param beta_deg: 高压线倾角 (度)
        :param weight: 机器人重量 (kg)
        :param g: 重力加速度
        :return: 所需最小抱紧力 F (N)
        """
        beta = np.radians(beta_deg)
        mu = 0.4   # 摩擦系数（橡胶轮对钢缆）
        n = 4      # 驱动轮数量
        W = weight * g
        # 防滑条件：法向力满足摩擦力需求
        F_n_slip    = W * np.sin(beta) / (n * mu) if np.sin(beta) > 0 else 0.0
        # 支撑条件：法向力满足支撑需求
        F_n_support = W * np.cos(beta) / n
        F_n = max(F_n_slip, F_n_support, 10.0)  # 最小10N保证接触
        # 通过连杆机构杠杆放大比传递到推杆
        lever_ratio = cls.L2 / cls.L1
        F_actuator = F_n * lever_ratio
        return F_actuator

    @classmethod
    def calc_grip_force_surface(cls, R_range, beta_range):
        """
        生成抱紧力曲面数据
        :param R_range: 半径范围数组
        :param beta_range: 倾角范围数组
        :return: (R_mesh, beta_mesh, F_mesh)
        """
        R_mesh, B_mesh = np.meshgrid(R_range, beta_range)
        F_mesh = np.vectorize(cls.calc_grip_force)(R_mesh, B_mesh)
        return R_mesh, B_mesh, F_mesh


class DriveMotorCalc:
    """
    驱动电机选型计算
    论文3.3节：驱动电机扭矩计算
    """
    WHEEL_R    = 0.05   # 驱动轮半径 (m)
    GEAR_RATIO = 30     # 减速比
    ETA        = 0.85   # 传动效率

    @classmethod
    def calc_torque_flat(cls, weight=15.0, mu_roll=0.02):
        """
        水平行走所需电机扭矩
        论文公式3-25 ~ 3-28
        """
        g = 9.81
        n_motors = 4
        F_total = weight * g * mu_roll
        F_per   = F_total / n_motors
        T_out   = F_per * cls.WHEEL_R
        T_motor = T_out / (cls.GEAR_RATIO * cls.ETA)
        return T_motor

    @classmethod
    def calc_torque_slope(cls, weight=15.0, beta_deg=45.0, mu_roll=0.02):
        """
        爬坡所需电机扭矩
        论文公式3-29 ~ 3-32
        """
        g = 9.81
        beta = np.radians(beta_deg)
        n_motors = 4
        F_grav = weight * g * np.sin(beta)
        F_fric = weight * g * np.cos(beta) * mu_roll
        F_per  = (F_grav + F_fric) / n_motors
        T_out  = F_per * cls.WHEEL_R
        T_motor = T_out / (cls.GEAR_RATIO * cls.ETA)
        return T_motor

    @classmethod
    def calc_torque_vs_angle(cls, weight=15.0, angles=None):
        """
        计算不同倾角下所需扭矩数组
        :return: (angles_array, torques_array)
        """
        if angles is None:
            angles = np.linspace(0, 45, 200)
        torques = np.array([cls.calc_torque_slope(weight, a) for a in angles])
        return angles, torques


class LinkStrengthCalc:
    """
    连杆强度校核（简化有限元分析）
    论文3.4节：关键部件强度计算
    """
    MATERIAL_YIELD = 235e6  # Q235钢屈服强度 (Pa)
    SAFETY_FACTOR  = 1.5

    @classmethod
    def calc_link_stress(cls, F_actuator, L_link=0.10, b=0.015, h=0.015):
        """
        连杆弯曲应力计算（简支梁中心受力模型）
        :param F_actuator: 推杆力 (N)
        :param L_link: 连杆长度 (m)
        :param b: 截面宽 (m)
        :param h: 截面高 (m)
        :return: dict 包含弯矩/应力/安全系数
        """
        M = F_actuator * L_link / 4.0      # 最大弯矩
        W = b * h**2 / 6.0                  # 抗弯截面系数
        sigma_max = M / W
        safety = cls.MATERIAL_YIELD / (sigma_max * cls.SAFETY_FACTOR)
        return {
            'bending_moment': M,
            'max_stress':     sigma_max,
            'safety_factor':  safety,
            'is_safe':        safety >= 1.0
        }

    @classmethod
    def calc_stress_distribution(cls, F_actuator, L_link=0.10, b=0.015, h=0.015, n_points=200):
        """
        连杆沿长度方向弯曲应力分布（简化FEM）
        :return: (x数组 in m, sigma数组 in Pa)
        """
        x = np.linspace(0, L_link, n_points)
        W = b * h**2 / 6.0
        # 简支梁集中力弯矩分布
        M = np.where(
            x <= L_link / 2,
            (F_actuator / 2.0) * x,
            (F_actuator / 2.0) * (L_link - x)
        )
        sigma = M / W
        return x, sigma
