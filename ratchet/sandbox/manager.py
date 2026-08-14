"""Sandbox manager - creates isolated environments for each run."""

import shutil
import tempfile
import hashlib
from pathlib import Path
from datetime import datetime


class SandboxManager:
    """Manages sandbox creation and cleanup for test runs."""
    
    def __init__(self, scenarios_base_path: Path):
        self.scenarios_base_path = scenarios_base_path
        self.active_sandboxes: list[Path] = []
    
    def create_sandbox(self, scenario_name: str, is_practice: bool = False) -> Path:
        """
        Create a fresh sandbox by copying a scenario's initial state.
        
        Returns the path to the sandbox directory.
        """
        subdir = "practice" if is_practice else "scenarios"
        scenario_path = self.scenarios_base_path / subdir / scenario_name
        
        if not scenario_path.exists():
            raise ValueError(f"Scenario not found: {scenario_name} (looked in {scenario_path})")
        
        sandbox_id = f"{scenario_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{_short_hash()}"
        sandbox_path = Path(tempfile.gettempdir()) / "ratchet_sandboxes" / sandbox_id
        
        if sandbox_path.exists():
            shutil.rmtree(sandbox_path)
        
        initial_state_path = scenario_path / "initial_state"
        if initial_state_path.exists():
            shutil.copytree(initial_state_path, sandbox_path)
        else:
            shutil.copytree(scenario_path, sandbox_path, ignore=shutil.ignore_patterns("scenario.yaml", "*.md"))
        
        self.active_sandboxes.append(sandbox_path)
        return sandbox_path
    
    def cleanup_sandbox(self, sandbox_path: Path):
        """Remove a sandbox directory."""
        if sandbox_path.exists():
            shutil.rmtree(sandbox_path)
        if sandbox_path in self.active_sandboxes:
            self.active_sandboxes.remove(sandbox_path)
    
    def cleanup_all(self):
        """Clean up all active sandboxes."""
        for sandbox_path in self.active_sandboxes.copy():
            self.cleanup_sandbox(sandbox_path)
    
    def compute_file_checksums(self, sandbox_path: Path, file_list: list[str]) -> dict[str, str]:
        """Compute MD5 checksums for a list of files."""
        checksums = {}
        for file_path in file_list:
            full_path = sandbox_path / file_path
            if full_path.exists() and full_path.is_file():
                checksums[file_path] = hashlib.md5(full_path.read_bytes()).hexdigest()
        return checksums


def _short_hash() -> str:
    """Generate a short random hash for uniqueness."""
    import random
    import string
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
