"""Low-level tools for V0 and V1 - no restrictions."""

import os
import subprocess
from pathlib import Path
from typing import Any


TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read the contents of a file",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to the file (relative to sandbox root)",
                    },
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Write content to a file (creates or overwrites)",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to the file (relative to sandbox root)",
                    },
                    "content": {
                        "type": "string",
                        "description": "Content to write to the file",
                    },
                },
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "delete_file",
            "description": "Delete a file or directory",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to delete (relative to sandbox root)",
                    },
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_dir",
            "description": "List contents of a directory with file metadata",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to directory (relative to sandbox root, use '.' for root)",
                    },
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_shell",
            "description": "Run a shell command in the sandbox directory",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "Shell command to execute",
                    },
                },
                "required": ["command"],
            },
        },
    },
]


def create_executor(sandbox_path: Path):
    """Create a tool executor bound to the given sandbox path."""
    
    def execute(tool_name: str, args: dict) -> Any:
        if tool_name == "read_file":
            return _read_file(sandbox_path, args.get("path", ""))
        elif tool_name == "write_file":
            return _write_file(sandbox_path, args.get("path", ""), args.get("content", ""))
        elif tool_name == "delete_file":
            return _delete_file(sandbox_path, args.get("path", ""))
        elif tool_name == "list_dir":
            return _list_dir(sandbox_path, args.get("path", "."))
        elif tool_name == "run_shell":
            return _run_shell(sandbox_path, args.get("command", ""))
        else:
            return {"error": f"Unknown tool: {tool_name}"}
    
    return execute


def _resolve_path(sandbox_path: Path, relative_path: str) -> Path:
    """Resolve a relative path within the sandbox."""
    if relative_path.startswith("/"):
        relative_path = relative_path[1:]
    full_path = (sandbox_path / relative_path).resolve()
    if not str(full_path).startswith(str(sandbox_path.resolve())):
        raise ValueError(f"Path escapes sandbox: {relative_path}")
    return full_path


def _read_file(sandbox_path: Path, path: str) -> dict:
    """Read file contents."""
    try:
        full_path = _resolve_path(sandbox_path, path)
        if not full_path.exists():
            return {"error": f"File not found: {path}"}
        if full_path.is_dir():
            return {"error": f"Path is a directory: {path}"}
        content = full_path.read_text()
        return {"content": content, "size": len(content)}
    except Exception as e:
        return {"error": str(e)}


def _write_file(sandbox_path: Path, path: str, content: str) -> dict:
    """Write content to a file."""
    try:
        full_path = _resolve_path(sandbox_path, path)
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text(content)
        return {"success": True, "path": path, "size": len(content)}
    except Exception as e:
        return {"error": str(e)}


def _delete_file(sandbox_path: Path, path: str) -> dict:
    """Delete a file or directory."""
    try:
        full_path = _resolve_path(sandbox_path, path)
        if not full_path.exists():
            return {"error": f"Path not found: {path}"}
        if full_path.is_dir():
            import shutil
            shutil.rmtree(full_path)
            return {"success": True, "deleted": path, "type": "directory"}
        else:
            full_path.unlink()
            return {"success": True, "deleted": path, "type": "file"}
    except Exception as e:
        return {"error": str(e)}


def _list_dir(sandbox_path: Path, path: str) -> dict:
    """List directory contents with metadata."""
    try:
        full_path = _resolve_path(sandbox_path, path)
        if not full_path.exists():
            return {"error": f"Directory not found: {path}"}
        if not full_path.is_dir():
            return {"error": f"Not a directory: {path}"}
        
        entries = []
        for entry in full_path.iterdir():
            stat = entry.stat()
            entries.append({
                "name": entry.name,
                "type": "directory" if entry.is_dir() else "file",
                "size": stat.st_size if entry.is_file() else None,
                "modified": stat.st_mtime,
            })
        
        entries.sort(key=lambda x: (x["type"] == "file", x["name"]))
        return {"path": path, "entries": entries}
    except Exception as e:
        return {"error": str(e)}


def _run_shell(sandbox_path: Path, command: str) -> dict:
    """Run a shell command in the sandbox."""
    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=sandbox_path,
            capture_output=True,
            text=True,
            timeout=30,
        )
        return {
            "stdout": result.stdout,
            "stderr": result.stderr,
            "exit_code": result.returncode,
        }
    except subprocess.TimeoutExpired:
        return {"error": "Command timed out after 30 seconds"}
    except Exception as e:
        return {"error": str(e)}
