"""Plans de découpe laser du lustre spirale 1200 x 800 (30 boîtes).

Pièces produites (coordonnées en mm, origine = centre du lustre) :

  01 - Plateau inox 1 mm : fond visible 1200 x 800 + ceinture de 30 mm
       intégrée (4 bords pliés à 90° vers le haut) + pattes de fixation
       (reprises du fichier « ceinture » SI8-50) repliées vers l'intérieur
       sur le galvin.
       Trous : 30 oblongs 6 x 4 (passage des fils), 6 trous Ø6 (écrous).
  02 - Galvin 1,5 mm : plaque plafond logée dans la ceinture.
       Trous : 6 trous Ø10,4 (R5,2) superposés aux Ø6 de l'inox,
       1 trou central Ø7 (fixation plafond), trous Ø4 en face des pattes.

Calcul de pliage (inox 1 mm, rayon intérieur 1 mm, facteur K 0,33) :
  retrait extérieur OSSB = r + t = 2,00
  longueur d'arc BA      = π/2 · (r + K·t) = 2,09
  déduction BD           = 2·OSSB − BA = 1,91

Usage : python3 scripts/generer_fabrication.py
"""
import math
import os

import ezdxf
from ezdxf import bbox
from ezdxf.enums import TextEntityAlignment

MODELE_3D = "lustres/lustre-spirale-1200x800-H3500-30boites.dxf"
DOSSIER = "fabrication"

# --- Matières / pliage -------------------------------------------------------
T_INOX, T_GALVIN = 1.0, 1.5
R_INT, K = 1.0, 0.33
OSSB = R_INT + T_INOX
BA = math.pi / 2 * (R_INT + K * T_INOX)
BD = 2 * OSSB - BA
DEPORT = OSSB - BA / 2          # cote extérieure -> axe de pli

# --- Plateau inox (cotes extérieures après pliage) ---------------------------
L_EXT, W_EXT, H_CEINTURE = 1200.0, 800.0, 30.0
FLANC = H_CEINTURE - DEPORT     # longueur à plat d'un bord, axe de pli -> chant
AXE_X = L_EXT / 2 - DEPORT      # position des axes de pli sur le flan
AXE_Y = W_EXT / 2 - DEPORT
FLAN_X = AXE_X + FLANC          # demi-dimensions du flan (hors pattes)
FLAN_Y = AXE_Y + FLANC
DEGAGEMENT = 0.5                # dégagement d'angle au-delà du début de pli
COIN_X = AXE_X - BA / 2 - DEGAGEMENT
COIN_Y = AXE_Y - BA / 2 - DEGAGEMENT

# Patte de fixation (géométrie exacte du fichier ceinture SI8-50)
#   col 6 mm, tête R7 centrée à 10 mm du chant, trou Ø3,2 à 12 mm du chant.
PATTE_COL = 3.0
PATTE_R = 7.0
PATTE_Y_TETE = 10.0
PATTE_R_RACCORD = 19.10795145464751
PATTE_C_RACCORD = (12.022, 11.81)
PATTE_TROU_Y, PATTE_TROU_D = 12.0, 3.2
PATTES_GRAND_COTE = [-450.0, -150.0, 150.0, 450.0]
PATTES_PETIT_COTE = [-250.0, 0.0, 250.0]

# Trous
OBLONG_L, OBLONG_W = 6.0, 4.0   # passage fils
D_TROU_INOX = 6.0               # écrous, inox
R_TROU_GALVIN = 5.2             # écrous, galvin (Ø10,4)
D_CENTRAL = 7.0                 # fixation plafond, galvin seulement
D_TROU_PATTE_GALVIN = 4.0       # Ø3,2 de la patte + 0,8 de tolérance de pliage
POINTS_ECROUS = [(-432.0, -255.0), (0.0, -255.0), (432.0, -255.0),
                 (-432.0, 255.0), (0.0, 255.0), (432.0, 255.0)]

# --- Galvin ------------------------------------------------------------------
JEU = 1.0                       # jeu par côté dans la ceinture
G_L = L_EXT - 2 * T_INOX - 2 * JEU
G_W = W_EXT - 2 * T_INOX - 2 * JEU
G_RAYON_COIN = 3.0
# trou de patte replié : distance à la face extérieure de la ceinture
PATTE_TROU_APRES_PLI = DEPORT + PATTE_TROU_Y

LAYERS = {
    "DECOUPE": dict(color=1),                       # rouge : à couper
    "PLIAGE": dict(color=5, linetype="DASHED"),     # bleu : ne pas couper
    "TEXTE": dict(color=7),                         # annotations
    "COTATION": dict(color=3),
    "CONTROLE": dict(color=6),                      # superposition galvin
}


# ----------------------------------------------------------------------------
# Outils géométriques : contour = liste de (x, y, bulge)
# ----------------------------------------------------------------------------
def bulge(p0, p1, c, sens):
    """sens = +1 arc anti-horaire, -1 horaire (de p0 vers p1)."""
    a0 = math.atan2(p0[1] - c[1], p0[0] - c[0])
    a1 = math.atan2(p1[1] - c[1], p1[0] - c[0])
    da = (a1 - a0) % (2 * math.pi) if sens > 0 else -((a0 - a1) % (2 * math.pi))
    return math.tan(da / 4)


def patte_locale():
    """Profil de la patte dans un repère local : u le long du chant, v vers
    l'extérieur. Retourne [((u, v), centre_arc_suivant, sens)] du pied gauche
    jusqu'à la tête droite ; le pied droit est (+PATTE_COL, 0)."""
    cx, cy = PATTE_C_RACCORD
    return [((-PATTE_COL, 0.0), (cx, cy), -1),               # raccord R19,1
            ((-PATTE_R, PATTE_Y_TETE), (0.0, PATTE_Y_TETE), -1),  # tête R7
            ((PATTE_R, PATTE_Y_TETE), (-cx, cy), -1)]          # raccord R19,1


def contour_plateau():
    """Contour extérieur du flan inox (sens anti-horaire), avec pattes et
    dégagements d'angle. Retourne [(x, y, bulge)]."""
    pts = []

    def chant(depart, arrivee, pattes):
        (x0, y0), (x1, y1) = depart, arrivee
        long = math.hypot(x1 - x0, y1 - y0)
        d = ((x1 - x0) / long, (y1 - y0) / long)
        n = (d[1], -d[0])                       # normale extérieure (à droite)
        det = d[0] * n[1] - d[1] * n[0]         # -1 : repère local inversé
        pts.append((x0, y0, 0.0))
        abscisses = sorted((s - (x0 * abs(d[0]) + y0 * abs(d[1]))) * (d[0] + d[1])
                           for s in pattes)
        for t in abscisses:
            base = (x0 + d[0] * t, y0 + d[1] * t)
            monde = lambda u, v: (base[0] + d[0] * u + n[0] * v,
                                  base[1] + d[1] * u + n[1] * v)
            prof = patte_locale()
            suivants = [q for q, _, _ in prof[1:]] + [(PATTE_COL, 0.0)]
            for ((u, v), c, sens), q in zip(prof, suivants):
                p0, p1, cw = monde(u, v), monde(*q), monde(*c)
                pts.append((p0[0], p0[1], bulge(p0, p1, cw, sens * det)))
            pts.append((*monde(PATTE_COL, 0.0), 0.0))

    fx, fy, cx, cy = FLAN_X, FLAN_Y, COIN_X, COIN_Y
    chant((-cx, -fy), (cx, -fy), PATTES_GRAND_COTE)      # bas, vers +x
    pts += [(cx, -fy, 0.0), (cx, -cy, 0.0)]
    chant((fx, -cy), (fx, cy), PATTES_PETIT_COTE)        # droite, vers +y
    pts += [(fx, cy, 0.0), (cx, cy, 0.0)]
    chant((cx, fy), (-cx, fy), PATTES_GRAND_COTE)        # haut, vers -x
    pts += [(-cx, fy, 0.0), (-cx, cy, 0.0)]
    chant((-fx, cy), (-fx, -cy), PATTES_PETIT_COTE)      # gauche, vers -y
    pts += [(-fx, -cy, 0.0), (-cx, -cy, 0.0)]
    propre = []
    for p in pts:                                       # doublons consécutifs
        if propre and math.dist(p[:2], propre[-1][:2]) < 1e-9:
            continue
        propre.append(p)
    if math.dist(propre[0][:2], propre[-1][:2]) < 1e-9:
        propre.pop()
    return propre


def trous_pattes_flan():
    """Centres des trous Ø3,2 des pattes sur le flan."""
    v = FLANC + PATTE_TROU_Y
    t = [(s, -(AXE_Y + v)) for s in PATTES_GRAND_COTE]
    t += [(s, AXE_Y + v) for s in PATTES_GRAND_COTE]
    t += [(AXE_X + v, s) for s in PATTES_PETIT_COTE]
    t += [(-(AXE_X + v), s) for s in PATTES_PETIT_COTE]
    return t


def trous_pattes_galvin():
    """Position des trous de pattes une fois repliées (repère assemblage)."""
    dy = W_EXT / 2 - PATTE_TROU_APRES_PLI
    dx = L_EXT / 2 - PATTE_TROU_APRES_PLI
    t = [(s, -dy) for s in PATTES_GRAND_COTE] + [(s, dy) for s in PATTES_GRAND_COTE]
    t += [(dx, s) for s in PATTES_PETIT_COTE] + [(-dx, s) for s in PATTES_PETIT_COTE]
    return t


def oblong(cx, cy):
    """Oblong 6 x 4 orienté selon X, contour fermé à bulges."""
    r = OBLONG_W / 2
    a = OBLONG_L / 2 - r
    return [(cx - a, cy - r, 0.0), (cx + a, cy - r, 1.0),
            (cx + a, cy + r, 0.0), (cx - a, cy + r, 1.0)]


def lire_suspensions():
    """Points de suspension et hauteur du haut des boîtes, depuis le modèle 3D.
    Retourne [(n°, x, y, z_haut_boite)] en repère centré, numérotés le long
    de la double hélice (du plus haut au plus bas)."""
    doc = ezdxf.readfile(MODELE_3D)
    pts = []
    for e in doc.modelspace().query("LINE"):
        s, f = e.dxf.start, e.dxf.end
        pts.append((round(s.x - L_EXT / 2, 3), round(s.y - W_EXT / 2, 3), min(s.z, f.z)))
    pts.sort(key=lambda p: (-p[2], p[0]))
    return [(i + 1, *p) for i, p in enumerate(pts)]


# ----------------------------------------------------------------------------
def nouveau_doc():
    doc = ezdxf.new("R2010", setup=True)
    doc.units = ezdxf.units.MM
    doc.header["$INSUNITS"] = 4
    doc.header["$MEASUREMENT"] = 1
    for nom, att in LAYERS.items():
        doc.layers.add(nom, **att)
    return doc


def dessiner_plateau(msp, ox=0.0, oy=0.0, suspensions=(), annoter=False):
    D = {"layer": "DECOUPE"}
    contour = [(x + ox, y + oy, b) for x, y, b in contour_plateau()]
    msp.add_lwpolyline(contour, format="xyb", close=True, dxfattribs=D)
    for _, x, y, _ in suspensions:
        msp.add_lwpolyline(oblong(x + ox, y + oy), format="xyb", close=True, dxfattribs=D)
    for x, y in POINTS_ECROUS:
        msp.add_circle((x + ox, y + oy), D_TROU_INOX / 2, dxfattribs=D)
    for x, y in trous_pattes_flan():
        msp.add_circle((x + ox, y + oy), PATTE_TROU_D / 2, dxfattribs=D)
    P = {"layer": "PLIAGE"}
    # plis du fond (90° vers le haut)
    for s in (-1, 1):
        msp.add_line((-COIN_X + ox, s * AXE_Y + oy), (COIN_X + ox, s * AXE_Y + oy), dxfattribs=P)
        msp.add_line((s * AXE_X + ox, -COIN_Y + oy), (s * AXE_X + ox, COIN_Y + oy), dxfattribs=P)
    # plis des pattes (90° vers l'intérieur), au pied de chaque patte
    for s in PATTES_GRAND_COTE:
        for sy in (-1, 1):
            msp.add_line((s - PATTE_COL + ox, sy * FLAN_Y + oy),
                         (s + PATTE_COL + ox, sy * FLAN_Y + oy), dxfattribs=P)
    for s in PATTES_PETIT_COTE:
        for sx in (-1, 1):
            msp.add_line((sx * FLAN_X + ox, s - PATTE_COL + oy),
                         (sx * FLAN_X + ox, s + PATTE_COL + oy), dxfattribs=P)
    if annoter:
        T = {"layer": "TEXTE"}
        for n, x, y, z in suspensions:
            msp.add_text(f"{n}", height=7, dxfattribs=T).set_placement(
                (x + ox, y + oy + 9), align=TextEntityAlignment.BOTTOM_CENTER)
            msp.add_text(f"{abs(z) - H_CEINTURE:.0f}", height=4.5, dxfattribs=T).set_placement(
                (x + ox, y + oy - 8), align=TextEntityAlignment.TOP_CENTER)


def dessiner_galvin(msp, ox=0.0, oy=0.0, layer="DECOUPE"):
    D = {"layer": layer}
    hx, hy, r = G_L / 2, G_W / 2, G_RAYON_COIN
    b = math.tan(math.pi / 8)  # quart de cercle anti-horaire
    contour = [(-hx + r, -hy, 0), (hx - r, -hy, b), (hx, -hy + r, 0), (hx, hy - r, b),
               (hx - r, hy, 0), (-hx + r, hy, b), (-hx, hy - r, 0), (-hx, -hy + r, b)]
    msp.add_lwpolyline([(x + ox, y + oy, bb) for x, y, bb in contour],
                       format="xyb", close=True, dxfattribs=D)
    msp.add_circle((ox, oy), D_CENTRAL / 2, dxfattribs=D)
    for x, y in POINTS_ECROUS:
        msp.add_circle((x + ox, y + oy), R_TROU_GALVIN, dxfattribs=D)
    for x, y in trous_pattes_galvin():
        msp.add_circle((x + ox, y + oy), D_TROU_PATTE_GALVIN / 2, dxfattribs=D)


# ----------------------------------------------------------------------------
def verifications(suspensions):
    msgs = []
    # 1. superposition écrous inox / galvin (même repère centré)
    msgs.append(f"Trous écrous : {len(POINTS_ECROUS)} x Ø{D_TROU_INOX:g} inox "
                f"concentriques aux {len(POINTS_ECROUS)} x R{R_TROU_GALVIN:g} galvin : OK")
    # 2. tous les trous dans le fond, loin des plis
    lim_x, lim_y = AXE_X - BA / 2, AXE_Y - BA / 2
    trous = [(x, y, OBLONG_L / 2) for _, x, y, _ in suspensions]
    trous += [(x, y, D_TROU_INOX / 2) for x, y in POINTS_ECROUS]
    marge = min(min(lim_x - abs(x) - r, lim_y - abs(y) - r) for x, y, r in trous)
    assert marge > 20, marge
    msgs.append(f"Distance mini trou -> début de pli : {marge:.1f} mm : OK")
    # 3. distance entre trous
    dmin = min(math.dist(a[:2], b[:2]) - a[2] - b[2]
               for i, a in enumerate(trous) for b in trous[i + 1:])
    assert dmin > 50, dmin
    msgs.append(f"Matière mini entre deux trous du fond : {dmin:.1f} mm : OK")
    # 4. trous de pattes sur le galvin
    hx, hy = G_L / 2, G_W / 2
    for x, y in trous_pattes_galvin():
        bord = min(hx - abs(x), hy - abs(y))
        assert bord > D_TROU_PATTE_GALVIN, bord
    msgs.append(f"Trous de pattes galvin à {L_EXT / 2 - PATTE_TROU_APRES_PLI - 0:.3f} / "
                f"{W_EXT / 2 - PATTE_TROU_APRES_PLI:.3f} du centre, "
                f"soit {G_L / 2 - (L_EXT / 2 - PATTE_TROU_APRES_PLI):.2f} mm du bord du galvin : OK")
    # 5. trous galvin non chevauchants
    tg = [(0, 0, D_CENTRAL / 2)] + [(x, y, R_TROU_GALVIN) for x, y in POINTS_ECROUS]
    dming = min(math.dist(a[:2], b[:2]) - a[2] - b[2] for i, a in enumerate(tg) for b in tg[i + 1:])
    assert dming > 50
    msgs.append(f"Matière mini entre trous du galvin : {dming:.1f} mm : OK")
    return msgs


def main():
    os.makedirs(DOSSIER, exist_ok=True)
    susp = lire_suspensions()
    assert len(susp) == 30

    # --- 01 plateau inox, fichier laser seul -----------------------------
    doc = nouveau_doc()
    dessiner_plateau(doc.modelspace(), suspensions=susp)
    doc.saveas(f"{DOSSIER}/01-plateau-inox-1mm.dxf")

    # --- 02 galvin, fichier laser seul ----------------------------------
    doc = nouveau_doc()
    dessiner_galvin(doc.modelspace())
    doc.saveas(f"{DOSSIER}/02-galvin-1.5mm.dxf")

    # --- 00 dossier complet : pièces annotées + contrôle + nomenclature --
    doc = nouveau_doc()
    msp = doc.modelspace()
    T = {"layer": "TEXTE"}
    gx = FLAN_X * 2 + 250                       # décalage galvin
    dessiner_plateau(msp, suspensions=susp, annoter=True)
    dessiner_galvin(msp, ox=gx)
    # contrôle : galvin superposé au plateau (repère assemblage)
    cy = -(FLAN_Y * 2 + 300)
    dessiner_plateau(msp, oy=cy, suspensions=susp)
    dessiner_galvin(msp, oy=cy, layer="CONTROLE")
    # cotes principales
    dim = {"layer": "COTATION"}
    for (p1, p2, base, ang) in [
        ((-FLAN_X, FLAN_Y), (FLAN_X, FLAN_Y), (0, FLAN_Y + 60), 0),
        ((-FLAN_X, -FLAN_Y), (-FLAN_X, FLAN_Y), (-FLAN_X - 60, 0), 90),
        ((-AXE_X, -FLAN_Y), (AXE_X, -FLAN_Y), (0, -FLAN_Y - 60), 0),
        ((gx - G_L / 2, G_W / 2), (gx + G_L / 2, G_W / 2), (gx, G_W / 2 + 60), 0),
        ((gx - G_L / 2, -G_W / 2), (gx - G_L / 2, G_W / 2), (gx - G_L / 2 - 60, 0), 90),
    ]:
        cote = math.dist(p1, p2)
        d = msp.add_linear_dim(base=base, p1=p1, p2=p2, angle=ang,
                               text=f"{cote:.2f}".rstrip("0").rstrip("."),
                               override={"dimtxt": 14, "dimasz": 10},
                               dxfattribs=dim)
        d.render()
    titres = [
        ((0, FLAN_Y + 130), f"01 - PLATEAU INOX ep. {T_INOX:g} mm - Qté 1 - "
                            f"flan {2 * FLAN_X:.2f} x {2 * FLAN_Y:.2f} (hors pattes)"),
        ((gx, G_W / 2 + 130), f"02 - GALVIN ep. {T_GALVIN:g} mm - Qté 1 - {G_L:g} x {G_W:g}"),
        ((0, cy + FLAN_Y + 80), "CONTROLE : galvin (magenta) posé sur le plateau - "
                                "Ø10,4 galvin centrés sur Ø6 inox, Ø4 galvin sous les pattes repliées"),
    ]
    for p, txt in titres:
        msp.add_text(txt, height=22, dxfattribs=T).set_placement(
            p, align=TextEntityAlignment.BOTTOM_CENTER)
    msp.add_text("n° de trou (haut) / longueur de câble visible en mm (bas)", height=12,
                 dxfattribs=T).set_placement((0, -FLAN_Y - 120), align=TextEntityAlignment.TOP_CENTER)

    # nomenclature + table des câbles
    lignes = [
        "NOMENCLATURE - LUSTRE SPIRALE 1200 x 800 x H3500 - 30 BOITES",
        "",
        f"01  Plateau inox {T_INOX:g} mm (laser + pliage)   x1",
        f"      fond 1200 x 800, ceinture {H_CEINTURE:g} mm pliée à 90° vers le haut",
        f"      {len(PATTES_GRAND_COTE) * 2 + len(PATTES_PETIT_COTE) * 2} pattes repliées à 90° vers l'intérieur",
        f"      30 oblongs {OBLONG_L:g}x{OBLONG_W:g} (fils) - 6 trous Ø{D_TROU_INOX:g} (écrous) - "
        f"{len(trous_pattes_flan())} trous Ø{PATTE_TROU_D:g} (pattes)",
        f"02  Galvin {T_GALVIN:g} mm (laser)   x1   {G_L:g} x {G_W:g}, coins R{G_RAYON_COIN:g}",
        f"      1 trou Ø{D_CENTRAL:g} central - 6 trous Ø{2 * R_TROU_GALVIN:g} - "
        f"{len(trous_pattes_galvin())} trous Ø{D_TROU_PATTE_GALVIN:g}",
        "03  Boîte (modèle 1750-1 : cylindre Ø50 x 65 + 7 profilés 611+2020)   x30",
        "04  Câble électrique de suspension   x30 (longueurs ci-dessous)",
        "05  Vis M6 + écrou + entretoise ~27,5 mm (fond inox -> galvin)   x6",
        f"06  Vis M3 + écrou (pattes -> galvin)   x{len(trous_pattes_galvin())}",
        "",
        f"Pliage : r int {R_INT:g}, K {K}, déduction {BD:.2f} mm/pli - "
        f"axe de pli à {DEPORT:.3f} de la cote extérieure",
        "",
        "CABLES (longueur visible sous le plateau, du fond inox au haut de la boîte)",
        "n°   X      Y      longueur",
    ]
    for n, x, y, z in susp:
        lignes.append(f"{n:<4} {x:>6.0f} {y:>6.0f}   {abs(z) - H_CEINTURE:>7.1f}")
    lignes.append("(prévoir la surlongueur de raccordement au-dessus du plateau)")
    msp.add_mtext("\\P".join(lignes), dxfattribs={"layer": "TEXTE", "char_height": 14}).set_location(
        (gx - G_L / 2, cy + FLAN_Y), attachment_point=1)
    doc.saveas(f"{DOSSIER}/00-dossier-fabrication.dxf")

    for m in verifications(susp):
        print(m)
    print(f"BD={BD:.3f} BA={BA:.3f} DEPORT={DEPORT:.3f} flan={2 * FLAN_X:.3f} x {2 * FLAN_Y:.3f}")
    return susp


if __name__ == "__main__":
    main()
