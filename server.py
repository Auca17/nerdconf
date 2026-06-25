#!/usr/bin/env python3
"""
🏛️ Subasta + Legado — Web Demo Server
Flask server that exposes the agent flow via a beautiful web frontend.
"""

import os
import sys
import json
import time
import re
import shutil
from pathlib import Path

# Fix SSL cert verification on Windows UV/portable Python environments
try:
    import truststore
    truststore.inject_into_ssl()
except ImportError:
    pass

import requests
from flask import Flask, render_template, request as flask_request, jsonify, Response
import queue
import threading

# ═══════════════════════════════════════════════════════════════════════════
# CONFIG
# ═══════════════════════════════════════════════════════════════════════════

ROOT = Path(__file__).parent
SKILLS_DIR = ROOT / "skills"
ENV_FILE = ROOT / ".env"

# Load .env file
if ENV_FILE.exists():
    for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
API_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL = os.environ.get("AGENT_MODEL", "nousresearch/hermes-3-llama-3.1-405b:free")

app = Flask(__name__, template_folder="templates", static_folder="static")


# ═══════════════════════════════════════════════════════════════════════════
# LLM CALLS
# ═══════════════════════════════════════════════════════════════════════════

def llm(messages, temperature=0.7, max_retries=5):
    """Single LLM call via OpenRouter, with automatic retry on rate-limit."""
    if not API_KEY:
        raise ValueError("OPENROUTER_API_KEY not set")

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/nerdconf/subasta-legado",
        "X-Title": "Subasta+Legado Agent",
    }
    body = {
        "model": MODEL,
        "messages": messages,
        "temperature": temperature,
    }

    for attempt in range(max_retries):
        try:
            r = requests.post(API_URL, headers=headers, json=body, timeout=90)

            if r.status_code == 429:
                data = r.json()
                retry_after = data.get("error", {}).get("metadata", {}).get(
                    "retry_after_seconds", 2 * (attempt + 1)
                )
                retry_after = max(int(retry_after), 2)
                time.sleep(retry_after)
                continue

            r.raise_for_status()
            data = r.json()
            return data["choices"][0]["message"]["content"]

        except requests.exceptions.RequestException as e:
            if attempt < max_retries - 1:
                time.sleep(2)
                continue
            raise RuntimeError(f"API error: {e}")
        except (KeyError, IndexError):
            raise RuntimeError(f"Unexpected API response: {data}")

    raise RuntimeError("Max retries exceeded")


# ═══════════════════════════════════════════════════════════════════════════
# CORE FLOW (same logic as agent.py, adapted for web)
# ═══════════════════════════════════════════════════════════════════════════

def find_skill(task):
    """Check if a previously distilled skill matches this task type."""
    SKILLS_DIR.mkdir(exist_ok=True)
    skills = list(SKILLS_DIR.glob("*.json"))
    if not skills:
        return None

    catalog = []
    for sp in skills:
        try:
            s = json.loads(sp.read_text(encoding="utf-8"))
            catalog.append({
                "file": sp.name,
                "type": s.get("type", ""),
                "description": s.get("description", ""),
            })
        except Exception:
            continue

    if not catalog:
        return None

    result = llm(
        [
            {
                "role": "system",
                "content": (
                    "You are a skill matcher. Respond with ONLY a filename or NONE. "
                    "No explanation, no quotes, no markdown. "
                    "Match by TASK TYPE, not by specific topic."
                ),
            },
            {
                "role": "user",
                "content": (
                    f'New task: "{task}"\n\n'
                    f"Available skills:\n{json.dumps(catalog, ensure_ascii=False)}\n\n"
                    "Does any skill match this task TYPE (not exact topic)? "
                    "Reply with ONLY the filename, or NONE."
                ),
            },
        ],
        temperature=0.0,
    )

    result = result.strip().strip("\"'` \n")
    if result.upper() == "NONE" or not result:
        return None

    path = SKILLS_DIR / result
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return None
    return None


def auction(task):
    """Simulated auction — single LLM call, 3 agent profiles."""
    prompt = f"""Actuá como un "subastador" interno. Te doy una tarea y necesito que generes 3 perfiles
de agente que podrían resolverla.

Para cada uno mostrá:
🏷️ **Nombre** y estilo
⏱️ **Tiempo estimado** (tokens aprox)
⭐ **Calidad** (1-10)
📋 **Oferta**: qué haría exactamente, en 1-2 líneas

Los 3 perfiles:
1. **"El Rayo"** — ultra rápido, conciso, directo al grano
2. **"El Artesano"** — metódico, detallista, resultado pulido
3. **"El Equilibrado"** — balance entre velocidad y calidad

Al final, en UNA sola línea, recomendá un ganador y por qué.

Tarea: {task}"""

    return llm(
        [
            {
                "role": "system",
                "content": (
                    "Sos un subastador de agentes IA. Presentá las ofertas de forma "
                    "clara, visual y entretenida. Usá emojis para los encabezados."
                ),
            },
            {"role": "user", "content": prompt},
        ]
    )


def execute_task(task, profile="El Equilibrado"):
    """Execute the task as the chosen agent profile."""
    return llm(
        [
            {
                "role": "system",
                "content": (
                    f"Sos un agente IA con el perfil '{profile}'. "
                    "Resolvé la tarea directamente, sin meta-comentarios ni preámbulos."
                ),
            },
            {"role": "user", "content": f"Resolvé esta tarea:\n{task}"},
        ]
    )


def execute_from_skill(task, skill):
    """Execute using a previously learned skill."""
    steps = "\n".join(f"  {i+1}. {s}" for i, s in enumerate(skill.get("steps", [])))
    template = skill.get("template", "N/A")

    return llm(
        [
            {
                "role": "system",
                "content": (
                    "Sos un agente veterano. Aplicá tu skill aprendida directamente. "
                    "Sin meta-comentarios ni preámbulos."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"SKILL APRENDIDA:\n{skill['description']}\n\n"
                    f"PASOS:\n{steps}\n\n"
                    f"TEMPLATE DE REFERENCIA:\n{template}\n\n"
                    f"TAREA NUEVA: {task}\n\n"
                    "Aplicá la skill y respondé con el resultado."
                ),
            },
        ]
    )


def distill(task, result):
    """Distill the approach into a reusable skill file."""
    raw = llm(
        [
            {
                "role": "system",
                "content": (
                    "Generás skill files en JSON puro. SOLO JSON válido. "
                    "Sin markdown fences (```), sin explicación, sin texto extra. "
                    "IMPORTANT: the 'type' field must describe the GENERIC task type."
                ),
            },
            {
                "role": "user",
                "content": f"""Acabás de resolver esta tarea:
"{task}"

Tu resultado fue:
{result}

Generá un JSON con esta estructura EXACTA (sin campos extra):
{{"type": "tipo-generico-en-kebab-case", "description": "Descripción GENÉRICA del tipo de tarea", "steps": ["paso 1", "paso 2", "paso 3"], "template": "template con {{{{TEMA}}}} como placeholder reemplazable"}}

REGLAS:
- "type" debe ser GENÉRICO (ej: "resumen-casual-readme", NO "resumen-nebius")
- "description" debe describir el TIPO de tarea
- "template" debe usar {{{{TEMA}}}} donde iría el tema variable
- SOLO JSON válido. Nada más.""",
            },
        ],
        temperature=0.2,
    )

    raw = raw.strip()
    if raw.startswith("```"):
        lines = raw.split("\n")
        end = -1 if lines[-1].strip().startswith("```") else len(lines)
        raw = "\n".join(lines[1:end])

    json_match = re.search(r"\{[\s\S]*\}", raw)
    if json_match:
        raw = json_match.group()

    skill = json.loads(raw)

    for key in ("type", "description", "steps"):
        if key not in skill:
            raise KeyError(f"Missing required field: {key}")

    SKILLS_DIR.mkdir(exist_ok=True)
    fname = f"{skill['type']}.json"
    path = SKILLS_DIR / fname
    path.write_text(json.dumps(skill, indent=2, ensure_ascii=False), encoding="utf-8")

    return skill, path


# ═══════════════════════════════════════════════════════════════════════════
# WEB ROUTES
# ═══════════════════════════════════════════════════════════════════════════

@app.route("/")
def index():
    return render_template("index.html", model=MODEL)


@app.route("/api/status")
def api_status():
    """Check API key and model status."""
    skills = []
    if SKILLS_DIR.exists():
        for sp in SKILLS_DIR.glob("*.json"):
            try:
                s = json.loads(sp.read_text(encoding="utf-8"))
                skills.append({
                    "file": sp.name,
                    "type": s.get("type", ""),
                    "description": s.get("description", ""),
                    "steps": s.get("steps", []),
                })
            except Exception:
                continue

    return jsonify({
        "api_key_set": bool(API_KEY),
        "model": MODEL,
        "skills_count": len(skills),
        "skills": skills,
    })


@app.route("/api/run", methods=["POST"])
def api_run():
    """Run the full agent flow for a task. Returns SSE stream."""
    data = flask_request.json
    task = data.get("task", "").strip()
    profile_choice = data.get("profile", "3")  # default: El Equilibrado

    if not task:
        return jsonify({"error": "No task provided"}), 400

    profiles = {"1": "El Rayo", "2": "El Artesano", "3": "El Equilibrado"}

    def generate():
        task_start = time.time()

        # Phase 1: Skill Lookup
        yield _sse("phase", {"phase": "skill_lookup", "title": "Búsqueda de Skills", "icon": "🔍"})
        try:
            skill = find_skill(task)
        except Exception as e:
            yield _sse("error", {"message": str(e)})
            return

        if skill:
            # REUSE PATH
            yield _sse("skill_found", {
                "type": skill["type"],
                "description": skill["description"],
                "steps": skill.get("steps", []),
            })

            yield _sse("phase", {"phase": "execution", "title": "Ejecución Directa", "icon": "⚡"})
            try:
                result = execute_from_skill(task, skill)
            except Exception as e:
                yield _sse("error", {"message": str(e)})
                return

            elapsed = time.time() - task_start
            yield _sse("result", {"text": result, "elapsed": round(elapsed, 2), "reused": True})
            yield _sse("done", {"elapsed": round(elapsed, 2)})
            return

        # AUCTION PATH
        yield _sse("skill_not_found", {})

        # Phase 2: Auction
        yield _sse("phase", {"phase": "auction", "title": "Subasta de Agentes", "icon": "🏛️"})
        try:
            bids = auction(task)
        except Exception as e:
            yield _sse("error", {"message": str(e)})
            return
        yield _sse("auction_result", {"bids": bids})

        # Phase 3: Selection
        winner = profiles.get(profile_choice, "El Equilibrado")
        yield _sse("selection", {"winner": winner})

        # Phase 4: Execution
        yield _sse("phase", {"phase": "execution", "title": f"Ejecución — {winner}", "icon": "⚙️"})
        try:
            result = execute_task(task, winner)
        except Exception as e:
            yield _sse("error", {"message": str(e)})
            return
        yield _sse("result", {"text": result, "elapsed": 0, "reused": False})

        # Phase 5: Distillation
        yield _sse("phase", {"phase": "distillation", "title": "Destilación", "icon": "🧬"})
        try:
            skill, path = distill(task, result)
            yield _sse("skill_saved", {
                "type": skill["type"],
                "description": skill["description"],
                "steps": skill.get("steps", []),
                "file": str(path.relative_to(ROOT)),
            })
        except Exception as e:
            yield _sse("distill_error", {"message": str(e)})

        elapsed = time.time() - task_start
        yield _sse("done", {"elapsed": round(elapsed, 2)})

    return Response(generate(), mimetype="text/event-stream")


@app.route("/api/clean", methods=["POST"])
def api_clean():
    """Reset learned skills."""
    if SKILLS_DIR.exists():
        shutil.rmtree(SKILLS_DIR)
    return jsonify({"status": "ok", "message": "Skills borradas"})


def _sse(event, data):
    """Format a Server-Sent Event."""
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


# ═══════════════════════════════════════════════════════════════════════════
# ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    # Fix encoding on Windows
    if sys.platform == "win32":
        os.system("")
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

    print(f"\n🏛️  Subasta + Legado — Web Demo")
    print(f"   Model: {MODEL}")
    print(f"   Skills: {SKILLS_DIR}")
    print(f"   Open: http://localhost:5000\n")
    app.run(debug=True, port=5000, host="0.0.0.0")
