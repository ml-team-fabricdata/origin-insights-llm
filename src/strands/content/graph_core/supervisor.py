from src.strands.content.nodes.prompt_content import CONTENT_PROMPT
from src.strands.utils.supervisor_helpers import (
    main_supervisor,
    create_route_from_supervisor,
    format_response
)
from src.strands.utils.classifier_factory import create_simple_classifier
from .state import State


content_classifier = create_simple_classifier(
    name="content",
    prompt=CONTENT_PROMPT,
    valid_options=["METADATA", "DISCOVERY"],
    default_option="METADATA"
)

route_from_main_supervisor = create_route_from_supervisor("content_classifier")