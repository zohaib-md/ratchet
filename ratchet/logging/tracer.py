"""Structured JSON tracer for agent runs."""

import json
from pathlib import Path
from datetime import datetime
from typing import Any


class Tracer:
    """Records structured trace data for a single agent run."""
    
    def __init__(
        self,
        version: str,
        scenario: str,
        trial: int,
        sandbox_path: Path,
        output_dir: Path | None = None,
    ):
        self.version = version
        self.scenario = scenario
        self.trial = trial
        self.sandbox_path = str(sandbox_path)
        self.timestamp = datetime.utcnow().isoformat() + "Z"
        
        self.turns: list[dict] = []
        self.current_turn: dict | None = None
        self.total_tokens = {"input": 0, "output": 0}
        
        if output_dir is None:
            output_dir = Path(__file__).parent.parent.parent / "logs"
        self.output_dir = output_dir / version
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def start_turn(self, turn_number: int):
        """Start recording a new turn."""
        self.current_turn = {
            "turn": turn_number,
            "request": None,
            "response": None,
            "tool_results": [],
            "permission_checks": [],
            "verification_attempts": [],
        }
    
    def log_request(self, request: dict):
        """Log the API request."""
        if self.current_turn:
            self.current_turn["request"] = {
                "messages_count": len(request.get("messages", [])),
                "tools_count": len(request.get("tools", []) or []),
            }
    
    def log_response(self, response):
        """Log the API response."""
        if self.current_turn:
            tool_calls = []
            if response.tool_calls:
                for tc in response.tool_calls:
                    tool_calls.append({
                        "name": tc.function.name,
                        "arguments": tc.function.arguments[:200] + "..." if len(tc.function.arguments) > 200 else tc.function.arguments,
                    })
            
            self.current_turn["response"] = {
                "content": response.content[:500] if response.content else None,
                "tool_calls": tool_calls,
            }
    
    def log_tool_execution(self, tool_name: str, args: dict, result: Any):
        """Log a tool execution."""
        if self.current_turn:
            result_str = json.dumps(result) if isinstance(result, (dict, list)) else str(result)
            self.current_turn["tool_results"].append({
                "tool": tool_name,
                "args_summary": {k: str(v)[:100] for k, v in args.items()},
                "result_summary": result_str[:300] + "..." if len(result_str) > 300 else result_str,
            })
    
    def log_tool_results(self, results: list[dict]):
        """Log raw tool results (for message history)."""
        pass
    
    def log_permission_check(self, tool_name: str, args: dict, allowed: bool, reason: str):
        """Log a permission check."""
        if self.current_turn:
            self.current_turn["permission_checks"].append({
                "tool": tool_name,
                "allowed": allowed,
                "reason": reason,
            })
    
    def log_verification_attempt(self, passed: bool, reason: str):
        """Log a verification attempt."""
        if self.current_turn:
            self.current_turn["verification_attempts"].append({
                "passed": passed,
                "reason": reason,
            })
    
    def end_turn(self):
        """Finalize the current turn."""
        if self.current_turn:
            self.turns.append(self.current_turn)
            self.current_turn = None
    
    def end_loop(self, termination_reason: str):
        """Finalize the current turn if pending and prepare for save."""
        if self.current_turn:
            self.end_turn()
        self._termination_reason = termination_reason
    
    def save(self, outcome: dict) -> Path:
        """Save the trace to a JSON file."""
        trace_data = {
            "version": self.version,
            "scenario": self.scenario,
            "trial": self.trial,
            "timestamp": self.timestamp,
            "sandbox_path": self.sandbox_path,
            "turns": self.turns,
            "outcome": outcome,
        }
        
        filename = f"{self.scenario}_{self.trial}_{self.timestamp.replace(':', '-')}.json"
        output_path = self.output_dir / filename
        
        with open(output_path, "w") as f:
            json.dump(trace_data, f, indent=2)
        
        return output_path
