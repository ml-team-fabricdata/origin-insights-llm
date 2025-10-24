"""Talent Router Configurations

Tool sets and configurations for talent domain routers.
"""

from app.strands.talent.nodes.prompt_talent import (
    ACTORS_ROUTER_PROMPT,
    DIRECTORS_ROUTER_PROMPT,
    COLLABORATIONS_ROUTER_PROMPT
)


ACTORS_TOOLS = {
    "get_actor_filmography",
    "get_actor_coactors",
    "get_actor_coactors_by_name"
}

DIRECTORS_TOOLS = {
    "get_director_filmography",
    "get_director_collaborators",
}

COLLABORATIONS_TOOLS = {
    "find_common_titles_actor_director",
    "get_common_projects_actor_director_by_name"
}
