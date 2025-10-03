# app/modules/availability.py
import datetime as dt
from typing import Any, Dict, List, Optional, Tuple
from infra.db import run_sql
from infra.config import SETTINGS

def fetch_availability_by_uid(uid: str, iso2: Optional[str] = None, with_prices: bool = False) -> List[Dict[str, Any]]:
    if SETTINGS.offline_mode or not uid:
        return []
    today = dt.date.today()
    params: Dict[str, Any] = {"u": uid, "today": today}
    where_country = ""
    if iso2:
        params["iso"] = str(iso2)
        where_country = """
          AND (
                COALESCE(ncp.iso_alpha2, '') ILIKE %(iso)s
             OR COALESCE(ncp.platform_country, '') ILIKE %(iso)s
          )
        """
    price_join = price_cols = ""
    if with_prices:
        price_join = """
        LEFT JOIN LATERAL (
          SELECT p.price, p.currency, COALESCE(p.created_at, p.entered_on, p.out_on) AS last_seen
          FROM ms.new_cp_presence_prices p
          WHERE p.hash_unique = ncp.hash_unique
          ORDER BY COALESCE(p.created_at, p.entered_on, p.out_on) DESC NULLS LAST
          LIMIT 1
        ) pr ON TRUE
        """
        price_cols = ", pr.price, pr.currency, pr.last_seen"

    sql = f"""
    SELECT ncp.platform_name AS platform,
           ncp.iso_alpha2    AS country_iso2,
           ncp.plan_name     AS plan,
           ncp.type,
           ncp.enter_on,
           ncp.out_on        AS leave_on,
           ncp.permalink,
           ncp.imdb_id,
           ncp.uid,
           ncp.hash_unique
           {price_cols}
    FROM ms.new_cp_presence ncp
    {price_join}
    WHERE ncp.uid = %(u)s
      {where_country}
      AND (ncp.enter_on IS NULL OR ncp.enter_on <= %(today)s)
      AND (ncp.out_on   IS NULL OR ncp.out_on   >= %(today)s)
    ORDER BY ncp.platform_name ASC, ncp.plan_name ASC, ncp.enter_on DESC NULLS LAST;
    """
    return run_sql(sql, params)

def render_availability_summary(rows: List[Dict[str, Any]], country_pretty: str = "", with_prices: bool = False) -> str:
    if not rows:
        return "No registramos disponibilidad en este momento."
    groups: Dict[Tuple[str, str], List[Dict[str, Any]]] = {}
    for r in rows:
        plat = r.get("platform") or "-"
        plan = r.get("plan") or "-"
        groups.setdefault((plat, plan), []).append(r)
    lines = []
    if country_pretty:
        lines.append(f"**{country_pretty}** - {len(groups)} plataforma(s):")
    for (plat, plan), items in groups.items():
        head = f"- **{plat}**"
        if plan and plan != "-":
            head += f" - {plan}"
        sample = items[0]
        if with_prices and sample.get("price") is not None:
            head += f" - {sample.get('price')} {sample.get('currency') or ''}".strip()
        if sample.get("permalink"):
            head += f" - {sample.get('permalink')}"
        lines.append(head)
    return "\n".join(lines)

def render_availability(rows, lang, country_pretty, include_details=False, include_prices=False) -> str:
    return render_availability_summary(rows, country_pretty=country_pretty, with_prices=include_prices)