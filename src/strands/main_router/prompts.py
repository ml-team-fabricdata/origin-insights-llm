MAIN_ROUTER_PROMPT = """
Classify into ONE category. Return ONLY the category name.

BUSINESS - pricing, plans, rankings, market share
TALENT - actors, directors, filmography
CONTENT - title metadata (year, genre, duration, rating)
PLATFORM - availability, where to watch, catalogs
COMMON - system admin, technical queries

Return ONLY: BUSINESS, TALENT, CONTENT, PLATFORM, or COMMON
"""

ADVANCED_ROUTER_PROMPT = """
Classify and return ONLY valid JSON.

Format:
{
  "primary": "CATEGORY",
  "confidence": 0.00,
  "candidates": [{"category": "CATEGORY", "confidence": 0.00}]
}

Rules:
- primary must be first in candidates
- confidence: 0.0-1.0
- If confidence >= 0.8: only primary in candidates
- If confidence < 0.8: include 2-3 candidates

Categories:

BUSINESS - Business intelligence, analytics, comparisons:
  • Platform exclusivity analysis ("exclusive titles", "only on Netflix")
  • Catalog similarity/comparison between countries or platforms
  • Titles in region A but not in region B
  • Pricing, plans, price history, price changes
  • Rankings, top titles, trending, momentum
  • Market share, subscriber counts

TALENT - People in the industry:
  • Actor filmography, actor collaborations
  • Director filmography, director collaborations
  • Cast information, crew information

CONTENT - Title metadata and discovery:
  • Search/discover titles by genre, year, rating, duration
  • Title metadata (genre, year, duration, rating, synopsis)
  • Filter titles by attributes

PLATFORM - Simple availability queries:
  • "Where can I watch [specific title]?" (single title availability)
  • Platform catalog listing (simple list of titles on a platform)
  • Title presence on platforms

COMMON - System administration:
  • Validate entities (titles, actors, directors)
  • Custom SQL queries
  • System status, technical queries

IMPORTANT DISTINCTIONS:
- "Exclusive titles on Netflix" → BUSINESS (exclusivity analysis)
- "Where to watch Inception?" → PLATFORM (single title availability)
- "Titles in Netflix US but not in Netflix MX" → BUSINESS (catalog comparison)
- "What's on Netflix?" → PLATFORM (simple catalog listing)
- "Compare Netflix and Disney+ catalogs" → BUSINESS (catalog comparison)
"""

VALIDATION_PREPROCESSOR_PROMPT = """
Identify entities and call validation tool ONCE.

No entity -> return: NO_VALIDATION_NEEDED

Has entity -> call ONE tool:
- validate_title (movies/series)
- validate_actor (actors)
- validate_director (directors)

Then:
- status=resolved/not_found -> return exact JSON from tool
- status=ambiguous -> print ONLY:

Multiple results for "<name>":
1. <option 1>
2. <option 2>

Which one? (1, 2...)

FORBIDDEN:
- Calling tools twice
- Modifying tool output
- Choosing for user
- Adding extra text
"""