"""
@log_action (логирование операций)
Логирование операций (INFO)
Исключения не подавляются,
они фиксируются в логе и пробрасываются дальше
"""

import functools
import inspect
import logging
from collections.abc import Callable
from typing import Any

from valutatrade_hub.logging_config import LOGGER_NAME

logger = logging.getLogger(LOGGER_NAME)

# Какие аргументы функции попадают в лог (имя аргумента -> поле в логе)
_LOGGED_ARGUMENTS = {
    "username": "user",
    "user_id": "user_id",
    "currency_code": "currency",
    "amount": "amount",
    "base": "base",
}
# Какие поля берём из результата операции
_RESULT_FIELDS = ("currency", "amount", "rate", "base")
# Порядок полей в строке лога
_FIELD_ORDER = ("user", "user_id", "currency", "amount", "rate", "base", "balance")


def _format_value(key: str, value: Any) -> str:
    if key == "balance":
        return str(value)
    if key == "amount":
        try:
            return f"{float(value):.4f}"
        except (TypeError, ValueError):
            return repr(value)
    if key == "rate" and isinstance(value, (int, float)):
        return f"{value:.2f}" if value >= 1 else f"{value:.6f}"
    if isinstance(value, str):
        return repr(value)
    return str(value)


def _build_message(
    action: str,
    fields: dict[str, Any],
    status: str,
    error: Exception | None = None,
) -> str:
    parts = [action]
    for key in _FIELD_ORDER:
        if key in fields:
            parts.append(f"{key}={_format_value(key, fields[key])}")
    parts.append(f"result={status}")
    if error is not None:
        parts.append(f"error_type={type(error).__name__}")
        parts.append(f"error_message={str(error)!r}")
    return " ".join(parts)


def _fields_from_result(result: dict, verbose: bool) -> dict[str, Any]:
    fields = {key: result[key] for key in _RESULT_FIELDS if key in result}
    if verbose and "before" in result and "after" in result:
        fields["balance"] = f"{result['before']:.4f}->{result['after']:.4f}"
    return fields


def log_action(action: str, verbose: bool = False) -> Callable[..., Any]:
    """Логирует операцию (INFO)
    Исключения не подавляются,
    они фиксируются в логе и пробрасываются дальше.
    verbose=True добавляет состояние кошелька
    «было->стало».
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        signature = inspect.signature(func)

        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            bound = signature.bind(*args, **kwargs)
            bound.apply_defaults()
            fields = {
                log_key: bound.arguments[arg]
                for arg, log_key in _LOGGED_ARGUMENTS.items()
                if arg in bound.arguments
            }
            try:
                result = func(*args, **kwargs)
            except Exception as error:
                logger.info(_build_message(action, fields, "ERROR", error))
                raise
            if isinstance(result, dict):
                fields.update(_fields_from_result(result, verbose))
            logger.info(_build_message(action, fields, "OK"))
            return result

        return wrapper

    return decorator
