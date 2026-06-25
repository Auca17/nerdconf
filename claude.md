# Subasta + Legado — Hermes Agent Hackathon

## Qué es esto
Proyecto para el **Hermes Agent Accelerated Business Hackathon** (NVIDIA × Stripe × Nous Research).
Track: **Autopilot Agents** ("Haz que un agente despierte, revise contexto e interrumpa solo cuando sirve").

Tiempo disponible: muy poco (~1h20). Todo lo de abajo está recortado a propósito para ser
construible rápido. NO agregar alcance nuevo sin antes tachar algo de la lista de "Fuera de
Alcance". Si algo no está en este archivo, no lo construyas todavía — preguntá primero.

## La idea (una sola frase)
Le tirás una tarea ambigua a un agente Hermes. El agente simula una subasta interna entre
2-3 "perfiles" de sí mismo (rápido/barato vs lento/prolijo), elige al ganador, ejecuta la
tarea, y al terminar destila lo aprendido en una skill reusable. La próxima vez que llega una
tarea parecida, ya no hay subasta: el agente veterano la resuelve directo.

Arco narrativo para el demo: **competencia → ejecución → aprendizaje → activo reusable.**

## Flujo técnico (en orden, así se construye)

1. **Input**: el humano tira una tarea ambigua en texto (ver `TAREA_DEMO` abajo).
2. **Subasta simulada**: UNA sola llamada al modelo (no 3 procesos reales) pidiéndole que actúe
   como 2-3 candidatos distintos y dé su "oferta" (tiempo estimado / tokens / nivel de calidad).
   Output esperado: texto visible mostrando las 3 ofertas, una por una.
3. **Selección**: se elige la oferta ganadora (regla simple: la más barata, o la que el humano
   aprueba con un solo click/mensaje).
4. **Ejecución**: el agente ganador resuelve la tarea de verdad.
5. **Destilación**: al terminar, el agente genera un archivo corto de skill (markdown, pasos
   concretos) resumiendo cómo resolvió la tarea. Esto se guarda en disco/memoria.
6. **Reuso**: se tira una segunda tarea parecida. Esta vez el agente detecta que ya tiene la
   skill guardada y la usa directo, sin pasar por la subasta. Esto es lo que se muestra al final
   del video como "antes/después".

## Stack
- **Hermes Agent** como runtime del agente (memoria, skill creation, multi-step).
- **Nebius** como motor de inferencia detrás de Hermes (configurado en el setup de Hermes,
  no hay que orquestar GPUs a mano).
- Stripe Skills: **NO entra en el MVP**. Ver "Fuera de Alcance".

## Tarea de demo (`TAREA_DEMO`)
Usar siempre la misma tarea en el demo para que sea reproducible. Ejemplo sugerido (ajustar si
ya tienen otra mejor, pero una sola, no improvisar en vivo):

> "Escribime un resumen de 3 bullets de qué es Nebius, en tono casual, para poner en un README."

Segunda tarea (para mostrar el reuso de skill, debe ser del mismo *tipo* que la primera):

> "Escribime un resumen de 3 bullets de qué es Stripe Skills, en tono casual, para un README."

## Fuera de alcance (NO hacer, aunque parezca fácil)
- Pagos reales o simulados con Stripe.
- Múltiples procesos/instancias reales de Hermes corriendo en paralelo.
- Multi-GPU o configuración custom de Nebius más allá de "modelo corriendo, endpoint andando".
- Integración con Telegram/Discord/Slack. Todo corre en terminal o en un solo chat.
- UI. El demo es texto en terminal o output de chat, nada de frontend.
- Manejo de errores robusto. Si algo se rompe en el demo, se re-grava esa toma.

## Checklist de construcción
- [ ] Hermes instalado y respondiendo (`hermes setup`, modelo conectado vía Nebius o el
      provider que tengan a mano — Nebius si da el tiempo, sino cualquiera y se aclara en el
      video que el target final es Nebius).
- [ ] Prompt de subasta probado una vez, ofertas se ven claras y distintas entre sí.
- [ ] Ejecución de la tarea ganadora probada.
- [ ] Skill generada y guardada en disco (confirmar que el archivo existe después de correrlo).
- [ ] Segunda tarea probada, confirmar que NO repite la subasta y usa la skill directo.
- [ ] Grabar video de 1-3 min mostrando los 4 pasos en orden.
- [ ] Escribir writeup corto (3-4 líneas) para el tweet/submission.
- [ ] Postear en Discord de Nous con el link del tweet.

## Prompt base para la subasta (punto de partida, ajustar tono si hace falta)

```
Actuá como un "subastador" interno. Te voy a dar una tarea. Generá 2-3 perfiles de agente que
podrían resolverla (ej: "rápido y simple" vs "lento y prolijo"), cada uno con una oferta breve
(tiempo estimado + qué tan detallada sería su respuesta). Mostrá las ofertas numeradas. Después
decime cuál recomendás como ganadora y por qué, en una sola línea.

Tarea: {TAREA_DEMO}
```

## Prompt base para la destilación de skill (después de ejecutar la tarea ganadora)

```
Acabás de resolver esta tarea: {TAREA_DEMO}. Generá un skill file corto en markdown
(máximo 10 líneas) con los pasos concretos que seguiste, para que la próxima vez que llegue
una tarea del mismo tipo, se pueda resolver directo sin pasar por la subasta. Guardalo como
skills/resumen-readme.md.
```

## Notas para quien retome esto
- Si Nebius no responde a tiempo, usar cualquier provider que Hermes soporte (OpenRouter,
  NVIDIA NIM, etc.) y aclararlo en el writeup — lo importante para el demo es el flujo, no el
  proveedor específico.
- Si el tiempo se acorta más todavía: lo mínimo defendible es el paso 2 (subasta) + paso 5
  (un skill file generado), mostrados como screenshots en el tweet en vez de video.
