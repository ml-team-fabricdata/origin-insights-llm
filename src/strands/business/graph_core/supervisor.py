from src.strands.business.nodes.prompt_business import BUSINESS_PROMPT
from src.strands.utils.supervisor_helpers import main_supervisor, create_route_from_supervisor, format_response
from src.strands.utils.classifier_factory import create_verbose_classifier
from .state import State
from typing import Literal


business_classifier = create_verbose_classifier(
    name="business",
    prompt=BUSINESS_PROMPT,
    valid_options=["PRICING", "RANKINGS", "INTELLIGENCE"],
    default_option="INTELLIGENCE"
)

route_from_main_supervisor = create_route_from_supervisor("business_classifier")