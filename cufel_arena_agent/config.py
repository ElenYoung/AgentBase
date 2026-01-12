"""
配置管理模块

提供配置加载和验证功能，支持环境变量和配置文件

数据库配置说明：
- ClickHouse (ETF Agent): 用于获取 ETF/股票行情数据，配合 quantchdb 使用
- PostgreSQL (FOF Agent): 用于获取 ETF Agents 的净值/持仓数据
"""

import os
from typing import Dict, Optional, Any
from dataclasses import dataclass, field


@dataclass
class DatabaseConfig:
    """
    数据库配置类

    Attributes
    ----------
    host : str
        数据库服务器地址
    port : str | int
        数据库端口
    user : str
        数据库用户名
    password : str
        数据库密码
    database : str
        数据库名称
    """
    host: str = ""
    port: str = ""
    user: str = ""
    password: str = ""
    database: str = ""

    def to_dict(self) -> Dict[str, str]:
        """转换为字典格式"""
        return {
            "host": self.host,
            "port": str(self.port),
            "user": self.user,
            "password": self.password,
            "database": self.database
        }

    def validate(self) -> bool:
        """
        验证配置是否完整

        Returns
        -------
        bool
            配置是否有效

        Raises
        ------
        ValueError
            如果配置不完整
        """
        required_fields = ["host", "port", "user", "password", "database"]
        missing = [f for f in required_fields if not getattr(self, f)]
        if missing:
            raise ValueError(f"Missing required database config fields: {missing}")
        return True

    @classmethod
    def from_env(cls, prefix: str = "ARENA_DB") -> "DatabaseConfig":
        """
        从环境变量加载配置

        Parameters
        ----------
        prefix : str
            环境变量前缀

        Returns
        -------
        DatabaseConfig
            配置实例
        """
        return cls(
            host=os.getenv(f"{prefix}_HOST", ""),
            port=os.getenv(f"{prefix}_PORT", ""),
            user=os.getenv(f"{prefix}_USER", ""),
            password=os.getenv(f"{prefix}_PASSWORD", ""),
            database=os.getenv(f"{prefix}_DATABASE", "")
        )

    @classmethod
    def from_dict(cls, config: Dict[str, Any]) -> "DatabaseConfig":
        """
        从字典加载配置

        Parameters
        ----------
        config : dict
            配置字典

        Returns
        -------
        DatabaseConfig
            配置实例
        """
        return cls(
            host=config.get("host", ""),
            port=config.get("port", ""),
            user=config.get("user", ""),
            password=config.get("password", ""),
            database=config.get("database", "")
        )


@dataclass
class AgentConfig:
    """
    Agent 配置类

    Attributes
    ----------
    name : str
        Agent 名称
    agent_type : str
        Agent 类型 ('ETF' 或 'FOF')
    db_config : DatabaseConfig
        数据库配置
    description : str
        Agent 描述
    version : str
        Agent 版本
    extra : dict
        额外配置项
    """
    name: str = ""
    agent_type: str = "ETF"
    db_config: Optional[DatabaseConfig] = None
    description: str = ""
    version: str = "1.0.0"
    extra: Dict[str, Any] = field(default_factory=dict)

    def validate(self) -> bool:
        """
        验证配置是否有效

        Returns
        -------
        bool
            配置是否有效

        Raises
        ------
        ValueError
            如果配置无效
        """
        if not self.name:
            raise ValueError("Agent name is required")

        if self.agent_type not in ("ETF", "FOF"):
            raise ValueError(f"Invalid agent_type: {self.agent_type}. Must be 'ETF' or 'FOF'")

        if self.db_config:
            self.db_config.validate()

        return True


class ConfigLoader:
    """
    配置加载器

    管理两种数据库配置：
    - ClickHouse: ETF Agent 使用，获取 ETF/股票行情数据
    - PostgreSQL: FOF Agent 使用，获取 ETF Agents 数据

    环境变量前缀：
    - ClickHouse: ARENA_CH_HOST, ARENA_CH_PORT, ARENA_CH_USER, ARENA_CH_PASSWORD, ARENA_CH_DATABASE
    - PostgreSQL: ARENA_PG_HOST, ARENA_PG_PORT, ARENA_PG_USER, ARENA_PG_PASSWORD, ARENA_PG_DATABASE

    使用示例
    --------
    >>> from cufel_arena_agent import ConfigLoader
    >>>
    >>> # 设置 ClickHouse 配置（ETF Agent 使用）
    >>> ConfigLoader.set_clickhouse_config({
    ...     "host": "localhost",
    ...     "port": "8123",
    ...     "user": "default",
    ...     "password": "xxx",
    ...     "database": "etf"
    ... })
    >>>
    >>> # 设置 PostgreSQL 配置（FOF Agent 使用）
    >>> ConfigLoader.set_postgres_config({
    ...     "host": "localhost",
    ...     "port": "5432",
    ...     "user": "postgres",
    ...     "password": "xxx",
    ...     "database": "arena"
    ... })
    """

    _instance = None
    _clickhouse_config: Optional[DatabaseConfig] = None
    _postgres_config: Optional[DatabaseConfig] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    # ==================== ClickHouse 配置 (ETF Agent) ====================

    @classmethod
    def set_clickhouse_config(cls, config: Dict[str, str]) -> None:
        """
        设置 ClickHouse 数据库配置（ETF Agent 使用）

        Parameters
        ----------
        config : dict
            数据库配置字典，包含 host, port, user, password, database
        """
        cls._clickhouse_config = DatabaseConfig.from_dict(config)
        cls._clickhouse_config.validate()

    @classmethod
    def get_clickhouse_config(cls) -> Optional[DatabaseConfig]:
        """
        获取 ClickHouse 数据库配置

        Returns
        -------
        DatabaseConfig or None
            数据库配置实例
        """
        if cls._clickhouse_config is None:
            # 尝试从环境变量加载
            cls._clickhouse_config = DatabaseConfig.from_env(prefix="ARENA_CH")
            try:
                cls._clickhouse_config.validate()
            except ValueError:
                cls._clickhouse_config = None

        return cls._clickhouse_config

    # ==================== PostgreSQL 配置 (FOF Agent) ====================

    @classmethod
    def set_postgres_config(cls, config: Dict[str, str]) -> None:
        """
        设置 PostgreSQL 数据库配置（FOF Agent 使用）

        Parameters
        ----------
        config : dict
            数据库配置字典，包含 host, port, user, password, database
        """
        cls._postgres_config = DatabaseConfig.from_dict(config)
        cls._postgres_config.validate()

    @classmethod
    def get_postgres_config(cls) -> Optional[DatabaseConfig]:
        """
        获取 PostgreSQL 数据库配置

        Returns
        -------
        DatabaseConfig or None
            数据库配置实例
        """
        if cls._postgres_config is None:
            # 尝试从环境变量加载
            cls._postgres_config = DatabaseConfig.from_env(prefix="ARENA_PG")
            try:
                cls._postgres_config.validate()
            except ValueError:
                cls._postgres_config = None

        return cls._postgres_config

    # ==================== 兼容旧接口 ====================

    @classmethod
    def set_database_config(cls, config: Dict[str, str]) -> None:
        """
        设置数据库配置（兼容旧接口，等同于 set_postgres_config）

        Parameters
        ----------
        config : dict
            数据库配置字典
        """
        cls.set_postgres_config(config)

    @classmethod
    def get_database_config(cls) -> Optional[DatabaseConfig]:
        """
        获取数据库配置（兼容旧接口，等同于 get_postgres_config）

        Returns
        -------
        DatabaseConfig or None
            数据库配置实例
        """
        return cls.get_postgres_config()

    # ==================== 通用方法 ====================

    @classmethod
    def load_from_env_file(cls, env_file: str = ".env") -> None:
        """
        从 .env 文件加载环境变量

        Parameters
        ----------
        env_file : str
            .env 文件路径
        """
        try:
            from dotenv import load_dotenv
            load_dotenv(env_file)
        except ImportError:
            pass  # python-dotenv 未安装，跳过

    @classmethod
    def reset(cls) -> None:
        """重置所有配置（主要用于测试）"""
        cls._clickhouse_config = None
        cls._postgres_config = None
