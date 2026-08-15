"""High-level tools for V2 and V3 - with built-in safety."""

import os
import subprocess
import shutil
import tarfile
import hashlib
from pathlib import Path
from datetime import datetime, timedelta
from typing import Any
from fnmatch import fnmatch


TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "list_directory",
            "description": "List contents of a directory with file metadata",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to directory (relative to sandbox root, use '.' for root)",
                    },
                    "recursive": {
                        "type": "boolean",
                        "description": "Whether to list recursively (default: false)",
                    },
                },
                "required": ["path"],
            },
        },
    },
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
            "name": "reorganize_files",
            "description": "Move files matching a pattern to a destination directory, organized by criteria",
            "parameters": {
                "type": "object",
                "properties": {
                    "source_glob": {
                        "type": "string",
                        "description": "Glob pattern for source files (e.g., '*.jpg', 'downloads/*')",
                    },
                    "dest_dir": {
                        "type": "string",
                        "description": "Destination directory path",
                    },
                    "criteria": {
                        "type": "string",
                        "enum": ["type", "date", "none"],
                        "description": "Organization criteria: 'type' (by extension), 'date' (by YYYY-MM), 'none' (flat)",
                    },
                    "confirm": {
                        "type": "boolean",
                        "description": "Set to true to execute after seeing preview (default: false for dry-run)",
                    },
                },
                "required": ["source_glob", "dest_dir", "criteria"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "archive_logs",
            "description": "Compress log files older than specified days into a tar.gz archive",
            "parameters": {
                "type": "object",
                "properties": {
                    "source_glob": {
                        "type": "string",
                        "description": "Glob pattern for log files (e.g., 'logs/*.log')",
                    },
                    "archive_path": {
                        "type": "string",
                        "description": "Path for the output archive (e.g., 'archive/old_logs.tar.gz')",
                    },
                    "older_than_days": {
                        "type": "integer",
                        "description": "Only archive files older than this many days",
                    },
                    "confirm": {
                        "type": "boolean",
                        "description": "Set to true to execute after seeing preview (default: false for dry-run)",
                    },
                },
                "required": ["source_glob", "archive_path", "older_than_days"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "delete_duplicates",
            "description": "Find and delete duplicate files in a directory",
            "parameters": {
                "type": "object",
                "properties": {
                    "directory": {
                        "type": "string",
                        "description": "Directory to scan for duplicates",
                    },
                    "keep": {
                        "type": "string",
                        "enum": ["newest", "oldest", "largest"],
                        "description": "Which duplicate to keep",
                    },
                    "confirm": {
                        "type": "boolean",
                        "description": "Set to true to execute after seeing preview (default: false for dry-run)",
                    },
                },
                "required": ["directory", "keep"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_tests",
            "description": "Run the test suite in the sandbox",
            "parameters": {
                "type": "object",
                "properties": {
                    "test_command": {
                        "type": "string",
                        "description": "Test command to run (default: 'pytest' or detected from project)",
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_config",
            "description": "Update a value in a YAML or JSON config file",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to config file",
                    },
                    "key": {
                        "type": "string",
                        "description": "Key to update (use dot notation for nested: 'database.host')",
                    },
                    "value": {
                        "type": "string",
                        "description": "New value to set",
                    },
                },
                "required": ["path", "key", "value"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "git_commit",
            "description": "Stage all changes and create a git commit",
            "parameters": {
                "type": "object",
                "properties": {
                    "message": {
                        "type": "string",
                        "description": "Commit message",
                    },
                },
                "required": ["message"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "delete_files",
            "description": "Delete files matching a glob pattern (with permission checking and dry-run)",
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {
                        "type": "string",
                        "description": "Glob pattern for files to delete (e.g., '*.tmp', 'config/dev/*.bak')",
                    },
                    "confirm": {
                        "type": "boolean",
                        "description": "Set to true to execute after seeing preview (default: false for dry-run)",
                    },
                },
                "required": ["pattern"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "report_done",
            "description": "Report that the task is complete. In V3, this triggers verification.",
            "parameters": {
                "type": "object",
                "properties": {
                    "summary": {
                        "type": "string",
                        "description": "Summary of what was accomplished",
                    },
                },
                "required": ["summary"],
            },
        },
    },
]


class DryRunState:
    """Track pending dry-run operations for confirmation."""
    def __init__(self):
        self.pending = {}
    
    def set_pending(self, operation_id: str, data: dict):
        self.pending[operation_id] = data
    
    def get_pending(self, operation_id: str) -> dict | None:
        return self.pending.get(operation_id)
    
    def clear_pending(self, operation_id: str):
        self.pending.pop(operation_id, None)


def create_executor(sandbox_path: Path, permission_checker=None):
    """Create a tool executor bound to the given sandbox path."""
    dry_run_state = DryRunState()
    
    def execute(tool_name: str, args: dict) -> Any:
        if tool_name == "list_directory":
            return _list_directory(sandbox_path, args.get("path", "."), args.get("recursive", False))
        elif tool_name == "read_file":
            return _read_file(sandbox_path, args.get("path", ""))
        elif tool_name == "reorganize_files":
            return _reorganize_files(sandbox_path, args, dry_run_state, permission_checker)
        elif tool_name == "archive_logs":
            return _archive_logs(sandbox_path, args, dry_run_state, permission_checker)
        elif tool_name == "delete_duplicates":
            return _delete_duplicates(sandbox_path, args, dry_run_state, permission_checker)
        elif tool_name == "delete_files":
            return _delete_files(sandbox_path, args, dry_run_state, permission_checker)
        elif tool_name == "run_tests":
            return _run_tests(sandbox_path, args.get("test_command"))
        elif tool_name == "update_config":
            return _update_config(sandbox_path, args, permission_checker)
        elif tool_name == "git_commit":
            return _git_commit(sandbox_path, args.get("message", ""))
        elif tool_name == "report_done":
            return {"status": "done", "summary": args.get("summary", "")}
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


def _list_directory(sandbox_path: Path, path: str, recursive: bool) -> dict:
    """List directory contents."""
    try:
        full_path = _resolve_path(sandbox_path, path)
        if not full_path.exists():
            return {"error": f"Directory not found: {path}"}
        if not full_path.is_dir():
            return {"error": f"Not a directory: {path}"}
        
        entries = []
        if recursive:
            for entry in full_path.rglob("*"):
                rel_path = entry.relative_to(full_path)
                stat = entry.stat()
                entries.append({
                    "name": str(rel_path),
                    "type": "directory" if entry.is_dir() else "file",
                    "size": stat.st_size if entry.is_file() else None,
                    "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                })
        else:
            for entry in full_path.iterdir():
                stat = entry.stat()
                entries.append({
                    "name": entry.name,
                    "type": "directory" if entry.is_dir() else "file",
                    "size": stat.st_size if entry.is_file() else None,
                    "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                })
        
        entries.sort(key=lambda x: (x["type"] == "file", x["name"]))
        return {"path": path, "entries": entries, "count": len(entries)}
    except Exception as e:
        return {"error": str(e)}


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


def _reorganize_files(sandbox_path: Path, args: dict, dry_run_state: DryRunState, permission_checker) -> dict:
    """Reorganize files by pattern."""
    source_glob = args.get("source_glob", "")
    dest_dir = args.get("dest_dir", "")
    criteria = args.get("criteria", "none")
    confirm = args.get("confirm", False)
    
    try:
        matching_files = list(sandbox_path.glob(source_glob))
        matching_files = [f for f in matching_files if f.is_file()]
        
        if not matching_files:
            return {"message": "No files matched the pattern", "pattern": source_glob}
        
        moves = []
        for file in matching_files:
            rel_path = file.relative_to(sandbox_path)
            
            if criteria == "type":
                ext = file.suffix.lstrip(".") or "no_extension"
                target_dir = f"{dest_dir}/{ext}"
            elif criteria == "date":
                mtime = datetime.fromtimestamp(file.stat().st_mtime)
                target_dir = f"{dest_dir}/{mtime.strftime('%Y-%m')}"
            else:
                target_dir = dest_dir
            
            target_path = f"{target_dir}/{file.name}"
            moves.append({"from": str(rel_path), "to": target_path})
        
        if not confirm:
            op_id = f"reorg_{hash(source_glob + dest_dir)}"
            dry_run_state.set_pending(op_id, {"moves": moves})
            return {
                "dry_run": True,
                "operation_id": op_id,
                "preview": moves,
                "total_files": len(moves),
                "message": "Call again with confirm=true to execute",
            }
        
        executed = []
        for move in moves:
            src = _resolve_path(sandbox_path, move["from"])
            dst = _resolve_path(sandbox_path, move["to"])
            
            if permission_checker:
                allowed, reason = permission_checker("move", {"path": move["from"]}, sandbox_path)
                if not allowed:
                    return {"error": f"Permission denied for {move['from']}: {reason}"}
            
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src), str(dst))
            executed.append(move)
        
        return {"success": True, "moved": executed, "count": len(executed)}
    except Exception as e:
        return {"error": str(e)}


def _archive_logs(sandbox_path: Path, args: dict, dry_run_state: DryRunState, permission_checker) -> dict:
    """Archive old log files."""
    source_glob = args.get("source_glob", "")
    archive_path = args.get("archive_path", "")
    older_than_days = args.get("older_than_days", 30)
    confirm = args.get("confirm", False)
    
    try:
        cutoff = datetime.now() - timedelta(days=older_than_days)
        matching_files = list(sandbox_path.glob(source_glob))
        old_files = []
        
        for f in matching_files:
            if f.is_file():
                mtime = datetime.fromtimestamp(f.stat().st_mtime)
                if mtime < cutoff:
                    old_files.append({
                        "path": str(f.relative_to(sandbox_path)),
                        "modified": mtime.isoformat(),
                        "size": f.stat().st_size,
                    })
        
        if not old_files:
            return {"message": f"No files older than {older_than_days} days found", "pattern": source_glob}
        
        if not confirm:
            op_id = f"archive_{hash(source_glob + archive_path)}"
            dry_run_state.set_pending(op_id, {"files": old_files, "archive_path": archive_path})
            total_size = sum(f["size"] for f in old_files)
            return {
                "dry_run": True,
                "operation_id": op_id,
                "files_to_archive": old_files,
                "total_files": len(old_files),
                "total_size_bytes": total_size,
                "message": "Call again with confirm=true to execute",
            }
        
        archive_full_path = _resolve_path(sandbox_path, archive_path)
        archive_full_path.parent.mkdir(parents=True, exist_ok=True)
        
        with tarfile.open(archive_full_path, "w:gz") as tar:
            for file_info in old_files:
                file_path = _resolve_path(sandbox_path, file_info["path"])
                tar.add(file_path, arcname=file_info["path"])
        
        for file_info in old_files:
            file_path = _resolve_path(sandbox_path, file_info["path"])
            file_path.unlink()
        
        return {
            "success": True,
            "archive": archive_path,
            "archived_count": len(old_files),
            "deleted_originals": True,
        }
    except Exception as e:
        return {"error": str(e)}


def _delete_duplicates(sandbox_path: Path, args: dict, dry_run_state: DryRunState, permission_checker) -> dict:
    """Find and delete duplicate files."""
    directory = args.get("directory", ".")
    keep = args.get("keep", "newest")
    confirm = args.get("confirm", False)
    
    try:
        dir_path = _resolve_path(sandbox_path, directory)
        if not dir_path.exists() or not dir_path.is_dir():
            return {"error": f"Directory not found: {directory}"}
        
        hash_map = {}
        for file in dir_path.rglob("*"):
            if file.is_file():
                file_hash = hashlib.md5(file.read_bytes()).hexdigest()
                if file_hash not in hash_map:
                    hash_map[file_hash] = []
                hash_map[file_hash].append(file)
        
        duplicates_to_delete = []
        for file_hash, files in hash_map.items():
            if len(files) > 1:
                if keep == "newest":
                    files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
                elif keep == "oldest":
                    files.sort(key=lambda f: f.stat().st_mtime)
                elif keep == "largest":
                    files.sort(key=lambda f: f.stat().st_size, reverse=True)
                
                keeper = files[0]
                for dup in files[1:]:
                    duplicates_to_delete.append({
                        "path": str(dup.relative_to(sandbox_path)),
                        "duplicate_of": str(keeper.relative_to(sandbox_path)),
                        "size": dup.stat().st_size,
                    })
        
        if not duplicates_to_delete:
            return {"message": "No duplicates found", "directory": directory}
        
        if not confirm:
            op_id = f"dedup_{hash(directory)}"
            dry_run_state.set_pending(op_id, {"to_delete": duplicates_to_delete})
            total_size = sum(d["size"] for d in duplicates_to_delete)
            return {
                "dry_run": True,
                "operation_id": op_id,
                "duplicates_to_delete": duplicates_to_delete,
                "total_duplicates": len(duplicates_to_delete),
                "space_to_free_bytes": total_size,
                "message": "Call again with confirm=true to execute",
            }
        
        deleted = []
        for dup in duplicates_to_delete:
            dup_path = _resolve_path(sandbox_path, dup["path"])
            
            if permission_checker:
                allowed, reason = permission_checker("delete", {"path": dup["path"]}, sandbox_path)
                if not allowed:
                    continue
            
            dup_path.unlink()
            deleted.append(dup["path"])
        
        return {"success": True, "deleted": deleted, "count": len(deleted)}
    except Exception as e:
        return {"error": str(e)}


def _delete_files(sandbox_path: Path, args: dict, dry_run_state: DryRunState, permission_checker) -> dict:
    """Delete files matching a glob pattern with permission checking."""
    pattern = args.get("pattern", "")
    confirm = args.get("confirm", False)
    
    try:
        matching_files = list(sandbox_path.glob(pattern))
        matching_files = [f for f in matching_files if f.is_file()]
        
        if not matching_files:
            return {"message": "No files matched the pattern", "pattern": pattern}
        
        files_to_delete = []
        for file in matching_files:
            rel_path = str(file.relative_to(sandbox_path))
            
            # Check permissions before including in list
            if permission_checker:
                allowed, reason = permission_checker("delete", {"path": rel_path}, sandbox_path)
                if not allowed:
                    files_to_delete.append({
                        "path": rel_path,
                        "size": file.stat().st_size,
                        "blocked": True,
                        "reason": reason,
                    })
                    continue
            
            files_to_delete.append({
                "path": rel_path,
                "size": file.stat().st_size,
                "blocked": False,
            })
        
        allowed_files = [f for f in files_to_delete if not f.get("blocked")]
        blocked_files = [f for f in files_to_delete if f.get("blocked")]
        
        if not confirm:
            op_id = f"delete_{hash(pattern)}"
            dry_run_state.set_pending(op_id, {"files": allowed_files})
            return {
                "dry_run": True,
                "operation_id": op_id,
                "files_to_delete": allowed_files,
                "blocked_files": blocked_files,
                "total_allowed": len(allowed_files),
                "total_blocked": len(blocked_files),
                "message": "Call again with confirm=true to execute",
            }
        
        deleted = []
        for file_info in allowed_files:
            file_path = sandbox_path / file_info["path"]
            file_path.unlink()
            deleted.append(file_info["path"])
        
        return {
            "success": True,
            "deleted": deleted,
            "count": len(deleted),
            "blocked": [f["path"] for f in blocked_files],
        }
    except Exception as e:
        return {"error": str(e)}


def _run_tests(sandbox_path: Path, test_command: str | None) -> dict:
    """Run tests in the sandbox."""
    try:
        if not test_command:
            if (sandbox_path / "pytest.ini").exists() or (sandbox_path / "tests").exists():
                test_command = "pytest -v"
            elif (sandbox_path / "package.json").exists():
                test_command = "npm test"
            else:
                test_command = "pytest -v"
        
        result = subprocess.run(
            test_command,
            shell=True,
            cwd=sandbox_path,
            capture_output=True,
            text=True,
            timeout=60,
        )
        
        return {
            "passed": result.returncode == 0,
            "output": result.stdout,
            "errors": result.stderr,
            "exit_code": result.returncode,
            "command": test_command,
        }
    except subprocess.TimeoutExpired:
        return {"error": "Tests timed out after 60 seconds"}
    except Exception as e:
        return {"error": str(e)}


def _update_config(sandbox_path: Path, args: dict, permission_checker) -> dict:
    """Update a config file value."""
    import yaml
    import json
    
    path = args.get("path", "")
    key = args.get("key", "")
    value = args.get("value", "")
    
    try:
        full_path = _resolve_path(sandbox_path, path)
        
        if permission_checker:
            allowed, reason = permission_checker("write", {"path": path}, sandbox_path)
            if not allowed:
                return {"error": f"Permission denied: {reason}"}
        
        if not full_path.exists():
            return {"error": f"Config file not found: {path}"}
        
        content = full_path.read_text()
        
        if path.endswith((".yaml", ".yml")):
            data = yaml.safe_load(content) or {}
            _set_nested_key(data, key, value)
            new_content = yaml.dump(data, default_flow_style=False)
        elif path.endswith(".json"):
            data = json.loads(content)
            _set_nested_key(data, key, value)
            new_content = json.dumps(data, indent=2)
        else:
            return {"error": f"Unsupported config format: {path}"}
        
        full_path.write_text(new_content)
        return {"success": True, "path": path, "key": key, "value": value}
    except Exception as e:
        return {"error": str(e)}


def _set_nested_key(data: dict, key: str, value: str):
    """Set a nested key using dot notation, preserving type when possible."""
    keys = key.split(".")
    current = data
    for k in keys[:-1]:
        if k not in current:
            current[k] = {}
        current = current[k]
    
    # Try to preserve type: bool, int, float, or keep as string
    parsed_value = value
    if value.lower() == "true":
        parsed_value = True
    elif value.lower() == "false":
        parsed_value = False
    elif value.lower() == "null" or value.lower() == "none":
        parsed_value = None
    else:
        try:
            parsed_value = int(value)
        except ValueError:
            try:
                parsed_value = float(value)
            except ValueError:
                parsed_value = value  # Keep as string
    
    current[keys[-1]] = parsed_value


def _git_commit(sandbox_path: Path, message: str) -> dict:
    """Create a git commit."""
    try:
        add_result = subprocess.run(
            ["git", "add", "-A"],
            cwd=sandbox_path,
            capture_output=True,
            text=True,
        )
        if add_result.returncode != 0:
            return {"error": f"git add failed: {add_result.stderr}"}
        
        commit_result = subprocess.run(
            ["git", "commit", "-m", message],
            cwd=sandbox_path,
            capture_output=True,
            text=True,
        )
        
        if commit_result.returncode != 0:
            if "nothing to commit" in commit_result.stdout:
                return {"message": "Nothing to commit", "success": True}
            return {"error": f"git commit failed: {commit_result.stderr}"}
        
        return {"success": True, "message": message, "output": commit_result.stdout}
    except Exception as e:
        return {"error": str(e)}
