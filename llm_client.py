"""
LLM Client - Using Ollama CLI (more reliable than API).

Supports vision models (qwen2.5-vl) and text models (qwen3.5, llama, etc.)
"""

import base64
import json
import subprocess
from pathlib import Path
from typing import Optional


class LLMClient:
    """LLM client using Ollama CLI."""

    def __init__(
        self,
        model: str = "qwen3.5:9b",
    ):
        self.model = model

    def chat(
        self,
        prompt: str,
        image_path: Optional[str] = None,
        system_prompt: Optional[str] = None,
    ) -> str:
        """
        Send chat request using ollama CLI.
        """
        # Build the prompt
        full_prompt = prompt
        if system_prompt:
            full_prompt = f"{system_prompt}\n\n{prompt}"

        # Check if vision model
        if "vl" in self.model.lower() and image_path:
            return self._chat_vision(full_prompt, image_path)
        else:
            return self._chat_text(full_prompt)

    def _chat_text(self, prompt: str) -> str:
        """Chat using text model via CLI."""
        try:
            # Use echo to pipe prompt to ollama
            result = subprocess.run(
                ["ollama", "run", self.model],
                input=prompt,
                capture_output=True,
                text=True,
                timeout=120,
            )
            
            if result.returncode != 0:
                return f"Error: {result.stderr}"
            
            # Filter out ANSI codes
            output = result.stdout
            # Remove ANSI escape sequences
            import re
            output = re.sub(r'\x1b\[[0-9;]*[a-zA-Z]', '', output)
            return output.strip()
            
        except subprocess.TimeoutExpired:
            return "Error: Timeout"
        except Exception as e:
            return f"Error: {str(e)}"

    def _chat_vision(self, prompt: str, image_path: str) -> str:
        """Chat using vision model with image."""
        # For vision models, we need to describe the image
        # Note: qwen2.5-vl via CLI expects image path as argument
        cmd = ["ollama", "run", self.model, f"Image: {image_path}", prompt]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120,
            )
            
            if result.returncode != 0:
                return f"Error: {result.stderr}"
            
            import re
            output = result.stdout
            output = re.sub(r'\x1b\[[0-9;]*[a-zA-Z]', '', output)
            return output.strip()
            
        except subprocess.TimeoutExpired:
            return "Error: Timeout"
        except Exception as e:
            return f"Error: {str(e)}"


# ------------------------------------------------------------------
# Convenience factory
# ------------------------------------------------------------------

def create_llm_client(
    provider: str = "ollama",
    model: Optional[str] = None,
    api_key: Optional[str] = None,
    **kwargs,
) -> LLMClient:
    """Create LLM client."""
    return LLMClient(model=model or "qwen3.5:9b")
