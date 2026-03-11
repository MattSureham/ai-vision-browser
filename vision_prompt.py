"""
Vision Prompt - Prompt templates for AI understanding of web pages.
"""

from typing import Optional


# System prompt for the AI browser agent
SYSTEM_PROMPT = """You are an AI browser automation agent. Your job is to understand what the user wants to do on a web page, look at the screenshot, and determine the exact action to take.

You must respond with a JSON object describing the action.

Available actions:
- click: Click at coordinates (x, y)
- type: Click at coordinates (x, y) then type text
- scroll: Scroll the page (up/down)
- wait: Wait for a duration
- done: Task is complete, no more actions needed
- error: Something went wrong

IMPORTANT:
1. Always look at the screenshot to find the correct element
2. Provide exact (x, y) coordinates for clicks
3. For clicking buttons/links, click at the CENTER of the element
4. Coordinates are in pixels from top-left of the screenshot
5. If you need more context, you can ask questions

Respond ONLY with JSON, no other text."""


def build_action_prompt(
    user_command: str,
    page_info: Optional[dict] = None,
    dom_snapshot: Optional[str] = None,
) -> str:
    """
    Build prompt for action determination.
    
    Args:
        user_command: What the user wants to do
        page_info: URL and title of current page
        dom_snapshot: Simplified DOM for context
    """
    prompt = f"""Current page: {page_info.get('title', 'Unknown')} ({page_info.get('url', 'Unknown')})

User command: "{user_command}"

Look at the screenshot and determine what action to take. 

Respond with JSON:
{{
    "action": "click|type|scroll|wait|done|error",
    "x": 500,           // x coordinate (only for click/type)
    "y": 300,           // y coordinate (only for click/type)
    "text": "...",      // text to type (only for type)
    "direction": "up|down",  // scroll direction (only for scroll)
    "reason": "..."     // explain what you're doing
}}

If the user wants to click something, find it visually in the screenshot and provide its center coordinates.
If the user wants to type, provide where to click first, then what to type.
If the action is done, set action to "done".
If something is wrong, set action to "error" and explain.
"""
    return prompt


def build_page_summary_prompt() -> str:
    """Build prompt for summarizing the current page."""
    return """Look at this screenshot of a web page. 

Provide a brief summary of:
1. What is this page about?
2. What are the main actions/buttons available?
3. Any important information visible?

Be concise - 2-3 sentences max."""


def build_element_find_prompt(
    element_description: str,
    dom_snapshot: Optional[str] = None,
) -> str:
    """Build prompt to find a specific element."""
    prompt = f"""Find the element described as: "{element_description}"

Look at the screenshot and find the center coordinates (x, y) of this element.

Respond with JSON:
{{
    "found": true/false,
    "x": 500,
    "y": 300,
    "description": "what you found"
}}

If not found, set found to false and describe what's available instead."""
    return prompt


# Example responses for testing

EXAMPLE_CLICK = """```json
{
    "action": "click",
    "x": 450,
    "y": 820,
    "reason": "Found the '发布' button at the center of the element"
}
```"""

EXAMPLE_TYPE = """```json
{
    "action": "type",
    "x": 400,
    "y": 200,
    "text": "My Video Title",
    "reason": "Clicking the title input field and typing the text"
}
```"""

EXAMPLE_SCROLL = """```json
{
    "action": "scroll",
    "direction": "down",
    "reason": "Scrolling down to see more content"
}
```"""

EXAMPLE_DONE = """```json
{
    "action": "done",
    "reason": "Successfully submitted the form"
}
```"""
