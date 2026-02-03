"""Claude Code (Claude Max) subscription usage collector."""

import asyncio
import re
from datetime import datetime, timezone
from typing import List, Optional, Tuple
from pathlib import Path

from .base import BaseCollector, TokenUsagePoint


class ClaudeCodeCollector(BaseCollector):
    """
    Collects usage data from Claude Code CLI (Claude Max subscription).
    
    This collector runs the `claude` CLI with usage-related commands
    and parses the output to extract subscription usage data.
    """
    
    def is_configured(self) -> bool:
        """Check if Claude CLI is available."""
        # We'll check during collection
        return True
    
    async def collect(self) -> List[TokenUsagePoint]:
        """Collect usage data from Claude Code CLI."""
        points = []
        
        # Try to get usage from Claude CLI
        usage_data = await self._get_claude_usage()
        
        if usage_data:
            points.append(usage_data)
        
        return points
    
    async def _get_claude_usage(self) -> Optional[TokenUsagePoint]:
        """Run claude CLI and parse usage output."""
        try:
            # Try running claude with /usage or similar command
            # The actual command may vary based on Claude Code version
            
            # First try: claude usage
            result = await self._run_command(["claude", "usage"])
            if result and "usage" in result.lower():
                return self._parse_usage_output(result)
            
            # Second try: claude --usage
            result = await self._run_command(["claude", "--usage"])
            if result and "usage" in result.lower():
                return self._parse_usage_output(result)
            
            # Third try: Look for usage in claude status
            result = await self._run_command(["claude", "status"])
            if result:
                return self._parse_status_output(result)
            
            self.log.debug("No usage data from Claude CLI")
            return None
            
        except FileNotFoundError:
            self.log.debug("Claude CLI not found")
            return None
        except Exception as e:
            self.log.error("Error getting Claude usage", error=str(e))
            return None
    
    async def _run_command(self, cmd: List[str], timeout: int = 10) -> Optional[str]:
        """Run a command and return stdout."""
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout
                )
                
                if process.returncode == 0:
                    return stdout.decode("utf-8", errors="ignore")
                else:
                    return None
                    
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                return None
                
        except Exception as e:
            self.log.debug("Command failed", cmd=cmd, error=str(e))
            return None
    
    def _parse_usage_output(self, output: str) -> Optional[TokenUsagePoint]:
        """Parse Claude CLI usage output."""
        # This parsing logic will need to be adjusted based on actual output format
        # Common patterns to look for:
        
        input_tokens = 0
        output_tokens = 0
        limit_tokens = 0
        used_pct = 0.0
        
        # Try to find token counts
        # Pattern: "Tokens: X in / Y out" or "Input: X, Output: Y"
        token_pattern = r"(\d+[\d,]*)\s*(?:tokens?)?\s*(?:in|input)"
        match = re.search(token_pattern, output, re.IGNORECASE)
        if match:
            input_tokens = int(match.group(1).replace(",", ""))
        
        token_pattern = r"(\d+[\d,]*)\s*(?:tokens?)?\s*(?:out|output)"
        match = re.search(token_pattern, output, re.IGNORECASE)
        if match:
            output_tokens = int(match.group(1).replace(",", ""))
        
        # Try to find usage percentage
        # Pattern: "X% used" or "Usage: X%"
        pct_pattern = r"(\d+(?:\.\d+)?)\s*%"
        match = re.search(pct_pattern, output)
        if match:
            used_pct = float(match.group(1))
        
        # Try to find limit
        # Pattern: "Limit: X tokens" or "of X tokens"
        limit_pattern = r"(?:limit|of)\s*:?\s*(\d+[\d,]*)\s*tokens?"
        match = re.search(limit_pattern, output, re.IGNORECASE)
        if match:
            limit_tokens = int(match.group(1).replace(",", ""))
        
        if input_tokens or output_tokens or used_pct:
            return TokenUsagePoint(
                provider="anthropic",
                model="claude-max",
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cost_usd=0.0,  # Subscription-based, no per-token cost
                timestamp=datetime.now(timezone.utc),
                tags={
                    "source": "claude-code",
                    "subscription": "claude-max"
                },
                fields={
                    "usage_percent": used_pct,
                    "limit_tokens": limit_tokens
                }
            )
        
        return None
    
    def _parse_status_output(self, output: str) -> Optional[TokenUsagePoint]:
        """Parse Claude CLI status output for usage info."""
        # Similar parsing but for status command format
        return self._parse_usage_output(output)
