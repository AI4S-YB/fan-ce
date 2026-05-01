# libs/tool_registry.py
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional


@dataclass
class ToolDefinition:
    name: str
    description: str
    parameters: dict  # JSON Schema
    execute: Callable  # async (db, arguments, user) -> dict
    require_admin: bool = True

    def to_openai_tool(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, ToolDefinition] = {}

    def register(self, tool: ToolDefinition) -> None:
        if tool.name in self._tools:
            raise ValueError(f"Tool '{tool.name}' is already registered")
        self._tools[tool.name] = tool

    def register_many(self, tools: List[ToolDefinition]) -> None:
        for tool in tools:
            self.register(tool)

    def get_all(self, admin: bool = True) -> List[ToolDefinition]:
        return [t for t in self._tools.values() if not t.require_admin or admin]

    def get(self, name: str) -> Optional[ToolDefinition]:
        return self._tools.get(name)

    def to_openai_tools(self, admin: bool = True) -> List[dict]:
        return [t.to_openai_tool() for t in self.get_all(admin=admin)]

    async def execute(self, name: str, arguments: dict, db, user) -> dict:
        tool = self._tools.get(name)
        if not tool:
            raise ValueError(f"Unknown tool: {name}")
        return await tool.execute(db=db, arguments=arguments, user=user)


# Global singleton
tool_registry = ToolRegistry()
