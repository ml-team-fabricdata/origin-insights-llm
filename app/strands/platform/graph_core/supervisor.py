from app.strands.platform.nodes.prompt_platform import PLATFORM_PROMPT
from app.strands.core.nodes.supervisor_helpers import (
    main_supervisor,
    create_route_from_supervisor,
    format_response
)
from app.strands.core.factories.classifier_factory import create_simple_classifier
from .state import State


platform_classifier = create_simple_classifier(
    name="platform",
    prompt=PLATFORM_PROMPT,
    valid_options=["AVAILABILITY", "PRESENCE"]
)

route_from_main_supervisor = create_route_from_supervisor("platform_node")