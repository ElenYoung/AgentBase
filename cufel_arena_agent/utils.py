"""
工具函数模块

提供日期验证、装饰器等通用工具函数
"""

import re
from functools import wraps
from typing import Callable, Any
import inspect


def validate_date_format(date_str: str, param_name: str = "date") -> None:
    """
    验证日期字符串格式是否为 YYYY-MM-DD

    Parameters
    ----------
    date_str : str
        待验证的日期字符串
    param_name : str
        参数名称（用于错误信息）

    Raises
    ------
    ValueError
        如果日期格式不正确或日期无效
    """
    if not isinstance(date_str, str):
        raise ValueError(
            f"Invalid type for parameter '{param_name}': expected str, got {type(date_str).__name__}"
        )

    if not re.match(r"^\d{4}-\d{2}-\d{2}$", date_str):
        raise ValueError(
            f"Invalid date format for parameter '{param_name}': '{date_str}'. "
            "Expected format: YYYY-MM-DD"
        )

    try:
        year, month, day = map(int, date_str.split("-"))
        if not (1 <= month <= 12):
            raise ValueError(f"Invalid month in {param_name}: {month}")
        if not (1 <= day <= 31):
            raise ValueError(f"Invalid day in {param_name}: {day}")
        if month in [4, 6, 9, 11] and day > 30:
            raise ValueError(f"Invalid day for month {month}: {day}")
        if month == 2:
            if (year % 4 == 0 and year % 100 != 0) or (year % 400 == 0):
                max_day = 29
            else:
                max_day = 28
            if day > max_day:
                raise ValueError(f"Invalid day for February {year}: {day}")
    except ValueError as e:
        raise ValueError(f"Invalid date for parameter '{param_name}': {str(e)}")


def validate_date_parameters(func: Callable) -> Callable:
    """
    装饰器：自动验证函数参数中包含 'date' 的参数格式

    Parameters
    ----------
    func : Callable
        被装饰的函数

    Returns
    -------
    Callable
        包装后的函数
    """
    @wraps(func)
    def wrapper(*args, **kwargs) -> Any:
        signature = inspect.signature(func)
        bound_args = signature.bind(*args, **kwargs)
        bound_args.apply_defaults()
        arg_values = bound_args.arguments

        for param_name, param_value in arg_values.items():
            if not isinstance(param_value, str):
                continue

            if "date" in param_name.lower():
                validate_date_format(param_value, param_name)

        return func(*args, **kwargs)

    return wrapper


def auto_validate(cls):
    """
    类装饰器：自动为指定方法添加日期参数验证

    这个装饰器会在类的 __init_subclass__ 中注册验证逻辑，
    确保子类重写的方法也会被自动验证。

    Parameters
    ----------
    cls : class
        被装饰的类

    Returns
    -------
    class
        装饰后的类
    """
    validate_methods = {'load_current_data', 'get_current_holdings', 'get_daily_holdings'}

    # 保存原始的 __init_subclass__
    original_init_subclass = getattr(cls, '__init_subclass__', None)

    @classmethod
    def new_init_subclass(subcls, **kwargs):
        # 调用原始的 __init_subclass__
        if original_init_subclass is not None:
            try:
                original_init_subclass(**kwargs)
            except TypeError:
                pass

        # 为子类中重写的方法添加验证
        for name in validate_methods:
            if name in subcls.__dict__:  # 只处理在子类中定义的方法
                method = subcls.__dict__[name]
                if callable(method):
                    setattr(subcls, name, validate_date_parameters(method))

    cls.__init_subclass__ = new_init_subclass

    # 同时为基类本身的方法添加验证
    for name in validate_methods:
        if hasattr(cls, name):
            method = getattr(cls, name)
            setattr(cls, name, validate_date_parameters(method))

    return cls


def validate_holdings_format(holdings: dict) -> bool:
    """
    验证持仓数据格式是否正确

    Parameters
    ----------
    holdings : dict
        持仓数据，格式应为 {date: {code: weight, ...}}

    Returns
    -------
    bool
        格式是否正确

    Raises
    ------
    ValueError
        如果格式不正确
    """
    if not isinstance(holdings, dict):
        raise ValueError(f"Holdings must be a dict, got {type(holdings).__name__}")

    for date_key, positions in holdings.items():
        # 验证日期格式
        validate_date_format(date_key, "holdings date key")

        if not isinstance(positions, dict):
            raise ValueError(
                f"Positions for date {date_key} must be a dict, got {type(positions).__name__}"
            )

        total_weight = 0.0
        for code, weight in positions.items():
            if not isinstance(code, str):
                raise ValueError(
                    f"Asset code must be str, got {type(code).__name__} for date {date_key}"
                )

            if not isinstance(weight, (int, float)):
                raise ValueError(
                    f"Weight for {code} must be numeric, got {type(weight).__name__}"
                )

            if weight < 0:
                raise ValueError(
                    f"Weight for {code} cannot be negative: {weight}"
                )

            total_weight += weight

        if total_weight > 1.0 + 1e-6:  # 允许小误差
            raise ValueError(
                f"Total weight for date {date_key} exceeds 1.0: {total_weight}"
            )

    return True
