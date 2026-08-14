"""Version configurations - defines what each agent version has access to."""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Any

from dotenv import load_dotenv

from ratchet.agent import tools_v0, tools_v2
from ratchet.agent.permissions import create_permission_checker
from ratchet.agent.verification import create_verifier

load_dotenv()


@dataclass
class VersionConfig:
    """Configuration for a specific agent version."""
    version: str
    api_key: str
    agents_md: str | None = None
    permission_checker: Callable | None = None
    verifier: Callable | None = None
    scenario_config: dict = field(default_factory=dict)
    
    def get_tool_definitions(self) -> list[dict]:
        """Get the tool definitions for this version."""
        if self.version in ("v0", "v1"):
            return tools_v0.TOOL_DEFINITIONS
        else:
            return tools_v2.TOOL_DEFINITIONS
    
    def get_tool_executor(self, sandbox_path: Path) -> Callable[[str, dict], Any]:
        """Get a tool executor function for this version."""
        if self.version in ("v0", "v1"):
            return tools_v0.create_executor(sandbox_path)
        else:
            return tools_v2.create_executor(sandbox_path, self.permission_checker)
    
    def handle_done_claim(self, content: str, sandbox_path: Path) -> dict:
        """Handle when agent claims to be done via text (not tool call)."""
        if self.version == "v3" and self.verifier:
            result = self.verifier(sandbox_path)
            return {"verified": result["passed"], "reason": result.get("reason", "")}
        return {"verified": True, "reason": "No verification required"}
    
    def run_verification(self, sandbox_path: Path) -> dict:
        """Run verification (V3 only)."""
        if self.verifier:
            return self.verifier(sandbox_path)
        return {"passed": True, "reason": "No verification configured"}


def create_version_config(
    version: str,
    scenario_config: dict | None = None,
) -> VersionConfig:
    """Factory function to create a version configuration."""
    api_key = os.environ.get("DEEPSEEK_API_KEY", "")
    if not api_key:
        raise ValueError("DEEPSEEK_API_KEY environment variable not set")
    
    scenario_config = scenario_config or {}
    
    agents_md = None
    if version in ("v1", "v2", "v3"):
        agents_md_path = Path(__file__).parent.parent.parent / "AGENTS.md"
        if agents_md_path.exists():
            agents_md = agents_md_path.read_text()
    
    permission_checker = None
    if version in ("v2", "v3"):
        additional_patterns = scenario_config.get("protected_patterns", [])
        permission_checker = create_permission_checker(additional_patterns)
    
    verifier = None
    if version == "v3" and scenario_config:
        verifier = create_verifier(scenario_config)
    
    return VersionConfig(
        version=version,
        api_key=api_key,
        agents_md=agents_md,
        permission_checker=permission_checker,
        verifier=verifier,
        scenario_config=scenario_config,
    )
