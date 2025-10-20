CONTENT_PROMPT = """
Choose ONE node. Return ONLY one word.

Context: Titles already validated.

METADATA - counts, unique values, stats, searches
DISCOVERY - filmography by UID, ratings

Return: METADATA or DISCOVERY
"""

METADATA_PROMPT = """
Catalog metadata analyst. Use metadata tools.

Context: Titles already validated.

Scope:
- Total counts
- Unique values
- Statistics
- Advanced searches
"""

DISCOVERY_PROMPT = """
Content discovery analyst. Use discovery tools.

Context: UIDs already validated.

Scope:
- Filmography by UID
- Ratings by UID (global/region)
"""

METADATA_ROUTER_PROMPT = """
Match to ONE tool. Return ONLY tool name.

TOOLS:
- simple_all_count
- simple_all_list
- simple_all_stats
- simple_all_query
"""

DISCOVERY_ROUTER_PROMPT = """
Match to ONE tool. Return ONLY tool name.

TOOLS:
- filmography_by_uid
- title_rating
- multiple_titles_info
"""