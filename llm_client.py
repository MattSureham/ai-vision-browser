"""
LLM Client - Supports Ollama, OpenAI, Anthropic, Kimi, Minimax.

Supports vision models for page understanding.
"""

import base64
import json
import os
import re
import subprocess
from pathlib import Path
from typing import Optional, Union

import requests


class LLMClient:
    """Universal LLM client."""

    def __init__(
        self,
        provider: str = "ollama",
        model: str = "qwen2.5-vl:7b",
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
    ):
        self.provider = provider
        self.model = model
        self.api_key = api_key or os.getenv("API_KEY", "")
        self.base_url = base_url

    def chat(
        self,
        prompt: str,
        image_path: Optional[str] = None,
        system_prompt: Optional[str] = None,
    ) -> str:
        """Send chat request."""
        if self.provider in ("ollama", "qwen"):
            return self._chat_ollama(prompt, image_path, system_prompt)
        elif self.provider == "openai":
            return self._chat_openai(prompt, image_path, system_prompt)
        elif self.provider == "anthropic":
            return self._chat_anthropic(prompt, image_path, system_prompt)
        elif self.provider == "kimi":
            return self._chat_kimi(prompt, image_path, system_prompt)
        elif self.provider == "minimax":
            return self._chat_minimax(prompt, image_path, system_prompt)
        else:
            return f"Error: Unknown provider {self.provider}"

    def _encode_image(self, image_path: str) -> str:
        """Encode image to base64."""
        with open(image_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")

    def _extract_json(self, response: str) -> dict:
        """Extract JSON from response - handles nested braces and markdown."""
        # Try to find JSON in markdown code blocks
        json_match = re.search(r'```(?:json)?\s*(\{[\s\S]*?\})\s*```', response)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass

        # Try to find the outermost braces
        try:
            # Find the first { and last }
            start = response.find("{")
            end = response.rfind("}")
            if start != -1 and end != -1 and end > start:
                json_str = response[start:end+1]
                return json.loads(json_str)
        except (json.JSONDecodeError, ValueError):
            pass

        # Fallback: try full response
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            pass

        return {"action": "error", "reason": f"Could not parse: {response[:200]}"}

    # ------------------------------------------------------------------
    # Ollama / Qwen
    # ------------------------------------------------------------------

    def _chat_ollama(
        self,
        prompt: str,
        image_path: Optional[str] = None,
        system_prompt: Optional[str] = None,
    ) -> str:
        """Chat using Ollama CLI."""
        is_vision = "vl" in self.model.lower() and image_path

        try:
            cmd = ["ollama", "run", self.model]
            if is_vision and image_path:
                cmd.extend([f"Image: {image_path}"])
            if system_prompt:
                cmd.insert(2, f"System: {system_prompt}")
            cmd.append(prompt)

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120,
            )

            if result.returncode != 0:
                return f"Error: {result.stderr}"

            output = result.stdout
            output = re.sub(r'\x1b\[[0-9;]*[a-zA-Z]', '', output)
            return output.strip()

        except subprocess.TimeoutExpired:
            return "Error: Timeout"
        except Exception as e:
            return f"Error: {str(e)}"

    # ------------------------------------------------------------------
    # OpenAI
    # ------------------------------------------------------------------

    def _chat_openai(
        self,
        prompt: str,
        image_path: Optional[str] = None,
        system_prompt: Optional[str] = None,
    ) -> str:
        """Chat using OpenAI API."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        base_url = self.base_url or "https://api.openai.com/v1"

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        content = [{"type": "text", "text": prompt}]

        # Add image if provided
        if image_path:
            base64_image = self._encode_image(image_path)
            content.insert(0, {
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/png;base64,{base64_image}"
                }
            })

        messages.append({"role": "user", "content": content})

        try:
            resp = requests.post(
                f"{base_url}/chat/completions",
                headers=headers,
                json={
                    "model": self.model,
                    "messages": messages,
                    "max_tokens": 1000,
                },
                timeout=120,
            )
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]
        except Exception as e:
            return f"Error: {str(e)}"

    # ------------------------------------------------------------------
    # Anthropic
    # ------------------------------------------------------------------

    def _chat_anthropic(
        self,
        prompt: str,
        image_path: Optional[str] = None,
        system_prompt: Optional[str] = None,
    ) -> str:
        """Chat using Anthropic API."""
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        }

        base_url = self.base_url or "https://api.anthropic.com/v1"

        content = [{"type": "text", "text": prompt}]

        if image_path:
            # Anthropic needs specific image format
            base64_image = self._encode_image(image_path)
            content.insert(0, {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/png",
                    "data": base64_image,
                }
            })

        body = {
            "model": self.model,
            "max_tokens": 1000,
            "messages": [{"role": "user", "content": content}],
        }

        if system_prompt:
            body["system"] = system_prompt

        try:
            resp = requests.post(
                f"{base_url}/messages",
                headers=headers,
                json=body,
                timeout=120,
            )
            resp.raise_for_status()
            data = resp.json()
            return data["content"][0]["text"]
        except Exception as e:
            return f"Error: {str(e)}"

    # ------------------------------------------------------------------
    # Kimi (Moonshot AI)
    # ------------------------------------------------------------------

    def _chat_kimi(
        self,
        prompt: str,
        image_path: Optional[str] = None,
        system_prompt: Optional[str] = None,
    ) -> str:
        """Chat using Kimi API (Moonshot AI)."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        base_url = self.base_url or "https://api.moonshot.cn/v1"

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        content = [{"type": "text", "text": prompt}]

        if image_path:
            base64_image = self._encode_image(image_path)
            content.insert(0, {
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/png;base64,{base64_image}"
                }
            })

        messages.append({"role": "user", "content": content})

        # Map model names
        model_map = {
            "k2p5": "moonshot-v1-8k-vision-preview",
            "kimi-k2p5": "moonshot-v1-8k-vision-preview",
            "kimi-v1": "moonshot-v1-8k-vision-preview",
        }
        model = model_map.get(self.model.lower(), self.model)

        try:
            resp = requests.post(
                f"{base_url}/chat/completions",
                headers=headers,
                json={
                    "model": model,
                    "messages": messages,
                    "max_tokens": 1000,
                },
                timeout=120,
            )
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]
        except Exception as e:
            return f"Error: {str(e)}"

    # ------------------------------------------------------------------
    # Minimax
    # ------------------------------------------------------------------

    def _chat_minimax(
        self,
        prompt: str,
        image_path: Optional[str] = None,
        system_prompt: Optional[str] = None,
    ) -> str:
        """Chat using Minimax API."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        base_url = self.base_url or "https://api.minimax.chat/v1"

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        content = [{"type": "text", "text": prompt}]

        if image_path:
            base64_image = self._encode_image(image_path)
            # Minimax uses different format
            content.insert(0, {
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/png;base64,{base64_image}"
                }
            })

        messages.append({"role": "user", "content": content})

        # Extract group_id and project_id from API key if needed
        # Minimax uses group_id/project_id format
        api_key = self.api_key
        parts = api_key.split("-")
        group_id = parts[0] if parts else "default"

        try:
            resp = requests.post(
                f"{base_url}/text/chatcompletion_v2",
                headers=headers,
                json={
                    "model": self.model,
                    "messages": messages,
                    "max_tokens": 1000,
                    "group_id": group_id,
                },
                timeout=120,
            )
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]
        except Exception as e:
            return f"Error: {str(e)}"


# ------------------------------------------------------------------
# Factory
# ------------------------------------------------------------------

def create_llm_client(
    provider: str = "ollama",
    model: Optional[str] = None,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    **kwargs,
) -> LLMClient:
    """Create LLM client."""
    # Default models per provider
    defaults = {
        "ollama": "qwen2.5-vl:7b",
        "openai": "gpt-4o",
        "anthropic": "claude-3-5-sonnet-20241022",
        "kimi": "k2p5",
        "minimax": "MiniMax-M2.5",
    }

    return LLMClient(
        provider=provider,
        model=model or defaults.get(provider, "qwen2.5-vl:7b"),
        api_key=api_key,
        base_url=base_url,
    )
