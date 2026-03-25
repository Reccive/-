# -*- coding: utf-8 -*-
"""
模块三：样机测试与数据采集模块（串口控制接口）
论文第5章：物理样机实验支撑

本模块实现了高压线巡检机器人的控制接口和数据采集功能，包括：
- 串口通信控制（连接物理样机）
- 虚拟模式仿真（无硬件时使用）
- 实时数据记录与日志管理
- 控制指令发送与状态反馈

通信协议：
- 支持USB转串口连接
- 波特率：115200 bps
- 数据位：8，停止位：1，校验位：无
- 二进制指令格式（CMD_MAP）

虚拟模式：
- 默认模式，无需硬件即可测试软件功能
- 模拟机器人运动状态更新
- 记录虚拟数据用于后续分析

注意：
- 本模块实现了单例模式，通过get_controller()获取实例
- 虚拟模式下位置更新频率为50ms
- 数据记录支持自动开始和手动停止
"""

import time
import threading
from datetime import datetime

__author__ = "李豪"
__copyright__ = "Copyright 2026, 高压线巡检机器人平台"
__license__ = "MIT"
__version__ = "1.0.0"
__maintainer__ = "李豪"
__status__ = "Production"


class RobotController:
    """
    机器人控制器
    支持串口（USB）和虚拟模式两种方式
    """

    CMD_MAP = {
        'forward':      b'\x01\x01',
        'backward':     b'\x01\x02',
        'stop':         b'\x01\x00',
        'grip_open':    b'\x02\x01',
        'grip_close':   b'\x02\x00',
        'speed_up':     b'\x03\x01',
        'speed_down':   b'\x03\x02',
        'cam_front':    b'\x04\x01',
        'cam_rear':     b'\x04\x02',
        'obstacle_seq': b'\x05\x01',  # 自动越障序列
    }

    def __init__(self):
        self._connected = False
        self._virtual = True      # 默认虚拟模式
        self._serial = None
        self._lock = threading.Lock()
        # 虚拟状态
        self._virtual_state = {
            'speed': 0.0,          # m/s
            'position': 0.0,       # m
            'grip': 'closed',      # open / closed
            'moving': False,
            'direction': 'stopped',
            'voltage': 24.0,       # V
            'current': 0.0,        # A
        }
        self._data_log = []        # 实验数据记录
        self._log_active = False
        self._sim_thread = None

    # ── 连接管理 ──────────────────────────────────
    def connect_serial(self, port: str, baudrate: int = 115200) -> bool:
        """尝试连接串口，失败则保持虚拟模式"""
        try:
            import serial
            self._serial = serial.Serial(port, baudrate, timeout=0.5)
            self._connected = True
            self._virtual = False
            return True
        except Exception as e:
            self._connected = False
            self._virtual = True
            return False

    def disconnect(self):
        """断开连接"""
        if self._serial and self._serial.is_open:
            self._serial.close()
        self._connected = False
        self._virtual = True
        self._stop_virtual_sim()

    @property
    def is_connected(self):
        return self._connected or self._virtual

    @property
    def mode(self):
        return '虚拟模式' if self._virtual else '硬件连接'

    # ── 指令发送 ──────────────────────────────────
    def send_command(self, cmd_name: str) -> bool:
        """发送控制指令"""
        if cmd_name not in self.CMD_MAP:
            return False
        if self._virtual:
            self._handle_virtual_cmd(cmd_name)
            return True
        # 真实串口模式
        try:
            with self._lock:
                self._serial.write(self.CMD_MAP[cmd_name])
            return True
        except Exception:
            return False

    def _handle_virtual_cmd(self, cmd: str):
        """处理虚拟模式下的指令"""
        s = self._virtual_state
        if cmd == 'forward':
            s['moving'] = True
            s['direction'] = 'forward'
            s['speed'] = 0.3
            s['current'] = 1.2
            self._start_virtual_sim()
        elif cmd == 'backward':
            s['moving'] = True
            s['direction'] = 'backward'
            s['speed'] = 0.3
            s['current'] = 1.2
            self._start_virtual_sim()
        elif cmd == 'stop':
            s['moving'] = False
            s['direction'] = 'stopped'
            s['speed'] = 0.0
            s['current'] = 0.2
            self._stop_virtual_sim()
        elif cmd == 'grip_open':
            s['grip'] = 'open'
            s['current'] = 2.0
        elif cmd == 'grip_close':
            s['grip'] = 'closed'
            s['current'] = 2.0
        elif cmd == 'speed_up':
            s['speed'] = min(s['speed'] + 0.1, 1.0)
        elif cmd == 'speed_down':
            s['speed'] = max(s['speed'] - 0.1, 0.0)

    def _start_virtual_sim(self):
        """启动虚拟位置更新线程"""
        self._stop_virtual_sim()
        self._running = True
        self._sim_thread = threading.Thread(target=self._sim_loop, daemon=True)
        self._sim_thread.start()

    def _stop_virtual_sim(self):
        self._running = False
        if self._sim_thread and self._sim_thread.is_alive():
            self._sim_thread.join(timeout=0.5)

    def _sim_loop(self):
        """虚拟位置更新循环（50ms间隔）"""
        while self._running:
            s = self._virtual_state
            if s['moving']:
                dt = 0.05
                if s['direction'] == 'forward':
                    s['position'] += s['speed'] * dt
                elif s['direction'] == 'backward':
                    s['position'] -= s['speed'] * dt
                # 记录日志
                if self._log_active:
                    self._data_log.append({
                        'timestamp': datetime.now().isoformat(),
                        'position':  round(s['position'], 4),
                        'speed':     round(s['speed'], 3),
                        'voltage':   round(s['voltage'], 2),
                        'current':   round(s['current'], 3),
                        'grip':      s['grip'],
                        'direction': s['direction'],
                    })
            time.sleep(0.05)

    # ── 数据读取 ──────────────────────────────────
    def get_state(self) -> dict:
        """获取当前机器人状态"""
        return dict(self._virtual_state)

    # ── 数据记录 ──────────────────────────────────
    def start_logging(self):
        """开始记录实验数据"""
        self._data_log.clear()
        self._log_active = True

    def stop_logging(self) -> list:
        """停止记录并返回数据"""
        self._log_active = False
        return list(self._data_log)

    def get_log(self) -> list:
        return list(self._data_log)


# 全局单例
_controller_instance = None


def get_controller() -> RobotController:
    global _controller_instance
    if _controller_instance is None:
        _controller_instance = RobotController()
    return _controller_instance
