"""Génère un lustre « spirale double hélice » à partir du DXF source 725-2536.

Principe repris du modèle d'origine (pavillon 800x800, 36 boîtes) :
  - les boîtes sont suspendues sur une grille régulière sous le pavillon ;
  - chaque anneau de la grille (extérieur -> intérieur -> centre) est découpé
    en deux demi-spirales symétriques (rotation 180°) qui descendent en
    continu : on obtient un vortex en double hélice, haut sur les bords et
    profond au centre.

Nouvelle version : pavillon 1200 x 800 mm, hauteur totale 3500 mm
(plafond -> bas de la boîte la plus basse), 30 boîtes sur une grille 6 x 5.
Le pas vertical diminue en descendant (progression géométrique) pour que
les boîtes soient plus concentrées en bas.

Usage : python3 scripts/generer_lustre_spirale.py [source.dxf] [sortie.dxf]
"""
import sys

import ezdxf
from ezdxf import bbox
from ezdxf.math import Matrix44

SRC = sys.argv[1] if len(sys.argv) > 1 else "sources/725-2536-sspyramides3D.dxf"
OUT = sys.argv[2] if len(sys.argv) > 2 else "lustres/lustre-spirale-1200x800-H3500-30boites.dxf"

# --- Paramètres -------------------------------------------------------------
LONGUEUR, LARGEUR = 1200.0, 800.0      # pavillon (mm)
EPAISSEUR_PAVILLON = 40.0
HAUTEUR_TOTALE = 3500.0                # plafond -> bas de la boîte la plus basse
NX, NY = 6, 5                          # 30 points de suspension
MARGE = 60.0                           # marge bord pavillon -> axe des câbles
PREMIER_NIVEAU = 450.0                 # plafond -> haut de la boîte la plus haute
RAPPORT_PAS = 3.0                      # pas du haut / pas du bas (concentration en bas)
ARRONDI = 5.0                          # cotes arrondies à 5 mm

# Point d'accroche d'une boîte dans le DXF source (bout de câble, haut du cylindre)
REF_SOURCE = (6762.193687281992, 1705.803228413862, -1420.0)


def construire_bloc_boite(doc):
    """Crée le bloc nommé BOITE (origine = point d'accroche du câble).

    Les boîtes du fichier source sont des blocs anonymes (*U37 / *U39) ;
    on les éclate d'un niveau pour ne garder que des blocs nommés
    (611+2020 pour les profilés, lignes + cercles pour le cylindre).
    """
    msp = doc.modelspace()
    sx, sy, sz = REF_SOURCE
    cible = [
        e for e in msp
        if e.dxftype() == "INSERT" and e.dxf.name in ("*U37", "*U39")
    ]
    assert len(cible) == 2, "boîte de référence introuvable dans le DXF source"
    retour = Matrix44.translate(-sx, -sy, -sz)
    bloc = doc.blocks.new("BOITE")
    for ins in cible:
        for e in ins.virtual_entities():           # *U36 / *U38 en WCS
            sous = list(e.virtual_entities()) if e.dxftype() == "INSERT" else [e]
            for s in sous:                          # 611+2020 / LINE en WCS
                s = s.copy()
                s.transform(retour)
                bloc.add_entity(s)
    for z in (0.0, -65.0):                          # cercles du cylindre Ø50
        bloc.add_circle((0, 0, z), 25.0)
    return bloc


def construire_bloc_pavillon(doc):
    nom = f"P{int(LONGUEUR)}-{int(LARGEUR)}"
    bloc = doc.blocks.new(nom)
    rect = [(0, 0), (LONGUEUR, 0), (LONGUEUR, LARGEUR), (0, LARGEUR)]
    for z in (0.0, EPAISSEUR_PAVILLON):
        bloc.add_lwpolyline(rect, close=True, dxfattribs={"elevation": z})
    for x, y in rect:
        bloc.add_line((x, y, 0), (x, y, EPAISSEUR_PAVILLON))
    return nom


def anneau(x0, y0, x1, y1):
    """Cellules d'un anneau rectangulaire, en partant du coin (x0, y0),
    en montant la colonne gauche puis en suivant la rangée du haut
    (même sens que le lustre source)."""
    if x0 == x1 or y0 == y1:                      # anneau dégénéré (centre)
        return [(x, y) for x in range(x0, x1 + 1) for y in range(y0, y1 + 1)]
    cells = [(x0, y) for y in range(y0, y1 + 1)]
    cells += [(x, y1) for x in range(x0 + 1, x1 + 1)]
    cells += [(x1, y) for y in range(y1 - 1, y0 - 1, -1)]
    cells += [(x, y0) for x in range(x1 - 1, x0, -1)]
    return cells


def double_helice():
    """Retourne la liste ordonnée [(niveau, (ix, iy)), ...] des 30 boîtes."""
    sequence = []
    x0, y0, x1, y1 = 0, 0, NX - 1, NY - 1
    niveau = 0
    while x0 <= x1 and y0 <= y1:
        cells = anneau(x0, y0, x1, y1)
        demi = len(cells) // 2
        for k in range(demi):
            a = cells[k]
            b = (NX - 1 - a[0], NY - 1 - a[1])      # symétrique à 180°
            sequence += [(niveau + k, a), (niveau + k, b)]
        niveau += demi
        x0, y0, x1, y1 = x0 + 1, y0 + 1, x1 - 1, y1 - 1
    return sequence, niveau


def cotes_niveaux(n_niveaux, hauteur_boite):
    """Hauteurs (z du haut de boîte) avec un pas qui décroît géométriquement."""
    z_haut = -PREMIER_NIVEAU
    z_bas = -(HAUTEUR_TOTALE - hauteur_boite)
    n_pas = n_niveaux - 1
    r = (1.0 / RAPPORT_PAS) ** (1.0 / (n_pas - 1))
    pas = [r ** k for k in range(n_pas)]
    echelle = (z_haut - z_bas) / sum(pas)
    z, cotes = z_haut, [z_haut]
    for p in pas:
        z -= p * echelle
        cotes.append(z)
    cotes = [round(c / ARRONDI) * ARRONDI for c in cotes[:-1]] + [z_bas]
    return cotes


def main():
    doc = ezdxf.readfile(SRC)
    msp = doc.modelspace()
    bloc = construire_bloc_boite(doc)

    # Hauteur réelle d'une boîte (≈ 233 mm) mesurée sur la géométrie éclatée
    tmp = msp.add_blockref("BOITE", (0, 0, 0))
    hb = -bbox.extents([tmp]).extmin.z
    msp.delete_entity(tmp)

    # Vide l'espace objet du modèle source
    for e in list(msp):
        msp.delete_entity(e)
    # Supprime les blocs anonymes / blocs du modèle source devenus inutiles
    for nom in ["1750-1", "Pyramid15+Lamp", "LG4+PD", "Lampe G4 LED", "P725-80"]:
        if nom in doc.blocks:
            doc.blocks.delete_block(nom, safe=False)
    for b in list(doc.blocks):
        if b.name.startswith("*U"):
            doc.blocks.delete_block(b.name, safe=False)

    pavillon = construire_bloc_pavillon(doc)
    msp.add_blockref(pavillon, (0, 0, -EPAISSEUR_PAVILLON))

    sequence, n_niveaux = double_helice()
    assert len(sequence) == NX * NY
    cotes = cotes_niveaux(n_niveaux, hb)
    px = (LONGUEUR - 2 * MARGE) / (NX - 1)
    py = (LARGEUR - 2 * MARGE) / (NY - 1)

    print(f"Hauteur boîte : {hb:.1f} mm — pas grille {px:.1f} x {py:.1f} mm")
    print("Niveau | haut boîte (mm) | pas | cellules")
    for niv in range(n_niveaux):
        cells = [c for n, c in sequence if n == niv]
        pas = "" if niv == 0 else f"{cotes[niv - 1] - cotes[niv]:.0f}"
        print(f"{niv:6d} | {cotes[niv]:15.1f} | {pas:>4} | {cells}")

    for niv, (ix, iy) in sequence:
        x, y, z = MARGE + ix * px, MARGE + iy * py, cotes[niv]
        msp.add_line((x, y, -EPAISSEUR_PAVILLON), (x, y, z))   # câble
        msp.add_blockref("BOITE", (x, y, z))

    doc.header["$INSUNITS"] = 4  # mm
    doc.audit()  # nettoie les objets de blocs dynamiques orphelins
    doc.saveas(OUT)
    print(f"Écrit : {OUT}")


if __name__ == "__main__":
    main()
