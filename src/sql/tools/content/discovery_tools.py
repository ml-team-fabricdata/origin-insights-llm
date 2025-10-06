from langchain_core.tools import Tool
from src.sql.utils.constants_sql import *
from src.sql.modules.content.discovery import *

FILMOGRAPHY_UID_TOOL = Tool(
    name="answer_filmography_by_uid",
    func=get_filmography_by_uid,
    description="Get complete filmography and profile information for a specific title using its UID. Returns detailed metadata including title, type, year, duration, and countries. ONLY use after UID has been confirmed or validated.",
)

TITLE_RATING_TOOL = Tool.from_function(
    name="get_title_rating",
    description=(
        f"Get rating and popularity metrics for a title by UID. "
        f"Supports global ratings or country/region-specific ratings (provide ISO-2 country code OR region name like 'LATAM', 'EU'). "
        f"Supports regions: LATAM/latin_america, EU, north_america, south_america, europe, asia, africa, oceania. "
        f"Returns total hits, average hits, and hit count from popularity data. {POLICY_TITLE}"
    ),
    func=get_title_rating,
)

ALL_DISCOVERY_TOOLS = [
    FILMOGRAPHY_UID_TOOL,
    TITLE_RATING_TOOL
]