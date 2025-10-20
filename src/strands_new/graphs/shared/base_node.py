"""Base node implementation - MIGRATED."""

# TODO: Migrar desde src/strands/utils/base_node.py
# Este será el base para todos los executor nodes

class BaseExecutorNode:
    """Base class for executor nodes."""
    
    def __init__(self, node_name: str, tools_map: dict, router_fn, system_prompt: str, model: str):
        self.node_name = node_name
        self.tools_map = tools_map
        self.router_fn = router_fn
        self.system_prompt = system_prompt
        self.model = model
    
    async def execute(self, state: dict) -> dict:
        """Execute node logic."""
        # TODO: Implement
        pass
