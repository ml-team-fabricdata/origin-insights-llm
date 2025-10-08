
from src.sql.modules.platform.availability import *
from src.sql.modules.platform.presence import *
from src.strands.platform.prompt import AVAILABILITY_PROMPT, PRESENCE_PROMPT
from strands import Agent


MODEL_TOOL = "us.anthropic.claude-3-5-haiku-20241022-v1:0"


AVAILABILITY_AGENT = Agent(
    model=MODEL_TOOL,
    tools=[get_availability_by_uid, get_platform_exclusives,compare_platforms_for_title,
           get_recent_premieres_by_country],
    system_prompt= AVAILABILITY_PROMPT
)

PRESENCE_AGENT = Agent(
    model=MODEL_TOOL,
    tools=[presence_count,
           presence_list, presence_distinct, presence_statistics, platform_count_by_country,
           country_platform_summary],
    system_prompt = PRESENCE_PROMPT
)
