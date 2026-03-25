# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, '.')

from modules.calculations import GripMechanismCalc, DriveMotorCalc, LinkStrengthCalc
from modules.simulation import ClimbingSimulator, ObstacleSimulator
from modules.knowledge_base import DESIGN_SPECS
from modules.control_interface import get_controller
import numpy as np

print('=== 模块导入测试 ===')
print('所有模块导入成功')

print('\n=== 计算模块测试 ===')
S = GripMechanismCalc.calc_stroke_from_radius([25])
print(f'推程测试 R=25mm -> S={S[0]:.2f} mm')

F = GripMechanismCalc.calc_grip_force(25, 30)
print(f'抱紧力测试 R=25,beta=30 -> F={F:.2f} N')

T = DriveMotorCalc.calc_torque_slope()
print(f'扭矩测试 beta=45 -> T={T*1000:.3f} mN.m')

info = LinkStrengthCalc.calc_link_stress(F * 0.5)
print(f'强度校核 -> sigma={info["max_stress"]/1e6:.3f} MPa, SF={info["safety_factor"]:.3f}')

print('\n=== 仿真模块测试 ===')
sim = ClimbingSimulator(beta_deg=30, wire_radius=25)
res = sim.run(t_end=3.0)
print(f'爬坡仿真 beta=30, t=3s -> 末速度={res["velocity"][-1]:.4f} m/s')

obs = ObstacleSimulator()
ores = obs.run()
print(f'越障仿真 -> 总时长={ores["time"][-1]:.1f}s, 阶段数={len(ores["phase_boundaries"])}')

print('\n=== 知识库测试 ===')
print(f'设计指标条目数: {len(DESIGN_SPECS)}')

print('\n=== 控制接口测试 ===')
ctrl = get_controller()
print(f'控制器模式: {ctrl.mode}')
ctrl.send_command('forward')
state = ctrl.get_state()
print(f'前进指令后速度: {state["speed"]} m/s')
ctrl.send_command('stop')

print('\n所有测试通过!')

