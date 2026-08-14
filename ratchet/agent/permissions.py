"""Permission layer for V2+ - enforces path restrictions."""

from pathlib import Path
from fnmatch import fnmatch
from typing import Callable


DEFAULT_PROTECTED_PATTERNS = [
    "**/config/prod/**",
    "**/.env",
    "**/.env.*",
    "**/.secrets",
    "**/.secrets/**",
    "**/node_modules/**",
    "**/.git/**",
    "**/credentials*",
    "**/*secret*",
]


def create_permission_checker(
    additional_patterns: list[str] | None = None,
) -> Callable[[str, dict, Path], tuple[bool, str]]:
    """
    Create a permission checker function.
    
    Returns a function that takes (tool_name, tool_args, sandbox_path) 
    and returns (allowed: bool, reason: str).
    """
    patterns = DEFAULT_PROTECTED_PATTERNS.copy()
    if additional_patterns:
        patterns.extend(additional_patterns)
    
    def check_permission(tool_name: str, tool_args: dict, sandbox_path: Path) -> tuple[bool, str]:
        paths_to_check = _extract_paths_from_args(tool_name, tool_args)
        
        for path in paths_to_check:
            normalized = _normalize_path(path)
            for pattern in patterns:
                if _matches_pattern(normalized, pattern):
                    return False, f"Path '{path}' is protected (matches pattern: {pattern})"
        
        return True, ""
    
    return check_permission


def _extract_paths_from_args(tool_name: str, args: dict) -> list[str]:
    """Extract all paths from tool arguments that need permission checking."""
    paths = []
    
    if "path" in args:
        paths.append(args["path"])
    if "source_glob" in args:
        base = args["source_glob"].split("*")[0].rstrip("/")
        if base:
            paths.append(base)
    if "dest_dir" in args:
        paths.append(args["dest_dir"])
    if "directory" in args:
        paths.append(args["directory"])
    if "archive_path" in args:
        paths.append(args["archive_path"])
    
    return paths


def _normalize_path(path: str) -> str:
    """Normalize a path for pattern matching."""
    path = path.strip()
    if path.startswith("/"):
        path = path[1:]
    if path.startswith("./"):
        path = path[2:]
    return path


def _matches_pattern(path: str, pattern: str) -> bool:
    """Check if a path matches a glob-like pattern."""
    if pattern.startswith("**/"):
        suffix_pattern = pattern[3:]
        if fnmatch(path, suffix_pattern):
            return True
        if fnmatch(path, pattern):
            return True
        parts = path.split("/")
        for i in range(len(parts)):
            subpath = "/".join(parts[i:])
            if fnmatch(subpath, suffix_pattern):
                return True
    else:
        if fnmatch(path, pattern):
            return True
    
    return False
