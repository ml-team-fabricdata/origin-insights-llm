from langchain_core.tools import Tool
from src.sql.modules.common.admin import *

BUILD_SQL_TOOL = Tool.from_function(
    name="admin_build_sql",
    description=(
        "Compila un intent validado a SQL parametrizado + params. "
        "Aplica políticas de columnas/funciones/tablas del módulo admin."
    ),
    func=build_sql,
)


RUN_SQL_TOOL = Tool.from_function(
    name="admin_run_sql",
    description=(
        "Ejecuta un intent (usa admin.build_sql internamente) y retorna filas JSON-serializables."
    ),
    func=run_sql,
)


RUN_SQL_ADAPTER_TOOL = Tool.from_function(
    name="admin_run_sql_adapter",
    description=(
        "[raw] Ejecuta SQL crudo con parámetros. Úsalo solo para casos controlados o debugging."
    ),
    func=run_sql_adapter,
)


VALIDATE_INTENT_TOOL = Tool.from_function(
    name="admin_validate_intent",
    description="Valida un intent sin ejecutarlo (True/False).",
    func=validate_intent,
)


SCHEMA_INFO_TOOL = Tool.from_function(
    name="admin_get_schema_info",
    description="Información de schema: columnas por tabla o resumen global de tablas/funciones permitidas.",
    func=get_schema_info,
)


ALL_ADMIN_TOOLS = [
    # RUN SQL
    BUILD_SQL_TOOL,
    RUN_SQL_TOOL,
    VALIDATE_INTENT_TOOL,
    SCHEMA_INFO_TOOL,

]
