# Subasta + Legado — Hermes Agent Hackathon

## Qué es esto
Proyecto para el **Hermes Agent Accelerated Business Hackathon** (NVIDIA × Stripe × Nous Research).
Track: **Autopilot Agents** ("Haz que un agente despierte, revise contexto e interrumpa solo cuando sirve").

Este documento reemplaza la versión anterior. El cambio principal: la subasta ya NO la decide
una sola llamada que genera 3 perfiles y se autorecomienda — ahora son **4 llamadas separadas**:
3 agentes que ofertan de forma independiente (sin verse entre sí) + un 4to rol, el **Juez**, que
recibe las 3 ofertas y decide cuál gana, con su razonamiento.

## La idea (una sola frase)
Le tirás una tarea ambigua a un sistema de agentes Hermes. 3 perfiles distintos ofertan en
paralelo e independiente (cada uno sin ver al otro). Un 4to agente, el Juez, lee las 3 ofertas
y elige ganador con justificación. El ganador ejecuta la tarea. Al terminar, destila lo
aprendido en una skill reusable. La próxima vez que llega una tarea parecida, no hay
subasta ni juez — el agente veterano la resuelve directo.

Arco narrativo para el demo: **competencia → veredicto → ejecución → aprendizaje → activo reusable.**

## Flujo técnico (en orden, así se construye)

1. **Input**: el humano tira una tarea ambigua en texto (ver `TAREA_DEMO` abajo).
2. **Skill lookup**: antes de todo, se revisa si ya existe una skill guardada para ese
   *tipo* de tarea. Si existe, se salta directo al paso 5 (ejecución con skill), sin pasar
   por subasta ni juez.
3. **Subasta (3 llamadas independientes)**: cada perfil de agente (rápido/barato,
   lento/prolijo, balanceado) recibe la tarea y devuelve SU oferta en su propia llamada al
   modelo — sin ver la oferta de los otros dos. Esto es importante: no es una sola llamada
   que inventa 3 voces, son 3 llamadas reales y separadas.
4. **Veredicto del Juez (4ta llamada, distinta)**: un 4to prompt, con rol explícito de
   "Juez", recibe las 3 ofertas ya generadas y debe:
   - elegir un ganador,
   - justificar la elección en 1-2 líneas,
   - el output del Juez es lo que se le muestra al humano como recomendación final
     (el humano puede aceptar el veredicto o elegir otro perfil manualmente).
5. **Ejecución**: el perfil ganador (según el Juez, o el que elija el humano) resuelve la
   tarea de verdad.
6. **Destilación**: al terminar, se genera un skill file corto (JSON o markdown) resumiendo
   cómo se resolvió la tarea, guardado en `skills/`.
7. **Reuso**: en una segunda tarea del mismo tipo, se detecta la skill guardada y se usa
   directo — sin subasta, sin juez.

## Diferencia clave con la versión anterior (por qué se reescribió)
La versión vieja generaba los 3 perfiles Y la recomendación en una sola llamada al modelo
(el mismo prompt pedía "generá 3 perfiles... y al final recomendá un ganador"). Eso no es
una subasta real con juicio independiente — es un solo agente inventando una conversación.
Ahora cada perfil es su propia llamada (no ve a los otros) y el Juez es una llamada aparte
que sólo recibe las 3 ofertas ya escritas, nunca la tarea original sin contexto de las ofertas.
Esto es lo que hace que el "debate" se sienta real en el demo.

## Stack
- **Hermes Agent** como runtime del agente (memoria, skill creation, multi-step).
- **Nebius** como motor de inferencia detrás de Hermes. **Pendiente de configurar** — la
  versión anterior usaba OpenRouter con el modelo gratis `hermes-3-llama-3.1-405b:free`,
  que se satura por rate limit compartido entre todos los usuarios free del hackathon
  (esto fue la causa confirmada del error "Max retries exceeded"). Antes de avanzar, decidir:
  - cambiar a Nebius de verdad (recomendado, ya que es el track), o
  - como mínimo cambiar a `nousresearch/hermes-3-llama-3.1-8b` en OpenRouter para salir
    del paso mientras se configura Nebius.
- Stripe Skills: **NO entra en el MVP**. Ver "Fuera de Alcance".

## Tarea de demo (`TAREA_DEMO`)
Usar siempre la misma tarea en el demo para que sea reproducible.

> "Escribime un resumen de 3 bullets de qué es Nebius, en tono casual, para poner en un README."

Segunda tarea (para mostrar el reuso de skill, debe ser del mismo *tipo* que la primera):

> "Escribime un resumen de 3 bullets de qué es Stripe Skills, en tono casual, para un README."

## Fuera de alcance (NO hacer, aunque parezca fácil)
- Pagos reales o simulados con Stripe.
- Más de 3 perfiles ofertando, o múltiples rondas de debate entre perfiles (el Juez ve las
  ofertas UNA vez, no hay ida y vuelta).
- Multi-GPU o configuración custom de Nebius más allá de "modelo corriendo, endpoint andando".
- Integración con Telegram/Discord/Slack. Todo corre en terminal o en un solo chat/web simple.
- Manejo de errores robusto más allá de reintentos básicos. Si algo se rompe en el demo, se
  re-grava esa toma.

## Checklist de construcción
- [ ] Confirmar proveedor de modelo (Nebius vs OpenRouter no-free) antes de seguir — esto
      bloqueó el intento anterior.
- [ ] Función de subasta separada en 3 llamadas independientes (no una sola llamada con 3 voces).
- [ ] Función de Juez como llamada aparte, recibe las 3 ofertas como input, devuelve ganador
      + justificación.
- [ ] Selección: humano puede aceptar al ganador del Juez o forzar otro perfil.
- [ ] Ejecución de la tarea por el perfil ganador.
- [ ] Skill generada y guardada en disco (confirmar que el archivo existe después de correrlo).
- [ ] Segunda tarea probada, confirmar que NO repite subasta+juez y usa la skill directo.
- [ ] Grabar video de 1-3 min mostrando el flujo completo.
- [ ] Escribir writeup corto (3-4 líneas) para el tweet/submission.
- [ ] Postear en Discord de Nous con el link del tweet.

## Prompts base

### Oferta de un perfil (se llama 3 veces, una por perfil, sin que se vean entre sí)
```
Sos un agente IA con el perfil "{NOMBRE_PERFIL}" ({DESCRIPCION_PERFIL}, ej: "rápido y
conciso" / "metódico y detallista" / "balance entre velocidad y calidad").

Te llega esta tarea. Dame tu oferta en máximo 3 líneas:
- tiempo/esfuerzo estimado
- nivel de detalle que ofrecés
- una frase de por qué tu enfoque conviene para esta tarea

Tarea: {TAREA_DEMO}
```

### Veredicto del Juez (se llama una vez, después de tener las 3 ofertas)
```
Sos el Juez de una subasta entre 3 agentes IA. Te paso sus 3 ofertas para la misma tarea.
Elegí UN ganador y justificá en 1-2 líneas, basándote en qué perfil conviene más para el
tipo de tarea (no asumas que el más rápido siempre gana, ni que el más detallado siempre
gana — depende de la tarea).

Tarea original: {TAREA_DEMO}

Oferta de "{PERFIL_1}": {OFERTA_1}
Oferta de "{PERFIL_2}": {OFERTA_2}
Oferta de "{PERFIL_3}": {OFERTA_3}

Respondé en este formato:
Ganador: {nombre del perfil}
Justificación: {1-2 líneas}
```

### Destilación de skill (después de ejecutar la tarea ganadora)
```
Acabás de resolver esta tarea: {TAREA_DEMO}. Generá un skill file corto en markdown
(máximo 10 líneas) con los pasos concretos que seguiste, para que la próxima vez que llegue
una tarea del mismo tipo, se pueda resolver directo sin pasar por subasta ni juez. Guardalo
como skills/resumen-readme.md.
```

## Notas para quien retome esto
- Si Nebius no responde a tiempo, usar cualquier provider no-free que Hermes soporte y
  aclararlo en el writeup — lo importante para el demo es el flujo de subasta+juez+legado,
  no el proveedor específico.
- Si el tiempo se acorta: lo mínimo defendible es subasta (3 llamadas) + veredicto del Juez,
  mostrados como texto/capturas, sin necesidad de ejecutar la tarea completa ni destilar skill.
