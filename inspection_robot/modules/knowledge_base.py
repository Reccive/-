# -*- coding: utf-8 -*-
"""
模块四：知识库与项目管理模块
整合论文研究成果、设计指标与设计方案管理

本模块提供了高压线巡检机器人的知识库管理功能，包括：
- 论文核心数据（表2-1设计指标、国内外研究综述）
- 设计方案的保存与加载（JSON格式）
- 实验记录的管理与查询

数据结构：
- 设计方案：包含参数、计算结果、备注信息
- 实验记录：包含测试数据、时间戳、对应方案
- 研究综述：国内外6个代表性机器人分析

文件管理：
- 数据目录：{项目根目录}/data/
- 设计方案文件格式：scheme_YYYYMMDD_HHMMSS.json
- 实验记录文件格式：exp_YYYYMMDD_HHMMSS.json

注意：
- 所有文件操作使用UTF-8编码
- 自动创建data目录（如不存在）
- 支持异常处理和文件损坏恢复
- 数据按时间倒序排列（最新的在前）

示例：
>>> # 保存设计方案
>>> scheme_id = save_design_scheme(
...     "基础方案",
...     {"R": 25.0, "beta": 30.0},
...     "初始设计方案"
... )
>>> # 加载所有方案
>>> schemes = load_all_schemes()
>>> # 保存实验记录
>>> record = {
...     "type": "climbing",
...     "duration": 10.0,
...     "results": {"max_speed": 0.34}
... }
>>> save_experiment_record(record)
"""

import json
import os
from datetime import datetime

__author__ = "李豪"
__copyright__ = "Copyright 2026, 高压线巡检机器人平台"
__license__ = "MIT"
__version__ = "1.0.0"
__maintainer__ = "李豪"
__status__ = "Production"

# ─────────────────────────────────────────────
# 论文表2-1：机器人设计指标
# ─────────────────────────────────────────────
DESIGN_SPECS = [
    {'指标项目': '适用线径范围',     '设计值': '30mm ~ 70mm',    '单位': 'mm',   '备注': '四分裂导线'},
    {'指标项目': '最大爬坡角度',     '设计值': '45',              '单位': '°',    '备注': '满载'},
    {'指标项目': '巡检速度',         '设计值': '0.3 ~ 1.0',      '单位': 'm/s',  '备注': '可调'},
    {'指标项目': '机器人总重量',     '设计值': '≤15',             '单位': 'kg',   '备注': '含检测设备'},
    {'指标项目': '驱动电机额定扭矩', '设计值': '2.0',             '单位': 'N·m',  '备注': '单电机'},
    {'指标项目': '电动推杆最大推力', '设计值': '500',             '单位': 'N',    '备注': '抱紧机构'},
    {'指标项目': '电动推杆推程',     '设计值': '0 ~ 80',          '单位': 'mm',   '备注': '适应线径变化'},
    {'指标项目': '续航时间',         '设计值': '≥4',              '单位': 'h',    '备注': '满电'},
    {'指标项目': '越障类型',         '设计值': '四分裂间隔棒',    '单位': '—',    '备注': '三臂轮流式'},
    {'指标项目': '防护等级',         '设计值': 'IP54',            '单位': '—',    '备注': '防尘防水'},
]

# ─────────────────────────────────────────────
# 国内外研究现状综述（论文第1章摘要）
# ─────────────────────────────────────────────
RESEARCH_REVIEW = [
    {
        'category': '国外代表性机器人',
        'items': [
            {'name': 'LineScout (加拿大 Hydro-Québec)',
             'features': '轮式，可越过间隔棒和悬垂线夹，搭载多种传感器，遥控操作',
             'drawback': '结构复杂，重量偏大'},
            {'name': 'Expliner (日本关西电力)',
             'features': '双臂夹持，行走轮+辅助轮组合，自动越障',
             'drawback': '仅适用于单导线'},
            {'name': 'TRAM (美国)',
             'features': '多关节臂，越障能力强',
             'drawback': '控制系统复杂'},
        ]
    },
    {
        'category': '国内代表性机器人',
        'items': [
            {'name': '武汉大学 巡线机器人',
             'features': '三臂结构，自主越障，搭载红外检测',
             'drawback': '样机阶段，可靠性待验证'},
            {'name': '山东大学 轮式巡检机器人',
             'features': '轮抱式夹持，适应多种线径',
             'drawback': '越障动作速度较慢'},
            {'name': '本论文提出的轮抱式机器人',
             'features': '三臂轮流越障、推杆抱紧自适应线径、结构紧凑',
             'drawback': '—'},
        ]
    },
]

# ─────────────────────────────────────────────
# 项目方案管理（本地JSON文件）
# ─────────────────────────────────────────────
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')


def _ensure_data_dir():
    os.makedirs(DATA_DIR, exist_ok=True)


def save_design_scheme(name: str, params: dict, notes: str = '') -> str:
    """保存设计方案到JSON文件"""
    _ensure_data_dir()
    scheme = {
        'name': name,
        'created_at': datetime.now().isoformat(),
        'params': params,
        'notes': notes
    }
    filename = f"scheme_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    filepath = os.path.join(DATA_DIR, filename)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(scheme, f, ensure_ascii=False, indent=2)
    return filepath


def load_all_schemes() -> list:
    """加载所有已保存的设计方案"""
    _ensure_data_dir()
    schemes = []
    for fname in os.listdir(DATA_DIR):
        if fname.startswith('scheme_') and fname.endswith('.json'):
            fpath = os.path.join(DATA_DIR, fname)
            try:
                with open(fpath, 'r', encoding='utf-8') as f:
                    schemes.append(json.load(f))
            except Exception:
                pass
    schemes.sort(key=lambda x: x.get('created_at', ''), reverse=True)
    return schemes


def save_experiment_record(record: dict) -> str:
    """保存实验记录（对应论文表5-2）"""
    _ensure_data_dir()
    filename = f"exp_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    filepath = os.path.join(DATA_DIR, filename)
    record['saved_at'] = datetime.now().isoformat()
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(record, f, ensure_ascii=False, indent=2)
    return filepath


def load_all_experiments() -> list:
    """加载所有实验记录"""
    _ensure_data_dir()
    records = []
    for fname in os.listdir(DATA_DIR):
        if fname.startswith('exp_') and fname.endswith('.json'):
            fpath = os.path.join(DATA_DIR, fname)
            try:
                with open(fpath, 'r', encoding='utf-8') as f:
                    records.append(json.load(f))
            except Exception:
                pass
    records.sort(key=lambda x: x.get('saved_at', ''), reverse=True)
    return records

