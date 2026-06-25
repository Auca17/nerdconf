#!/usr/bin/env python3
"""
🏛️ Subasta + Legado — Hermes Agent Hackathon (NVIDIA × Stripe × Nous Research)
Track: Autopilot Agents

An agent that simulates an internal auction between agent profiles,
executes the winning bid, and distills the learned approach into a
reusable skill. Next time a similar task arrives, the auction is
skipped entirely — the veteran agent solves it directly.

Arc: competition → execution → learning → reusable asset
"""

import os
import sys
import json
import time
import re
import shutil
from pathlib import Path

# Fix SSL cert verification on Windows UV/portable Python environments
# Must be done BEFORE importing requests
try:
    import truststore
    truststore.inject_into_ssl()
except ImportError:
    pass  # truststore not installed; system certs will be used

import requests

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

# Enable ANSI escape sequences and UTF-8 output on Windows 10+
if sys.platform == "win32":
    os.system("")
    # Force UTF-8 for emoji and Unicode box-drawing support
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


# ═══════════════════════════════════════════════════════════════════════════
# TERMINAL UI
# ═══════════════════════════════════════════════════════════════════════════

class C:
    """256-color ANSI palette for a premium terminal look."""
    BOLD   = "\033[1m"
    DIM    = "\033[2m"
    ITALIC = "\033[3m"
    PURPLE = "\033[38;5;141m"
    BLUE   = "\033[38;5;75m"
    CYAN   = "\033[38;5;80m"
    GREEN  = "\033[38;5;114m"
    YELLOW = "\033[38;5;221m"
    RED    = "\033[38;5;203m"
    ORANGE = "\033[38;5;209m"
    GRAY   = "\033[38;5;245m"
    WHITE  = "\033[38;5;255m"
    R      = "\033[0m"


def hr(char="─", width=65):
    print(f"{C.GRAY}{char * width}{C.R}")


def phase(icon, title, subtitle=""):
    """Print a distinct phase header."""
    print()
    hr("━")
    print(f"  {icon}  {C.BOLD}{C.WHITE}{title}{C.R}")
    if subtitle:
        print(f"     {C.DIM}{subtitle}{C.R}")
    hr("━")


def typewrite(text, speed=0.008):
    """Typewriter effect for dramatic output."""
    for ch in text:
        sys.stdout.write(ch)
        sys.stdout.flush()
        time.sleep(speed)
    print()


def spinner(msg="Thinking", duration=1.2):
    """Braille-dot spinner while the LLM call is conceptually 'working'."""
    frames = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
    end_time = time.time() + duration
    i = 0
    while time.time() < end_time:
        sys.stdout.write(f"\r  {C.CYAN}{frames[i % len(frames)]} {msg}...{C.R}   ")
        sys.stdout.flush()
        time.sleep(0.1)
        i += 1
    sys.stdout.write(f"\r{'':50}\r")
    sys.stdout.flush()


def fmt_time(seconds):
    """Format seconds into a human-readable string."""
    if seconds < 1:
        return f"{seconds*1000:.0f}ms"
    return f"{seconds:.1f}s"


# ═══════════════════════════════════════════════════════════════════════════
# LLM CALLS (OpenRouter)
# ═══════════════════════════════════════════════════════════════════════════

def llm(messages, temperature=0.7, max_retries=5):
    """Single LLM call via OpenRouter, with automatic retry on rate-limit."""
    if not API_KEY:
        print(f"\n{C.RED}  ❌ OPENROUTER_API_KEY not set. Check your .env file.{C.R}")
        sys.exit(1)

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

            # Handle rate-limiting with retry
            if r.status_code == 429:
                data = r.json()
                retry_after = data.get("error", {}).get("metadata", {}).get(
                    "retry_after_seconds", 2 * (attempt + 1)
                )
                retry_after = max(int(retry_after), 2)
                sys.stdout.write(
                    f"\r  {C.YELLOW}⏳ Rate-limited. Retrying in {retry_after}s "
                    f"(attempt {attempt + 1}/{max_retries})...{C.R}   "
                )
                sys.stdout.flush()
                time.sleep(retry_after)
                continue

            r.raise_for_status()
            data = r.json()
            # Clear any retry messages
            sys.stdout.write(f"\r{'':60}\r")
            sys.stdout.flush()
            return data["choices"][0]["message"]["content"]

        except requests.exceptions.RequestException as e:
            if attempt < max_retries - 1:
                time.sleep(2)
                continue
            print(f"\n{C.RED}  ❌ API error: {e}{C.R}")
            if hasattr(e, "response") and e.response is not None:
                print(f"{C.DIM}  {e.response.text[:500]}{C.R}")
            sys.exit(1)
        except (KeyError, IndexError):
            print(f"\n{C.RED}  ❌ Unexpected API response shape.{C.R}")
            print(f"{C.DIM}  {data}{C.R}")
            sys.exit(1)

    print(f"\n{C.RED}  ❌ Max retries exceeded. Try again later or switch to a paid model.{C.R}")
    sys.exit(1)


# ═══════════════════════════════════════════════════════════════════════════
# CORE FLOW
# ═══════════════════════════════════════════════════════════════════════════

# ── 1. SKILL LOOKUP ─────────────────────────────────────────────────────

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
                    "Match by TASK TYPE, not by specific topic. "
                    "For example, 'write a summary about X' and 'write a summary about Y' "
                    "are the SAME task type."
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


# ── 2. AUCTION ──────────────────────────────────────────────────────────

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


# ── 3. EXECUTION ────────────────────────────────────────────────────────

def execute(task, profile="El Equilibrado"):
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


# ── 4. DISTILLATION ────────────────────────────────────────────────────

def distill(task, result):
    """Distill the approach into a reusable skill file (JSON on disk)."""
    raw = llm(
        [
            {
                "role": "system",
                "content": (
                    "Generás skill files en JSON puro. SOLO JSON válido. "
                    "Sin markdown fences (```), sin explicación, sin texto extra. "
                    "Si incluís ``` la respuesta es INVÁLIDA. "
                    "IMPORTANT: the 'type' field must describe the GENERIC task type, "
                    "not the specific topic. For example: 'resumen-casual-readme' "
                    "instead of 'resumen-nebius'. The skill should be reusable for "
                    "any similar task with a different topic."
                ),
            },
            {
                "role": "user",
                "content": f"""Acabás de resolver esta tarea:
"{task}"

Tu resultado fue:
{result}

Generá un JSON con esta estructura EXACTA (sin campos extra):
{{"type": "tipo-generico-en-kebab-case", "description": "Descripción GENÉRICA del tipo de tarea (NO menciones el tema específico)", "steps": ["paso 1", "paso 2", "paso 3"], "template": "template con {{{{TEMA}}}} como placeholder reemplazable"}}

REGLAS:
- "type" debe ser GENÉRICO (ej: "resumen-casual-readme", NO "resumen-nebius")
- "description" debe describir el TIPO de tarea, no la instancia específica
- "template" debe usar {{{{TEMA}}}} donde iría el tema variable
- SOLO JSON válido. Nada más.""",
            },
        ],
        temperature=0.2,
    )

    # Clean up LLM output to extract valid JSON
    raw = raw.strip()
    if raw.startswith("```"):
        lines = raw.split("\n")
        end = -1 if lines[-1].strip().startswith("```") else len(lines)
        raw = "\n".join(lines[1:end])

    json_match = re.search(r"\{[\s\S]*\}", raw)
    if json_match:
        raw = json_match.group()

    skill = json.loads(raw)

    # Ensure required fields exist
    for key in ("type", "description", "steps"):
        if key not in skill:
            raise KeyError(f"Missing required field: {key}")

    SKILLS_DIR.mkdir(exist_ok=True)
    fname = f"{skill['type']}.json"
    path = SKILLS_DIR / fname
    path.write_text(json.dumps(skill, indent=2, ensure_ascii=False), encoding="utf-8")

    return skill, path


# ═══════════════════════════════════════════════════════════════════════════
# MAIN FLOW
# ═══════════════════════════════════════════════════════════════════════════

BANNER = f"""
{C.PURPLE}╔══════════════════════════════════════════════════════════════════╗
║                                                                  ║
║   {C.BOLD}🏛️  S U B A S T A   +   L E G A D O{C.R}{C.PURPLE}                         ║
║   {C.CYAN}Hermes Agent Hackathon  ·  Autopilot Agents Track{C.R}{C.PURPLE}            ║
║   {C.DIM}competencia → ejecución → aprendizaje → activo reusable{C.R}{C.PURPLE}      ║
║                                                                  ║
╚══════════════════════════════════════════════════════════════════╝{C.R}
{C.GRAY}  model : {MODEL}
  skills: {SKILLS_DIR}{C.R}
"""

DEMO_TASKS = [
    "Escribime un resumen de 3 bullets de qué es Nebius, en tono casual, para poner en un README.",
    "Escribime un resumen de 3 bullets de qué es Stripe Skills, en tono casual, para un README.",
]


def run_task(task, auto_select=False):
    """Run the full agent flow for a single task.

    Args:
        auto_select: If True, automatically select the recommended agent
                     (skips the interactive prompt — useful for --demo mode).
    """
    task_start = time.time()
    print(f"\n  {C.BOLD}📝 Tarea:{C.R} {C.WHITE}{task}{C.R}")

    # ── Phase 1: Skill Lookup ──
    phase("🔍", "BÚSQUEDA DE SKILLS", "Revisando memoria de tareas anteriores...")
    spinner("Buscando skills aprendidas")
    skill = find_skill(task)

    if skill:
        # ═══════════════════════════════════════════════════════
        # REUSE PATH — skill found, skip auction entirely
        # ═══════════════════════════════════════════════════════
        print(f"  {C.GREEN}✅ ¡Skill encontrada!{C.R}")
        print(f"     {C.CYAN}tipo :{C.R} {skill['type']}")
        print(f"     {C.CYAN}desc :{C.R} {skill['description']}")
        for i, step in enumerate(skill.get("steps", [])):
            print(f"     {C.DIM}  {i+1}. {step}{C.R}")

        phase("⚡", "EJECUCIÓN DIRECTA", "Usando skill aprendida — SIN subasta")
        spinner("Aplicando skill")
        result = execute_from_skill(task, skill)
        print()
        typewrite(result)

        elapsed = time.time() - task_start
        hr()
        print(f"\n  {C.GREEN}{C.BOLD}🏆 Resuelto con skill existente{C.R}")
        print(f"  {C.GREEN}   0 subastas · resolución directa · {fmt_time(elapsed)}{C.R}")
        return result, elapsed

    else:
        # ═══════════════════════════════════════════════════════
        # AUCTION PATH — no skill, full flow
        # ═══════════════════════════════════════════════════════
        print(f"  {C.YELLOW}⚠  No hay skills para este tipo de tarea.{C.R}")
        print(f"     {C.YELLOW}Iniciando subasta de agentes...{C.R}")

        # ── Phase 2: Auction ──
        phase("🏛️", "SUBASTA DE AGENTES", "Generando perfiles y ofertas...")
        spinner("Preparando ofertas")
        bids = auction(task)
        print()
        print(bids)

        # ── Phase 3: Selection ──
        phase("🎯", "SELECCIÓN", "Elegí al agente ganador")
        profiles = {"1": "El Rayo", "2": "El Artesano", "3": "El Equilibrado"}

        if auto_select:
            # In demo mode, auto-select El Equilibrado
            winner = "El Equilibrado"
            print(f"\n  {C.DIM}  (auto-selección para demo){C.R}")
        else:
            print(f"\n  {C.DIM}  1 → El Rayo  (rápido){C.R}")
            print(f"  {C.DIM}  2 → El Artesano  (prolijo){C.R}")
            print(f"  {C.DIM}  3 → El Equilibrado  (balanced){C.R}")
            choice = input(
                f"\n  {C.BOLD}→ Elegí (1/2/3) o Enter para el recomendado: {C.R}"
            ).strip()
            winner = profiles.get(choice, "El Equilibrado")

        print(f"\n  {C.CYAN}🏅 Ganador seleccionado: {C.BOLD}{winner}{C.R}")

        # ── Phase 4: Execution ──
        phase("⚙️", "EJECUCIÓN", f"Agente '{winner}' resolviendo la tarea...")
        spinner(f"{winner} trabajando")
        result = execute(task, winner)
        print()
        typewrite(result)

        # ── Phase 5: Distillation ──
        phase("🧬", "DESTILACIÓN", "Extrayendo skill reusable...")
        spinner("Destilando aprendizaje")
        try:
            skill, path = distill(task, result)
            print(f"  {C.GREEN}✅ Skill guardada:{C.R} {path.relative_to(ROOT)}")
            print(f"     {C.CYAN}  tipo :{C.R} {skill['type']}")
            print(f"     {C.CYAN}  desc :{C.R} {skill['description']}")
            print(f"     {C.CYAN} pasos :{C.R} {len(skill.get('steps', []))}")
        except (json.JSONDecodeError, KeyError) as e:
            print(
                f"  {C.YELLOW}⚠  Skill parse error ({e}). Saving raw output...{C.R}"
            )
            SKILLS_DIR.mkdir(exist_ok=True)
            fallback = SKILLS_DIR / "last-skill-raw.txt"
            fallback.write_text(str(result), encoding="utf-8")
            print(f"  {C.DIM}  Saved to: {fallback}{C.R}")

        elapsed = time.time() - task_start
        hr()
        print(f"\n  {C.GREEN}{C.BOLD}🏆 Tarea resuelta. Skill destilada y lista para reuso.{C.R}")
        print(f"  {C.GREEN}   5 fases completadas · {fmt_time(elapsed)}{C.R}")
        return result, elapsed


def main():
    print(BANNER)

    args = sys.argv[1:]

    # ── --clean: reset skills ──
    if "--clean" in args:
        if SKILLS_DIR.exists():
            shutil.rmtree(SKILLS_DIR)
            print(f"  {C.YELLOW}🗑️  Skills borradas. Estado limpio.{C.R}")
        else:
            print(f"  {C.DIM}  No hay skills que borrar.{C.R}")
        return

    # ── --demo: run both demo tasks in sequence (non-interactive) ──
    if "--demo" in args:
        print(f"  {C.PURPLE}{C.BOLD}▶ MODO DEMO{C.R}")
        print(f"  {C.DIM}Ejecutando las 2 tareas en secuencia para mostrar el arco completo{C.R}")

        # Start clean
        if SKILLS_DIR.exists():
            shutil.rmtree(SKILLS_DIR)
            print(f"  {C.DIM}  (skills reseteadas para demo limpio){C.R}")

        timings = []
        for i, task in enumerate(DEMO_TASKS):
            print(f"\n\n{'═' * 65}")
            print(
                f"  {C.BOLD}{C.PURPLE}TAREA {i + 1} de {len(DEMO_TASKS)}{C.R}"
            )
            print(f"{'═' * 65}")
            _, elapsed = run_task(task, auto_select=True)
            timings.append(elapsed)

            if i < len(DEMO_TASKS) - 1:
                print()
                print(f"\n  {C.DIM}{'─' * 55}{C.R}")
                print(f"  {C.PURPLE}{C.BOLD}  Siguiente: tarea similar para demostrar REUSO{C.R}")
                print(f"  {C.DIM}{'─' * 55}{C.R}")
                time.sleep(2)  # Brief dramatic pause instead of waiting for Enter

        # ── Final summary with timing comparison ──
        print(f"\n\n{'═' * 65}")
        print(f"  {C.GREEN}{C.BOLD}✨ DEMO COMPLETO{C.R}")
        print(f"{'═' * 65}")
        print()
        print(f"  {C.BOLD}Resumen del arco:{C.R}")
        print(f"  {C.DIM}competencia → ejecución → aprendizaje → reuso  ✅{C.R}")
        print()

        if len(timings) >= 2:
            speedup = timings[0] / timings[1] if timings[1] > 0 else 0
            print(f"  {C.BOLD}⏱️  Comparación de tiempos:{C.R}")
            print(f"     Tarea 1 (con subasta):  {C.YELLOW}{fmt_time(timings[0])}{C.R}")
            print(f"     Tarea 2 (con skill):    {C.GREEN}{fmt_time(timings[1])}{C.R}")
            if speedup > 1:
                print(f"     Speedup:                {C.GREEN}{C.BOLD}{speedup:.1f}x más rápido{C.R}")
            print()

        # Show skill files on disk
        if SKILLS_DIR.exists():
            skill_files = list(SKILLS_DIR.glob("*.json"))
            if skill_files:
                print(f"  {C.BOLD}📁 Skills persistidas en disco:{C.R}")
                for sf in skill_files:
                    try:
                        s = json.loads(sf.read_text(encoding="utf-8"))
                        print(f"     {C.CYAN}{sf.name}{C.R} — {s.get('description', '?')}")
                    except Exception:
                        print(f"     {C.CYAN}{sf.name}{C.R}")
                print()

        print(f"{'═' * 65}\n")
        return

    # ── Interactive mode ──
    task_from_args = [a for a in args if not a.startswith("--")]
    if task_from_args:
        task = " ".join(task_from_args)
    else:
        print(f"  {C.DIM}Tareas demo sugeridas:{C.R}")
        for i, t in enumerate(DEMO_TASKS):
            print(f"  {C.DIM}  {i + 1}. {t}{C.R}")
        print()
        task = input(
            f"  {C.BOLD}📝 Tu tarea (o Enter para la demo 1): {C.R}"
        ).strip()
        if not task:
            task = DEMO_TASKS[0]
            print(f"  {C.DIM}(usando tarea demo){C.R}")

    run_task(task)
    print()


if __name__ == "__main__":
    main()
