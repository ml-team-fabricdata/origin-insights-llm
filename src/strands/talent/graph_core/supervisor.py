from src.strands.talent.nodes.prompt_talent import TALENT_PROMPT
from src.strands.core.nodes.supervisor_helpers import (
    main_supervisor,
    create_route_from_supervisor,
    format_response
)
from src.strands.core.factories.classifier_factory import create_simple_classifier
from .state import State
from typing import Literal


talent_classifier = create_simple_classifier(
    name="talent",
    prompt=TALENT_PROMPT,
    valid_options=["ACTORS", "DIRECTORS", "COLLABORATIONS"]
)

route_from_main_supervisor = create_route_from_supervisor("talent_classifier")