# -*- coding: utf-8 -*-
"""Diagrama de arquitectura de PRODUCCION para un entorno real de casino con
trafico masivo: orquestador, cola de eventos, cache, Telegram, logs, redes.

Salida: docs/img/arquitectura_produccion.png (referenciado desde
docs/arquitectura_produccion.md). Regenerar con:
    python scripts/generar_diagrama_produccion.py
"""

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Rectangle
from matplotlib.lines import Line2D

ROOT = Path(__file__).resolve().parents[1]

# ---------------------------------------------------------------- paleta ---
NAVY   = "#0A1B3D"
GOLD   = "#C9A24B"
CREAM  = "#FBF9F5"

C_CANAL = "#0E1B33"
C_RED   = "#4A5A72"
C_APP   = "#2E6E6A"
C_ASYNC = "#8A5A2B"
C_ML    = "#6C4B8C"
C_DATA  = "#2C5578"
C_CROSS = "#A6392F"

fig, ax = plt.subplots(figsize=(26, 16.5), dpi=160)
ax.set_xlim(0, 26)
ax.set_ylim(0, 16.5)
ax.axis("off")
fig.patch.set_facecolor(CREAM)
ax.set_facecolor(CREAM)


def box(x, y, w, h, text, color, fontsize=11, text_color="white", sub=None, subsize=8.6):
    r = FancyBboxPatch(
        (x, y), w, h,
        boxstyle="round,pad=0.02,rounding_size=0.10",
        linewidth=0, facecolor=color, alpha=1.0, zorder=3,
    )
    ax.add_patch(r)
    cy = y + h * (0.66 if sub else 0.5)
    ax.text(x + w / 2, cy, text, ha="center", va="center", color=text_color,
             fontsize=fontsize, fontweight="bold", zorder=4)
    if sub:
        ax.text(x + w / 2, y + h * 0.27, sub, ha="center", va="center",
                 color=text_color, fontsize=subsize, zorder=4, alpha=0.94)
    return (x, y, w, h)


def arrow(b1, b2, color="#8890A0", style="-|>", lw=1.5, side1="bottom", side2="top",
          connection="arc3,rad=0.0", z=2, ls="-"):
    def pt(b, side):
        x, y, w, h = b
        return {
            "top": (x + w / 2, y + h), "bottom": (x + w / 2, y),
            "left": (x, y + h / 2), "right": (x + w, y + h / 2),
        }[side]
    p1, p2 = pt(b1, side1), pt(b2, side2)
    a = FancyArrowPatch(p1, p2, arrowstyle=style, mutation_scale=13,
                         color=color, linewidth=lw, connectionstyle=connection, zorder=z,
                         linestyle=ls)
    ax.add_patch(a)


def banda_label(y, texto, color):
    ax.text(0.15, y, texto, fontsize=10.5, fontweight="bold", color=color,
             ha="left", va="center", zorder=4,
             bbox=dict(boxstyle="round,pad=0.28", facecolor="white",
                        edgecolor=color, linewidth=1.3))


# ---------------------------------------------------------------- titulo ---
ax.add_patch(Rectangle((0, 15.65), 26, 0.85, facecolor=NAVY, zorder=1, linewidth=0))
ax.add_patch(Rectangle((0, 15.65), 0.14, 0.85, facecolor=GOLD, zorder=2, linewidth=0))
ax.text(0.4, 16.25, "Arquitectura de producción — Casino Palacio Real",
        fontsize=21, fontweight="bold", color="white", va="center", family="serif")
ax.text(0.4, 15.82, "Entorno real con tráfico masivo de clientes · orquestación, mensajería asíncrona, Telegram, observabilidad",
        fontsize=11.5, color="#C7D0E4", va="center")

# ==========================================================================
# BANDA 1 - CANALES
# ==========================================================================
y1 = 14.0
banda_label(y1 + 0.55, "1 · CANALES", C_CANAL)
b_cliente_tg = box(2.6, y1, 3.6, 1.1, "Cliente del casino", C_CANAL,
                    sub="app Telegram · recibe ofertas, responde")
b_operador = box(7.0, y1, 3.8, 1.1, "Operador de marketing\n/ Analista", C_CANAL,
                  sub="web interna, consultas sobre clientes")
b_piso = box(11.6, y1, 3.6, 1.1, "Piso de juego", C_CANAL,
             sub="sesiones en vivo (POS/slots), alto volumen")
b_publico = box(16.2, y1, 3.8, 1.1, "Público en general", C_CANAL,
                sub="web pública, miles de sesiones concurrentes")

# ==========================================================================
# BANDA 2 - BORDE / RED / CONECTIVIDAD
# ==========================================================================
y2 = 12.1
banda_label(y2 + 0.55, "2 · RED Y CONECTIVIDAD", C_RED)
b_bot_wh = box(2.6, y2, 3.4, 1.1, "Telegram Bot API\n(webhook HTTPS)", C_RED,
               sub="canal cifrado con Telegram")
b_cdn = box(6.6, y2, 3.4, 1.1, "CDN + WAF", C_RED, sub="cachea estáticos, filtra ataques")
b_gw = box(10.6, y2, 3.6, 1.1, "API Gateway", C_RED, sub="autenticación, rate limiting, versionado")
b_lb = box(14.8, y2, 3.6, 1.1, "Load Balancer\n+ autoescalado", C_RED,
           sub="reparte carga entre réplicas")
b_vpn = box(19.0, y2, 3.6, 1.1, "VPN / Private Link", C_RED,
            sub="acceso privado al SQL on-prem del casino")

arrow(b_cliente_tg, b_bot_wh, color=C_CANAL)
arrow(b_publico, b_cdn, color=C_CANAL)
arrow(b_operador, b_gw, color=C_CANAL, connection="arc3,rad=0.15")
arrow(b_piso, b_vpn, color=C_CANAL, connection="arc3,rad=0.25")
arrow(b_cdn, b_gw, color=C_RED)
arrow(b_gw, b_lb, color=C_RED)

# ==========================================================================
# BANDA 3 - APLICACION / ORQUESTACION
# ==========================================================================
y3 = 10.1
banda_label(y3 + 0.55, "3 · APLICACIÓN", C_APP)
b_front = box(2.4, y3, 3.4, 1.15, "Frontend web\n(React / Next.js)", C_APP,
              sub="reemplaza a Streamlit cara al negocio")
b_orq = box(6.2, y3, 4.0, 1.15, "ORQUESTADOR\n(FastAPI / Azure Functions)", C_APP,
            sub="coordina modelos, optimizador, notificaciones")
b_chat = box(10.6, y3, 4.0, 1.15, "Servicio de Chat\n(RAG + LLM, un único motor)", C_APP,
             sub="widget web · Telegram · consultas del operador")
b_tgbot = box(15.0, y3, 3.6, 1.15, "Bot de Telegram", C_APP,
              sub="envía la oferta, registra la respuesta")
b_streamlit = box(19.0, y3, 3.0, 1.15, "Panel interno\n(Streamlit)", C_APP,
                   sub="solo equipo de datos, no cara al cliente")

arrow(b_lb, b_front, color=C_RED)
arrow(b_gw, b_orq, color=C_RED, connection="arc3,rad=-0.15")
arrow(b_gw, b_streamlit, color=C_RED, connection="arc3,rad=0.35")
arrow(b_bot_wh, b_tgbot, color=C_RED, connection="arc3,rad=0.25")
arrow(b_front, b_chat, color=C_APP, side1="right", side2="left", connection="arc3,rad=0.2")
arrow(b_orq, b_chat, color=C_APP)
arrow(b_tgbot, b_chat, color=C_APP, side1="left", side2="right", connection="arc3,rad=-0.2")

# ==========================================================================
# BANDA 4 - MENSAJERIA ASINCRONA (trafico masivo)
# ==========================================================================
y4 = 8.15
banda_label(y4 + 0.55, "4 · MENSAJERÍA ASÍNCRONA (tráfico masivo)", C_ASYNC)
b_queue = box(7.0, y4, 4.6, 1.1, "Cola de eventos\n(Azure Service Bus / Kafka)", C_ASYNC,
              sub="sesiones nuevas · resultados · respuestas")
b_workers = box(12.6, y4, 4.6, 1.1, "Workers de scoring\n(auto-escalables)", C_ASYNC,
                sub="consumen la cola, corren los modelos en paralelo")

arrow(b_orq, b_queue, color=C_ASYNC)
arrow(b_piso, b_queue, color=C_ASYNC, lw=1.3, ls="--",
      side1="bottom", side2="top", connection="arc3,rad=-0.55")
arrow(b_tgbot, b_queue, color=C_ASYNC, side1="bottom", side2="top", connection="arc3,rad=0.3")
arrow(b_queue, b_workers, color=C_ASYNC)

# ==========================================================================
# BANDA 5 - NUCLEO ML / NEGOCIO
# ==========================================================================
y5 = 6.2
banda_label(y5 + 0.55, "5 · NÚCLEO ML / NEGOCIO", C_ML)
b_riesgo = box(3.4, y5, 3.2, 1.1, "Modelo de riesgo", C_ML, sub="Bajo / Medio / Alto")
b_respV1 = box(6.9, y5, 3.2, 1.1, "Modelo de respuesta\n(V1)", C_ML, sub="P(responde)")
b_nbo = box(10.4, y5, 3.6, 1.1, "Modelo NBO (V2)", C_ML,
            sub="P y valor por tipo de recompensa")
b_opt = box(14.3, y5, 3.8, 1.1, "Optimizador de\nrecompensas", C_ML,
            sub="valor esperado − costo ≤ presupuesto")

arrow(b_workers, b_riesgo, color=C_ML, connection="arc3,rad=-0.3")
arrow(b_workers, b_respV1, color=C_ML, connection="arc3,rad=-0.15")
arrow(b_workers, b_nbo, color=C_ML, connection="arc3,rad=0.05")
arrow(b_riesgo, b_opt, color=C_ML, connection="arc3,rad=0.35")
arrow(b_respV1, b_opt, color=C_ML, connection="arc3,rad=0.2")
arrow(b_nbo, b_opt, color=C_ML)
arrow(b_opt, b_orq, color=GOLD, lw=2.2, side1="top", side2="bottom", connection="arc3,rad=0.0")
ax.text(16.7, (y5 + 1.1 + y3) / 2, "decisión", fontsize=8, color="#9C7A22",
        fontweight="bold", ha="center", rotation=90)

# guardrail
b_guard = box(18.7, y5, 4.4, 1.1, "Guardrail duro", C_CROSS,
              sub="Riesgo Alto: 0 ofertas, se deriva a juego responsable", fontsize=11)
arrow(b_opt, b_guard, color=C_CROSS, style="-", lw=1.6)

# ==========================================================================
# BANDA 6 - DATOS
# ==========================================================================
y6 = 4.25
banda_label(y6 + 0.55, "6 · DATOS", C_DATA)
b_sql = box(2.6, y6, 3.6, 1.1, "Azure SQL\n(réplica productiva)", C_DATA, sub="modelo estrella")
b_redis = box(6.6, y6, 3.2, 1.1, "Cache (Redis)", C_DATA, sub="features calientes, baja latencia")
b_vec = box(10.2, y6, 3.6, 1.1, "Vector Store (RAG)", C_DATA, sub="políticas + FAQ + guías")
b_lake = box(14.2, y6, 3.8, 1.1, "Data Lake / Blob", C_DATA, sub="logs, resultados de campaña")

arrow(b_vpn, b_sql, color=C_RED, connection="arc3,rad=0.6")
arrow(b_sql, b_redis, color=C_DATA)
arrow(b_redis, b_riesgo, color=C_DATA, side1="top", side2="bottom", connection="arc3,rad=-0.3")
arrow(b_redis, b_respV1, color=C_DATA, side1="top", side2="bottom", connection="arc3,rad=-0.15")
arrow(b_redis, b_nbo, color=C_DATA, side1="top", side2="bottom", connection="arc3,rad=0.05")
arrow(b_chat, b_vec, color=C_APP, side1="bottom", side2="top", connection="arc3,rad=-0.5", lw=1.3)
arrow(b_tgbot, b_lake, color=C_APP, side1="bottom", side2="top", connection="arc3,rad=0.5", lw=1.3)
arrow(b_opt, b_lake, color=C_ML, side1="bottom", side2="top", connection="arc3,rad=0.35", lw=1.3)

# ==========================================================================
# BANDA 7 - TRANSVERSAL: seguridad / logs / feedback
# ==========================================================================
y7 = 1.4
banda_label(y7 + 0.68, "7 · TRANSVERSAL", C_CROSS)
b_sec = box(4.4, y7, 5.0, 1.15, "Seguridad", C_CROSS,
            sub="Key Vault · IAM · cifrado en tránsito y en reposo")
b_logs = box(9.7, y7, 5.0, 1.15, "Logs y observabilidad", C_CROSS,
             sub="Application Insights / ELK · tracing · alertas")
b_feedback = box(15.0, y7, 6.6, 1.15, "Tabla de resultados de campaña", C_CROSS,
                  sub="oferta enviada -> respuesta real -> reentrenamiento periódico")

for b in (b_orq, b_chat, b_tgbot):
    arrow(b, b_logs, color="#D9BAB2", lw=0.9, side1="bottom", side2="top",
          connection="arc3,rad=0.0", z=1)
arrow(b_lake, b_feedback, color=C_CROSS, side1="bottom", side2="top", connection="arc3,rad=0.0")

# lazo de realimentacion: Tabla de resultados -> Modelo NBO (margen derecho, limpio)
fx = 24.6
ax.plot([b_feedback[0] + b_feedback[2], fx, fx, b_nbo[0] + b_nbo[2]],
        [y7 + 0.6, y7 + 0.6, y5 + 0.55, y5 + 0.55],
        color=GOLD, linewidth=2.4, zorder=2, solid_capstyle="round")
ax.annotate("", xy=(b_nbo[0] + b_nbo[2] + 0.05, y5 + 0.55), xytext=(fx - 0.3, y5 + 0.55),
            arrowprops=dict(arrowstyle="-|>", color=GOLD, lw=2.4), zorder=2)
ax.text(fx + 0.15, (y7 + y5) / 2 + 0.6, "reentrena periódicamente\ncon respuestas reales",
        fontsize=8.6, color="#9C7A22", fontweight="bold", ha="left", va="center", rotation=90)

# ---------------------------------------------------------------- leyenda ---
legend_items = [
    ("Canales", C_CANAL), ("Red / conectividad", C_RED), ("Aplicación / orquestación", C_APP),
    ("Mensajería asíncrona", C_ASYNC), ("Núcleo ML", C_ML), ("Datos", C_DATA), ("Transversal", C_CROSS),
]
handles = [Line2D([0], [0], marker="s", color="w", markerfacecolor=c, markersize=15, label=t)
           for t, c in legend_items]
ax.legend(handles=handles, loc="lower center", bbox_to_anchor=(0.5, -0.035),
          ncol=7, frameon=False, fontsize=10)

out = ROOT / "docs" / "img" / "arquitectura_produccion.png"
out.parent.mkdir(parents=True, exist_ok=True)
plt.savefig(out, facecolor=CREAM, bbox_inches="tight", dpi=160)
print("OK:", out)
