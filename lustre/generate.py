#!/usr/bin/env python3
"""Générateur du plan de perçage et des longueurs de fil du lustre « cascade »
(trous en quinconce : 20 cm en rangée / colonne, 14,14 cm en diagonale).

Python 3 standard uniquement (aucune dépendance). Relancer avec une autre
graine (SEED) pour obtenir une autre répartition aléatoire.

Sorties (dans le même dossier) :
  suspensions.csv   coordonnées de chaque trou + longueur de fil
  plan_plateau.svg  plan 2D du plateau à l'échelle (unités = mm, imprimable 1:1 ou 1:10)
  lustre.html       plan interactif + vues de face / de côté + tableau
"""
import csv
import json
import math
import os
import random

# --- Paramètres du lustre (cm) -------------------------------------------
W, H = 300.0, 240.0      # plateau 3,00 x 2,40 m (x = longueur, y = largeur)
# Grille en quinconce : 20 cm entre deux trous d'une même rangée ou d'une même colonne,
# 14,14 cm en diagonale (rangées tous les 10 cm, décalées de 10 cm une sur deux).
PITCH = 20.0
MARGIN_X, MARGIN_Y = 10.0, 5.0   # 24 rangées alternées de 15 et 14 trous = 348 suspensions
SUSP_D, SUSP_H = 5.0, 24.0
FIL_MIN = 100.0          # 1,00 m de fil nu sous le plateau avant la 1re suspension
ZONE = 550.0             # 5,50 m de zone de suspension (haut de la plus haute -> bas de la plus basse)
FIL_MAX = FIL_MIN + ZONE - SUSP_H   # 626 cm : fil de la suspension la plus basse
DROP = 140.0             # les suspensions du bord s'arrêtent jusqu'à 1,40 m plus haut qu'au centre
DROP_EXP = 1.7           # forme du fond : >1 = fond arrondi en « goutte »
BOTTOM_NOISE = 18.0      # irrégularité du contour bas (cm)
SEED = 2026

random.seed(SEED)
HERE = os.path.dirname(os.path.abspath(__file__))


# --- 1. Trous en quinconce -------------------------------------------------
def grid_points():
    half = PITCH / 2
    pts, rows = [], []
    nrows = int(round((H - 2 * MARGIN_Y) / half)) + 1
    for r in range(nrows):                      # r = 0 : rangée du haut du plan (A)
        y = H - MARGIN_Y - r * half
        x = MARGIN_X + (half if r % 2 else 0.0)
        c = 0
        while x <= W - MARGIN_X + 1e-9:
            c += 1
            pts.append([x, y]); rows.append((r, c))
            x += PITCH
    return pts, rows


# --- 2. Hauteurs : contour en goutte + voisins à des hauteurs différentes --
def assign_lengths(pts):
    N = len(pts)
    cx, cy = W / 2, H / 2
    hx, hy = W / 2 - MARGIN_X, H / 2 - MARGIN_Y
    rho = [math.hypot((x - cx) / hx, (y - cy) / hy) / math.sqrt(2) for x, y in pts]  # 0 centre, 1 coin
    rho = [min(1.0, r * 1.15) for r in rho]
    lmax = [FIL_MAX - DROP * r ** DROP_EXP - abs(random.gauss(0, BOTTOM_NOISE)) for r in rho]

    # Fractions stratifiées : chaque « étage » de hauteur est utilisé une seule fois.
    u = [(i + 0.5) / N for i in range(N)]
    random.shuffle(u)

    # Voisinage dans le plan
    R = 32.0
    nbr = [[] for _ in range(N)]
    for i in range(N):
        for j in range(i + 1, N):
            d = math.hypot(pts[i][0] - pts[j][0], pts[i][1] - pts[j][1])
            if d < R:
                w = 1.0 - d / R
                nbr[i].append((j, w)); nbr[j].append((i, w))

    def z(i, ui):          # profondeur du haut de la suspension = longueur de fil
        return FIL_MIN + ui * (lmax[i] - FIL_MIN)

    def local_cost(i, ui, skip=-1):
        zi = z(i, ui); c = 0.0
        for j, w in nbr[i]:
            if j == skip:
                continue
            dz = zi - z(j, u[j])
            c += w * math.exp(-(dz / 45.0) ** 2)   # pénalise deux voisins à hauteur proche
        return c

    # Recuit simple par échanges : éviter les « paquets » de suspensions au même niveau.
    T = 0.3
    for it in range(120000):
        i, j = random.randrange(N), random.randrange(N)
        if i == j:
            continue
        before = local_cost(i, u[i], j) + local_cost(j, u[j], i)
        u[i], u[j] = u[j], u[i]
        after = local_cost(i, u[i], j) + local_cost(j, u[j], i)
        if after > before and random.random() > math.exp((before - after) / T):
            u[i], u[j] = u[j], u[i]
        T *= 0.99996
    raw = [z(i, u[i]) for i in range(N)]
    # Étirement final pour que la plus basse touche exactement FIL_MAX (5,50 m de zone).
    k = (FIL_MAX - FIL_MIN) / (max(raw) - FIL_MIN)
    return [round(FIL_MIN + (v - FIL_MIN) * k) for v in raw]


# --- 3. Contrôles -----------------------------------------------------------
def check(pts, L):
    N = len(pts)
    nn, clear = [], 1e9
    for i in range(N):
        best = 1e9
        for j in range(N):
            if i == j:
                continue
            d = math.hypot(pts[i][0] - pts[j][0], pts[i][1] - pts[j][1])
            best = min(best, d)
            if j > i:
                vert_overlap = abs(L[i] - L[j]) < SUSP_H
                gap = d - SUSP_D if vert_overlap else math.hypot(d, abs(L[i] - L[j]) - SUSP_H)
                clear = min(clear, gap)
        nn.append(best)
    return min(nn), sum(nn) / N, clear


# --- 4. Repérage : lettre de rangée (A = haut du plan) + numéro de gauche à droite
def label(pts, rows, L):
    return [{"id": f"{chr(ord('A') + r)}{c:02d}", "x": round(p[0], 1), "y": round(p[1], 1), "fil": l}
            for p, (r, c), l in zip(pts, rows, L)]


def color(t):   # 0 = court (clair) -> 1 = long (foncé), dégradé ambre
    a, b = (250, 214, 140), (150, 72, 10)
    return "#%02x%02x%02x" % tuple(int(a[k] + (b[k] - a[k]) * t) for k in range(3))


def write_svg(rows, path):
    mm = 10
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W*mm+400}mm" height="{H*mm+500}mm" '
           f'viewBox="-200 -300 {W*mm+400} {H*mm+500}" font-family="Arial">',
           f'<rect x="0" y="0" width="{W*mm}" height="{H*mm}" fill="#fbf7ef" stroke="#222" stroke-width="6"/>']
    for gx in range(0, int(W) + 1, 10):
        sw = 2.5 if gx % 50 == 0 else 0.8
        out.append(f'<line x1="{gx*mm}" y1="0" x2="{gx*mm}" y2="{H*mm}" stroke="#bbb" stroke-width="{sw}"/>')
        if gx % 50 == 0:
            out.append(f'<text x="{gx*mm}" y="-25" font-size="40" text-anchor="middle">{gx}</text>')
    for gy in range(0, int(H) + 1, 10):
        sw = 2.5 if gy % 50 == 0 else 0.8
        out.append(f'<line x1="0" y1="{(H-gy)*mm}" x2="{W*mm}" y2="{(H-gy)*mm}" stroke="#bbb" stroke-width="{sw}"/>')
        if gy % 50 == 0:
            out.append(f'<text x="-25" y="{(H-gy)*mm+14}" font-size="40" text-anchor="end">{gy}</text>')
    for ry in sorted({r["y"] for r in rows}, reverse=True):   # repères de rangées
        b = next(r["id"][0] for r in rows if r["y"] == ry)
        out.append(f'<text x="{W*mm+30}" y="{(H-ry)*mm+14}" font-size="40" font-weight="bold" fill="#8a5a14">{b}  y={ry:g}</text>')
    for r in rows:
        t = (r["fil"] - FIL_MIN) / (FIL_MAX - FIL_MIN)
        X, Y = r["x"] * mm, (H - r["y"]) * mm
        out.append(f'<circle cx="{X:.0f}" cy="{Y:.0f}" r="25" fill="{color(t)}" stroke="#333" stroke-width="2"/>')
        out.append(f'<text x="{X:.0f}" y="{Y-32:.0f}" font-size="22" text-anchor="middle" fill="#333">{r["id"]}</text>')
        out.append(f'<text x="{X:.0f}" y="{Y+52:.0f}" font-size="24" font-weight="bold" text-anchor="middle">{r["fil"]}</text>')
    out.append(f'<text x="0" y="-200" font-size="70" font-weight="bold">Plateau 3,00 x 2,40 m - {len(rows)} trous en quinconce (20 cm / diag. 14,14 cm) - vue de dessous</text>')
    out.append('<text x="0" y="-120" font-size="40">Cotes en cm depuis le coin bas-gauche (0,0). '
               'Sous chaque point : longueur de fil (cm) du plateau au haut de la suspension. Quadrillage 10 cm.</text>')
    out.append('</svg>')
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(out))


def main():
    pts, rc = grid_points()
    L = assign_lengths(pts)
    dmin, dmean, clear = check(pts, L)
    rows = label(pts, rc, L)
    stats = {"n": len(pts), "pitch": PITCH, "dmin": round(dmin, 1), "dmean": round(dmean, 1),
             "clear": round(clear, 1), "fil_min": min(L), "fil_max": max(L),
             "W": W, "H": H, "susp_d": SUSP_D, "susp_h": SUSP_H, "FIL_MIN": FIL_MIN,
             "FIL_MAX": FIL_MAX, "seed": SEED}

    with open(os.path.join(HERE, "suspensions.csv"), "w", newline="", encoding="utf-8") as f:
        wr = csv.writer(f, delimiter=";")
        wr.writerow(["repere", "x_cm", "y_cm", "fil_cm", "bas_suspension_cm"])
        for r in rows:
            wr.writerow([r["id"], r["x"], r["y"], r["fil"], r["fil"] + int(SUSP_H)])
    write_svg(rows, os.path.join(HERE, "plan_plateau.svg"))
    with open(os.path.join(HERE, "template.html"), encoding="utf-8") as f:
        html = f.read()
    html = html.replace("__DATA__", json.dumps(rows)).replace("__STATS__", json.dumps(stats))
    with open(os.path.join(HERE, "lustre.html"), "w", encoding="utf-8") as f:
        f.write(html)
    print(json.dumps(stats, indent=1))


if __name__ == "__main__":
    main()
