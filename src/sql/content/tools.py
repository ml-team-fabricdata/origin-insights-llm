from langchain_core.tools import Tool

from src.sql.constants_sql import *
from src.sql.content.metadata import *
from src.sql.content.discovery import *

FILMOGRAPHY_UID_TOOL = Tool(
    name="answer_filmography_by_uid",
    func=get_filmography_by_uid,
    description="ONLY use after having UID confirmed by user. Returns filmography/profile information.",
)

TITLE_RATING_TOOL = Tool.from_function(
    name="get_title_rating",
    description=f"Rating/score for a title by UID. {POLICY_TITLE}",
    func=get_title_rating,
)

DISCOVERY_TOOLS = [
    FILMOGRAPHY_UID_TOOL,
    TITLE_RATING_TOOL
]