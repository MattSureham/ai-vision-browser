#!/usr/bin/env python3
"""Quick test of AI Vision Browser - full workflow."""

import sys
sys.path.insert(0, ".")

from browser_agent import BrowserAgent, ensure_chrome
from llm_client import create_llm_client
from vision_prompt import SYSTEM_PROMPT, build_action_prompt
import json
import re
import time

def parse_action(response):
    # Try to extract JSON from markdown code blocks
    json_match = re.search(r'```(?:json)?\s*(\{[\s\S]*?\})\s*```', response)
    if json_match:
        try:
            return json.loads(json_match.group(1))
        except:
            pass
    
    # Try to find the outermost braces
    try:
        start = response.find("{")
        end = response.rfind("}")
        if start != -1 and end != -1 and end > start:
            json_str = response[start:end+1]
            return json.loads(json_str)
    except:
        pass
    
    return {"action": "error", "reason": f"Parse failed: {response[:200]}"}

# Initialize
print("=== Initializing browser and LLM ===")
ensure_chrome(port=9222)
browser = BrowserAgent(port=9222)
llm = create_llm_client("ollama", "qwen3.5:9b")
print(f"LLM: {llm.model}")

# Navigate
print("\n=== Navigating to example.com ===")
browser.connect("https://example.com")
browser.navigate("https://example.com")
ctx = browser.get_context_for_llm()
print(f"Page: {ctx['page_title']}")
print(f"URL: {ctx['page_url']}")

# Ask AI to click "Learn more"
print("\n=== Asking AI to click 'Learn more' ===")
prompt = build_action_prompt("click the Learn more link", {
    "url": ctx["page_url"],
    "title": ctx["page_title"],
})

response = llm.chat(prompt, image_path=ctx["screenshot_path"], system_prompt=SYSTEM_PROMPT)
print(f"LLM Response: {response[:800]}...")

action = parse_action(response)
print(f"\nParsed action: {action}")

# Execute
if action.get("action") == "click":
    browser.click(action["x"], action["y"])
    print(f"Clicked at ({action['x']}, {action['y']})")
    time.sleep(2)
    
    # Check new page
    info = browser.get_page_info()
    print(f"New page: {info['title']} - {info['url']}")
    
    browser.screenshot("after_click.png")
    print("Screenshot saved: after_click.png")
elif action.get("action") == "done":
    print(f"Done: {action.get('reason')}")
else:
    print(f"Action: {action}")

# Test scroll
print("\n=== Testing scroll ===")
browser.scroll("down")
browser.screenshot("after_scroll.png")
print("Scrolled down, screenshot saved")

# Test type (on a simple page)
print("\n=== Testing type on example.com ===")
browser.navigate("https://example.com")
time.sleep(2)

# Try to find search box (won't exist on example.com, but let's see)
ctx = browser.get_context_for_llm()
prompt = build_action_prompt('type "test" in the search box', {
    "url": ctx["page_url"],
    "title": ctx["page_title"],
})

response = llm.chat(prompt, image_path=ctx["screenshot_path"], system_prompt=SYSTEM_PROMPT)
print(f"LLM Response: {response[:600]}...")

action = parse_action(response)
print(f"Parsed action: {action}")

if action.get("action") in ("click", "type"):
    x, y = action.get("x", 500), action.get("y", 300)
    browser.type_text(x, y, "test input")
    print(f"Typed at ({x}, {y})")

browser.disconnect()
print("\n=== Test complete ===")
