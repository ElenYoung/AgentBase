"""
Arena 数据客户端

提供获取 Arena 平台中 ETF Agents 历史数据的功能，
主要用于 FOF Agents 构建 ETF Agents 的赋权组合。

支持的数据：
- Agent 基础信息（agent_pool）
- 日频净值（daily_nav）
- 每日持仓（daily_positions）
- 回测指标（backtest_res）
"""

import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, List, Optional, Any, Union

from .config import DatabaseConfig, ConfigLoader


class ArenaDataClient:
    """
    Arena 数据客户端

    用于获取 Arena 平台中 ETF Agents 的历史数据，
    供 FOF Agents 开发者使用。

    使用示例
    --------
    >>> from cufel_arena_agent import ArenaDataClient, ConfigLoader
    >>>
    >>> # 方式1：使用全局配置
    >>> ConfigLoader.set_database_config({
    ...     "host": "your_host",
    ...     "port": "5432",
    ...     "user": "your_user",
    ...     "password": "your_password",
    ...     "database": "arena"
    ... })
    >>> client = ArenaDataClient()
    >>>
    >>> # 方式2：直接传入配置
    >>> client = ArenaDataClient(db_config={...})
    >>>
    >>> # 获取所有 ETF Agents
    >>> agents = client.get_all_agents(agent_type='ETF')
    >>>
    >>> # 获取净值数据
    >>> nav_df = client.get_multi_agents_nav(['Agent1', 'Agent2'])
    """

    def __init__(self, db_config: Optional[Dict[str, str]] = None):
        """
        初始化数据客户端

        Parameters
        ----------
        db_config : dict, optional
            数据库配置字典。如果不传入，将使用全局配置。
        """
        if db_config:
            self._db_config = DatabaseConfig.from_dict(db_config)
        else:
            self._db_config = ConfigLoader.get_database_config()

        if self._db_config is None:
            raise ValueError(
                "Database config not provided. Please either:\n"
                "1. Pass db_config to ArenaDataClient(db_config={...})\n"
                "2. Set global config via ConfigLoader.set_database_config({...})\n"
                "3. Set environment variables with ARENA_DB_ prefix"
            )

        self._db_config.validate()
        self._connection = None

    def _get_connection(self):
        """获取数据库连接"""
        try:
            import psycopg2
        except ImportError:
            raise ImportError(
                "psycopg2 is required for database connection. "
                "Install it with: pip install psycopg2-binary"
            )

        if self._connection is None or self._connection.closed:
            config = self._db_config.to_dict()
            self._connection = psycopg2.connect(
                host=config['host'],
                port=config['port'],
                database=config['database'],
                user=config['user'],
                password=config['password']
            )
        return self._connection

    def _close_connection(self):
        """关闭数据库连接"""
        if self._connection and not self._connection.closed:
            self._connection.close()
            self._connection = None

    def _execute_query(self, query: str, params: tuple = None) -> List:
        """
        执行 SQL 查询

        Parameters
        ----------
        query : str
            SQL 查询语句
        params : tuple, optional
            查询参数

        Returns
        -------
        list
            查询结果
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(query, params)
            result = cursor.fetchall()
            return result
        except Exception as e:
            raise e
        finally:
            cursor.close()

    # ==================== Agent Pool 查询 ====================

    def get_all_agents(self, agent_type: str = None) -> pd.DataFrame:
        """
        获取所有 Agent 的基础信息

        Parameters
        ----------
        agent_type : str, optional
            Agent 类型过滤，如 'ETF', 'FOF'。默认返回所有类型

        Returns
        -------
        pd.DataFrame
            Agent 信息表，包含 agent_id, agent_name, type, agent_dirname,
            other_info, created_at, update_at
        """
        query = """
            SELECT agent_id, agent_name, type, agent_dirname, other_info, created_at, update_at
            FROM arena.agent_pool
        """
        params = None

        if agent_type:
            query += " WHERE type = %s"
            params = (agent_type,)

        query += " ORDER BY agent_id"

        result = self._execute_query(query, params)

        if result:
            df = pd.DataFrame(result, columns=[
                'agent_id', 'agent_name', 'type', 'agent_dirname',
                'other_info', 'created_at', 'update_at'
            ])
            return df

        return pd.DataFrame(columns=[
            'agent_id', 'agent_name', 'type', 'agent_dirname',
            'other_info', 'created_at', 'update_at'
        ])

    def get_agent_names(self, agent_type: str = None) -> List[str]:
        """
        获取所有 Agent 名称列表

        Parameters
        ----------
        agent_type : str, optional
            Agent 类型过滤

        Returns
        -------
        list
            Agent 名称列表
        """
        query = "SELECT agent_name FROM arena.agent_pool"
        params = None

        if agent_type:
            query += " WHERE type = %s"
            params = (agent_type,)

        query += " ORDER BY agent_id"

        result = self._execute_query(query, params)
        return [row[0] for row in result] if result else []

    def get_agent_id(self, agent_name: str) -> Optional[int]:
        """
        根据 agent_name 获取 agent_id

        Parameters
        ----------
        agent_name : str
            Agent 名称

        Returns
        -------
        int or None
            Agent ID，如果不存在则返回 None
        """
        result = self._execute_query(
            "SELECT agent_id FROM arena.agent_pool WHERE agent_name = %s",
            (agent_name,)
        )
        return result[0][0] if result else None

    def get_agent_info(self, agent_name: str) -> Optional[Dict]:
        """
        获取单个 Agent 的完整信息

        Parameters
        ----------
        agent_name : str
            Agent 名称

        Returns
        -------
        dict or None
            Agent 信息字典
        """
        result = self._execute_query(
            """
            SELECT agent_id, agent_name, type, agent_dirname, other_info, created_at, update_at
            FROM arena.agent_pool WHERE agent_name = %s
            """,
            (agent_name,)
        )
        if result:
            row = result[0]
            return {
                'agent_id': row[0],
                'agent_name': row[1],
                'type': row[2],
                'agent_dirname': row[3],
                'other_info': row[4],
                'created_at': row[5],
                'update_at': row[6]
            }
        return None

    # ==================== Daily NAV 查询 ====================

    def get_agent_nav(self,
                      agent_name: str,
                      start_date: str = None,
                      end_date: str = None) -> pd.Series:
        """
        获取单个 Agent 的净值序列

        Parameters
        ----------
        agent_name : str
            Agent 名称
        start_date : str, optional
            开始日期 'YYYY-MM-DD'
        end_date : str, optional
            结束日期 'YYYY-MM-DD'

        Returns
        -------
        pd.Series
            净值序列，index 为日期
        """
        agent_id = self.get_agent_id(agent_name)
        if agent_id is None:
            return pd.Series(dtype=float, name=agent_name)

        query = "SELECT date, nav FROM arena.daily_nav WHERE agent_id = %s"
        params = [agent_id]

        if start_date:
            query += " AND date >= %s"
            params.append(start_date)
        if end_date:
            query += " AND date <= %s"
            params.append(end_date)

        query += " ORDER BY date"

        result = self._execute_query(query, tuple(params))

        if result:
            dates = [row[0] for row in result]
            navs = [float(row[1]) for row in result]
            return pd.Series(navs, index=pd.to_datetime(dates), name=agent_name)

        return pd.Series(dtype=float, name=agent_name)

    def get_agent_returns(self,
                          agent_name: str,
                          start_date: str = None,
                          end_date: str = None) -> pd.Series:
        """
        获取单个 Agent 的日收益率序列

        Parameters
        ----------
        agent_name : str
            Agent 名称
        start_date : str, optional
            开始日期 'YYYY-MM-DD'
        end_date : str, optional
            结束日期 'YYYY-MM-DD'

        Returns
        -------
        pd.Series
            日收益率序列，index 为日期
        """
        agent_id = self.get_agent_id(agent_name)
        if agent_id is None:
            return pd.Series(dtype=float, name=agent_name)

        query = "SELECT date, ret FROM arena.daily_nav WHERE agent_id = %s"
        params = [agent_id]

        if start_date:
            query += " AND date >= %s"
            params.append(start_date)
        if end_date:
            query += " AND date <= %s"
            params.append(end_date)

        query += " ORDER BY date"

        result = self._execute_query(query, tuple(params))

        if result:
            dates = [row[0] for row in result]
            rets = [float(row[1]) if row[1] is not None else 0.0 for row in result]
            return pd.Series(rets, index=pd.to_datetime(dates), name=agent_name)

        return pd.Series(dtype=float, name=agent_name)

    def get_multi_agents_nav(self,
                             agent_names: List[str] = None,
                             agent_type: str = None,
                             start_date: str = None,
                             end_date: str = None,
                             fillna_method: str = None) -> pd.DataFrame:
        """
        获取多个 Agent 的净值数据（宽表格式）

        Parameters
        ----------
        agent_names : list, optional
            Agent 名称列表。如果为 None，则获取所有 Agent
        agent_type : str, optional
            Agent 类型过滤（仅当 agent_names 为 None 时生效）
        start_date : str, optional
            开始日期 'YYYY-MM-DD'
        end_date : str, optional
            结束日期 'YYYY-MM-DD'
        fillna_method : str, optional
            缺失值填充方法：'ffill' 向前填充, 'bfill' 向后填充, None 不填充

        Returns
        -------
        pd.DataFrame
            净值数据表，columns 为 agent_name，index 为日期
        """
        if agent_names is None:
            agent_names = self.get_agent_names(agent_type)

        if not agent_names:
            return pd.DataFrame()

        query = """
            SELECT n.date, p.agent_name, n.nav
            FROM arena.daily_nav n
            JOIN arena.agent_pool p ON n.agent_id = p.agent_id
            WHERE p.agent_name = ANY(%s)
        """
        params = [agent_names]

        if start_date:
            query += " AND n.date >= %s"
            params.append(start_date)
        if end_date:
            query += " AND n.date <= %s"
            params.append(end_date)

        query += " ORDER BY n.date, p.agent_name"

        result = self._execute_query(query, tuple(params))

        if not result:
            return pd.DataFrame(columns=agent_names)

        df = pd.DataFrame(result, columns=['date', 'agent_name', 'nav'])
        df['date'] = pd.to_datetime(df['date'])
        df['nav'] = df['nav'].astype(float)

        nav_df = df.pivot(index='date', columns='agent_name', values='nav')
        nav_df = nav_df.reindex(columns=[n for n in agent_names if n in nav_df.columns])

        if fillna_method:
            if fillna_method == 'ffill':
                nav_df = nav_df.ffill()
            elif fillna_method == 'bfill':
                nav_df = nav_df.bfill()

        return nav_df

    def get_multi_agents_returns(self,
                                 agent_names: List[str] = None,
                                 agent_type: str = None,
                                 start_date: str = None,
                                 end_date: str = None,
                                 fillna_value: float = 0.0) -> pd.DataFrame:
        """
        获取多个 Agent 的日收益率数据（宽表格式）

        Parameters
        ----------
        agent_names : list, optional
            Agent 名称列表。如果为 None，则获取所有 Agent
        agent_type : str, optional
            Agent 类型过滤（仅当 agent_names 为 None 时生效）
        start_date : str, optional
            开始日期 'YYYY-MM-DD'
        end_date : str, optional
            结束日期 'YYYY-MM-DD'
        fillna_value : float, optional
            缺失值填充值，默认为 0.0

        Returns
        -------
        pd.DataFrame
            日收益率数据表，columns 为 agent_name，index 为日期
        """
        if agent_names is None:
            agent_names = self.get_agent_names(agent_type)

        if not agent_names:
            return pd.DataFrame()

        query = """
            SELECT n.date, p.agent_name, n.ret
            FROM arena.daily_nav n
            JOIN arena.agent_pool p ON n.agent_id = p.agent_id
            WHERE p.agent_name = ANY(%s)
        """
        params = [agent_names]

        if start_date:
            query += " AND n.date >= %s"
            params.append(start_date)
        if end_date:
            query += " AND n.date <= %s"
            params.append(end_date)

        query += " ORDER BY n.date, p.agent_name"

        result = self._execute_query(query, tuple(params))

        if not result:
            return pd.DataFrame(columns=agent_names)

        df = pd.DataFrame(result, columns=['date', 'agent_name', 'ret'])
        df['date'] = pd.to_datetime(df['date'])
        df['ret'] = df['ret'].astype(float)

        ret_df = df.pivot(index='date', columns='agent_name', values='ret')
        ret_df = ret_df.reindex(columns=[n for n in agent_names if n in ret_df.columns])

        if fillna_value is not None:
            ret_df = ret_df.fillna(fillna_value)

        return ret_df

    def get_nav_date_range(self, agent_name: str = None) -> Dict[str, str]:
        """
        获取净值数据的日期范围

        Parameters
        ----------
        agent_name : str, optional
            Agent 名称。如果为 None，返回所有数据的日期范围

        Returns
        -------
        dict
            {'min_date': 'YYYY-MM-DD', 'max_date': 'YYYY-MM-DD'}
        """
        if agent_name:
            agent_id = self.get_agent_id(agent_name)
            if agent_id is None:
                return {'min_date': None, 'max_date': None}

            result = self._execute_query(
                "SELECT MIN(date), MAX(date) FROM arena.daily_nav WHERE agent_id = %s",
                (agent_id,)
            )
        else:
            result = self._execute_query(
                "SELECT MIN(date), MAX(date) FROM arena.daily_nav"
            )

        if result and result[0][0]:
            return {
                'min_date': result[0][0].strftime('%Y-%m-%d'),
                'max_date': result[0][1].strftime('%Y-%m-%d')
            }
        return {'min_date': None, 'max_date': None}

    # ==================== Daily Positions 查询 ====================

    def get_agent_daily_positions(self,
                                   agent_name: str,
                                   start_date: str = None,
                                   end_date: str = None) -> Dict[str, Dict[str, float]]:
        """
        获取单个 Agent 的每日持仓权重

        Parameters
        ----------
        agent_name : str
            Agent 名称
        start_date : str, optional
            开始日期 'YYYY-MM-DD'
        end_date : str, optional
            结束日期 'YYYY-MM-DD'

        Returns
        -------
        dict
            每日持仓数据 {date: {code: weight, ...}, ...}
        """
        agent_id = self.get_agent_id(agent_name)
        if agent_id is None:
            return {}

        query = "SELECT date, holdings FROM arena.daily_positions WHERE agent_id = %s"
        params = [agent_id]

        if start_date:
            query += " AND date >= %s"
            params.append(start_date)
        if end_date:
            query += " AND date <= %s"
            params.append(end_date)

        query += " ORDER BY date"

        result = self._execute_query(query, tuple(params))

        if result:
            return {row[0].strftime('%Y-%m-%d'): row[1] for row in result}

        return {}

    def get_multi_agents_daily_positions(self,
                                          agent_names: List[str] = None,
                                          agent_type: str = 'ETF',
                                          start_date: str = None,
                                          end_date: str = None) -> Dict[str, Dict[str, Dict[str, float]]]:
        """
        获取多个 Agent 的每日持仓权重

        Parameters
        ----------
        agent_names : list, optional
            Agent 名称列表。如果为 None，则获取所有指定类型的 Agent
        agent_type : str, optional
            Agent 类型过滤
        start_date : str, optional
            开始日期 'YYYY-MM-DD'
        end_date : str, optional
            结束日期 'YYYY-MM-DD'

        Returns
        -------
        dict
            多个 Agent 的每日持仓数据 {agent_name: {date: {code: weight, ...}, ...}, ...}
        """
        if agent_names is None:
            agent_names = self.get_agent_names(agent_type)

        if not agent_names:
            return {}

        query = """
            SELECT p.agent_name, d.date, d.holdings
            FROM arena.daily_positions d
            JOIN arena.agent_pool p ON d.agent_id = p.agent_id
            WHERE p.agent_name = ANY(%s)
        """
        params = [agent_names]

        if start_date:
            query += " AND d.date >= %s"
            params.append(start_date)
        if end_date:
            query += " AND d.date <= %s"
            params.append(end_date)

        query += " ORDER BY p.agent_name, d.date"

        result = self._execute_query(query, tuple(params))

        if not result:
            return {}

        positions_dict = {}
        for row in result:
            agent_name = row[0]
            date_str = row[1].strftime('%Y-%m-%d')
            holdings = row[2]

            if agent_name not in positions_dict:
                positions_dict[agent_name] = {}
            positions_dict[agent_name][date_str] = holdings

        return positions_dict

    def get_agents_positions_for_date(self,
                                       agent_names: List[str] = None,
                                       agent_type: str = 'ETF',
                                       target_date: str = None) -> Dict[str, Dict[str, float]]:
        """
        获取指定日期所有 Agent 的持仓权重

        Parameters
        ----------
        agent_names : list, optional
            Agent 名称列表。如果为 None，则获取所有指定类型的 Agent
        agent_type : str, optional
            Agent 类型过滤
        target_date : str, optional
            目标日期 'YYYY-MM-DD'。如果为 None，使用最新日期

        Returns
        -------
        dict
            各 Agent 的持仓数据 {agent_name: {code: weight, ...}, ...}
        """
        if agent_names is None:
            agent_names = self.get_agent_names(agent_type)

        if not agent_names:
            return {}

        if target_date:
            query = """
                SELECT p.agent_name, d.holdings
                FROM arena.daily_positions d
                JOIN arena.agent_pool p ON d.agent_id = p.agent_id
                WHERE p.agent_name = ANY(%s) AND d.date = %s
            """
            result = self._execute_query(query, (agent_names, target_date))
        else:
            query = """
                WITH latest AS (
                    SELECT d.agent_id, d.date, d.holdings,
                           ROW_NUMBER() OVER (PARTITION BY d.agent_id ORDER BY d.date DESC) as rn
                    FROM arena.daily_positions d
                    JOIN arena.agent_pool p ON d.agent_id = p.agent_id
                    WHERE p.agent_name = ANY(%s)
                )
                SELECT p.agent_name, l.holdings
                FROM latest l
                JOIN arena.agent_pool p ON l.agent_id = p.agent_id
                WHERE l.rn = 1
            """
            result = self._execute_query(query, (agent_names,))

        if not result:
            return {}

        return {row[0]: row[1] for row in result}

    # ==================== Backtest Results 查询 ====================

    def get_agent_metrics(self,
                          agent_name: str,
                          start_date: str = None,
                          end_date: str = None,
                          latest_only: bool = False) -> pd.DataFrame:
        """
        获取单个 Agent 的回测指标

        Parameters
        ----------
        agent_name : str
            Agent 名称
        start_date : str, optional
            开始日期 'YYYY-MM-DD'
        end_date : str, optional
            结束日期 'YYYY-MM-DD'
        latest_only : bool
            是否只获取最新一条记录

        Returns
        -------
        pd.DataFrame
            回测指标数据，包含 date 和 metrics 中的各字段
        """
        agent_id = self.get_agent_id(agent_name)
        if agent_id is None:
            return pd.DataFrame()

        query = "SELECT date, metrics FROM arena.backtest_res WHERE agent_id = %s"
        params = [agent_id]

        if start_date:
            query += " AND date >= %s"
            params.append(start_date)
        if end_date:
            query += " AND date <= %s"
            params.append(end_date)

        query += " ORDER BY date DESC" if latest_only else " ORDER BY date"

        if latest_only:
            query += " LIMIT 1"

        result = self._execute_query(query, tuple(params))

        if not result:
            return pd.DataFrame()

        records = []
        for row in result:
            record = {'date': row[0], 'agent_name': agent_name}
            if row[1]:
                record.update(row[1])
            records.append(record)

        df = pd.DataFrame(records)
        df['date'] = pd.to_datetime(df['date'])
        df = df.set_index('date')

        return df

    def get_latest_metrics(self, agent_names: List[str] = None, agent_type: str = None) -> pd.DataFrame:
        """
        获取多个 Agent 的最新回测指标

        Parameters
        ----------
        agent_names : list, optional
            Agent 名称列表。如果为 None，则获取所有 Agent
        agent_type : str, optional
            Agent 类型过滤（仅当 agent_names 为 None 时生效）

        Returns
        -------
        pd.DataFrame
            最新回测指标表，每行一个 Agent
        """
        if agent_names is None:
            agent_names = self.get_agent_names(agent_type)

        if not agent_names:
            return pd.DataFrame()

        query = """
            WITH latest AS (
                SELECT
                    r.agent_id,
                    p.agent_name,
                    r.date,
                    r.metrics,
                    ROW_NUMBER() OVER (PARTITION BY r.agent_id ORDER BY r.date DESC) as rn
                FROM arena.backtest_res r
                JOIN arena.agent_pool p ON r.agent_id = p.agent_id
                WHERE p.agent_name = ANY(%s)
            )
            SELECT agent_name, date, metrics
            FROM latest
            WHERE rn = 1
            ORDER BY agent_name
        """

        result = self._execute_query(query, (agent_names,))

        if not result:
            return pd.DataFrame()

        records = []
        for row in result:
            record = {
                'agent_name': row[0],
                'date': row[1]
            }
            if row[2]:
                record.update(row[2])
            records.append(record)

        df = pd.DataFrame(records)
        df['date'] = pd.to_datetime(df['date'])

        return df

    def get_multi_agents_metrics(self,
                                 agent_names: List[str] = None,
                                 agent_type: str = None,
                                 metric_name: str = 'sharpe_ratio',
                                 start_date: str = None,
                                 end_date: str = None) -> pd.DataFrame:
        """
        获取多个 Agent 的指定指标时间序列（宽表格式）

        Parameters
        ----------
        agent_names : list, optional
            Agent 名称列表。如果为 None，则获取所有 Agent
        agent_type : str, optional
            Agent 类型过滤（仅当 agent_names 为 None 时生效）
        metric_name : str
            指标名称，如 'sharpe_ratio', 'cum_ret', 'max_drawdown', 'turnover'
        start_date : str, optional
            开始日期 'YYYY-MM-DD'
        end_date : str, optional
            结束日期 'YYYY-MM-DD'

        Returns
        -------
        pd.DataFrame
            指标数据表，columns 为 agent_name，index 为日期
        """
        if agent_names is None:
            agent_names = self.get_agent_names(agent_type)

        if not agent_names:
            return pd.DataFrame()

        query = f"""
            SELECT r.date, p.agent_name, r.metrics->>'{metric_name}' as metric_value
            FROM arena.backtest_res r
            JOIN arena.agent_pool p ON r.agent_id = p.agent_id
            WHERE p.agent_name = ANY(%s)
        """
        params = [agent_names]

        if start_date:
            query += " AND r.date >= %s"
            params.append(start_date)
        if end_date:
            query += " AND r.date <= %s"
            params.append(end_date)

        query += " ORDER BY r.date, p.agent_name"

        result = self._execute_query(query, tuple(params))

        if not result:
            return pd.DataFrame(columns=agent_names)

        df = pd.DataFrame(result, columns=['date', 'agent_name', metric_name])
        df['date'] = pd.to_datetime(df['date'])
        df[metric_name] = pd.to_numeric(df[metric_name], errors='coerce')

        metrics_df = df.pivot(index='date', columns='agent_name', values=metric_name)
        metrics_df = metrics_df.reindex(columns=[n for n in agent_names if n in metrics_df.columns])

        return metrics_df

    # ==================== 综合查询方法 ====================

    def get_agents_summary(self, agent_type: str = None) -> pd.DataFrame:
        """
        获取所有 Agent 的汇总信息（包含最新指标）

        Parameters
        ----------
        agent_type : str, optional
            Agent 类型过滤

        Returns
        -------
        pd.DataFrame
            Agent 汇总表，包含基础信息和最新指标
        """
        agents_df = self.get_all_agents(agent_type)

        if agents_df.empty:
            return pd.DataFrame()

        agent_names = agents_df['agent_name'].tolist()

        latest_metrics = self.get_latest_metrics(agent_names)

        if not latest_metrics.empty:
            summary_df = agents_df.merge(
                latest_metrics,
                on='agent_name',
                how='left',
                suffixes=('', '_metrics')
            )
        else:
            summary_df = agents_df

        return summary_df

    def get_data_for_fof(self,
                         agent_names: List[str] = None,
                         agent_type: str = 'ETF',
                         start_date: str = None,
                         end_date: str = None) -> Dict[str, pd.DataFrame]:
        """
        获取 FOF Agent 构建所需的完整数据

        Parameters
        ----------
        agent_names : list, optional
            Agent 名称列表。如果为 None，则获取所有指定类型的 Agent
        agent_type : str
            Agent 类型过滤，默认 'ETF'
        start_date : str, optional
            开始日期 'YYYY-MM-DD'
        end_date : str, optional
            结束日期 'YYYY-MM-DD'

        Returns
        -------
        dict
            {
                'agents_info': pd.DataFrame,   # Agent 基础信息
                'nav': pd.DataFrame,           # 净值宽表
                'returns': pd.DataFrame,       # 收益率宽表
                'sharpe': pd.DataFrame,        # 夏普比率时间序列
                'cum_ret': pd.DataFrame,       # 累计收益率时间序列
                'max_drawdown': pd.DataFrame,  # 最大回撤时间序列
                'latest_metrics': pd.DataFrame # 最新指标
            }
        """
        if agent_names is None:
            agent_names = self.get_agent_names(agent_type)

        if not agent_names:
            return {
                'agents_info': pd.DataFrame(),
                'nav': pd.DataFrame(),
                'returns': pd.DataFrame(),
                'sharpe': pd.DataFrame(),
                'cum_ret': pd.DataFrame(),
                'max_drawdown': pd.DataFrame(),
                'latest_metrics': pd.DataFrame()
            }

        agents_info = self.get_all_agents(agent_type)
        agents_info = agents_info[agents_info['agent_name'].isin(agent_names)]

        nav = self.get_multi_agents_nav(agent_names, start_date=start_date, end_date=end_date)
        returns = self.get_multi_agents_returns(agent_names, start_date=start_date, end_date=end_date)

        sharpe = self.get_multi_agents_metrics(
            agent_names, metric_name='sharpe_ratio',
            start_date=start_date, end_date=end_date
        )
        cum_ret = self.get_multi_agents_metrics(
            agent_names, metric_name='cum_ret',
            start_date=start_date, end_date=end_date
        )
        max_drawdown = self.get_multi_agents_metrics(
            agent_names, metric_name='max_drawdown',
            start_date=start_date, end_date=end_date
        )

        latest_metrics = self.get_latest_metrics(agent_names)

        return {
            'agents_info': agents_info,
            'nav': nav,
            'returns': returns,
            'sharpe': sharpe,
            'cum_ret': cum_ret,
            'max_drawdown': max_drawdown,
            'latest_metrics': latest_metrics
        }

    def __del__(self):
        """析构函数，关闭数据库连接"""
        self._close_connection()
