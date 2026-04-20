import oracledb
from typing import Any
import oracledb
from typing import Any


def fetch_data(
    query: str,
    params: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """
    Oracle SQL 실행 후 결과를 list[dict] 형태로 반환한다.

    특징:
    - bind params 지원
    - CLOB / NCLOB / BLOB(oracledb.LOB) 자동 read()
    - 컬럼명을 key로 사용하는 dict row 반환

    Example:
        rows = fetch_data(
            "SELECT issue_no, issue_name FROM Q_ISSUE WHERE issue_no=:issue_id_0",
            {"issue_id_0": "ISSUE-001"}
        )

        rows == [
            {
                "ISSUE_NO": "ISSUE-001",
                "ISSUE_NAME": "Bridge 불량"
            }
        ]
    """
    with get_oracle_db() as connection:
        cursor = connection.cursor()

        try:
            cursor.execute(query, params or {})

            col_names = [col[0] for col in cursor.description]
            raw_rows = cursor.fetchall()

            result: list[dict[str, Any]] = []

            for row in raw_rows:
                row_dict: dict[str, Any] = {}

                for idx, value in enumerate(row):
                    # LOB 타입은 문자열/bytes로 변환
                    if isinstance(value, oracledb.LOB):
                        converted_value = value.read()
                    else:
                        converted_value = value

                    row_dict[col_names[idx]] = converted_value

                result.append(row_dict)

            return result

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
