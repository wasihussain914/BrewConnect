# BrewConnect

AI-powered LinkedIn outreach automation. Finds alumni from your university working at a target company, generates personalized coffee-chat connection notes using Claude, and sends the requests — all from your existing browser session with no credential storage.

## How it works

1. **Browser launch** — opens Brave with a dedicated automation profile and verifies your existing LinkedIn session (you log in manually once; the profile persists).
2. **Alumni search** — navigates to the target company's LinkedIn people page filtered by your university.
3. **Note generation** — calls the Claude API (claude-3-haiku) to write a personalized, ≤300-character connection request for each person.
4. **Request send** — clicks through LinkedIn's connect flow and submits each request with the generated note.
5. **Safety limits** — configurable `MAX_REQUESTS_PER_RUN` cap, randomized inter-request delays (45–120 s), and automatic logging of failed requests to `failed_requests.txt`.

## Setup

### Prerequisites

- Python 3.9+
- [Brave Browser](https://brave.com/) installed at the default Windows path
- ChromeDriver (Selenium fetches it automatically)
- An [Anthropic API key](https://console.anthropic.com/)

### Install dependencies

```bash
pip install selenium requests python-dotenv
```

### Configure

Copy `.env.example` to `api_key.env` and fill in your key:

```bash
cp .env.example api_key.env
```

```env
CLAUDE_API_KEY=sk-ant-...
```

Edit the constants at the top of `main.py`:

```python
TARGET_COMPANY    = "Google"             # LinkedIn company slug
TARGET_UNIVERSITY = "Vanderbilt University"
MAX_REQUESTS_PER_RUN = 10               # Keep low (5–10); run once per day max
```

### Log in to LinkedIn

Open Brave Browser and log into LinkedIn normally. BrewConnect reuses that session — it never touches your credentials.

### Run

```bash
python main.py
```

## Project structure

```
BrewConnect/
├── main.py          # All logic: browser setup, scraping, AI note gen, sending
├── .env.example     # Environment variable template
└── failed_requests.txt  # Created at runtime; profiles that errored
```

## Safety & rate limits

LinkedIn actively detects automation. Built-in guards:

| Guard | Value |
|---|---|
| Max requests per run | `MAX_REQUESTS_PER_RUN` (default 10) |
| Delay between requests | 45–120 s (randomized) |
| Separate browser profile | avoids polluting your main session |
| Failed request log | manual follow-up on errors |

Run at most once per day. Start with 5 requests and increase gradually.

## Tech stack

- **Selenium** — browser automation
- **Brave Browser** — Chromium base with separate automation profile
- **Claude API** (`claude-3-haiku-20240307`) — personalized note generation
- **python-dotenv** — environment variable loading

## License

MIT
