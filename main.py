#!/usr/bin/env python3
"""
AI Vision Browser - Main CLI entry point.

Usage:
    python main.py navigate <url>
    python main.py click "the login button"
    python main.py type "the search box" "query"
    python main.py screenshot
    python main.py interactive <url>
"""

import argparse
import json
import re
import sys
from pathlib import Path

from browser_agent import BrowserAgent, ensure_chrome
from llm_client import create_llm_client
from vision_prompt import (
    SYSTEM_PROMPT,
    build_action_prompt,
    build_element_find_prompt,
)


def parse_action_response(response: str) -> dict:
    """Parse JSON from LLM response."""
    # Try to extract JSON from response
    # Handle cases where LLM wraps JSON in markdown code blocks
    json_match = re.search(r'\{[^{}]*\}', response, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group())
        except json.JSONDecodeError:
            pass
    
    # Try full response as JSON
    try:
        return json.loads(response)
    except json.JSONDecodeError:
        pass
    
    # Fallback - try to find key values
    return {
        "action": "error",
        "reason": f"Could not parse LLM response: {response[:200]}"
    }


def cmd_navigate(args, browser: BrowserAgent, llm):
    """Navigate to URL."""
    browser.connect(args.url)
    browser.navigate(args.url)
    ctx = browser.get_context_for_llm()
    print(f"Page: {ctx['page_title']}")
    print(f"URL: {ctx['page_url']}")
    print(f"Screenshot: {ctx['screenshot_path']}")


def cmd_screenshot(args, browser: BrowserAgent, llm):
    """Take screenshot."""
    if not browser.ws:
        print("[!] Not connected. Use 'navigate' first or provide URL.")
        sys.exit(1)
    
    path = browser.screenshot(args.filename or "")
    print(f"Screenshot: {path}")


def cmd_click(args, browser: BrowserAgent, llm):
    """Click an element based on natural language description."""
    if not browser.ws:
        print("[!] Not connected. Use 'navigate' first or provide URL.")
        sys.exit(1)
    
    # Get page context
    ctx = browser.get_context_for_llm()
    
    # Build prompt
    prompt = build_action_prompt(args.description, {
        "url": ctx["page_url"],
        "title": ctx["page_title"],
    })
    
    # Ask LLM
    print(f"[AI] Analyzing: {args.description}")
    response = llm.chat(prompt, image_path=ctx["screenshot_path"], system_prompt=SYSTEM_PROMPT)
    
    print(f"[AI] Response: {response[:500]}...")
    
    # Parse action
    action = parse_action_response(response)
    print(f"[AI] Action: {action}")
    
    # Execute
    if action.get("action") == "click":
        browser.click(action["x"], action["y"])
        print(f"[✓] Clicked at ({action['x']}, {action['y']})")
    elif action.get("action") == "done":
        print(f"[✓] Done: {action.get('reason', 'Task complete')}")
    else:
        print(f"[!] Unexpected action: {action}")


def cmd_type(args, browser: BrowserAgent, llm):
    """Type text at element described by natural language."""
    if not browser.ws:
        print("[!] Not connected. Use 'navigate' first or provide URL.")
        sys.exit(1)
    
    # Get page context
    ctx = browser.get_context_for_llm()
    
    # Build prompt - user wants to type at some field
    prompt = build_action_prompt(
        f'type "{args.text}" in {args.target}',
        {"url": ctx["page_url"], "title": ctx["page_title"]}
    )
    
    # Ask LLM
    print(f"[AI] Analyzing: type '{args.text}' in {args.target}")
    response = llm.chat(prompt, image_path=ctx["screenshot_path"], system_prompt=SYSTEM_PROMPT)
    
    action = parse_action_response(response)
    print(f"[AI] Action: {action}")
    
    # Execute
    if action.get("action") == "type":
        browser.type_text(action["x"], action["y"], args.text)
        print(f"[✓] Typed at ({action['x']}, {action['y']})")
    elif action.get("action") == "click":
        # Click first, then type
        browser.click(action["x"], action["y"])
        browser.type_text(action["x"], action["y"], args.text)
        print(f"[✓] Clicked and typed at ({action['x']}, {action['y']})")
    else:
        print(f"[!] Unexpected action: {action}")


def cmd_scroll(args, browser: BrowserAgent, llm):
    """Scroll the page."""
    if not browser.ws:
        print("[!] Not connected.")
        sys.exit(1)
    
    direction = args.direction or "down"
    browser.scroll(direction)
    print(f"[✓] Scrolled {direction}")


def cmd_interactive(args, browser: BrowserAgent, llm):
    """Interactive mode - enter commands in loop."""
    # Navigate to URL if provided
    if args.url:
        browser.connect(args.url)
        browser.navigate(args.url)
        print(f"Opened: {args.url}")
        browser.screenshot("start.png")
        print("Screenshot saved. Ready for commands.\n")
    
    print("Interactive mode. Commands:")
    print("  click <description>  - Click element")
    print("  type <target> <text>  - Type text")  
    print("  scroll up|down        - Scroll")
    print("  screenshot           - Take screenshot")
    print("  quit                 - Exit")
    print()
    
    while True:
        try:
            cmd = input("> ").strip()
        except EOFError:
            break
        
        if not cmd:
            continue
        
        if cmd == "quit" or cmd == "exit":
            break
        
        parts = cmd.split(None, 1)
        action = parts[0]
        rest = parts[1] if len(parts) > 1 else ""
        
        if action == "screenshot":
            path = browser.screenshot()
            print(f"Screenshot: {path}")
        
        elif action == "scroll":
            direction = rest if rest in ("up", "down") else "down"
            browser.scroll(direction)
            print(f"Scrolled {direction}")
        
        elif action == "click" and rest:
            # Use LLM to find and click
            ctx = browser.get_context_for_llm()
            prompt = build_action_prompt(rest, {"url": ctx["page_url"], "title": ctx["page_title"]})
            response = llm.chat(prompt, image_path=ctx["screenshot_path"], system_prompt=SYSTEM_PROMPT)
            action_obj = parse_action_response(response)
            
            if action_obj.get("action") == "click":
                browser.click(action_obj["x"], action_obj["y"])
                print(f"Clicked at ({action_obj['x']}, {action_obj['y']})")
            else:
                print(f"AI: {action_obj}")
        
        elif action == "type":
            # Parse: type <target> <text>
            parts = rest.split(None, 1)
            if len(parts) == 2:
                target, text = parts
                ctx = browser.get_context_for_llm()
                prompt = build_action_prompt(f'type "{text}" in {target}', {"url": ctx["page_url"], "title": ctx["page_title"]})
                response = llm.chat(prompt, image_path=ctx["screenshot_path"], system_prompt=SYSTEM_PROMPT)
                action_obj = parse_action_response(response)
                
                if action_obj.get("action") in ("type", "click"):
                    x, y = action_obj.get("x", 500), action_obj.get("y", 300)
                    browser.type_text(x, y, text)
                    print(f"Typed at ({x}, {y})")
                else:
                    print(f"AI: {action_obj}")
            else:
                print("Usage: type <target> <text>")
        
        else:
            print(f"Unknown command: {cmd}")
    
    print("Goodbye!")


def main():
    parser = argparse.ArgumentParser(description="AI Vision Browser")
    parser.add_argument("--port", type=int, default=9222, help="CDP port")
    parser.add_argument("--llm", default="ollama", choices=["ollama", "qwen", "openai", "anthropic"], help="LLM provider")
    parser.add_argument("--model", help="LLM model name")
    parser.add_argument("--api-key", help="API key for cloud LLM providers (Qwen, OpenAI, Anthropic)")
    
    subparsers = parser.add_subparsers(dest="command", help="Commands")
    
    # navigate
    nav_parser = subparsers.add_parser("navigate", help="Navigate to URL")
    nav_parser.add_argument("url", help="URL to navigate to")
    
    # screenshot
    ss_parser = subparsers.add_parser("screenshot", help="Take screenshot")
    ss_parser.add_argument("filename", nargs="?", help="Output filename")
    
    # click
    click_parser = subparsers.add_parser("click", help="Click element by description")
    click_parser.add_argument("description", help="Element description (e.g., 'the login button')")
    
    # type
    type_parser = subparsers.add_parser("type", help="Type text at element")
    type_parser.add_argument("target", help="Target element description")
    type_parser.add_argument("text", help="Text to type")
    
    # scroll
    scroll_parser = subparsers.add_parser("scroll", help="Scroll page")
    scroll_parser.add_argument("direction", nargs="?", choices=["up", "down"], default="down", help="Direction")
    
    # interactive
    inter_parser = subparsers.add_parser("interactive", help="Interactive mode")
    inter_parser.add_argument("url", nargs="?", help="Initial URL")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Initialize browser
    ensure_chrome(port=args.port)
    browser = BrowserAgent(port=args.port)
    
    # Initialize LLM
    llm = create_llm_client(provider=args.llm, model=args.model, api_key=args.api_key)
    
    # Execute command
    try:
        if args.command == "navigate":
            cmd_navigate(args, browser, llm)
        elif args.command == "screenshot":
            cmd_screenshot(args, browser, llm)
        elif args.command == "click":
            cmd_click(args, browser, llm)
        elif args.command == "type":
            cmd_type(args, browser, llm)
        elif args.command == "scroll":
            cmd_scroll(args, browser, llm)
        elif args.command == "interactive":
            cmd_interactive(args, browser, llm)
    finally:
        browser.disconnect()


if __name__ == "__main__":
    main()
