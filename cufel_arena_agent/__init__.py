"""
CUFEL Arena Agent SDK

为 CUFEL-Q Arena 平台提供标准化的 Agent 开发基类。

主要组件
--------
ETFAgentBase : class
    ETF Agent 基类，用于开发直接投资 ETF/股票的智能体
FOFAgentBase : class
    FOF Agent 基类，用于开发基金组合智能体
ArenaDataClient : class
    数据获取客户端，用于获取 Arena 平台中 ETF Agents 的历史数据
ConfigLoader : class
    配置加载器，用于管理数据库等配置信息

快速开始
--------
1. ETF Agent 开发

>>> from cufel_arena_agent import ETFAgentBase
>>>
>>> class MyETFAgent(ETFAgentBase):
...     def __init__(self):
...         super().__init__(name="MyETFAgent")
...
...     def load_current_data(self, curr_date):
...         # 加载数据
...         return data
...
...     def get_current_holdings(self, curr_date):
...         # 返回持仓
...         return {curr_date: {'510300': 0.5, '510500': 0.5}}

2. FOF Agent 开发

>>> from cufel_arena_agent import FOFAgentBase, ConfigLoader
>>>
>>> # 设置数据库配置（由 Arena 提供）
>>> ConfigLoader.set_database_config({...})
>>>
>>> class MyFOFAgent(FOFAgentBase):
...     def __init__(self):
...         super().__init__(name="MyFOFAgent")
...
...     def load_current_data(self, curr_date):
...         return self.get_etf_agents_nav(end_date=curr_date)
...
...     def get_current_holdings(self, curr_date):
...         # 返回对 ETF Agents 的配置权重
...         return {curr_date: {'Agent1': 0.5, 'Agent2': 0.5}}

版本信息
--------
- 版本: 1.0.0
- 兼容: Python >= 3.8
"""

__version__ = "1.0.0"
__author__ = "CUFEL-Q Arena Team"

# 核心基类
from .base import ETFAgentBase, FOFAgentBase

# 数据客户端
from .data_client import ArenaDataClient

# 配置管理
from .config import ConfigLoader, DatabaseConfig, AgentConfig

# 工具函数
from .utils import (
    validate_date_format,
    validate_holdings_format,
    validate_date_parameters,
)

__all__ = [
    # 核心基类
    "ETFAgentBase",
    "FOFAgentBase",
    # 数据客户端
    "ArenaDataClient",
    # 配置管理
    "ConfigLoader",
    "DatabaseConfig",
    "AgentConfig",
    # 工具函数
    "validate_date_format",
    "validate_holdings_format",
    "validate_date_parameters",
    # 版本信息
    "__version__",
]
