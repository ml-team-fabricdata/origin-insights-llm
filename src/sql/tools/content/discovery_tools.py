from langchain_core.tools import Tool
from src.sql.utils.constants_sql import *
from src.sql.modules.content.discovery import *

FILMOGRAPHY_UID_TOOL = Tool(
    name="answer_filmography_by_uid",
    func=get_filmography_by_uid,
    description="ONLY use after having UID confirmed by user. Returns filmography/profile information.",
)

TITLE_RATING_TOOL = Tool.from_function(
    name="get_title_rating",
    description=f"Rating/score for a title by UID optional country iso. {POLICY_TITLE}",
    func=get_title_rating,
)

ALL_DISCOVERY_TOOLS = [
    FILMOGRAPHY_UID_TOOL,
    TITLE_RATING_TOOL
]