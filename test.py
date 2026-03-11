#!/usr/bin/env python3
"""Quick test of AI Vision Browser - text-only mode."""

import sys
sys.path.insert(0, ".")

from browser_agent import BrowserAgent
from llm_client import create_llm_client
from vision_prompt import SYSTEM_PROMPT, build_action_prompt
import json
import re

def parse_action(response):
    json_match = re.search(r'\{[^{}]*\}', response, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group())
        except:
            pass
    try:
        return json.loads(response)
    except:
        return {"action": "error", "reason": f"Parse failed: {response[:200]}"}

# Initialize
print("=== Initializing browser and LLM ===")
browser = BrowserAgent(port=9222)
llm = create_llm_client("ollama")
print(f"LLM: {llm.model}")

# Navigate
print("\n=== Navigating to example.com ===")
browser.connect("https://example.com")
browser.navigate("https://example.com")
ctx = browser.get_context_for_llm()
print(f"Page: {ctx['page_title']}")
print(f"URL: {ctx['page_url']}")

# Ask AI a simple question (no image - text only)
print("\n=== Asking AI: what's on this page? ===")
prompt = "What is this web page about? Just give me a one sentence answer."

response = llm.chat(prompt, image_path=None, system_prompt="You are a helpful assistant.")
print(f"AI Response: {response}")

# Now try action
print("\n=== Asking AI to provide click coordinates for 'Learn more' ===")
# Simpler prompt - just ask for the JSON directly without DOM
action_prompt = """Look at the page 'Example Domain' at URL https://example.com/

The page has these elements (from HTML):
- A heading "Example Domain"  
- A paragraph with text "This domain is for use in illustrative examples in documents."
- A link with text "Learn more"

The "Learn more" link goes to https://www.iana.org/domains/example

Based on this information, where should I click to click the "Learn more" link?

Respond with ONLY this JSON format:
{"action": "click", "x": 500, "y": 300, "reason": "brief reason"}"""

response = llm.chat(action_prompt, image_path=None, system_prompt=SYSTEM_PROMPT)
print(f"LLM Response: {response[:600]}...")

action = parse_action(response)
print(f"\nParsed action: {action}")

# Execute
if action.get("action") == "click":
    browser.click(action["x"], action["y"])
    print(f"Clicked at ({action['x']}, {action['y']})")
    browser.screenshot("after_click.png")
    print("Screenshot saved: after_click.png")
    
    # Check new page
    import time
    time.sleep(1)
    info = browser.get_page_info()
    print(f"New page: {info['title']} - {info['url']}")
elif action.get("action") == "done":
    print(f"Done: {action.get('reason')}")
else:
    print(f"Action: {action}")

browser.disconnect()
print("\n=== Test complete ===")
