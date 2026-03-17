"""
Browser Agent - CDP (Chrome DevTools Protocol) wrapper.

Provides high-level browser operations: screenshot, click, type, navigate, etc.
"""

import base64
import json
import os
import time
from pathlib import Path
from typing import Optional

import requests
import websockets.sync.client as ws_client

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 9222
DEFAULT_SCREENSHOT_DIR = Path("screenshots")


class BrowserAgent:
    """High-level browser automation via CDP."""

    def __init__(
        self,
        host: str = DEFAULT_HOST,
        port: int = DEFAULT_PORT,
        screenshot_dir: Path = DEFAULT_SCREENSHOT_DIR,
    ):
        self.host = host
        self.port = port
        self.screenshot_dir = screenshot_dir
        self.ws: Optional[ws_client.Client] = None
        self._msg_id = 0
        self.target_id: Optional[str] = None

        # Create screenshot directory
        self.screenshot_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Connection
    # ------------------------------------------------------------------

    def connect(self, target_url: str = "", new_tab: bool = False) -> bool:
        """Connect to existing Chrome tab or create new one."""
        targets = self._get_targets()

        # Find existing tab with matching URL
        found = False
        if not new_tab:
            for t in targets:
                if t.get("type") == "page":
                    url = t.get("url", "")
                    if not target_url or target_url in url:
                        self.target_id = t.get("id")
                        found = True
                        break

        # Create new tab if none found or requested
        if not self.target_id:
            self.target_id = self._create_tab(target_url or "about:blank")

        # Connect via WebSocket
        ws_url = self._get_ws_url(self.target_id)
        if not ws_url:
            raise ConnectionError(f"Could not get WebSocket URL for target {self.target_id}")

        print(f"[browser_agent] Connecting to {ws_url}")
        self.ws = ws_client.connect(ws_url)
        print("[browser_agent] Connected.")
        return True

    def disconnect(self):
        """Close WebSocket connection."""
        if self.ws:
            self.ws.close()
            self.ws = None

    def _get_targets(self) -> list:
        """Get list of browser targets."""
        url = f"http://{self.host}:{self.port}/json"
        resp = requests.get(url, timeout=5)
        resp.raise_for_status()
        return resp.json()

    def _create_tab(self, url: str) -> str:
        """Create new browser tab."""
        resp = requests.put(
            f"http://{self.host}:{self.port}/json/new?{url}",
            timeout=5
        )
        resp.raise_for_status()
        return resp.json().get("id")

    def _close_tab(self):
        """Close current tab."""
        if self.target_id:
            self._send("Target.closeTarget", {"targetId": self.target_id})

    def _get_ws_url(self, target_id: str) -> Optional[str]:
        """Get WebSocket URL for a target."""
        targets = self._get_targets()
        for t in targets:
            if t.get("id") == target_id:
                return t.get("webSocketDebuggerUrl")
        return None

    # ------------------------------------------------------------------
    # CDP Primitives
    # ------------------------------------------------------------------

    def _send(self, method: str, params: Optional[dict] = None, retries: int = 3) -> dict:
        """Send CDP command and return result."""
        if not self.ws:
            raise ConnectionError("Not connected. Call connect() first.")

        last_error = None
        for attempt in range(retries):
            try:
                self._msg_id += 1
                msg = {"id": self._msg_id, "method": method}
                if params:
                    msg["params"] = params

                self.ws.send(json.dumps(msg))

                while True:
                    raw = self.ws.recv()
                    data = json.loads(raw)
                    if data.get("id") == self._msg_id:
                        if "error" in data:
                            raise RuntimeError(f"CDP error: {data['error']}")
                        return data.get("result", {})
                break
            except Exception as e:
                last_error = e
                if attempt < retries - 1:
                    time.sleep(0.5)
                    continue
                raise last_error

    def _evaluate(self, expression: str):
        """Execute JavaScript in page."""
        result = self._send("Runtime.evaluate", {
            "expression": expression,
            "returnByValue": True,
            "awaitPromise": True,
        })
        return result.get("result", {}).get("value")

    # ------------------------------------------------------------------
    # Navigation Actions
    # ------------------------------------------------------------------

    def navigate(self, url: str):
        """Navigate to URL."""
        print(f"[browser_agent] Navigating to {url}")
        self._send("Page.enable")
        self._send("Page.navigate", {"url": url})
        time.sleep(2)  # Wait for page load
        print("[browser_agent] Navigation complete.")

    def refresh(self):
        """Refresh the page."""
        print("[browser_agent] Refreshing page")
        self._send("Page.reload")
        time.sleep(2)

    def go_back(self):
        """Go back in history."""
        print("[browser_agent] Going back")
        self._send("History.goBack")
        time.sleep(2)

    def go_forward(self):
        """Go forward in history."""
        print("[browser_agent] Going forward")
        self._send("History.goForward")
        time.sleep(2)

    # ------------------------------------------------------------------
    # Screenshot
    # ------------------------------------------------------------------

    def screenshot(self, filename: Optional[str] = None, full_page: bool = True) -> str:
        """Take screenshot and return path."""
        if not filename:
            filename = f"screenshot_{int(time.time())}.png"
        filepath = self.screenshot_dir / filename

        result = self._send("Page.captureScreenshot", {
            "format": "png",
            "captureBeyondViewport": full_page,
        })

        # Decode base64 and save
        img_data = result.get("data")
        if not img_data:
            raise RuntimeError("No image data returned")

        with open(filepath, "wb") as f:
            f.write(base64.b64decode(img_data))

        print(f"[browser_agent] Screenshot saved: {filepath}")
        return str(filepath)

    # ------------------------------------------------------------------
    # Click Actions
    # ------------------------------------------------------------------

    def click(self, x: int, y: int, button: str = "left"):
        """Click at coordinates (x, y)."""
        print(f"[browser_agent] Clicking at ({x}, {y})")
        
        # Dispatch mouse events
        self._send("Input.dispatchMouseEvent", {
            "type": "mousePressed",
            "x": x,
            "y": y,
            "button": button,
            "clickCount": 1,
        })
        self._send("Input.dispatchMouseEvent", {
            "type": "mouseReleased",
            "x": x,
            "y": y,
            "button": button,
        })
        time.sleep(0.3)  # Wait for click to register

    def double_click(self, x: int, y: int, button: str = "left"):
        """Double-click at coordinates (x, y)."""
        print(f"[browser_agent] Double-clicking at ({x}, {y})")
        
        self._send("Input.dispatchMouseEvent", {
            "type": "mousePressed",
            "x": x,
            "y": y,
            "button": button,
            "clickCount": 2,
        })
        self._send("Input.dispatchMouseEvent", {
            "type": "mouseReleased",
            "x": x,
            "y": y,
            "button": button,
        })
        time.sleep(0.3)

    def right_click(self, x: int, y: int):
        """Right-click at coordinates (x, y)."""
        print(f"[browser_agent] Right-clicking at ({x}, {y})")
        self.click(x, y, "right")

    def click_element_at_center(self, selector: str):
        """Click an element by finding its bounding box center."""
        js = f"""
        (() => {{
            const el = document.querySelector('{selector}');
            if (!el) return null;
            const rect = el.getBoundingClientRect();
            return {{
                x: rect.x + rect.width / 2,
                y: rect.y + rect.height / 2,
                width: rect.width,
                height: rect.height
            }};
        }})()
        """
        result = self._evaluate(js)
        if not result:
            raise ValueError(f"Element not found: {selector}")
        
        self.click(int(result["x"]), int(result["y"]))

    # ------------------------------------------------------------------
    # Type Actions - OPTIMIZED
    # ------------------------------------------------------------------

    def type_text(self, x: int, y: int, text: str, delay: float = 0.01):
        """Click at (x,y) then type text - optimized version."""
        print(f"[browser_agent] Typing at ({x}, {y}): {text}")
        
        # Click to focus
        self.click(x, y)
        time.sleep(0.2)
        
        # Clear existing text with Ctrl+A + Delete
        self._send("Input.dispatchKeyEvent", {
            "type": "keyDown",
            "text": "\u0001",  # Ctrl+A
            "modifiers": 2,
        })
        self._send("Input.dispatchKeyEvent", {
            "type": "keyUp",
            "text": "\u0001",
            "modifiers": 2,
        })
        
        # Type using insertText (much faster than keyBy key)
        self._send("Input.insertText", {"text": text})
        time.sleep(0.1)

    def type_text_slow(self, x: int, y: int, text: str, delay: float = 0.05):
        """Type character by character - for sites that need it."""
        print(f"[browser_agent] Typing slowly at ({x}, {y}): {text}")
        
        self.click(x, y)
        time.sleep(0.2)
        
        for char in text:
            self._send("Input.dispatchKeyEvent", {
                "type": "keyDown",
                "text": char,
            })
            self._send("Input.dispatchKeyEvent", {
                "type": "keyUp",
                "text": char,
            })
            time.sleep(delay)

    def press_key(self, key: str):
        """Press a single key."""
        self._send("Input.dispatchKeyEvent", {
            "type": "keyDown",
            "key": key,
        })
        self._send("Input.dispatchKeyEvent", {
            "type": "keyUp",
            "key": key,
        })
        time.sleep(0.1)

    def press_enter(self):
        """Press Enter."""
        self.press_key("Enter")

    def press_escape(self):
        """Press Escape."""
        self.press_key("Escape")

    def press_tab(self):
        """Press Tab."""
        self.press_key("Tab")

    # ------------------------------------------------------------------
    # Scroll Actions
    # ------------------------------------------------------------------

    def scroll(self, direction: str = "down", amount: int = 500, x: int = 500, y: int = 300):
        """Scroll the page."""
        delta_y = amount if direction == "down" else -amount
        
        self._send("Input.dispatchMouseEvent", {
            "type": "mouseWheel",
            "x": x,
            "y": y,
            "deltaY": delta_y,
        })
        print(f"[browser_agent] Scrolled {direction}")

    def scroll_to_top(self):
        """Scroll to top of page."""
        self._evaluate("window.scrollTo(0, 0)")
        time.sleep(0.3)

    def scroll_to_bottom(self):
        """Scroll to bottom of page."""
        self._evaluate("window.scrollTo(0, document.body.scrollHeight)")
        time.sleep(0.3)

    # ------------------------------------------------------------------
    # Hover
    # ------------------------------------------------------------------

    def hover(self, x: int, y: int):
        """Hover at coordinates (x, y)."""
        print(f"[browser_agent] Hovering at ({x}, {y})")
        self._send("Input.dispatchMouseEvent", {
            "type": "mouseMoved",
            "x": x,
            "y": y,
        })
        time.sleep(0.3)

    # ------------------------------------------------------------------
    # Page Info
    # ------------------------------------------------------------------

    def get_page_info(self) -> dict:
        """Get current page URL and title."""
        url = self._evaluate("window.location.href")
        title = self._evaluate("document.title")
        return {"url": url, "title": title}

    def get_dom_snapshot(self) -> str:
        """Get simplified DOM snapshot for LLM context."""
        js = """
        (() => {
            const getVisibleText = (el) => {
                if (el.hidden) return '';
                const tag = el.tagName?.toLowerCase();
                if (tag === 'script' || tag === 'style') return '';
                let text = el.innerText?.trim() || '';
                if (text.length > 100) text = text.substring(0, 100) + '...';
                return text;
            };
            
            const getElements = () => {
                const els = document.querySelectorAll('button, a, input, textarea, select, [role="button"], [onclick]');
                return Array.from(els).slice(0, 50).map((el, i) => {
                    const rect = el.getBoundingClientRect();
                    if (rect.width < 5 || rect.height < 5 || rect.y < 0) return null;
                    return {
                        index: i,
                        tag: el.tagName.toLowerCase(),
                        text: getVisibleText(el),
                        type: el.type || '',
                        placeholder: el.placeholder || '',
                        href: el.href || '',
                        rect: { x: Math.round(rect.x), y: Math.round(rect.y), w: Math.round(rect.width), h: Math.round(rect.height) }
                    };
                }).filter(Boolean);
            };
            
            return JSON.stringify({
                url: window.location.href,
                title: document.title,
                elements: getElements()
            });
        })()
        """
        return self._evaluate(js)

    # ------------------------------------------------------------------
    # Context for LLM
    # ------------------------------------------------------------------

    def get_context_for_llm(self) -> dict:
        """Get all context needed for LLM to understand page."""
        screenshot_path = self.screenshot()
        page_info = self.get_page_info()
        dom_snapshot = self.get_dom_snapshot()
        
        return {
            "screenshot_path": screenshot_path,
            "page_url": page_info["url"],
            "page_title": page_info["title"],
            "dom_snapshot": dom_snapshot,
        }

    # ------------------------------------------------------------------
    # Wait
    # ------------------------------------------------------------------

    def wait(self, seconds: float):
        """Wait for specified seconds."""
        time.sleep(seconds)


def ensure_chrome(port: int = DEFAULT_PORT, headless: bool = False):
    """Ensure Chrome is running with remote debugging."""
    import subprocess
    
    # Check if already running
    try:
        resp = requests.get(f"http://127.0.0.1:{port}/json", timeout=2)
        if resp.ok:
            print(f"[browser_agent] Chrome already running on port {port}")
            return True
    except Exception:
        pass
    
    # Launch Chrome
    if os.path.exists("/Applications/Google Chrome.app"):
        cmd = [
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            f"--remote-debugging-port={port}",
            "--no-first-run",
            "--no-default-browser-check",
            "--disable-popup-blocking",
        ]
        if headless:
            cmd.append("--headless=new")
        
        subprocess.Popen(cmd)
        print(f"[browser_agent] Launched Chrome on port {port}")
        time.sleep(3)
        return True
    
    # Try linux
    if os.system("which google-chrome") == 0:
        cmd = [
            "google-chrome",
            f"--remote-debugging-port={port}",
            "--no-first-run",
            "--no-default-browser-check",
        ]
        if headless:
            cmd.append("--headless=new")
        
        subprocess.Popen(cmd)
        time.sleep(3)
        return True
    
    raise RuntimeError("Chrome not found")
