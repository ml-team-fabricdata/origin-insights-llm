# Business
from src.sql.tools.business.pricing_tools import ALL_PRICING_TOOLS
from src.sql.tools.business.rankings_tools import ALL_RANKING_TOOLS
from src.sql.tools.business.intelligence_tools import ALL_INTELLIGENCE_TOOLS

# Content
from src.sql.tools.common.admin_tools import ALL_ADMIN_TOOLS
from src.sql.tools.common.validation_tools import ALL_VALIDATION_TOOLS

# Content
from src.sql.tools.content.metadata_tools import ALL_METADATA_TOOLS
from src.sql.tools.content.discovery_tools import ALL_DISCOVERY_TOOLS

# Platform
from src.sql.tools.platform.availability_tools import ALL_AVAILABILITY_TOOLS
from src.sql.tools.platform.presence_tools import ALL_PRESENCE_TOOLS

# Talent
from src.sql.tools.talent.actors_tools import ALL_ACTORS_TOOLS
from src.sql.tools.talent.directors_tools import ALL_DIRECTORS_TOOLS
from src.sql.tools.talent.collaborations_tools import ALL_COLLABORATIONS_TOOLS

ALL_BUSINESS_TOOLS = ALL_PRICING_TOOLS + ALL_RANKING_TOOLS + ALL_INTELLIGENCE_TOOLS
ALL_COMMON_TOOLS = ALL_ADMIN_TOOLS + ALL_VALIDATION_TOOLS
ALL_CONTENT_TOOLS = ALL_METADATA_TOOLS + ALL_DISCOVERY_TOOLS
ALL_PLATFORM_TOOLS = ALL_AVAILABILITY_TOOLS + ALL_PRESENCE_TOOLS
ALL_TALENT_TOOLS = ALL_ACTORS_TOOLS + ALL_DIRECTORS_TOOLS + ALL_COLLABORATIONS_TOOLS

# Combinar todas las herramientas en una lista plana
ALL_SQL_TOOLS = (ALL_BUSINESS_TOOLS + 
                 ALL_COMMON_TOOLS + 
                 ALL_CONTENT_TOOLS + 
                 ALL_PLATFORM_TOOLS + 
                 ALL_TALENT_TOOLS)