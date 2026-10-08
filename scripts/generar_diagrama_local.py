# -*- coding: utf-8 -*-
"""Diagrama de la arquitectura LOCAL (la que realmente corre para la demo):
una sola PC, SQL Server local, app local. Sin nube, salvo 2 llamadas externas
opcionales (API de Anthropic y, si se activa, Telegram).

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
    "#0B1C3D", "#C9A24B", "#F7F4EC", "#FFFFFF", "#1D2233", "#767A86")
C_USER, C_PC, C_SQL, C_CLOUD, C_CROSS = (
    "#15213F", "#2C6E68", "#2B557C", "#6C4B8C", "#9C3B31")

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

def ic_paperplane(cx, cy, s, c):
    ax.add_patch(Polygon([(cx-s*.55, cy-s*.35), (cx+s*.6, cy), (cx-s*.55, cy+s*.35),
                 (cx-s*.2, cy)], closed=True, facecolor=c, zorder=9))

def ic_warn(cx, cy, s, c):
    ax.add_patch(Polygon([(cx, cy+s*.6), (cx+s*.55, cy-s*.45), (cx-s*.55, cy-s*.45)],
                 closed=True, facecolor="none", edgecolor=c, linewidth=s*5, zorder=9))
    ax.plot([cx, cx], [cy+s*.15, cy-s*.1], color=c, lw=s*5, zorder=9, solid_capstyle="round")
    ax.add_patch(Circle((cx, cy-s*.28), s*.045, facecolor=c, zorder=9))


def shadow(x, y, w, h, r=0.12):
    ax.add_patch(FancyBboxPatch((x+0.06, y-0.06), w, h, boxstyle=f"round,pad=0.0,rounding_size={r}",
                 linewidth=0, facecolor="#000000", alpha=0.07, zorder=1))

def panel(x, y, w, h, title, color, icon_fn):
    shadow(x, y, w, h, r=0.16)
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.0,rounding_size=0.16",
                 linewidth=1.6, edgecolor=color, facecolor=WHITE, zorder=2))
    ax.add_patch(FancyBboxPatch((x, y+h-0.6), w, 0.6, boxstyle="round,pad=0.0,rounding_size=0.16",
                 linewidth=0, facecolor=color, zorder=3))
    ax.add_patch(Rectangle((x, y+h-0.6), w, 0.3, facecolor=color, linewidth=0, zorder=3))
    icon_fn(x+0.42, y+h-0.3, 0.23, WHITE)
    ax.text(x+0.85, y+h-0.3, title, fontsize=14, fontweight="bold", color=WHITE, va="center", ha="left", zorder=4)

def card(x, y, w, h, title, sub, color, icon_fn, fs=11, subfs=8.6):
    shadow(x, y, w, h, r=0.1)
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.0,rounding_size=0.1",
                 linewidth=0, facecolor="#F2F0EA", zorder=3))
    ax.add_patch(Rectangle((x, y), 0.08, h, facecolor=color, linewidth=0, zorder=4))
    icon_fn(x+0.45, y+h/2, h*0.32, color)
    tx0 = x+0.88
    ax.text(tx0, y+h*0.64, title, fontsize=fs, fontweight="bold", color=INK, va="center", ha="left", zorder=5)
    if sub:
        ax.text(tx0, y+h*0.26, sub, fontsize=subfs, color=MUT, va="center", ha="left", zorder=5)

def row_cards(items, y, h, color, icon_fns, x0, x1, gap=0.3):
    n = len(items)
    w = (x1-x0-gap*(n-1))/n
    for i, (title, sub) in enumerate(items):
        card(x0+i*(w+gap), y, w, h, title, sub, color, icon_fns[i])

def flow(x1, y1, x2, y2, color=GOLD, lw=2.6, ls="-"):
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle="-|>", mutation_scale=18,
                 color=color, linewidth=lw, zorder=6, linestyle=ls))


W = 22
ax.set_xlim(0, W)

# -------- se arma de ABAJO hacia ARRIBA con un cursor, como en el otro script --------
cursor = 0.0
def place(h):
    global cursor
    y0 = cursor
    cursor += h
    return y0

# 1) pie: guardrail (queda abajo de todo)
y_guard = place(1.0)
cursor += 0.5

# 2) nube (opcional) — abajo de la PC
y_cloud = place(1.9)
cursor += 0.85

# 3) la PC (grande) — al medio
y_pc = place(5.6)
cursor += 0.9

# 4) usuario — arriba de todo (se lee primero)
y_user = place(1.7)

ZONE_TOP = cursor
TITLE_H = 2.15
TOP = ZONE_TOP + 0.5 + TITLE_H
ax.set_ylim(0, TOP)
fig.set_size_inches(W, TOP)

# ---- usuario ----
panel(0.6, y_user, 7.2, 1.7, "QUIÉN LO USA", C_USER, ic_monitor)
card(0.95, y_user+0.28, 6.5, 1.0, "Analista / jurado", "abre el navegador en localhost:8501, en la misma PC", C_USER, ic_monitor)

flow(W/2, y_user, W/2, y_pc + 5.6, color=GOLD, lw=2.8)

# ---- la PC ----
pc_h = 5.6
panel(0.6, y_pc, W - 1.2, pc_h, "TU PC — TODO CORRE ACÁ, SIN NUBE", C_PC, ic_window)
row_cards(
    [("App web (Streamlit)", "localhost:8501 · pestañas Cartera y Cliente"),
     ("Chat flotante (RAG)", "TF-IDF sobre rag/politicas + rag/referencia"),
     ("Modelos .joblib", "riesgo, respuesta V1, NBO calibrado — en disco"),
     ("Optimizador", "Python puro: valor esperado, guardrails, topes")],
    y_pc + pc_h - 1.85, 1.1, C_PC, [ic_window, ic_bubble, ic_target, ic_funnel],
    1.0, W - 1.0)
card(1.0, y_pc + 0.45, W - 2.0, 1.1, "SQL Server Express (MILI\\SQLEXPRESS)",
     "base CasinoPalacioReal: sesiones, dimensiones, vistas, esquemas ext.* y ml.* — en la misma PC",
     C_SQL, ic_db, fs=12)

flow(W*0.3, y_pc, W*0.3, y_cloud + 1.9, color=C_CLOUD, lw=2.2, ls="--")
flow(W*0.7, y_pc, W*0.7, y_cloud + 1.9, color=C_CLOUD, lw=2.2, ls="--")
ax.text(W*0.5, y_pc - 0.45, "Internet (HTTPS) — únicas 2 salidas de la PC; todo lo demás queda local",
        fontsize=10, color=MUT, ha="center", style="italic")

# ---- nube (opcional) ----
panel(0.6, y_cloud, W - 1.2, 1.9, "SERVICIOS EN LA NUBE — opcionales, 2 llamadas puntuales", C_CLOUD, ic_cloud)
row_cards(
    [("API de Anthropic (Claude)", "genera explicación/oferta/mensaje y responde el chat — si hay API key válida"),
     ("Telegram Bot API", "hoy en modo dry-run: arma el mensaje, no lo envía — sin credenciales activas")],
    y_cloud + 0.3, 1.1, C_CLOUD, [ic_cloud, ic_paperplane], 1.0, W - 1.0)

# ---- guardrail (pie) ----
ax.add_patch(FancyBboxPatch((1.0, y_guard), W - 2.0, 1.0, boxstyle="round,pad=0,rounding_size=0.1",
             facecolor="#F6E3DF", edgecolor=C_CROSS, linewidth=1.3, zorder=6))
ic_warn(1.6, y_guard+0.5, 0.22, C_CROSS)
ax.text(2.0, y_guard+0.5,
        "Guardrail duro (corre local, no depende de la nube): riesgo Alto → cero ofertas, se deriva al protocolo de juego responsable.",
        fontsize=10, color=C_CROSS, va="center", ha="left", fontweight="bold", zorder=7)

# ---- titulo ----
banner_y0 = ZONE_TOP + 0.3
ax.add_patch(Rectangle((0, banner_y0), W, TITLE_H - 0.3, facecolor=NAVY, zorder=1, linewidth=0))
ax.add_patch(Rectangle((0, banner_y0), 0.16, TITLE_H - 0.3, facecolor=GOLD, zorder=2, linewidth=0))
ax.text(0.45, banner_y0 + 1.42, "Arquitectura actual — demo local", fontsize=22, fontweight="bold",
        color=WHITE, va="center", family="serif")
ax.text(0.45, banner_y0 + 0.95, "Casino Palacio Real · lo que realmente corre hoy: una sola PC, sin nube salvo 2 llamadas opcionales",
        fontsize=11.5, color="#C7D0E4", va="center")
ax.text(0.45, banner_y0 + 0.5, "Es la arquitectura de la presentación/demo. El objetivo de producción (distribuido, en Azure) está en arquitectura_produccion.md",
        fontsize=9.5, color="#9AA7C4", va="center", style="italic")

out = ROOT / "docs" / "img" / "arquitectura_local.png"
out.parent.mkdir(parents=True, exist_ok=True)
fig.savefig(out, facecolor=CREAM, bbox_inches="tight", dpi=160)
print("OK:", out)
