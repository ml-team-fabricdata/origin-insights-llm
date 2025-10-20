from src.strands.utils.default_import import *
from src.strands.utils.db_utils_sql import *
from src.strands.utils.constants_sql import *
from src.strands.utils.validators import *
from src.strands.common.common_queries.base_queries import *
from strands import tool

_ident = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$", re.IGNORECASE)
_func = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*\s*\(", re.IGNORECASE)
_numeric = re.compile(r"^-?\d+(\.\d+)?$", re.IGNORECASE)
_qualified = re.compile(
    r"^[A-Za-z_][A-Za-z0-9_]*\.[A-Za-z_][A-Za-z0-9_]*$", re.IGNORECASE)

def _norm_table(t: str) -> str:
    return TABLE_MAP.get(t, t)

def _ensure_table(t: str) -> bool:
    return t in SCHEMAS

def _ensure_col(t: str, c: str) -> bool:
    return _ensure_table(t) and c in SCHEMAS[t]

def _ensure_alias(a: Optional[str]) -> bool:
    return a is None or _ident.match(a) is not None

def _is_func(expr: str) -> bool:
    return bool(_func.match(expr))

def _split_args(arglist: str) -> List[str]:
    """Divide argumentos de función respetando paréntesis."""
    if not arglist.strip():
        return []

    args, buf, depth = [], [], 0
    i = 0
    while i < len(arglist):
        ch = arglist[i]
        if ch == '(' and depth >= 0:
            depth += 1
        elif ch == ')' and depth > 0:
            depth -= 1
        elif ch == ',' and depth == 0:
            args.append(''.join(buf).strip())
            buf = []
            i += 1
            continue
        buf.append(ch)
        i += 1

    tail = ''.join(buf).strip()
    if tail:
        args.append(tail)
    return args

def _render_colref(colref: str, tables: Dict[str, str]) -> Optional[str]:
    """Renderiza referencia a columna."""
    if "." not in colref:
        return None

    left, c = colref.split(".", 1)
    if left not in tables and left not in SCHEMAS:
        return None

    table_name = tables.get(left, left)
    if not _ensure_col(table_name, c):
        return None

    return f"{left}.{c}"

def _render_expr(expr: str, tables: Dict[str, str]) -> Optional[str]:
    """Renderiza expresión SQL."""
    expr = expr.strip()

    m_cast = re.match(
        r"^CAST\s*\((.+)\s+AS\s+([A-Za-z0-9_]+)\s*\)$", expr, re.I)
    if m_cast:
        inner, type_ = m_cast.groups()
        inner_rendered = _render_expr(inner, tables)
        return f"CAST({inner_rendered} AS {type_})" if inner_rendered else None

    if _is_func(expr):
        m = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)\s*\((.*)\)$", expr)
        if not m:
            return None

        fname, inside = m.group(1).upper(), m.group(2)
        if fname not in ALLOWED_FUNCS:
            return None

        raw_args = _split_args(inside)
        min_a, max_a = ALLOWED_FUNCS[fname]

        if len(raw_args) < min_a or (max_a != -1 and len(raw_args) > max_a):
            return None

        args_rendered = []
        for arg in raw_args:
            arg_rendered = _render_value_or_col(arg, tables)
            if arg_rendered is None:
                return None
            args_rendered.append(arg_rendered)

        return f"{fname}(" + ", ".join(args_rendered) + ")"

    if "." in expr and _qualified.match(expr):
        return _render_colref(expr, tables)

    if expr.startswith("'") and expr.endswith("'"):
        return expr
    if _numeric.match(expr):
        return expr

    return None

def _render_value_or_col(token: str, tables: Dict[str, str]) -> Optional[str]:
    """Renderiza token (literal o columna)."""
    token = token.strip()

    if _numeric.match(token) or (len(token) >= 2 and token[0] == token[-1] == "'"):
        return token

    if "." in token or _is_func(token) or token.upper().startswith("CAST("):
        return _render_expr(token, tables)

    return None

def _render_select_item(item: str, tables: Dict[str, str]) -> Optional[str]:
    """Renderiza item de SELECT."""
    m = re.match(
        r"^(.*?)(?:\s+AS\s+|\s+)([A-Za-z_][A-Za-z0-9_]*)$", item, re.I)
    if m:
        expr, alias = m.group(1).strip(), m.group(2)
        if not _ensure_alias(alias):
            return None
        expr_rendered = _render_expr(expr, tables)
        return f"{expr_rendered} AS {alias}" if expr_rendered else None

    return _render_expr(item, tables)

def _apply_resolver(qualified_col: str, value: Any) -> Any:
    """Aplica resolver si existe."""
    fn = RESOLVERS.get(qualified_col)
    if fn is None:
        return value
    if isinstance(value, (list, tuple, set)):
        return [fn(v) for v in value]
    return fn(value)

def _render_filters(table_alias_map: Dict[str, str],
                    filters: Optional[Mapping[str, Tuple[str, Any]]],
                    params: Dict[str, Any],
                    param_counter: List[int],
                    clause: str) -> str:
    """Renderiza filtros WHERE/HAVING."""
    if not filters:
        return ""

    parts = []
    for key, (op, val) in filters.items():
        if "." not in key:
            continue

        alias, col = key.split(".", 1)
        if alias not in table_alias_map:
            continue

        table = table_alias_map[alias]
        if not _ensure_col(table, col):
            continue

        op = op.upper().strip()
        if op not in ALLOWED_OPERATORS:
            continue

        qcol = f"{alias}.{col}"
        val = _apply_resolver(qcol, val)

        if op in {"IS", "IS NOT"}:
            sval = str(val).upper()
            if sval not in {"NULL", "TRUE", "FALSE"}:
                continue
            parts.append(f"{qcol} {op} {sval}")
        elif op in {"IN", "NOT IN"}:
            if not isinstance(val, (list, tuple, set)) or len(val) == 0:
                continue
            phs = []
            for v in val:
                p_key = f"p{param_counter[0]}"
                params[p_key] = v
                param_counter[0] += 1
                phs.append(f"%({p_key})s")
            parts.append(f"{qcol} {op} (" + ", ".join(phs) + ")")
        elif op == "BETWEEN":
            if not isinstance(val, (list, tuple)) or len(val) != 2:
                continue
            p1, p2 = f"p{param_counter[0]}", f"p{param_counter[0]+1}"
            params[p1], params[p2] = val[0], val[1]
            param_counter[0] += 2
            parts.append(f"{qcol} BETWEEN %({p1})s AND %({p2})s")
        else:
            p_key = f"p{param_counter[0]}"
            params[p_key] = val
            param_counter[0] += 1
            parts.append(f"{qcol} {op} %({p_key})s")

    return f" {clause} " + " AND ".join(parts) if parts else ""

@tool
def build_sql(*,
              base_table: str, base_alias: str,
              select: Sequence[str],
              joins: Optional[Sequence[Dict[str, Any]]] = None,
              where: Optional[Mapping[str, Tuple[str, Any]]] = None,
              group_by: Optional[Sequence[str]] = None,
              having: Optional[Mapping[str, Tuple[str, Any]]] = None,
              order_by: Optional[Sequence[str]] = None,
              limit: Optional[int] = None,
              offset: Optional[int] = None,
              ) -> Optional[Tuple[str, Dict[str, Any]]]:
    """Construye query SQL validada."""

    base_table = _norm_table(base_table)
    if not _ensure_table(base_table) or not _ensure_alias(base_alias):
        return None

    tables = {base_alias: base_table}

    join_sql = []
    if joins:
        for j in joins:
            jt = j.get("type", "LEFT JOIN").upper().strip()
            if jt not in ALLOWED_JOIN_TYPES:
                continue

            tbl = _norm_table(j["table"])
            als = j["alias"]
            on = j["on"]

            if not _ensure_table(tbl) or not _ensure_alias(als) or als in tables:
                continue

            if not isinstance(on, (list, tuple)) or len(on) == 0:
                continue

            tables[als] = tbl
            on_parts = []
            for lp, rp in on:
                left_rendered = _render_colref(lp, tables)
                right_rendered = _render_colref(rp, tables)
                if left_rendered and right_rendered:
                    on_parts.append(f"{left_rendered} = {right_rendered}")

            if on_parts:
                join_sql.append(f"{jt} {tbl} {als} ON " +
                                " AND ".join(on_parts))

    if len(select) == 0:
        return None

    sel_rendered = []
    for item in select:
        item_rendered = _render_select_item(item, tables)
        if item_rendered:
            sel_rendered.append(item_rendered)

    if not sel_rendered:
        return None

    params = {}
    param_counter = [0]

    where_sql = _render_filters(tables, where, params, param_counter, "WHERE")
    having_sql = _render_filters(
        tables, having, params, param_counter, "HAVING")

    group_sql = ""
    if group_by:
        group_items = []
        for it in group_by:
            if "." in it:
                rendered = _render_colref(it, tables)
            else:
                rendered = _render_expr(it, tables)
            if rendered:
                group_items.append(rendered)
        if group_items:
            group_sql = " GROUP BY " + ", ".join(group_items)

    order_sql = ""
    if order_by:
        obs = []
        for ob in order_by:
            ob = ob.strip()
            dir_ = ""
            if ob.upper().endswith(" DESC"):
                dir_ = " DESC"
                ob = ob[:-5].strip()
            elif ob.upper().endswith(" ASC"):
                dir_ = " ASC"
                ob = ob[:-4].strip()

            expr = _render_expr(ob, tables)
            if expr:
                obs.append(expr + dir_)
        if obs:
            order_sql = " ORDER BY " + ", ".join(obs)

    limoff = ""
    if limit is not None and isinstance(limit, int) and limit > 0:
        limoff += f" LIMIT {limit}"
    if offset is not None and isinstance(offset, int) and offset >= 0:
        limoff += f" OFFSET {offset}"

    sql = (
        "SELECT " + ", ".join(sel_rendered) +
        f" FROM {base_table} {base_alias}" +
        (" " + " ".join(join_sql) if join_sql else "") +
        where_sql + group_sql + having_sql + order_sql + limoff
    ).strip() + ";"

    return sql, params

@tool
def run_sql(intent: Dict[str, Any], op_name: str = "intent_query") -> List[Dict]:
    """Ejecuta intent compilado."""

    sql_result = build_sql(**intent)
    if sql_result is None:
        logger.warning(f"Falló compilación de intent: {op_name}")
        return []

    sql, params = sql_result
    rows = db.execute_query(sql, params)
    return _process_results(rows, op_name)

def _process_results(raw_rows: List[Any], op_name: str) -> List[Dict[str, Any]]:
    """Procesa resultados crudos."""
    if not raw_rows:
        return []

    if isinstance(raw_rows[0], dict):
        return raw_rows

    processed = []
    for row in raw_rows:
        if hasattr(row, '_asdict'):
            processed.append(row._asdict())
        elif hasattr(row, 'keys'):
            processed.append(dict(row))
        else:
            processed.append({'row': row})

    return processed

@tool
def run_sql_adapter(*args, **kwargs) -> List[Dict[str, Any]]:
    """Adaptador para múltiples formatos."""
    a1 = kwargs.pop("__arg1", None)
    query = kwargs.pop("query", None)
    params = kwargs.pop("params", None)

    if a1 is not None:
        if isinstance(a1, str):
            query = query or a1
            params = params or {}
        elif isinstance(a1, dict):
            query = query or a1.get("query")
            params = params or a1.get("params", {})
        else:
            return []

    if query is None and args:
        first = args[0]
        if isinstance(first, str):
            query = first
            params = params or {}
        elif isinstance(first, dict):
            query = first.get("query")
            params = params or first.get("params", {})

    if not isinstance(query, str) or not query.strip():
        return []

    if params is None:
        params = {}
    elif isinstance(params, (list, tuple)):
        params = {f"param_{i}": v for i, v in enumerate(params)}
    elif not isinstance(params, dict):
        return []

    rows = db.execute_query(query, params)
    return _process_results(rows, "adapter_query")

@tool
def validate_intent(intent: Dict[str, Any]) -> bool:
    """Valida intent sin ejecutar."""
    return build_sql(**intent) is not None

def get_schema_info(table_name: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Info del schema."""
    if table_name:
        normalized = _norm_table(table_name)
        if normalized not in SCHEMAS:
            return None
        return {
            'table': normalized,
            'columns': list(SCHEMAS[normalized]),
            'column_count': len(SCHEMAS[normalized])
        }

    return {
        'tables': list(SCHEMAS.keys()),
        'table_count': len(SCHEMAS),
        'functions': list(ALLOWED_FUNCS.keys())
    }