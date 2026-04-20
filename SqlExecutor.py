import oracledb
from typing import Any


def fetch_data(query: str, params: dict[str, Any] | None = None):
    with get_oracle_db() as connection:
        cursor = connection.cursor()
        try:
            cursor.execute(query, params or {})
            raw_result = cursor.fetchall()
            col_names = [col[0] for col in cursor.description]

            # CLOB/NCLOB/BLOB 수동 변환
            result = []
            for row in raw_result:
                converted_row = []
                for value in row:
                    if isinstance(value, oracledb.LOB):
                        converted_row.append(value.read())
                    else:
                        converted_row.append(value)
                result.append(converted_row)

            return result, col_names

        finally:
            cursor.close()

from dataclasses import dataclass
from typing import Any


@dataclass
class SQLExecutorConfig:
    log_sql_preview_chars: int = 300


class SQLExecutor:
    def __init__(self, config: SQLExecutorConfig | None = None):
        self.config = config or SQLExecutorConfig()

    def execute(self, state: AgentState) -> dict[str, Any]:
        if not state.generated_sql or not state.generated_sql.strip():
            return {
                "sql_result": [],
                "sql_reason": "generated_sql이 없어 SQL 실행을 생략",
            }

        params = state.sql_params or {}

        rows, col_names = fetch_data(state.generated_sql, params)
        sql_result = rows_to_dicts(rows, col_names)

        reason = (
            f"SQL 실행 완료: {len(sql_result)}건 조회"
        )

        return {
            "sql_result": sql_result,
            "sql_reason": reason,
        }
