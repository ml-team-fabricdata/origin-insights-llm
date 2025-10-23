from app.strands.common.nodes.prompt_common import GOVERNANCE_PROMPT
from app.strands.core.nodes.supervisor_helpers import (
    main_supervisor,
    create_route_from_supervisor,
    format_response
)
from app.strands.core.factories.classifier_factory import create_simple_classifier
from .state import State


governance_classifier = create_simple_classifier(
    name="governance",
    prompt=GOVERNANCE_PROMPT,
    valid_options=["ADMIN", "VALIDATION"]
)

route_from_main_supervisor = create_route_from_supervisor("governance_node")