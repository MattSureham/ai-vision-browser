# AI Vision Browser

AI-first browser automation using vision-capable LLM + CDP (Chrome DevTools Protocol). No hardcoded selectors — the AI understands the page visually.

## How It Works

```
┌─────────────┐    ┌───────────────┐    ┌─────────────┐
│  Screenshot │───▶│  Vision LLM  │───▶│  Action     │
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
- Chrome/Chromium with remote debugging enabled
- At least one LLM provider (Ollama, OpenAI, Anthropic, Kimi, or Minimax)

## Installation

```bash
pip install -r requirements.txt
```

## Supported LLM Providers

| Provider | Vision Models | API Key Required |
|----------|---------------|------------------|
| Ollama | qwen2.5-vl, llava | No (local) |
| OpenAI | gpt-4o, gpt-4-vision | Yes |
| Anthropic | claude-3-5-sonnet | Yes |
| Kimi (Moonshot) | moonshot-v1-8k-vision | Yes |
| Minimax | MiniMax-M2.5 | Yes |

## Usage

### 1. Start Chrome with remote debugging

```bash
# Mac
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --remote-debugging-port=9222

# Linux
google-chrome --remote-debugging-port=9222
```

### 2. Run commands

```bash
# Navigate to a URL
python main.py navigate "https://www.xiaohongshu.com"

# Click an element by description
python main.py click "the upload button"

# Type text into a field
python main.py type "the title input" "My Video Title"

# Take screenshot
python main.py screenshot

# Scroll
python main.py scroll down
python main.py scroll up

# Refresh / Go back / Go forward
python main.py refresh
python main.py back
python main.py forward
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
- `refresh`
- `back`
- `forward`
- `quit`

### 4. Using different LLM providers

```bash
# Ollama (local, default)
python main.py --llm ollama --model qwen2.5-vl:7b click "the button"

# OpenAI
python main.py --llm openai --model gpt-4o --api-key sk-xxx click "the button"

# Anthropic
python main.py --llm anthropic --model claude-3-5-sonnet-20241022 --api-key sk-ant-xxx click "the button"

# Kimi (Moonshot AI)
python main.py --llm kimi --model k2p5 --api-key your-kimi-api-key click "the button"

# Minimax
python main.py --llm minimax --model MiniMax-M2.5 --api-key your-minimax-key click "the button"
```

## Architecture

```
ai-vision-browser/
├── browser_agent.py      # CDP wrapper (screenshot, click, type, navigate)
├── vision_prompt.py      # Prompt templates for LLM
├── llm_client.py         # Multi-provider LLM client
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
| `refresh` | `refresh` |
| `back` | `back` |
| `forward` | `forward` |

## API Keys

Set via `--api-key` flag or environment variable:

```bash
export OPENAI_API_KEY=sk-xxx
export ANTHROPIC_API_KEY=sk-ant-xxx
export KIMI_API_KEY=your-kimi-key
export MINIMAX_API_KEY=your-minimax-key
```

## Retry Logic

Failed actions automatically retry (default: 3 retries). Configure with `--retries`:

```bash
python main.py --retries 5 click "the submit button"
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
