"""
LLM Client - Vision-capable LLM integration.

Supports Qwen VL (via Ollama), OpenAI GPT-4V, Anthropic Claude, etc.
"""

import base64
import json
from pathlib import Path
from typing import Optional

import requests


class LLMClient:
    """Vision-capable LLM client."""

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "qwen2.5-vl:7b",
        api_key: Optional[str] = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key = api_key

    def chat(
        self,
        prompt: str,
        image_path: Optional[str] = None,
        system_prompt: Optional[str] = None,
    ) -> str:
        """
        Send chat request with optional image.
        
        Returns the model's response text.
        """
        if "ollama" in self.base_url:
            return self._chat_ollama(prompt, image_path, system_prompt)
        elif "openai" in self.base_url:
            return self._chat_openai(prompt, image_path, system_prompt)
        elif "anthropic" in self.base_url:
            return self._chat_anthropic(prompt, image_path, system_prompt)
        else:
            raise ValueError(f"Unknown LLM provider: {self.base_url}")

    def _chat_ollama(
        self,
        prompt: str,
        image_path: Optional[str] = None,
        system_prompt: Optional[str] = None,
    ) -> str:
        """Chat with Ollama (Qwen VL)."""
        url = f"{self.base_url}/api/chat"
        
        messages = []
        
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        # Build message with image
        content = []
        if image_path:
            # Read and encode image
            with open(image_path, "rb") as f:
                img_b64 = base64.b64encode(f.read()).decode("utf-8")
            content.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/png;base64,{img_b64}"
                }
            })
        
        content.append({"type": "text", "text": prompt})
        messages.append({"role": "user", "content": content})
        
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
        }
        
        resp = requests.post(url, json=payload, timeout=120)
        resp.raise_for_status()
        
        result = resp.json()
        return result.get("message", {}).get("content", "")

    def _chat_openai(
        self,
        prompt: str,
        image_path: Optional[str] = None,
        system_prompt: Optional[str] = None,
    ) -> str:
        """Chat with OpenAI GPT-4V."""
        url = f"{self.base_url}/v1/chat/completions"
        
        headers = {
            "Content-Type": "application/json",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        # Build message with image
        content = []
        if image_path:
            with open(image_path, "rb") as f:
                img_b64 = base64.b64encode(f.read()).decode("utf-8")
            content.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/png;base64,{img_b64}"
                }
            })
        
        content.append({"type": "text", "text": prompt})
        messages.append({"role": "user", "content": content})
        
        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": 512,
        }
        
        resp = requests.post(url, headers=headers, json=payload, timeout=120)
        resp.raise_for_status()
        
        result = resp.json()
        return result["choices"][0]["message"]["content"]

    def _chat_anthropic(
        self,
        prompt: str,
        image_path: Optional[str] = None,
        system_prompt: Optional[str] = None,
    ) -> str:
        """Chat with Anthropic Claude."""
        url = f"{self.base_url}/v1/messages"
        
        headers = {
            "Content-Type": "application/json",
            "x-api-key": self.api_key or "",
            "anthropic-version": "2023-06-01",
        }
        
        # Build content
        content = []
        if image_path:
            with open(image_path, "rb") as f:
                img_b64 = base64.b64encode(f.read()).decode("utf-8")
            content.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/png",
                    "data": img_b64
                }
            })
        
        content.append({
            "type": "text",
            "text": prompt
        })
        
        payload = {
            "model": self.model,
            "max_tokens": 512,
            "messages": [{
                "role": "user",
                "content": content
            }]
        }
        
        if system_prompt:
            payload["system"] = system_prompt
        
        resp = requests.post(url, headers=headers, json=payload, timeout=120)
        resp.raise_for_status()
        
        result = resp.json()
        return result["content"][0]["text"]


# ------------------------------------------------------------------
# Convenience factory
# ------------------------------------------------------------------

def create_llm_client(
    provider: str = "ollama",
    model: Optional[str] = None,
    **kwargs,
) -> LLMClient:
    """Create LLM client based on provider."""
    
    configs = {
        "ollama": {
            "base_url": "http://localhost:11434",
            "model": model or "qwen2.5-vl:7b",
        },
        "openai": {
            "base_url": "https://api.openai.com/v1",
            "model": model or "gpt-4o",
        },
        "anthropic": {
            "base_url": "https://api.anthropic.com",
            "model": model or "claude-3-5-sonnet-20241022",
        },
    }
    
    config = configs.get(provider, configs["ollama"])
    config.update(kwargs)
    
    return LLMClient(**config)
