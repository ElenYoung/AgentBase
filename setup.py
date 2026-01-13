"""
CUFEL Arena Agent SDK - Setup Configuration

用于将 cufel-arena-agent 包发布到 PyPI。
"""

from setuptools import setup, find_packages
import os

# 读取 README
def read_readme():
    readme_path = os.path.join(os.path.dirname(__file__), 'README.md')
    if os.path.exists(readme_path):
        with open(readme_path, 'r', encoding='utf-8') as f:
            return f.read()
    return ""

# 读取版本号
def get_version():
    init_path = os.path.join(os.path.dirname(__file__), 'cufel_arena_agent', '__init__.py')
    with open(init_path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.startswith('__version__'):
                return line.split('=')[1].strip().strip('"').strip("'")
    return "1.0.0"

setup(
    name="cufel-arena-agent",
    version=get_version(),
    author="CUFEL-Q Arena Team",
    author_email="arena@cufel.edu.cn",
    description="CUFEL-Q Arena 平台智能体开发 SDK - 支持 ETF Agent 和 FOF Agent 开发",
    long_description=read_readme(),
    long_description_content_type="text/markdown",
    url="https://github.com/cufel-q/arena-agent-sdk",
    project_urls={
        "Documentation": "https://arena.cufel.edu.cn/docs",
        "Bug Tracker": "https://github.com/cufel-q/arena-agent-sdk/issues",
        "Source": "https://github.com/cufel-q/arena-agent-sdk",
    },
    packages=find_packages(exclude=["tests", "tests.*", "examples", "examples.*"]),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: Financial and Insurance Industry",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
        "Topic :: Office/Business :: Financial :: Investment",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "Typing :: Typed",
    ],
    python_requires=">=3.8",
    install_requires=[
        "pandas>=1.3.0",
        "numpy>=1.20.0",
    ],
    extras_require={
        "clickhouse": [
            "quantchdb>=0.1.0",
        ],
        "postgres": [
            "psycopg2-binary>=2.9.0",
        ],
        "dotenv": [
            "python-dotenv>=0.19.0",
        ],
        "dev": [
            "pytest>=6.0.0",
            "pytest-cov>=2.0.0",
            "black>=21.0.0",
            "flake8>=3.9.0",
            "mypy>=0.900",
        ],
        "etf": [
            "quantchdb>=0.1.0",
        ],
        "fof": [
            "psycopg2-binary>=2.9.0",
        ],
        "all": [
            "quantchdb>=0.1.0",
            "psycopg2-binary>=2.9.0",
            "python-dotenv>=0.19.0",
        ],
    },
    keywords=[
        "quantitative-finance",
        "trading",
        "etf",
        "fof",
        "portfolio",
        "investment",
        "arena",
        "agent",
        "clickhouse",
        "postgresql",
    ],
    package_data={
        "cufel_arena_agent": ["py.typed"],
    },
    include_package_data=True,
    zip_safe=False,
)
