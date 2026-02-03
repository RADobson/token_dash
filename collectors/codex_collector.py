"""Codex CLI (ChatGPT Plus) subscription usage collector."""

import asyncio
import re
from datetime import datetime, timezone
from typing import List, Optional

from .base import BaseCollector, TokenUsagePoint


class CodexCollector(BaseCollector):
    """
    Collects usage data from OpenAI Codex CLI (ChatGPT Plus subscription).
    
    This collector runs the `codex` CLI with usage-related commands
    and parses the output to extract subscription usage data.
    """
    
    def is_configured(self) -> bool:
        """Check if Codex CLI is available."""
        return True
    
    async def collect(self) -> List[TokenUsagePoint]:
        """Collect usage data from Codex CLI."""
        points = []
        
        usage_data = await self._get_codex_usage()
        if usage_data:
            points.append(usage_data)
        
        return points
    
    async def _get_codex_usage(self) -> Optional[TokenUsagePoint]:
        """Run codex CLI and parse usage output."""
        try:
            # Try running codex with usage command
            result = await self._run_command(["codex", "usage"])
            if result:
                parsed = self._parse_usage_output(result)
                if parsed:
                    return parsed
            
            # Try /usage within codex
            result = await self._run_command(["codex", "--usage"])
            if result:
                parsed = self._parse_usage_output(result)
                if parsed:
                    return parsed
            
            # Try status command
            result = await self._run_command(["codex", "status"])
            if result:
                return self._parse_status_output(result)
            
            self.log.debug("No usage data from Codex CLI")
            return None
            
        except FileNotFoundError:
            self.log.debug("Codex CLI not found")
            return None
        except Exception as e:
            self.log.error("Error getting Codex usage", error=str(e))
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
        """Parse Codex CLI usage output."""
        input_tokens = 0
        output_tokens = 0
        limit_tokens = 0
        used_pct = 0.0
        model = "gpt-4"
        
        # Look for token counts
        # Patterns like "X tokens used" or "Input: X, Output: Y"
        
        # Total tokens pattern
        total_pattern = r"(\d+[\d,]*)\s*(?:total\s*)?tokens?\s*used"
        match = re.search(total_pattern, output, re.IGNORECASE)
        if match:
            total = int(match.group(1).replace(",", ""))
            # Estimate split (typically more input than output in coding)
            input_tokens = int(total * 0.7)
            output_tokens = total - input_tokens
        
        # Separate input/output patterns
        input_pattern = r"(?:input|prompt)\s*(?:tokens?)?\s*:?\s*(\d+[\d,]*)"
        match = re.search(input_pattern, output, re.IGNORECASE)
        if match:
            input_tokens = int(match.group(1).replace(",", ""))
        
        output_pattern = r"(?:output|completion)\s*(?:tokens?)?\s*:?\s*(\d+[\d,]*)"
        match = re.search(output_pattern, output, re.IGNORECASE)
        if match:
            output_tokens = int(match.group(1).replace(",", ""))
        
        # Usage percentage
        pct_pattern = r"(\d+(?:\.\d+)?)\s*%\s*(?:used|of)"
        match = re.search(pct_pattern, output, re.IGNORECASE)
        if match:
            used_pct = float(match.group(1))
        
        # Limit
        limit_pattern = r"limit\s*:?\s*(\d+[\d,]*)"
        match = re.search(limit_pattern, output, re.IGNORECASE)
        if match:
            limit_tokens = int(match.group(1).replace(",", ""))
        
        # Model detection
        if "gpt-4o" in output.lower():
            model = "gpt-4o"
        elif "gpt-4-turbo" in output.lower():
            model = "gpt-4-turbo"
        elif "gpt-4" in output.lower():
            model = "gpt-4"
        elif "gpt-3.5" in output.lower():
            model = "gpt-3.5-turbo"
        
        if input_tokens or output_tokens or used_pct:
            return TokenUsagePoint(
                provider="openai",
                model=model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cost_usd=0.0,  # Subscription-based
                timestamp=datetime.now(timezone.utc),
                tags={
                    "source": "codex-cli",
                    "subscription": "chatgpt-plus"
                },
                fields={
                    "usage_percent": used_pct,
                    "limit_tokens": limit_tokens
                }
            )
        
        return None
    
    def _parse_status_output(self, output: str) -> Optional[TokenUsagePoint]:
        """Parse Codex CLI status output."""
        return self._parse_usage_output(output)
