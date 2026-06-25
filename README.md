# Subasta + Legado 🏛️

**Hermes Agent Hackathon** — NVIDIA × Stripe × Nous Research  
Track: *Autopilot Agents*

## What it does

An agent receives an ambiguous task and simulates an **internal auction** between 2-3 agent profiles (fast/cheap vs slow/thorough). The winning profile executes the task, then the agent **distills** what it learned into a reusable skill file. Next time a similar task arrives, the auction is skipped entirely — the veteran agent solves it directly.

**Arc: competition → execution → learning → reusable asset.**

---

## 🚀 Quick Start

### Prerequisites

- **Python 3.8+** installed ([python.org](https://www.python.org/downloads/))
- An **OpenRouter API key** ([openrouter.ai](https://openrouter.ai/settings/keys))

### 1. Clone the repo

```bash
git clone https://github.com/nerdconf/subasta-legado.git
cd subasta-legado
```

### 2. Install dependencies

```bash
pip install requests flask
```

> 💡 On some Windows environments you may also need: `pip install truststore`

### 3. Configure your API key

Create a `.env` file in the project root:

```env
OPENROUTER_API_KEY=sk-or-v1-your-key-here
AGENT_MODEL=nousresearch/hermes-3-llama-3.1-405b:free
```

You can swap `AGENT_MODEL` for any model supported by [OpenRouter](https://openrouter.ai/models).

### 4. Run it!

You have two ways to use Subasta + Legado:

#### 🖥️ Terminal Mode (original)

```bash
# Run the full demo (both tasks in sequence, non-interactive)
python agent.py --demo

# Interactive mode — type your own task
python agent.py

# Pass a task directly
python agent.py "Escribime un resumen de 3 bullets de qué es Nebius, en tono casual, para un README."

# Reset learned skills (clean state)
python agent.py --clean
```

#### 🌐 Web Demo (frontend)

```bash
python server.py
```

Then open **http://localhost:5000** in your browser. The web interface lets you:
- Type or pick demo tasks
- Select an agent profile (El Rayo / El Artesano / El Equilibrado)
- Watch the full flow in real-time (SSE streaming)
- See learned skills in the inventory panel
- Clean/reset skills with one click

---

## How it works

1. **Skill Lookup** — checks if a matching skill already exists from a previous task
2. **Auction** (if no skill found) — single LLM call generates 3 agent profiles with bids
3. **Selection** — user picks the winner (or accepts the recommended one)
4. **Execution** — the winning agent profile solves the task
5. **Distillation** — the approach is extracted into a JSON skill file saved to `skills/`
6. **Reuse** — on similar future tasks, the skill is applied directly (no auction)

## Config

Edit `.env`:

```env
OPENROUTER_API_KEY=sk-or-v1-your-key-here
AGENT_MODEL=nousresearch/hermes-3-llama-3.1-405b:free
```

## Stack

- **Runtime**: Python + OpenRouter API
- **Frontend**: Flask + vanilla HTML/CSS/JS (SSE streaming)
- **Model**: NousResearch Hermes 3 (via OpenRouter; swappable to any provider)
- **Persistence**: JSON skill files on disk

## Project Structure

```
nerdconf/
├── agent.py           # CLI agent (terminal mode)
├── server.py          # Flask web server (web demo)
├── .env               # API key config (gitignored)
├── templates/
│   └── index.html     # Web frontend
├── static/
│   └── style.css      # Design system
├── skills/            # Auto-generated skill files (gitignored)
├── README.md
├── WRITEUP.md
└── claude.md          # Dev spec
```
