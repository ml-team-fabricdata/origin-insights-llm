from src.strands.platform.nodes.prompt_platform import PLATFORM_PROMPT
from src.strands.utils.supervisor_helpers import (
    main_supervisor,
    create_route_from_supervisor,
    format_response
)
from src.strands.utils.classifier_factory import create_simple_classifier
from .state import State


platform_classifier = create_simple_classifier(
    name="platform",
    prompt=PLATFORM_PROMPT,
    valid_options=["AVAILABILITY", "PRESENCE"],
    default_option="PRESENCE"
)

route_from_main_supervisor = create_route_from_supervisor("platform_node")