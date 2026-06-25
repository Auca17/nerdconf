# Subasta + Legado 🏛️

**Hermes Agent Hackathon** — NVIDIA × Stripe × Nous Research  
Track: *Autopilot Agents*

## What it does

An agent receives an ambiguous task and simulates an **internal auction** between 2-3 agent profiles (fast/cheap vs slow/thorough). The winning profile executes the task, then the agent **distills** what it learned into a reusable skill file. Next time a similar task arrives, the auction is skipped entirely — the veteran agent solves it directly.

**Arc: competition → execution → learning → reusable asset.**

## Quick Start

```bash
# Install the only dependency
pip install requests

# Run the full demo (both tasks in sequence)
python agent.py --demo

# Or run interactively
python agent.py

# Or pass a task directly
python agent.py "Escribime un resumen de 3 bullets de qué es Nebius, en tono casual, para un README."

# Reset learned skills (clean state for re-recording)
python agent.py --clean
```

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
AGENT_MODEL=nousresearch/hermes-3-llama-3.1-8b
```

## Stack

- **Runtime**: Python + OpenRouter API
- **Model**: NousResearch Hermes 3 (via OpenRouter; swappable to Nebius endpoint)
- **Persistence**: JSON skill files on disk
