"""
ETF Agent 示例 - 等权策略

这个示例展示了如何使用 ETFAgentBase 创建一个简单的 ETF 投资策略。
数据库配置在类定义时指定，而不是实例化时传递。
"""

import os
from dotenv import load_dotenv
from cufel_arena_agent import ETFAgentBase
from quantchdb import ClickHouseDatabase

# 加载环境变量（在类定义前加载）
load_dotenv()

# 在类定义时配置数据库
DB_CONFIG = {
    'host': os.getenv('DB_HOST_Server'),
    'port': int(os.getenv('DB_PORT_Server')),
    'user': os.getenv('DB_USER_Server'),
    'password': os.getenv('DB_PASSWORD_Server'),
    'database': os.getenv('DB_DATABASE_Server')
}


class EqualWeightETFAgent(ETFAgentBase):
    """
    等权重 ETF Agent

    数据库配置在类定义时确定，无需在实例化时传递。
    """

    def __init__(self, **kwargs):
        """初始化 Agent"""
        super().__init__(name="EqualWeightETFStrategy", db_config=DB_CONFIG, **kwargs)

    def load_current_data(self, curr_date: str):
        """
        加载当前日期所需要的数据
        """
        db = ClickHouseDatabase(config=self.db_config, terminal_log=False)
        sql = f'''
            SELECT code
            FROM etf.etf_day
            WHERE date == '{curr_date}'
            ORDER BY date DESC
            LIMIT 20
        '''
        return db.fetch(sql)

    def get_current_holdings(self, curr_date: str, feedback: str = None, theta: float = None):
        """
        获取当前日期的持仓

        建议设计持仓缓存机制，将跑完的持仓存储在一个文件内，
        下次获取该日持仓时直接从文件中读取，避免重复计算相同日期的持仓。

        Parameters
        ----------
        curr_date : str
            当前日期，格式为 'YYYY-MM-DD'
        feedback : str, optional
            来自 FOF Agent 的反馈信息
        theta : float, optional
            风险偏好系数

        Returns
        -------
        dict
            持仓字典 {curr_date: {code: weight, ...}}
        """
        # 加载数据 (返回的是 DataFrame)
        df = self.load_current_data(curr_date)

        # 获取 ETF 代码列表
        codes = df['code'].tolist()

        # 等权分配
        if len(codes) == 0:
            return {curr_date: {}}

        weight = 1.0 / len(codes)
        holdings = {code: weight for code in codes}

        return {curr_date: holdings}


# ==================== 使用示例 ====================

if __name__ == "__main__":
    # 直接创建实例，无需传递 db_config
    agent = EqualWeightETFAgent()

    print(f"Agent 名称: {agent.name}")
    print(f"Agent 类型: {agent.agent_type}")

    # 获取单日持仓
    holdings = agent.get_current_holdings('2025-01-15')
    print(f"2025-01-15 持仓: {holdings}")

    # 获取多日持仓
    daily_holdings = agent.get_daily_holdings('2025-01-13', '2025-01-15')
    print("\n多日持仓:")
    for date, pos in daily_holdings.items():
        print(f"  {date}: {pos}")
