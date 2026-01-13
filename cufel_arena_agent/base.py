"""
Agent 基类模块

提供 ETFAgentBase 和 FOFAgentBase 两个抽象基类，
用于规范化 Arena 平台中智能体的开发。

主要特点：
- 简化的接口：仅需实现 load_current_data() 和 get_current_holdings() 两个方法
- FOF Agent 可直接获取 ETF Agents 数据
- 自动日期格式验证
"""

from abc import ABC, abstractmethod, ABCMeta
from typing import Dict, Any, Optional, List, Annotated
import inspect

from .utils import auto_validate, validate_holdings_format
from .config import DatabaseConfig, ConfigLoader
from .data_client import ArenaDataClient


class SignatureMeta(ABCMeta):
    """
    元类：强制派生类方法签名与基类匹配

    确保所有继承类实现的抽象方法具有相同的参数签名，
    避免因参数名称不一致导致的问题。
    """

    def __init__(cls, name, bases, attrs, **kwargs):
        super().__init__(name, bases, attrs, **kwargs)

        # 跳过基类检查
        if not bases:
            return

        # 获取基类
        for base in bases:
            if not hasattr(base, '_abc_impl'):
                continue

            # 检查所有抽象方法
            for method_name, attr in base.__dict__.items():
                if not getattr(attr, "__isabstractmethod__", False):
                    continue

                # 获取基类方法签名
                base_sig = inspect.signature(attr)

                # 获取派生类方法
                derived_method = getattr(cls, method_name, None)
                if derived_method is None:
                    continue

                # 获取派生类方法签名
                derived_sig = inspect.signature(derived_method)

                # 比较参数（跳过 self）
                base_params = list(base_sig.parameters.values())[1:]
                derived_params = list(derived_sig.parameters.values())[1:]

                # 检查参数数量
                if len(base_params) != len(derived_params):
                    raise TypeError(
                        f"Class {cls.__name__}: Method {method_name} has {len(derived_params)} parameters, "
                        f"but base class requires {len(base_params)}"
                    )

                # 检查参数名称
                for i, (base_param, derived_param) in enumerate(zip(base_params, derived_params)):
                    if base_param.name != derived_param.name:
                        raise TypeError(
                            f"Class {cls.__name__}: Parameter {i+1} in {method_name} is named '{derived_param.name}', "
                            f"but base class requires '{base_param.name}'"
                        )


@auto_validate
class ETFAgentBase(ABC, metaclass=SignatureMeta):
    """
    ETF Agent 基类

    用于开发直接投资 ETF 的智能体。
    开发者只需实现两个核心方法：
    - load_current_data(): 加载当前日期所需的数据
    - get_current_holdings(): 返回当前日期的持仓

    数据获取需要配合 quantchdb 库使用 ClickHouse 数据库。

    属性
    ----
    name : str
        Agent 名称
    agent_type : str
        Agent 类型，固定为 'ETF'
    db_config : dict
        ClickHouse 数据库配置字典，用于 quantchdb

    方法
    ----
    load_current_data(curr_date)
        加载当前日期所需的数据（抽象方法，必须实现）
    get_current_holdings(curr_date, feedback=None, theta=None)
        返回当前日期的持仓（抽象方法，必须实现）
    get_daily_holdings(start_date, end_date)
        返回日期范围内的每日持仓（可选重写）
    """

    def __init__(self,
                 name: str = None,
                 db_config: Dict[str, str] = None):
        """
        初始化 ETF Agent

        Parameters
        ----------
        name : str, optional
            Agent 名称。如果不指定，将使用类名
        db_config : dict, optional
            ClickHouse 数据库配置。如果不指定，将使用全局配置。
            配置字典应包含: host, port, user, password, database
        """
        self.name = name or self.__class__.__name__
        self.agent_type = "ETF"
        self._db_config = db_config

    @property
    def db_config(self) -> Dict[str, str]:
        """
        获取 ClickHouse 数据库配置

        优先使用实例配置，如果没有则使用全局配置。
        返回的配置字典可直接用于 quantchdb.ClickHouseDatabase

        Returns
        -------
        dict
            数据库配置字典，包含 host, port, user, password, database

        Raises
        ------
        ValueError
            如果没有配置数据库连接信息
        """
        if self._db_config is not None:
            return self._db_config

        # 尝试从全局配置获取
        global_config = ConfigLoader.get_clickhouse_config()
        if global_config is not None:
            return global_config.to_dict()

        raise ValueError(
            "ClickHouse database config not provided. Please either:\n"
            "1. Pass db_config to ETFAgentBase(db_config={...})\n"
            "2. Set global config via ConfigLoader.set_clickhouse_config({...})\n"
            "3. Set environment variables with ARENA_CH_ prefix"
        )

    @abstractmethod
    def load_current_data(self,
                          curr_date: Annotated[str, "current date in 'YYYY-MM-DD'"]) -> Any:
        """
        加载当前日期所需的数据

        此方法应加载计算当前日期持仓所需的所有数据，
        包括历史价格、因子数据、宏观数据等。

        Parameters
        ----------
        curr_date : str
            当前日期，格式为 'YYYY-MM-DD'

        Returns
        -------
        Any
            加载的数据，格式由具体实现决定
        """
        pass

    @abstractmethod
    def get_current_holdings(self,
                             curr_date: Annotated[str, "current date in 'YYYY-MM-DD'"],
                             feedback: Annotated[str, "FOFAgent feedback information"] = None,
                             theta: Annotated[float, "风险偏好系数"] = None) -> Dict[str, Dict[str, float]]:
        """
        获取当前日期的持仓

        返回当前日期的资产配置权重。

        Parameters
        ----------
        curr_date : str
            当前日期，格式为 'YYYY-MM-DD'
        feedback : str, optional
            来自 FOF Agent 的反馈信息（如果有）
        theta : float, optional
            风险偏好系数

        Returns
        -------
        dict
            持仓字典，格式为:
            {
                'YYYY-MM-DD': {
                    'asset_code_1': weight_1,
                    'asset_code_2': weight_2,
                    ...
                }
            }

            约束条件：
            - 所有权重必须非负
            - 权重总和不超过 1（允许持有现金）

        示例
        ----
        >>> agent.get_current_holdings('2025-01-15')
        {'2025-01-15': {'510300': 0.5, '510500': 0.3, '159915': 0.2}}
        """
        pass

    def get_daily_holdings(self,
                           start_date: Annotated[str, "start date in 'YYYY-MM-DD'"],
                           end_date: Annotated[str, "end date in 'YYYY-MM-DD'"],
                           theta: Annotated[float, "风险偏好系数"] = None) -> Dict[str, Dict[str, float]]:
        """
        获取日期范围内的每日持仓

        默认实现：遍历日期范围，调用 get_current_holdings()。
        如果有更高效的实现方式，可以重写此方法。

        Parameters
        ----------
        start_date : str
            开始日期，格式为 'YYYY-MM-DD'
        end_date : str
            结束日期，格式为 'YYYY-MM-DD'
        theta : float, optional
            风险偏好系数

        Returns
        -------
        dict
            每日持仓字典，格式为:
            {
                'YYYY-MM-DD': {'code': weight, ...},
                'YYYY-MM-DD': {'code': weight, ...},
                ...
            }
        """
        import pandas as pd

        date_range = pd.date_range(start=start_date, end=end_date)
        daily_holdings = {}

        for single_date in date_range:
            date_str = single_date.strftime('%Y-%m-%d')
            holdings = self.get_current_holdings(date_str, theta=theta)
            if holdings and date_str in holdings:
                daily_holdings[date_str] = holdings[date_str]

        return daily_holdings

    def validate_holdings(self, holdings: Dict) -> bool:
        """
        验证持仓格式是否正确

        Parameters
        ----------
        holdings : dict
            待验证的持仓数据

        Returns
        -------
        bool
            验证是否通过
        """
        return validate_holdings_format(holdings)


@auto_validate
class FOFAgentBase(ABC, metaclass=SignatureMeta):
    """
    FOF Agent 基类

    用于开发基金组合（Fund of Funds）智能体，
    即投资于其他 ETF Agents 的智能体。

    内置数据获取功能，可直接获取 ETF Agents 的历史数据。

    属性
    ----
    name : str
        Agent 名称
    agent_type : str
        Agent 类型，固定为 'FOF'
    data_client : ArenaDataClient
        数据获取客户端，用于获取 ETF Agents 数据
    target_agents : list
        目标 ETF Agents 列表（可选）

    方法
    ----
    load_current_data(curr_date)
        加载当前日期所需的数据（抽象方法，必须实现）
    get_current_holdings(curr_date, feedback=None, theta=None)
        返回当前日期的持仓（抽象方法，必须实现）
    get_daily_holdings(start_date, end_date)
        返回日期范围内的每日持仓（可选重写）
    get_etf_agents_nav(...)
        获取 ETF Agents 净值数据（便捷方法）
    get_etf_agents_returns(...)
        获取 ETF Agents 收益率数据（便捷方法）
    """

    def __init__(self,
                 name: str = None,
                 db_config: Dict[str, str] = None,
                 target_agents: List[str] = None):
        """
        初始化 FOF Agent

        Parameters
        ----------
        name : str, optional
            Agent 名称。如果不指定，将使用类名
        db_config : dict, optional
            PostgreSQL 数据库配置。如果不指定，将使用全局配置。
            配置字典应包含: host, port, user, password, database
        target_agents : list, optional
            目标 ETF Agents 列表。如果不指定，将获取所有 ETF Agents
        """
        self.name = name or self.__class__.__name__
        self.agent_type = "FOF"
        self.target_agents = target_agents
        self._data_client = None
        self._db_config = db_config

    @property
    def data_client(self) -> ArenaDataClient:
        """
        获取数据客户端（延迟初始化）

        Returns
        -------
        ArenaDataClient
            数据获取客户端
        """
        if self._data_client is None:
            self._data_client = ArenaDataClient(db_config=self._db_config)
        return self._data_client

    @abstractmethod
    def load_current_data(self,
                          curr_date: Annotated[str, "current date in 'YYYY-MM-DD'"]) -> Any:
        """
        加载当前日期所需的数据

        此方法应加载计算当前日期持仓所需的所有数据。
        可使用 self.data_client 获取 ETF Agents 的历史数据。

        Parameters
        ----------
        curr_date : str
            当前日期，格式为 'YYYY-MM-DD'

        Returns
        -------
        Any
            加载的数据，格式由具体实现决定
        """
        pass

    @abstractmethod
    def get_current_holdings(self,
                             curr_date: Annotated[str, "current date in 'YYYY-MM-DD'"],
                             feedback: Annotated[str, "Other FOFAgent feedback information"] = None,
                             theta: Annotated[float, "风险偏好系数"] = None) -> Dict[str, Dict[str, float]]:
        """
        获取当前日期的持仓（对 ETF Agents 的配置权重）

        返回当前日期对各 ETF Agents 的配置权重。

        Parameters
        ----------
        curr_date : str
            当前日期，格式为 'YYYY-MM-DD'
        feedback : str, optional
            来自其他 FOF Agent 的反馈信息（如果有）
        theta : float, optional
            风险偏好系数

        Returns
        -------
        dict
            持仓字典，格式为:
            {
                'YYYY-MM-DD': {
                    'ETF_Agent_1': weight_1,
                    'ETF_Agent_2': weight_2,
                    ...
                }
            }

            约束条件：
            - 所有权重必须非负
            - 权重总和不超过 1（允许持有现金）

        示例
        ----
        >>> agent.get_current_holdings('2025-01-15')
        {'2025-01-15': {'Qwhen_o1': 0.4, 'MyAgent': 0.3, 'Benchmark': 0.3}}
        """
        pass

    def get_daily_holdings(self,
                           start_date: Annotated[str, "start date in 'YYYY-MM-DD'"],
                           end_date: Annotated[str, "end date in 'YYYY-MM-DD'"],
                           theta: Annotated[float, "风险偏好系数"] = None) -> Dict[str, Dict[str, float]]:
        """
        获取日期范围内的每日持仓

        默认实现：遍历日期范围，调用 get_current_holdings()。
        如果有更高效的实现方式，可以重写此方法。

        Parameters
        ----------
        start_date : str
            开始日期，格式为 'YYYY-MM-DD'
        end_date : str
            结束日期，格式为 'YYYY-MM-DD'
        theta : float, optional
            风险偏好系数

        Returns
        -------
        dict
            每日持仓字典
        """
        import pandas as pd

        date_range = pd.date_range(start=start_date, end=end_date)
        daily_holdings = {}

        for single_date in date_range:
            date_str = single_date.strftime('%Y-%m-%d')
            holdings = self.get_current_holdings(date_str, theta=theta)
            if holdings and date_str in holdings:
                daily_holdings[date_str] = holdings[date_str]

        return daily_holdings

    # ==================== 便捷数据获取方法 ====================

    def get_etf_agents_nav(self,
                           agent_names: List[str] = None,
                           start_date: str = None,
                           end_date: str = None,
                           fillna_method: str = 'ffill'):
        """
        获取 ETF Agents 净值数据

        Parameters
        ----------
        agent_names : list, optional
            Agent 名称列表。如果为 None，使用 target_agents
        start_date : str, optional
            开始日期
        end_date : str, optional
            结束日期
        fillna_method : str, optional
            缺失值填充方法

        Returns
        -------
        pd.DataFrame
            净值数据宽表
        """
        return self.data_client.get_multi_agents_nav(
            agent_names=agent_names,
            start_date=start_date,
            end_date=end_date,
            fillna_method=fillna_method
        )

    def get_etf_agents_returns(self,
                               agent_names: List[str] = None,
                               start_date: str = None,
                               end_date: str = None,
                               fillna_value: float = 0.0):
        """
        获取 ETF Agents 日收益率数据

        Parameters
        ----------
        agent_names : list, optional
            Agent 名称列表。如果为 None，使用 target_agents
        start_date : str, optional
            开始日期
        end_date : str, optional
            结束日期
        fillna_value : float, optional
            缺失值填充值

        Returns
        -------
        pd.DataFrame
            收益率数据宽表
        """
        return self.data_client.get_multi_agents_returns(
            agent_names=agent_names,
            start_date=start_date,
            end_date=end_date,
            fillna_value=fillna_value
        )

    def get_etf_agents_positions(self,
                                 agent_names: List[str] = None,
                                 target_date: str = None):
        """
        获取 ETF Agents 的持仓权重

        Parameters
        ----------
        agent_names : list, optional
            Agent 名称列表。如果为 None，使用 target_agents
        target_date : str, optional
            目标日期。如果为 None，获取最新持仓

        Returns
        -------
        dict
            各 Agent 的持仓数据 {agent_name: {code: weight, ...}, ...}
        """
        if agent_names is None:
            agent_names = self.target_agents

        return self.data_client.get_agents_positions_for_date(
            agent_names=agent_names,
            agent_type='ETF',
            target_date=target_date
        )

    def get_all_etf_agents_info(self):
        """
        获取所有 ETF Agents 的基础信息

        Returns
        -------
        pd.DataFrame
            Agent 信息表
        """
        return self.data_client.get_all_agents(agent_type='ETF')

    def validate_holdings(self, holdings: Dict) -> bool:
        """
        验证持仓格式是否正确

        Parameters
        ----------
        holdings : dict
            待验证的持仓数据

        Returns
        -------
        bool
            验证是否通过
        """
        return validate_holdings_format(holdings)
