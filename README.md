# AI Vision Browser

AI-first browser automation using vision-capable LLM + CDP (Chrome DevTools Protocol). No hardcoded selectors — the AI understands the page visually.

## How It Works

```
┌─────────────┐    ┌───────────────┐    ┌─────────────┐
│  Screenshot │───▶│  Qwen VL      │───▶│  Action     │
│  of page    │    │  "Click 发布" │    │  click@x,y │
└─────────────┘    └───────────────┘    └─────────────┘
                           │
                           ▼
                    ┌─────────────┐
                    │  CDP        │
                    │  Execute    │
                    └─────────────┘
```

## Requirements

- Python 3.9+
- Chrome/Chromium
- Qwen VL model (or any vision LLM with API)

## Installation

```bash
pip install -r requirements.txt
```

## Usage

### 1. Start Chrome with remote debugging

```bash
google-chrome --remote-debugging-port=9222
# or on Mac
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --remote-debugging-port=9222
```

### 2. Run a command

```bash
python main.py navigate "https://www.xiaohongshu.com"
python main.py click "the upload button"
python main.py type "the title input" "My Video Title"
python main.py screenshot
```

### 3. Interactive mode

```bash
python main.py interactive https://creator.douyin.com
```

Then type commands like:
- `click the 发布 button`
- `type the title field "Hello World"`
- `scroll down`
- `screenshot`

## Architecture

```
ai-vision-browser/
├── browser_agent.py      # CDP wrapper (screenshot, click, type)
├── vision_prompt.py      # Prompt templates for LLM
├── llm_client.py         # LLM API client (Qwen VL)
├── main.py               # CLI entry point
└── requirements.txt      # Python dependencies
```

## Supported Actions

| Action | Example |
|--------|---------|
| `navigate` | `navigate https://example.com` |
| `click` | `click the login button` |
| `type` | `type the search box "query"` |
| `screenshot` | `screenshot` |
| `scroll` | `scroll down` / `scroll up` |
| `wait` | `wait 2 seconds` |

## LLM Configuration

Default: Qwen VL via Ollama (`http://localhost:11434`)

To use other LLMs, edit `llm_client.py`:

```python
# OpenAI GPT-4V
BASE_URL = "https://api.openai.com/v1"
MODEL = "gpt-4-vision-preview"

# Anthropic Claude
BASE_URL = "https://api.anthropic.com/v1"
MODEL = "claude-3-opus-20240229"
```

## Why This Approach

Traditional CDP automation:
```python
driver.find_element(By.CSS_SELECTOR, "#submit-btn").click()
# Breaks when UI changes
```

AI Vision approach:
```python
# "Click the submit button" → AI finds it visually
click("the submit button")
# Works even with dynamic UIs
```

## License

MIT
