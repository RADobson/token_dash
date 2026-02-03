#!/usr/bin/env python3
"""
Standalone CLI script to view Claude Code (Claude Max) usage.

Usage:
    python claude_code_usage.py              # Show summary
    python claude_code_usage.py --detailed   # Show per-session details
    python claude_code_usage.py --json       # Output as JSON
"""

import json
import argparse
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, List
import re


def normalize_model_name(model: str) -> str:
    """Remove date suffixes from model names."""
    return re.sub(r'-\d{8}$', '', model).lower()


def calculate_hypothetical_cost(
    model: str,
    input_tokens: int,
    output_tokens: int,
    cache_read: int = 0,
    cache_write: int = 0
) -> float:
    """Calculate what this usage would cost on API pricing."""
    pricing = {
        "claude-opus-4-5": {"input": 15.00, "output": 75.00, "cache_read": 1.875, "cache_write": 18.75},
        "claude-sonnet-4": {"input": 3.00, "output": 15.00, "cache_read": 0.30, "cache_write": 3.75},
        "claude-3-5-sonnet": {"input": 3.00, "output": 15.00, "cache_read": 0.30, "cache_write": 3.75},
        "claude-3-opus": {"input": 15.00, "output": 75.00, "cache_read": 1.875, "cache_write": 18.75},
    }
    
    model_lower = normalize_model_name(model)
    p = pricing.get(model_lower, pricing["claude-opus-4-5"])
    
    return round(
        (input_tokens / 1_000_000) * p["input"] +
        (output_tokens / 1_000_000) * p["output"] +
        (cache_read / 1_000_000) * p["cache_read"] +
        (cache_write / 1_000_000) * p["cache_write"],
        4
    )


def get_stats_cache() -> Dict[str, Any]:
    """Read stats-cache.json."""
    path = Path.home() / ".claude" / "stats-cache.json"
    if not path.exists():
        return {}
    
    with open(path) as f:
        return json.load(f)


def get_session_details() -> List[Dict[str, Any]]:
    """Parse all session JSONL files for detailed usage."""
    projects_dir = Path.home() / ".claude" / "projects"
    if not projects_dir.exists():
        return []
    
    sessions = []
    
    for jsonl_path in projects_dir.rglob("*.jsonl"):
        session_data = {
            "session_id": jsonl_path.stem,
            "path": str(jsonl_path.relative_to(projects_dir.parent)),
            "messages": [],
            "total_input": 0,
            "total_output": 0,
            "total_cache_read": 0,
            "total_cache_write": 0,
            "tool_calls": 0,
            "thinking_blocks": 0,
        }
        
        with open(jsonl_path) as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue
                
                if entry.get("type") != "assistant":
                    continue
                
                message = entry.get("message", {})
                usage = message.get("usage")
                if not usage:
                    continue
                
                input_tok = usage.get("input_tokens", 0)
                output_tok = usage.get("output_tokens", 0)
                cache_read = usage.get("cache_read_input_tokens", 0)
                cache_write = usage.get("cache_creation_input_tokens", 0)
                
                session_data["total_input"] += input_tok
                session_data["total_output"] += output_tok
                session_data["total_cache_read"] += cache_read
                session_data["total_cache_write"] += cache_write
                
                # Check content types
                content = message.get("content", [])
                for item in content if isinstance(content, list) else []:
                    if isinstance(item, dict):
                        if item.get("type") == "tool_use":
                            session_data["tool_calls"] += 1
                        if item.get("type") == "thinking":
                            session_data["thinking_blocks"] += 1
                
                session_data["messages"].append({
                    "timestamp": entry.get("timestamp"),
                    "model": message.get("model"),
                    "input": input_tok,
                    "output": output_tok,
                    "cache_read": cache_read,
                    "cache_write": cache_write,
                })
        
        if session_data["messages"]:
            sessions.append(session_data)
    
    return sessions


def format_number(n: int) -> str:
    """Format large numbers with commas."""
    return f"{n:,}"


def print_summary(stats: Dict, sessions: List[Dict], detailed: bool = False):
    """Print formatted usage summary."""
    print("\n╔══════════════════════════════════════════════════════════════╗")
    print("║              🤖 Claude Code Usage Summary                    ║")
    print("╠══════════════════════════════════════════════════════════════╣")
    
    if not stats:
        print("║  ⚠️  No stats-cache.json found                               ║")
        print("║  Run Claude Code to generate usage data                      ║")
        print("╚══════════════════════════════════════════════════════════════╝")
        return
    
    print(f"║  📅 First session: {stats.get('firstSessionDate', 'Unknown')[:10]:<35}║")
    print(f"║  💬 Total sessions: {stats.get('totalSessions', 0):<34}║")
    print(f"║  📝 Total messages: {stats.get('totalMessages', 0):<34}║")
    print("╠══════════════════════════════════════════════════════════════╣")
    
    model_usage = stats.get("modelUsage", {})
    total_cost = 0.0
    
    for model, usage in model_usage.items():
        input_tok = usage.get("inputTokens", 0)
        output_tok = usage.get("outputTokens", 0)
        cache_read = usage.get("cacheReadInputTokens", 0)
        cache_write = usage.get("cacheCreationInputTokens", 0)
        
        cost = calculate_hypothetical_cost(model, input_tok, output_tok, cache_read, cache_write)
        total_cost += cost
        
        print(f"║  Model: {normalize_model_name(model):<48}║")
        print(f"║    Input tokens:      {format_number(input_tok):>32}║")
        print(f"║    Output tokens:     {format_number(output_tok):>32}║")
        print(f"║    Cache read:        {format_number(cache_read):>32}║")
        print(f"║    Cache write:       {format_number(cache_write):>32}║")
        print(f"║    Hypothetical cost: ${cost:>30.2f}║")
    
    print("╠══════════════════════════════════════════════════════════════╣")
    print(f"║  💵 Total hypothetical cost: ${total_cost:>24.2f}       ║")
    print(f"║  💰 Actual cost (Claude Max): ${'0.00 (subscription)':>25}    ║")
    print("╚══════════════════════════════════════════════════════════════╝")
    
    # Daily activity
    daily = stats.get("dailyActivity", [])
    if daily:
        print("\n📊 Recent Daily Activity:")
        print("─" * 50)
        for day in sorted(daily, key=lambda x: x.get("date", ""), reverse=True)[:7]:
            print(f"  {day.get('date', 'Unknown')}: {day.get('messageCount', 0)} messages, {day.get('sessionCount', 0)} sessions")
    
    # Session details
    if detailed and sessions:
        print("\n📁 Session Details:")
        print("─" * 60)
        for sess in sorted(sessions, key=lambda x: x.get("messages", [{}])[0].get("timestamp", "") if x.get("messages") else "", reverse=True)[:10]:
            msg_count = len(sess.get("messages", []))
            print(f"\n  Session: {sess['session_id'][:20]}...")
            print(f"    Messages: {msg_count}, Tools: {sess['tool_calls']}, Thinking: {sess['thinking_blocks']}")
            print(f"    Tokens: {format_number(sess['total_input'])} in / {format_number(sess['total_output'])} out")
            print(f"    Cache: {format_number(sess['total_cache_read'])} read / {format_number(sess['total_cache_write'])} write")


def main():
    parser = argparse.ArgumentParser(description="View Claude Code usage statistics")
    parser.add_argument("--detailed", "-d", action="store_true", help="Show per-session details")
    parser.add_argument("--json", "-j", action="store_true", help="Output as JSON")
    args = parser.parse_args()
    
    stats = get_stats_cache()
    sessions = get_session_details()
    
    if args.json:
        output = {
            "stats": stats,
            "sessions": sessions,
            "summary": {
                "total_sessions": stats.get("totalSessions", 0),
                "total_messages": stats.get("totalMessages", 0),
                "models": list(stats.get("modelUsage", {}).keys()),
                "session_files": len(sessions),
            }
        }
        print(json.dumps(output, indent=2, default=str))
    else:
        print_summary(stats, sessions, detailed=args.detailed)


if __name__ == "__main__":
    main()
