"""
FOF Agent 示例 - 动态筛选策略

这个示例展示了如何使用 FOFAgentBase 创建一个动态筛选的 FOF 投资策略。
策略逻辑：根据 ETF Agents 的历史表现（夏普比率）动态筛选并配置权重。

特点：
- 不需要预先指定 target_agents，而是从数据库动态获取所有可用的 ETF Agents
- 根据历史表现筛选表现最好的 Agents
- 使用真实数据库连接
"""

import os
from dotenv import load_dotenv
from cufel_arena_agent import FOFAgentBase, ConfigLoader


class DynamicFOFAgent(FOFAgentBase):
    """
    动态筛选 FOF Agent

    根据历史表现动态筛选 ETF Agents，选择夏普比率最高的进行投资。
    """

    def __init__(self, top_n: int = 3, lookback_days: int = 30, db_config=None, **kwargs):
        """
        初始化 Agent

        Parameters
        ----------
        top_n : int
            选择表现最好的前 N 个 ETF Agents
        lookback_days : int
            回看天数，用于计算历史表现
        db_config : dict, optional
            PostgreSQL 数据库配置
        """
        super().__init__(
            name="DynamicFOF",
            db_config=db_config,
            target_agents=None,  # 不预先指定，动态获取
            **kwargs
        )
        self.top_n = top_n
        self.lookback_days = lookback_days

    def load_current_data(self, curr_date: str):
        """
        加载当前日期的数据；建议设计持仓缓存机制，将跑完的持仓存储在一个文件内，下次获取改日持仓时直接从文件中读取，避免重复计算相同日期的持仓


        动态获取所有 ETF Agents 的历史收益率数据
        """
        from datetime import datetime, timedelta

        # 计算回看起始日期
        end_dt = datetime.strptime(curr_date, '%Y-%m-%d')
        start_dt = end_dt - timedelta(days=self.lookback_days)
        start_date = start_dt.strftime('%Y-%m-%d')

        # 获取所有 ETF Agents 的收益率数据
        returns_df = self.data_client.get_multi_agents_returns(
            agent_names=None,  # None 表示获取所有
            agent_type='ETF',
            start_date=start_date,
            end_date=curr_date,
            fillna_value=0.0
        )

        return returns_df

    def get_current_holdings(self, curr_date: str, feedback: str = None, theta: float=None):
        """
        获取当前日期的持仓

        根据历史表现筛选最优的 ETF Agents
        """
        import numpy as np

        # 加载历史数据
        returns_df = self.load_current_data(curr_date)

        if returns_df.empty:
            return {curr_date: {}}

        # 计算每个 Agent 的夏普比率（简化版：年化收益/年化波动率）
        agent_scores = {}
        for agent_name in returns_df.columns:
            rets = returns_df[agent_name].dropna()
            if len(rets) < 5:  # 至少需要5天数据
                continue

            mean_ret = rets.mean() * 252  # 年化收益
            std_ret = rets.std() * np.sqrt(252)  # 年化波动率

            if std_ret > 0:
                sharpe = mean_ret / std_ret
            else:
                sharpe = 0

            agent_scores[agent_name] = sharpe

        if not agent_scores:
            return {curr_date: {}}

        # 选择夏普比率最高的 top_n 个 Agents
        sorted_agents = sorted(agent_scores.items(), key=lambda x: x[1], reverse=True)
        top_agents = sorted_agents[:self.top_n]

        # 等权分配
        weight = 1.0 / len(top_agents)
        holdings = {agent: weight for agent, _ in top_agents}

        return {curr_date: holdings}


# ==================== 使用示例 ====================

if __name__ == "__main__":
    # 加载环境变量
    load_dotenv()

    # 从环境变量读取数据库配置
    db_config = {
        'host': os.getenv('POSTGRES_HOST'),
        'port': os.getenv('POSTGRES_PORT'),
        'user': os.getenv('POSTGRES_USER'),
        'password': os.getenv('POSTGRES_PASSWORD'),
        'database': os.getenv('POSTGRES_DB')
    }

    print("=" * 50)
    print("FOF Agent 示例 - 动态筛选策略")
    print("=" * 50)

    # 测试数据库连接
    print("\n1. 测试数据库连接...")
    try:
        from cufel_arena_agent import ArenaDataClient
        client = ArenaDataClient(db_config=db_config)

        # 获取所有 ETF Agents
        all_agents = client.get_all_agents(agent_type='ETF')
        print(f"   连接成功! 共找到 {len(all_agents)} 个 ETF Agents")

        if not all_agents.empty:
            print(f"   ETF Agents 列表: {all_agents['agent_name'].tolist()}")

        # 获取数据日期范围
        date_range = client.get_nav_date_range()
        print(f"   数据日期范围: {date_range['min_date']} 至 {date_range['max_date']}")

    except Exception as e:
        print(f"   连接失败: {e}")
        exit(1)

    # 创建 Agent 实例
    print("\n2. 创建 DynamicFOFAgent...")
    agent = DynamicFOFAgent(
        top_n=3,
        lookback_days=30,
        db_config=db_config
    )

    print(f"   Agent 名称: {agent.name}")
    print(f"   Agent 类型: {agent.agent_type}")
    print(f"   选择 Top N: {agent.top_n}")
    print(f"   回看天数: {agent.lookback_days}")

    # 获取单日持仓
    print("\n3. 获取单日持仓...")
    test_date = date_range['max_date'] if date_range['max_date'] else '2025-01-15'
    try:
        holdings = agent.get_current_holdings(test_date)
        print(f"   {test_date} 持仓:")
        if holdings.get(test_date):
            for agent_name, weight in holdings[test_date].items():
                print(f"      {agent_name}: {weight:.2%}")
        else:
            print("      (无持仓数据)")
    except Exception as e:
        print(f"   获取失败: {e}")

    print("\n" + "=" * 50)
    print("测试完成!")
    print("=" * 50)
