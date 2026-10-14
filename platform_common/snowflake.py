"""Shared Snowflake configuration and connection construction."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Any


# The first character must be alphabet or _
# * represnets 0 or many times
# ^: start, $: end
# re.compile: compile the pattern that can be reused
IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_$]*$")


# @dataclass讓Python 自動幫 class 產生常用方法，並且讓建立後的物件不能被修改
# 它會根據欄位自動產生 __init__()、__repr__() 和 __eq__() 等方法
# 如果沒有 @dataclass，就要自己寫__init__(self,...)等方法
@dataclass(frozen=True)
class SnowflakeSettings:
    account: str
    user: str
    role: str
    database: str
    warehouse: str
    schema: str
    private_key_path: str

    # alternative constructor from its environment
    @classmethod
    def from_environment(cls) -> "SnowflakeSettings":
        names = {
            "account": "SNOWFLAKE_ACCOUNT",
            "user": "SNOWFLAKE_USER",
            "role": "SNOWFLAKE_ROLE",
            "database": "SNOWFLAKE_DATABASE",
            "warehouse": "SNOWFLAKE_WAREHOUSE",
            "schema": "SNOWFLAKE_SCHEMA",
            "private_key_path": "SNOWFLAKE_PRIVATE_KEY_PATH",
        }
        missing = [name for name in names.values() if not os.getenv(name)]
        if missing:
            raise RuntimeError(
                f"Missing Snowflake environment variables: {', '.join(missing)}"
            )
        return cls(**{field: os.environ[name] for field, name in names.items()})


def connect_snowflake(
    settings: SnowflakeSettings,
    *,
    autocommit: bool = False,
) -> Any:
    # * represent：all the other arguments after * should use keyword argument
    # because we do not know how many arguments in the settings
    # correct: connection = connect_snowflake(settings, autocommit=True,)
    # false: connection = connect_snowflake(settings, True)
    """Open a new connector session; callers own and close the connection."""

    try:
        # lazy import
        import snowflake.connector
    except ImportError as error:
        raise RuntimeError(
            "Install snowflake-connector-python to use warehouse I/O"
        ) from error

    return snowflake.connector.connect(
        account=settings.account,
        user=settings.user,
        role=settings.role,
        database=settings.database,
        warehouse=settings.warehouse,
        schema=settings.schema,
        private_key_file=settings.private_key_path,
        autocommit=autocommit,
    )


def validate_identifier(identifier: str) -> str:
    if not IDENTIFIER_PATTERN.fullmatch(identifier):
        raise ValueError(f"Unsafe Snowflake identifier: {identifier!r}")
    return identifier
