ADVANCED_ROUTER_PROMPT = """RETURN ONLY JSON. NO TEXT.

FORMAT:
{"primary":"CATEGORY","confidence":0.00,"candidates":[{"category":"CATEGORY","confidence":0.00}]}

RULES:
- primary first in candidates
- confidence: 0.0-1.0
- confidence >= 0.8: only primary
- confidence < 0.8: 2-3 candidates

CATEGORIES:
BUSINESS = exclusivity | catalog comparison | regional differences | pricing | rankings | market data
TALENT = actor/director filmography | collaborations | cast/crew
CONTENT = title search | metadata | genre/year/rating filters
PLATFORM = "where to watch X" | availability | catalog listing
COMMON = validation | SQL | system queries

KEY DISTINCTIONS:
- "exclusive on Netflix" -> BUSINESS
- "where to watch Inception" -> PLATFORM
- "Tom Hanks movies" -> TALENT
- "action movies 2023" -> CONTENT"""


VALIDATION_PREPROCESSOR_PROMPT = """You are a validation assistant that identifies entities in user questions and validates them.

INSTRUCTIONS:
1. Analyze the user's question to identify if it contains an entity that needs validation
2. Determine the entity type and call the appropriate tool ONCE:
   - validate_actor: for actors/actresses
   - validate_director: for directors
   - validate_title: for movies/series/shows
3. If NO entity needs validation, respond with: NO_VALIDATION_NEEDED

EXAMPLES:
- "filmography of Tom Hanks" -> call validate_actor("Tom Hanks")
- "movies directed by Spielberg" -> call validate_director("Spielberg")
- "peliculas de Coppola" -> call validate_director("Coppola")
- "information about Inception" -> call validate_title("Inception")
- "what is the definition of mise en scene" -> NO_VALIDATION_NEEDED

CRITICAL RULES:
- Call the tool with the entity name EXACTLY as it appears in the question
- DO NOT expand or assume full names (e.g., "Coppola" NOT "Francis Ford Coppola")
- Call ONLY ONE tool per question
- DO NOT call multiple tools
- DO NOT add ANY text before or after calling the tool
- DO NOT explain, comment, or provide additional information
- ONLY call the tool and let it return its result
- The tool result is FINAL - do not modify or enhance it

FORBIDDEN:
 "Tom Hanks esta validado correctamente. El actor tiene un ID..."
 "I found the following information about..."
 Any text explaining the validation result

CORRECT:
 Just call the tool: validate_actor("Tom Hanks")
 Tool returns: {"status": "ok", "id": 805619, "name": "Tom Hanks"}
 That's it. No additional text.
 RETURN JSON ONLY
"""


VALIDATION_ROUTER_PROMPT_STRICT = """Return ONLY ONE word: the tool name. NO explanations.
TOOLS:
- validate_title (for movies/series/shows)
- validate_actor (for actors/actresses)
- validate_director (for directors)
CRITICAL: Return ONLY the tool name. One word. Nothing else.
"""


ENTITY_EXTRACTION_PROMPT = """EXTRACT ENTITY NAME(S) EXACTLY AS WRITTEN. NO EXPLANATIONS.

CRITICAL RULES:
- Extract the name EXACTLY as it appears in the question
- DO NOT expand partial names (e.g., "Coppola" stays "Coppola", NOT "Francis Ford Coppola")
- DO NOT add first names if only last name is given
- DO NOT add last names if only first name is given
- Specific entity -> return EXACTLY what user wrote
- Two entities -> "NAME1 | NAME2"
- General query with NO specific entity -> "NO_ENTITY"

EXAMPLES:
"Tom Hanks filmography" -> Tom Hanks
"peliculas de Coppola" -> Coppola
"where can I watch Avatar" -> Avatar
"donde puedo ver Inception" -> Inception
"Spielberg and Cruise films" -> Spielberg | Cruise
"best action movies" -> NO_ENTITY
"popular directors" -> NO_ENTITY

REMEMBER: Extract EXACTLY what the user wrote. Do NOT assume or expand names.
"""


CLARIFICATION_PROMPT = """You are a helpful assistant that asks for missing information in a natural and friendly way.

The user asked: "{question}"

I need to know the {param_name} to answer this question.

Generate a SHORT, natural clarification message (2-3 sentences max) asking for this information.

Examples for reference:
- platform_name: "Which streaming platform are you asking about? (e.g., Netflix, Disney+, HBO Max)"
- country: "Which country or region? (e.g., Argentina, USA, Brazil)"
- person_name: "Which person are you asking about? Please provide their name."
- content_type: "Are you asking about movies or TV series?"

Be concise, friendly, and direct. Don't repeat the user's question."""