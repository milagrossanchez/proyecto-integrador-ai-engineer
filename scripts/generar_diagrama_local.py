# -*- coding: utf-8 -*-
"""Diagrama de la arquitectura LOCAL (la que realmente corre para la demo):
una sola PC, SQL Server local, app local. Sin nube, salvo la llamada
opcional a la API de Anthropic.

Estilo corporativo: misma paleta navy + dorado que el diagrama de
producción, un solo color de acento por tarjeta en vez de uno por zona.

Salida: docs/img/arquitectura_local.png. Regenerar con:
    python scripts/generar_diagrama_local.py
"""

from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import (FancyBboxPatch, FancyArrowPatch, Rectangle,
                                 Circle, Ellipse, Polygon, Arc)

ROOT = Path(__file__).resolve().parents[1]

NAVY, GOLD, CREAM, WHITE, INK, MUT = (
    "#0B1C3D", "#B8923F", "#F5F3EE", "#FFFFFF", "#1D2233", "#6B6F7A")
SLATE = "#3C4A63"
Z_CROSS = "#8C3A32"

fig, ax = plt.subplots(figsize=(22, 15.5), dpi=160)
ax.axis("off")
fig.patch.set_facecolor(CREAM)
ax.set_facecolor(CREAM)


def ic_monitor(cx, cy, s, c):
    ax.add_patch(Rectangle((cx - s*.55, cy - s*.15), s*1.1, s*.72,
                 facecolor="none", edgecolor=c, linewidth=s*7, zorder=9))
    ax.plot([cx - s*.22, cx + s*.22], [cy - s*.45, cy - s*.45], color=c, lw=s*7, zorder=9)
    ax.plot([cx, cx], [cy - s*.15, cy - s*.45], color=c, lw=s*7, zorder=9)

def ic_window(cx, cy, s, c):
    ax.add_patch(Rectangle((cx - s*.55, cy - s*.45), s*1.1, s*.9,
                 facecolor="none", edgecolor=c, linewidth=s*5.5, zorder=9))
    ax.plot([cx - s*.55, cx + s*.55], [cy + s*.2, cy + s*.2], color=c, lw=s*4.5, zorder=9)

def ic_bubble(cx, cy, s, c):
    ax.add_patch(FancyBboxPatch((cx - s*.55, cy - s*.3), s*1.1, s*.72,
                 boxstyle=f"round,pad=0,rounding_size={s*.2}", facecolor=c, zorder=9))
    ax.add_patch(Polygon([(cx-s*.2, cy-s*.28), (cx-s*.35, cy-s*.58), (cx+s*.05, cy-s*.28)],
                 closed=True, facecolor=c, zorder=9))

def ic_target(cx, cy, s, c):
    for rad in (.5, .3, .1):
        ax.add_patch(Circle((cx, cy), s*rad, facecolor="none" if rad != .1 else c,
                     edgecolor=c, linewidth=s*4, zorder=9))

def ic_funnel(cx, cy, s, c):
    ax.add_patch(Polygon([(cx-s*.55, cy+s*.45), (cx+s*.55, cy+s*.45), (cx+s*.12, cy-s*.1),
                 (cx+s*.12, cy-s*.55), (cx-s*.12, cy-s*.55), (cx-s*.12, cy-s*.1)],
                 closed=True, facecolor=c, zorder=9))

def ic_db(cx, cy, s, c):
    ax.add_patch(Ellipse((cx, cy+s*.35), s*.9, s*.32, facecolor=c, zorder=9))
    ax.add_patch(Rectangle((cx-s*.45, cy-s*.35), s*.9, s*.7, facecolor=c, zorder=9))
    ax.add_patch(Ellipse((cx, cy-s*.35), s*.9, s*.32, facecolor=c, zorder=9))
    ax.add_patch(Ellipse((cx, cy+s*.35), s*.9, s*.32, facecolor=WHITE, edgecolor=c, linewidth=s*1.8, zorder=10))

def ic_cloud(cx, cy, s, c):
    for dx, dy, r in ((-.3, -.05, .32), (0, .12, .4), (.32, -.05, .3)):
        ax.add_patch(Circle((cx+s*dx, cy+s*dy), s*r, facecolor="none", edgecolor=c, linewidth=s*4.2, zorder=9))
    ax.add_patch(Rectangle((cx-s*.5, cy-s*.25), s*1.0, s*.25, facecolor=CREAM, edgecolor="none", zorder=8.5))
    ax.add_patch(Arc((cx, cy-s*.1), s*1.1, s*.5, theta1=200, theta2=340, color=c, linewidth=s*4.2, zorder=9))

def ic_warn(cx, cy, s, c):
    ax.add_patch(Polygon([(cx, cy+s*.6), (cx+s*.55, cy-s*.45), (cx-s*.55, cy-s*.45)],
                 closed=True, facecolor="none", edgecolor=c, linewidth=s*5, zorder=9))
    ax.plot([cx, cx], [cy+s*.15, cy-s*.1], color=c, lw=s*5, zorder=9, solid_capstyle="round")
    ax.add_patch(Circle((cx, cy-s*.28), s*.045, facecolor=c, zorder=9))

def ic_paperplane(cx, cy, s, c):
    ax.add_patch(Polygon([(cx-s*.55, cy-s*.35), (cx+s*.6, cy), (cx-s*.55, cy+s*.35),
                 (cx-s*.2, cy)], closed=True, facecolor=c, zorder=9))


def shadow(x, y, w, h, r=0.12):
    ax.add_patch(FancyBboxPatch((x+0.045, y-0.045), w, h, boxstyle=f"round,pad=0.0,rounding_size={r}",
                 linewidth=0, facecolor="#000000", alpha=0.05, zorder=1))

def panel(x, y, w, h, title, icon_fn, color=NAVY):
    shadow(x, y, w, h, r=0.16)
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.0,rounding_size=0.16",
                 linewidth=1.1, edgecolor="#D9D4C8", facecolor=WHITE, zorder=2))
    ax.add_patch(FancyBboxPatch((x, y+h-0.6), w, 0.6, boxstyle="round,pad=0.0,rounding_size=0.16",
                 linewidth=0, facecolor=color, zorder=3))
    ax.add_patch(Rectangle((x, y+h-0.6), w, 0.3, facecolor=color, linewidth=0, zorder=3))
    icon_fn(x+0.42, y+h-0.3, 0.23, WHITE)
    ax.text(x+0.85, y+h-0.3, title, fontsize=14, fontweight="bold", color=WHITE, va="center", ha="left", zorder=4)

def card(x, y, w, h, title, sub, icon_fn, fs=11, subfs=8.6, color=SLATE):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.0,rounding_size=0.1",
                 linewidth=0, facecolor="#F0EEE7", zorder=3))
    ax.add_patch(Rectangle((x, y), 0.07, h, facecolor=color, linewidth=0, zorder=4))
    icon_fn(x+0.45, y+h/2, h*0.32, color)
    tx0 = x+0.88
    ax.text(tx0, y+h*0.64, title, fontsize=fs, fontweight="bold", color=INK, va="center", ha="left", zorder=5)
    if sub:
        ax.text(tx0, y+h*0.26, sub, fontsize=subfs, color=MUT, va="center", ha="left", zorder=5)

def row_cards(items, y, h, icon_fns, x0, x1, gap=0.3, color=SLATE, fs=11, subfs=8.6):
    n = len(items)
    w = (x1-x0-gap*(n-1))/n
    for i, (title, sub) in enumerate(items):
        card(x0+i*(w+gap), y, w, h, title, sub, icon_fns[i], color=color, fs=fs, subfs=subfs)

def flow(x1, y1, x2, y2, color=GOLD, lw=2.4, ls="-"):
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle="-|>", mutation_scale=18,
                 color=color, linewidth=lw, zorder=6, linestyle=ls))


W = 22
ax.set_xlim(0, W)

# -------- se arma de ABAJO hacia ARRIBA con un cursor --------
cursor = 0.0
def place(h):
    global cursor
    y0 = cursor
    cursor += h
    return y0

# Alturas calculadas con margen explícito (header 0.6 + padding superior/
# inferior + contenido), para que ningún título choque con la tarjeta de
# abajo y no queden huecos grandes sin usar.
H_USER = 2.1
H_CLOUD = 2.1
PC_H = 3.8

# 1) pie: guardrail (queda abajo de todo)
y_guard = place(1.0)
cursor += 0.5

# 2) nube (opcional) — abajo de la PC
y_cloud = place(H_CLOUD)
cursor += 0.85

# 3) la PC (grande) — al medio
y_pc = place(PC_H)
cursor += 0.9

# 4) usuario — arriba de todo (se lee primero)
y_user = place(H_USER)

ZONE_TOP = cursor
TITLE_H = 2.15
TOP = ZONE_TOP + 0.5 + TITLE_H
ax.set_ylim(0, TOP)
fig.set_size_inches(W, TOP)

# ---- usuario ----
panel(0.6, y_user, 7.2, H_USER, "QUIÉN LO USA", ic_monitor)
card(0.95, y_user+0.35, 6.5, 1.0, "Analista / jurado", "abre el navegador en localhost:8501, en la misma PC", ic_monitor)

flow(W/2, y_user, W/2, y_pc + PC_H, color=GOLD, lw=2.6)

# ---- la PC ----
panel(0.6, y_pc, W - 1.2, PC_H, "TU PC — TODO CORRE ACÁ, SIN NUBE", ic_window)
row_cards(
    [("App web (Streamlit)", "localhost:8501 · pestañas Cartera y Cliente"),
     ("Chat flotante (RAG)", "TF-IDF sobre rag/politicas + rag/referencia"),
     ("Modelos .joblib", "riesgo, respuesta, NBO — en disco"),
     ("Optimizador", "beneficio incremental, guardrails"),
     ("Bot de Telegram", "run_telegram_bot.py, polling")],
    y_pc + 1.9, 1.1, [ic_window, ic_bubble, ic_target, ic_funnel, ic_paperplane],
    1.0, W - 1.0, fs=10, subfs=7.6)
card(1.0, y_pc + 0.4, W - 2.0, 1.1, "SQL Server Express (MILI\\SQLEXPRESS)",
     "base CasinoPalacioReal: sesiones, dimensiones, vistas, esquemas ext.* y ml.* — en la misma PC",
     ic_db, fs=12)

flow(W*0.5, y_pc, W*0.5, y_cloud + H_CLOUD, color=SLATE, lw=2.1, ls="--")
ax.text(W*0.5, y_pc - 0.45, "Internet (HTTPS) — únicas salidas de la PC; todo lo demás queda local",
        fontsize=10, color=MUT, ha="center", style="italic")

# ---- nube (opcional) ----
panel(0.6, y_cloud, W - 1.2, H_CLOUD, "SERVICIOS EN LA NUBE — opcionales, llamadas puntuales", ic_cloud)
row_cards(
    [("API de Anthropic (Claude)", "explicación/oferta/mensaje y chat — si no hay API key válida, modo plantilla"),
     ("Telegram Bot API", "bot real conectado, long polling — notifica oferta y recibe respuesta")],
    y_cloud + 0.3, 0.95, [ic_cloud, ic_paperplane], 1.0, W - 1.0)

# ---- guardrail (pie) ----
ax.add_patch(FancyBboxPatch((1.0, y_guard), W - 2.0, 1.0, boxstyle="round,pad=0,rounding_size=0.1",
             facecolor="#F3E1DC", edgecolor=Z_CROSS, linewidth=1.1, zorder=6))
ic_warn(1.6, y_guard+0.5, 0.22, Z_CROSS)
ax.text(2.0, y_guard+0.5,
        "Guardrail duro (corre local, no depende de la nube): riesgo Alto → cero ofertas, se deriva al protocolo de juego responsable.",
        fontsize=10, color=Z_CROSS, va="center", ha="left", fontweight="bold", zorder=7)

# ---- titulo ----
banner_y0 = ZONE_TOP + 0.3
ax.add_patch(Rectangle((0, banner_y0), W, TITLE_H - 0.3, facecolor=NAVY, zorder=1, linewidth=0))
ax.add_patch(Rectangle((0, banner_y0), 0.16, TITLE_H - 0.3, facecolor=GOLD, zorder=2, linewidth=0))
ax.text(0.45, banner_y0 + 1.42, "Arquitectura actual — demo local", fontsize=22, fontweight="bold",
        color=WHITE, va="center", family="serif")
ax.text(0.45, banner_y0 + 0.95, "Casino Palacio Real · lo que realmente corre hoy: una sola PC, sin nube salvo dos llamadas opcionales",
        fontsize=11.5, color="#C7D0E4", va="center")
ax.text(0.45, banner_y0 + 0.5, "Es la arquitectura de la presentación/demo. El objetivo de producción (distribuido, en Azure) está en arquitectura_produccion.md",
        fontsize=9.5, color="#9AA7C4", va="center", style="italic")

out = ROOT / "docs" / "img" / "arquitectura_local.png"
out.parent.mkdir(parents=True, exist_ok=True)
fig.savefig(out, facecolor=CREAM, bbox_inches="tight", dpi=160)
print("OK:", out)
