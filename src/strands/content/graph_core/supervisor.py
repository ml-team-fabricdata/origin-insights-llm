from src.strands.content.nodes.prompt_content import CONTENT_PROMPT
from src.strands.core.nodes.supervisor_helpers import (
    main_supervisor,
    create_route_from_supervisor,
    format_response
)
from src.strands.core.factories.classifier_factory import create_simple_classifier
from .state import State


content_classifier = create_simple_classifier(
    name="content",
    prompt=CONTENT_PROMPT,
    valid_options=["METADATA", "DISCOVERY"]
)

route_from_main_supervisor = create_route_from_supervisor("content_classifier")