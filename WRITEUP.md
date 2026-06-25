# Writeup — Subasta + Legado

## Tweet / Submission (3-4 lines)

🏛️ Subasta + Legado: an agent that runs an internal auction between agent personas before solving tasks, then distills what it learned into reusable skills. Next time a similar task arrives → no auction needed, the veteran agent handles it directly. Built on Hermes 4 via OpenRouter.

competition → execution → learning → reusable asset 🧬

## Extended Description (for Discord / submission form)

**What it does:** When you give the agent an ambiguous task, it simulates an internal auction between 3 agent profiles ("El Rayo" — fast/cheap, "El Artesano" — slow/thorough, "El Equilibrado" — balanced). Each profile presents its bid. The winning agent executes the task, then the system distills the approach into a reusable JSON skill file saved to disk. On the next similar task, the agent detects the existing skill and skips the auction entirely — resolving the task directly with the learned approach.

**Why it matters:** This demonstrates an autopilot agent pattern where the system gets smarter over time. The first run explores options through competition; every subsequent run is faster because the agent built institutional knowledge. It's the difference between a junior who debates every decision vs. a senior who pattern-matches from experience.

**Stack:** Hermes 4 (70B) via OpenRouter, Python, JSON skill persistence on disk. No UI — pure terminal demo as intended for the track.

**Track:** Autopilot Agents — "Make an agent that wakes up, reviews context, and interrupts only when useful."
