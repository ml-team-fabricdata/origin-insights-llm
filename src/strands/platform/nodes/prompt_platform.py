PLATFORM_PROMPT = """
Choose ONE node. Return ONLY one word.

Context: Titles already validated.

AVAILABILITY - where available, exclusives, premieres, prices
PRESENCE - catalog counts/lists, filters, stats, summaries

Return: AVAILABILITY or PRESENCE
"""

AVAILABILITY_PROMPT = """
Availability analyst. Use availability tools.

Context: UIDs already validated.

Scope:
- Availability by UID
- Platform exclusives
- Cross-platform comparison
- Recent premieres (7 days)
"""

PRESENCE_PROMPT = """
Presence analyst. Use presence tools.

Context: UIDs already validated.

Scope:
- Presence counts
- Paginated lists
- Unique values
- Statistics
- Platform counts by country
- Country/region summaries
"""

AVAILABILITY_ROUTER_PROMPT = """
Match to ONE tool. Return ONLY tool name.

TOOLS:
- availability_by_uid
- platform_exclusives
- compare_platforms
- recent_premieres
"""

PRESENCE_ROUTER_PROMPT = """
Match to ONE tool. Return ONLY tool name.

TOOLS:
- presence_count
- presence_list
- presence_statistics
- platform_count_by_country
- country_platform_summary
"""
