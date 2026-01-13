"""
ETF Agent 示例 - 动量策略

这个示例展示了如何使用 ETFAgentBase 创建一个简单的 ETF 投资策略。
策略逻辑：根据近期涨幅选择表现最好的 ETF。
"""

from cufel_arena_agent import ETFAgentBase, ConfigLoader

# 如果需要使用 quantchdb 获取数据，需要安装并导入
from quantchdb import ClickHouseDatabase


class EqualWeightETFAgent(ETFAgentBase):
    """
    等权重 ETF Agent

    """

    def __init__(self, db_config=None, **kwargs):
        """
        初始化 Agent

        Parameters
        ----------
        db_config : dict, optional
            ClickHouse 数据库配置
        """
        super().__init__(name="EqualWeightETFStrategy", db_config=db_config, **kwargs)

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

    def get_current_holdings(self, curr_date: str, feedback: str = None, theta: float=None):
        """
        获取当前日期的持仓

        Parameters
        ----------
        curr_date : str
            当前日期，格式为 'YYYY-MM-DD'
        feedback : str, optional
            来自 FOF Agent 的反馈信息

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
    # 创建 Agent 实例
    import os
    from dotenv import load_dotenv
    load_dotenv()
    db_config={
        'host': os.getenv('DB_HOST_Server'),
        'port': int(os.getenv('DB_PORT_Server')),
        'user': os.getenv('DB_USER_Server'),
        'password': os.getenv('DB_PASSWORD_Server'),
        'database': os.getenv('DB_DATABASE_Server')
    }

    agent = EqualWeightETFAgent(db_config=db_config)

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
