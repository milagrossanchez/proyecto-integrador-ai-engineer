# -*- coding: utf-8 -*-
"""Diagrama de arquitectura de produccion: zonas agrupadas (pocas flechas,
solo el flujo principal numerado) + iconos dibujados a mano (sin depender de
fuentes emoji, para que el PNG se vea igual en cualquier maquina).

Salida: docs/img/arquitectura_produccion.png (referenciado desde
docs/arquitectura_produccion.md). Regenerar con:
    python scripts/generar_diagrama_produccion.py
"""

from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import (FancyBboxPatch, FancyArrowPatch, Rectangle,
                                 Circle, Ellipse, Polygon, Arc)

ROOT = Path(__file__).resolve().parents[1]

NAVY, GOLD, CREAM, WHITE, INK, MUT = (
    "#0B1C3D", "#C9A24B", "#F7F4EC", "#FFFFFF", "#1D2233", "#767A86")
Z_CANAL, Z_RED, Z_APP, Z_PROC, Z_DATA, Z_CROSS = (
    "#15213F", "#51607A", "#2C6E68", "#8A5A2B", "#2B557C", "#9C3B31")

W = 26  # ancho fijo del lienzo
fig, ax = plt.subplots(figsize=(W, 24), dpi=160)
ax.axis("off")
fig.patch.set_facecolor(CREAM)
ax.set_facecolor(CREAM)


# ================================================================ iconos ==
def ic_phone(cx, cy, s, c):
    ax.add_patch(FancyBboxPatch((cx - s*.32, cy - s*.55), s*.64, s*1.1,
                 boxstyle=f"round,pad=0,rounding_size={s*.12}", facecolor="none",
                 edgecolor=c, linewidth=s*7, zorder=9))
    ax.add_patch(Circle((cx, cy + s*.38), s*.06, facecolor=c, zorder=9))

def ic_monitor(cx, cy, s, c):
    ax.add_patch(Rectangle((cx - s*.55, cy - s*.15), s*1.1, s*.72,
                 facecolor="none", edgecolor=c, linewidth=s*7, zorder=9))
    ax.plot([cx - s*.22, cx + s*.22], [cy - s*.45, cy - s*.45], color=c, lw=s*7, zorder=9)
    ax.plot([cx, cx], [cy - s*.15, cy - s*.45], color=c, lw=s*7, zorder=9)

def ic_grid(cx, cy, s, c):
    for i in (-1, 1):
        for j in (-1, 1):
            ax.add_patch(Rectangle((cx + i*s*.5 - s*.32, cy + j*s*.3 - s*.2), s*.5, s*.4,
                         facecolor=c, zorder=9))

def ic_globe(cx, cy, s, c):
    ax.add_patch(Circle((cx, cy), s*.55, facecolor="none", edgecolor=c, linewidth=s*5.5, zorder=9))
    ax.add_patch(Ellipse((cx, cy), s*.55, s*1.1, facecolor="none", edgecolor=c, linewidth=s*4.5, zorder=9))
    ax.plot([cx - s*.55, cx + s*.55], [cy, cy], color=c, lw=s*4.5, zorder=9)

def ic_shield(cx, cy, s, c):
    pts = [(cx, cy+s*.62), (cx+s*.5, cy+s*.32), (cx+s*.5, cy-s*.22), (cx, cy-s*.62),
           (cx-s*.5, cy-s*.22), (cx-s*.5, cy+s*.32)]
    ax.add_patch(Polygon(pts, closed=True, facecolor=c, zorder=9))

def ic_scale(cx, cy, s, c):
    ax.plot([cx, cx], [cy - s*.55, cy + s*.55], color=c, lw=s*5.5, zorder=9)
    ax.plot([cx - s*.55, cx + s*.55], [cy + s*.4, cy + s*.4], color=c, lw=s*5.5, zorder=9)
    for i in (-1, 1):
        ax.add_patch(Arc((cx+i*s*.55, cy+s*.05), s*.5, s*.45, theta1=180, theta2=360,
                     color=c, linewidth=s*5.5, zorder=9))

def ic_key(cx, cy, s, c):
    ax.add_patch(Circle((cx - s*.3, cy), s*.3, facecolor="none", edgecolor=c, linewidth=s*5.5, zorder=9))
    ax.plot([cx - s*.02, cx + s*.6], [cy, cy], color=c, lw=s*5.5, zorder=9)
    ax.plot([cx + s*.4, cx + s*.4], [cy, cy - s*.22], color=c, lw=s*5.5, zorder=9)

def ic_window(cx, cy, s, c):
    ax.add_patch(Rectangle((cx - s*.55, cy - s*.45), s*1.1, s*.9,
                 facecolor="none", edgecolor=c, linewidth=s*5.5, zorder=9))
    ax.plot([cx - s*.55, cx + s*.55], [cy + s*.2, cy + s*.2], color=c, lw=s*4.5, zorder=9)

def ic_gear(cx, cy, s, c):
    ax.add_patch(Circle((cx, cy), s*.3, facecolor="none", edgecolor=c, linewidth=s*5, zorder=9))
    for ang in np.linspace(0, 360, 8, endpoint=False):
        a = np.radians(ang)
        x1, y1 = cx + s*.38*np.cos(a), cy + s*.38*np.sin(a)
        x2, y2 = cx + s*.6*np.cos(a), cy + s*.6*np.sin(a)
        ax.plot([x1, x2], [y1, y2], color=c, lw=s*5.5, zorder=9, solid_capstyle="round")

def ic_bubble(cx, cy, s, c):
    ax.add_patch(FancyBboxPatch((cx - s*.55, cy - s*.3), s*1.1, s*.72,
                 boxstyle=f"round,pad=0,rounding_size={s*.2}", facecolor=c, zorder=9))
    ax.add_patch(Polygon([(cx-s*.2, cy-s*.28), (cx-s*.35, cy-s*.58), (cx+s*.05, cy-s*.28)],
                 closed=True, facecolor=c, zorder=9))

def ic_paperplane(cx, cy, s, c):
    ax.add_patch(Polygon([(cx-s*.55, cy-s*.35), (cx+s*.6, cy), (cx-s*.55, cy+s*.35),
                 (cx-s*.2, cy)], closed=True, facecolor=c, zorder=9))

def ic_layers(cx, cy, s, c):
    for i, dy in enumerate((-.32, 0, .32)):
        ax.add_patch(Rectangle((cx - s*.5, cy + s*dy - s*.09), s, s*.18,
                     facecolor=c, zorder=9, alpha=1 - i*0.18))

def ic_cpu(cx, cy, s, c):
    ax.add_patch(Rectangle((cx - s*.38, cy - s*.38), s*.76, s*.76,
                 facecolor="none", edgecolor=c, linewidth=s*5.5, zorder=9))
    for i in (-.22, .22):
        ax.plot([cx+i, cx+i], [cy-s*.55, cy-s*.38], color=c, lw=s*4.5, zorder=9)
        ax.plot([cx+i, cx+i], [cy+s*.38, cy+s*.55], color=c, lw=s*4.5, zorder=9)
        ax.plot([cx-s*.55, cx-s*.38], [cy+i, cy+i], color=c, lw=s*4.5, zorder=9)
        ax.plot([cx+s*.38, cx+s*.55], [cy+i, cy+i], color=c, lw=s*4.5, zorder=9)

def ic_gauge(cx, cy, s, c):
    ax.add_patch(Arc((cx, cy-s*.1), s*1.0, s*1.0, theta1=20, theta2=160, color=c, linewidth=s*5.5, zorder=9))
    ax.plot([cx, cx+s*.35], [cy-s*.1, cy+s*.3], color=c, lw=s*5, zorder=9)
    ax.add_patch(Circle((cx, cy-s*.1), s*.06, facecolor=c, zorder=9))

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

def ic_bolt(cx, cy, s, c):
    ax.add_patch(Polygon([(cx+s*.18, cy+s*.62), (cx-s*.32, cy-s*.05), (cx, cy-s*.05),
                 (cx-s*.18, cy-s*.62), (cx+s*.32, cy+s*.12), (cx, cy+s*.12)],
                 closed=True, facecolor=c, zorder=9))

def ic_cluster(cx, cy, s, c):
    for dx, dy in ((0, .35), (-.4, -.2), (.4, -.2)):
        ax.add_patch(Circle((cx+s*dx, cy+s*dy), s*.2, facecolor=c, zorder=9))
    ax.plot([cx, cx-s*.4], [cy+s*.2, cy-s*.05], color=c, lw=s*2, zorder=8)
    ax.plot([cx, cx+s*.4], [cy+s*.2, cy-s*.05], color=c, lw=s*2, zorder=8)

def ic_lake(cx, cy, s, c):
    ax.add_patch(Polygon([(cx, cy+s*.6), (cx+s*.42, cy-s*.1), (cx+s*.42, cy-s*.4), (cx, cy-s*.6),
                 (cx-s*.42, cy-s*.4), (cx-s*.42, cy-s*.1)],
                 closed=True, facecolor="none", edgecolor=c, linewidth=s*4.5, zorder=9))

def ic_doc(cx, cy, s, c):
    ax.add_patch(Rectangle((cx-s*.42, cy-s*.55), s*.84, s*1.1, facecolor="none",
                 edgecolor=c, linewidth=s*4.5, zorder=9))
    for dy in (-.2, .05, .3):
        ax.plot([cx-s*.22, cx+s*.22], [cy+s*dy, cy+s*dy], color=c, lw=s*3, zorder=9)

def ic_loop(cx, cy, s, c):
    ax.add_patch(Arc((cx, cy), s*1.0, s*1.0, theta1=30, theta2=320, color=c, linewidth=s*5.5, zorder=9))
    a = np.radians(320)
    hx, hy = cx + s*.5*np.cos(a), cy + s*.5*np.sin(a)
    ax.add_patch(Polygon([(hx, hy), (hx-s*.22, hy+s*.05), (hx-s*.05, hy-s*.2)],
                 closed=True, facecolor=c, zorder=9))

def ic_warn(cx, cy, s, c):
    ax.add_patch(Polygon([(cx, cy+s*.6), (cx+s*.55, cy-s*.45), (cx-s*.55, cy-s*.45)],
                 closed=True, facecolor="none", edgecolor=c, linewidth=s*5, zorder=9))
    ax.plot([cx, cx], [cy+s*.15, cy-s*.1], color=c, lw=s*5, zorder=9, solid_capstyle="round")
    ax.add_patch(Circle((cx, cy-s*.28), s*.045, facecolor=c, zorder=9))


# ============================================================ utilidades ==
def shadow(x, y, w, h, r=0.12):
    ax.add_patch(FancyBboxPatch((x+0.06, y-0.06), w, h, boxstyle=f"round,pad=0.0,rounding_size={r}",
                 linewidth=0, facecolor="#000000", alpha=0.07, zorder=1))

def zone(x, y, w, h, title, color, icon_fn):
    shadow(x, y, w, h, r=0.18)
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.0,rounding_size=0.18",
                 linewidth=1.4, edgecolor=color, facecolor=WHITE, zorder=2))
    ax.add_patch(FancyBboxPatch((x, y+h-0.6), w, 0.6, boxstyle="round,pad=0.0,rounding_size=0.18",
                 linewidth=0, facecolor=color, zorder=3))
    ax.add_patch(Rectangle((x, y+h-0.6), w, 0.3, facecolor=color, linewidth=0, zorder=3))
    icon_fn(x+0.42, y+h-0.3, 0.23, WHITE)
    ax.text(x+0.85, y+h-0.3, title, fontsize=14, fontweight="bold", color=WHITE,
            va="center", ha="left", zorder=4)

def card(x, y, w, h, title, sub, color, icon_fn, fs=10.2, subfs=8.0):
    shadow(x, y, w, h, r=0.1)
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.0,rounding_size=0.1",
                 linewidth=0, facecolor="#F2F0EA", zorder=3))
    ax.add_patch(Rectangle((x, y), 0.08, h, facecolor=color, linewidth=0, zorder=4))
    icon_fn(x+0.42, y+h/2, h*0.3, color)
    tx0 = x+0.82
    ax.text(tx0, y+h*0.64, title, fontsize=fs, fontweight="bold", color=INK, va="center", ha="left", zorder=5)
    if sub:
        ax.text(tx0, y+h*0.27, sub, fontsize=subfs, color=MUT, va="center", ha="left", zorder=5)

def row_cards(items, y, h, color, icon_fns, x0, x1, gap=0.28):
    n = len(items)
    w = (x1-x0-gap*(n-1))/n
    for i, (title, sub) in enumerate(items):
        card(x0+i*(w+gap), y, w, h, title, sub, color, icon_fns[i])

def flow_arrow(cx, y_top, y_bot, label):
    ax.add_patch(FancyArrowPatch((cx, y_top), (cx, y_bot), arrowstyle="-|>", mutation_scale=22,
                 color=GOLD, linewidth=3.2, zorder=6, capstyle="round"))
    my = (y_top+y_bot)/2
    ax.add_patch(Circle((cx, my), 0.26, facecolor=NAVY, zorder=7))
    ax.text(cx, my, label, fontsize=11, color=WHITE, ha="center", va="center", fontweight="bold", zorder=8)


# =============================================================== layout ===
XM, X1 = 0.5, W - 0.5          # margenes del lienzo
cx_mid = W / 2
cursor = 0.0                    # se acumula de ABAJO hacia ARRIBA

def place(h):
    """Reserva h unidades de alto; devuelve el 'y' (base) de ese bloque."""
    global cursor
    y = cursor
    cursor += h
    return y

GAP_ZONE = 0.35
GAP_ARROW = 0.55

# ---- de abajo hacia arriba: Transversal, Datos, Procesamiento, Aplicacion, Red, Clientes
y_trans = place(1.95)
cursor += GAP_ZONE
y_datos = place(1.95)
cursor += GAP_ARROW
y_proc  = place(4.15)
cursor += GAP_ARROW
y_app   = place(1.95)
cursor += GAP_ARROW
y_red   = place(1.95)
cursor += GAP_ARROW
y_cli   = place(1.95)

ZONE_TOP = cursor            # tope de la zona 1 (la ultima colocada)
BANNER_H = 1.15
banner_y0 = ZONE_TOP + 0.3
YLIM_TOP = banner_y0 + BANNER_H + 0.15

fig.set_size_inches(W, YLIM_TOP)
ax.set_xlim(0, W)
ax.set_ylim(0, YLIM_TOP)

# ----- titulo -----
ax.add_patch(Rectangle((0, banner_y0), W, BANNER_H, facecolor=NAVY, zorder=1, linewidth=0))
ax.add_patch(Rectangle((0, banner_y0), 0.16, BANNER_H, facecolor=GOLD, zorder=2, linewidth=0))
ax.text(0.45, banner_y0 + 0.83, "Arquitectura de producción — Casino Palacio Real", fontsize=23,
        fontweight="bold", color=WHITE, va="center", family="serif")
ax.text(0.45, banner_y0 + 0.3, "Entorno real con tráfico masivo de clientes · orquestación, Telegram, observabilidad",
        fontsize=12, color="#C7D0E4", va="center")

# ----- 1 Clientes -----
zone(XM, y_cli, X1-XM, 1.95, "1 · CLIENTES Y CANALES", Z_CANAL, ic_phone)
row_cards([("Cliente del casino", "Telegram, recibe ofertas y responde"),
           ("Operador de marketing", "consultas sobre clientes"),
           ("Piso de juego", "sesiones en vivo, alto volumen"),
           ("Público en general", "web, miles de sesiones concurrentes")],
          y_cli + 0.32, 1.0, Z_CANAL, [ic_phone, ic_monitor, ic_grid, ic_globe], XM+0.45, X1-0.45)
flow_arrow(cx_mid, y_cli, y_red + 1.95, "1")

# ----- 2 Red -----
zone(XM, y_red, X1-XM, 1.95, "2 · RED Y CONECTIVIDAD", Z_RED, ic_shield)
row_cards([("CDN + WAF", "cachea estáticos, filtra ataques"),
           ("API Gateway", "autenticación, rate limiting"),
           ("Load Balancer", "reparte carga, autoescalado"),
           ("VPN / Private Link", "acceso privado al SQL on-prem")],
          y_red + 0.32, 1.0, Z_RED, [ic_globe, ic_funnel, ic_scale, ic_key], XM+0.45, X1-0.45)
flow_arrow(cx_mid, y_red, y_app + 1.95, "2")

# ----- 3 Aplicacion -----
zone(XM, y_app, X1-XM, 1.95, "3 · APLICACIÓN Y ORQUESTACIÓN", Z_APP, ic_gear)
row_cards([("Frontend web", "React / Next.js, reemplaza a Streamlit"),
           ("Orquestador", "FastAPI, coordina todo"),
           ("Servicio de Chat", "RAG + LLM, un único motor"),
           ("Bot de Telegram", "envía oferta, registra respuesta"),
           ("Panel interno", "Streamlit, solo equipo de datos")],
          y_app + 0.32, 1.0, Z_APP, [ic_window, ic_gear, ic_bubble, ic_paperplane, ic_monitor], XM+0.45, X1-0.45)
flow_arrow(cx_mid, y_app, y_proc + 4.15, "3")

# ----- 4 Procesamiento -----
zone(XM, y_proc, X1-XM, 4.15, "4 · PROCESAMIENTO ASÍNCRONO Y NÚCLEO ML", Z_PROC, ic_cpu)
row_cards([("Cola de eventos", "Service Bus / Kafka, tráfico masivo"),
           ("Workers de scoring", "auto-escalables, en paralelo")],
          y_proc + 2.75, 1.0, Z_PROC, [ic_layers, ic_cpu], XM+3.9, X1-3.9)
row_cards([("Modelo de riesgo", "Bajo / Medio / Alto"),
           ("Modelo de respuesta V1", "P(responde)"),
           ("Modelo NBO (V2)", "P y valor por recompensa"),
           ("Optimizador", "valor esperado − costo")],
          y_proc + 1.35, 1.0, Z_PROC, [ic_gauge, ic_target, ic_target, ic_funnel], XM+0.45, X1-0.45)
# franja de guardrail (ancho completo, sin solaparse con nada)
gy = y_proc + 0.25
ax.add_patch(FancyBboxPatch((XM+0.45, gy), X1-XM-0.9, 0.85, boxstyle="round,pad=0,rounding_size=0.09",
             facecolor="#F6E3DF", edgecolor=Z_CROSS, linewidth=1.3, zorder=6))
ic_warn(XM+1.05, gy+0.42, 0.22, Z_CROSS)
ax.text(XM+1.5, gy+0.42, "Guardrail duro: un cliente de riesgo Alto no recibe ninguna oferta "
        "y se deriva al protocolo de juego responsable — la regla vive en el optimizador, no en la interfaz.",
        fontsize=9.3, color=Z_CROSS, va="center", ha="left", fontweight="bold", zorder=7)
flow_arrow(cx_mid, y_proc, y_datos + 1.95, "4")

# ----- 5 Datos -----
zone(XM, y_datos, X1-XM, 1.95, "5 · DATOS", Z_DATA, ic_db)
row_cards([("Azure SQL", "réplica productiva"),
           ("Cache (Redis)", "features calientes"),
           ("Vector Store (RAG)", "políticas + guías"),
           ("Data Lake / Blob", "logs, resultados de campaña")],
          y_datos + 0.32, 1.0, Z_DATA, [ic_db, ic_bolt, ic_cluster, ic_lake], XM+0.45, X1-0.45)

# ----- Transversal -----
zone(XM, y_trans, X1-XM, 1.95, "TRANSVERSAL — en todas las capas", Z_CROSS, ic_shield)
row_cards([("Seguridad", "Key Vault, IAM, cifrado"),
           ("Logs y observabilidad", "Application Insights / ELK"),
           ("Resultados de campaña", "oferta, respuesta real, reentrenamiento")],
          y_trans + 0.32, 1.0, Z_CROSS, [ic_key, ic_doc, ic_loop], XM+0.45, X1-0.45)

# lazo de reentrenamiento: Resultados de campaña -> Modelo NBO, por el margen derecho
fx = X1 - 0.15
y_nbo = y_proc + 1.35 + 0.5
ax.plot([X1 - 0.95, fx, fx, X1 - 0.95], [y_trans + 0.82, y_trans + 0.82, y_nbo, y_nbo],
        color=GOLD, linewidth=2.6, zorder=6, solid_capstyle="round")
ax.add_patch(FancyArrowPatch((fx, y_nbo), (X1 - 0.95, y_nbo), arrowstyle="-|>", mutation_scale=16,
             color=GOLD, linewidth=2.6, zorder=6))
ax.text(fx + 0.2, (y_trans + y_nbo) / 2, "reentrena con respuestas reales", fontsize=8.8, color="#8A6A20",
        fontweight="bold", ha="left", va="center", rotation=90)

out = ROOT / "docs" / "img" / "arquitectura_produccion.png"
out.parent.mkdir(parents=True, exist_ok=True)
fig.savefig(out, facecolor=CREAM, bbox_inches="tight", dpi=160)
print("OK:", out, "canvas:", W, "x", YLIM_TOP)
