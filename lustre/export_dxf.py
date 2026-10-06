#!/usr/bin/env python3
"""Export AutoCAD (DXF R2018, unités = mm) à partir de suspensions.csv.

  lustre_plan.dxf  plan 2D coté du plateau (trous, repères, longueurs de fil)
  lustre_3d.dxf    modèle 3D : plateau, fils et suspensions (cylindres génériques)
  lustre_3d_suspension5.dxf  modèle 3D avec la suspension réelle (suspension5.dxf en bloc)
  lustre_3d.lsp    AutoLISP : construit le lustre 3D dans AutoCAD avec VOTRE suspension
                   (suspension5.dwg insérée comme bloc à chaque point, à la bonne hauteur)

Ouvrir dans AutoCAD puis SAUVEGARDER SOUS (ENREGSOUS / SAVEAS) au format .dwg.
Dépendance : pip install ezdxf
"""
import csv
import math
import unicodedata
import os

import ezdxf
from ezdxf.render import forms
from ezdxf.math import Matrix44

HERE = os.path.dirname(os.path.abspath(__file__))
W, H = 3000, 2400                 # plateau (mm)
SUSP_D, SUSP_H = 50, 240          # suspension Ø 5 cm x 24 cm
CAP_H = 50                        # culot métallique en haut de la suspension
HOLE_D = 8                        # Ø de perçage indicatif pour le passage du fil
PLATE_T = 30                      # épaisseur indicative du plateau (vue 3D)


def load():
    with open(os.path.join(HERE, "suspensions.csv"), encoding="utf-8") as f:
        rows = list(csv.DictReader(f, delimiter=";"))
    return [{"id": r["repere"], "x": float(r["x_cm"]) * 10, "y": float(r["y_cm"]) * 10,
             "fil": int(r["fil_cm"]) * 10} for r in rows]


def new_doc(layers):
    doc = ezdxf.new("R2018", setup=True)
    doc.units = ezdxf.units.MM
    doc.header["$INSUNITS"] = 4
    doc.header["$MEASUREMENT"] = 1
    for name, color in layers:
        doc.layers.add(name, color=color)
    return doc


def aci_for(fil, fmin, fmax):
    # 5 classes de longueur -> couleurs AutoCAD distinctes (court = jaune ... long = rouge)
    classes = [2, 40, 30, 20, 1]
    t = (fil - fmin) / max(1, fmax - fmin)
    return classes[min(4, int(t * 5))]


def plan(rows):
    doc = new_doc([("PLATEAU", 7), ("GRILLE_100", 8), ("PERCAGES", 1), ("EMPRISE_SUSPENSION", 3),
                   ("REPERES", 5), ("LONGUEURS_FIL", 7), ("COTES", 4), ("CARTOUCHE", 7)])
    msp = doc.modelspace()
    fmin, fmax = min(r["fil"] for r in rows), max(r["fil"] for r in rows)

    msp.add_lwpolyline([(0, 0), (W, 0), (W, H), (0, H)], close=True, dxfattribs={"layer": "PLATEAU", "lineweight": 50})
    for x in range(100, W, 100):
        msp.add_line((x, 0), (x, H), dxfattribs={"layer": "GRILLE_100"})
    for y in range(100, H, 100):
        msp.add_line((0, y), (W, y), dxfattribs={"layer": "GRILLE_100"})

    for r in rows:
        c = (r["x"], r["y"])
        msp.add_circle(c, HOLE_D / 2, dxfattribs={"layer": "PERCAGES"})
        msp.add_point(c, dxfattribs={"layer": "PERCAGES"})
        msp.add_circle(c, SUSP_D / 2, dxfattribs={"layer": "EMPRISE_SUSPENSION", "color": aci_for(r["fil"], fmin, fmax)})
        msp.add_text(r["id"], height=11, dxfattribs={"layer": "REPERES"}).set_placement(
            (c[0], c[1] + 30), align=ezdxf.enums.TextEntityAlignment.BOTTOM_CENTER)
        msp.add_text(f'{r["fil"] / 10:g}', height=15, dxfattribs={"layer": "LONGUEURS_FIL"}).set_placement(
            (c[0], c[1] - 30), align=ezdxf.enums.TextEntityAlignment.TOP_CENTER)

    ds = {"dimtxt": 40, "dimasz": 30, "dimexo": 10, "dimdec": 0, "dimlfac": 1, "dimdsep": ord(",")}
    def dim(p1, p2, base, angle=0):
        msp.add_linear_dim(base=base, p1=p1, p2=p2, angle=angle, dimstyle="EZDXF",
                           override=ds, dxfattribs={"layer": "COTES"}).render()
    xs = sorted({r["x"] for r in rows}); ys = sorted({r["y"] for r in rows})
    dim((0, H), (W, H), (0, H + 300))                         # 3000
    dim((0, 0), (0, H), (-300, 0), angle=90)                  # 2400
    dim((0, H), (xs[0], H), (0, H + 150))                     # pourtour gauche
    dim((xs[-1], H), (W, H), (0, H + 150))                    # pourtour droit
    dim((0, 0), (0, ys[0]), (-150, 0), angle=90)              # pourtour bas
    dim((0, ys[-1]), (0, H), (-150, 0), angle=90)             # pourtour haut
    top = [r for r in rows if r["y"] == ys[-1]]
    dim((top[0]["x"], ys[-1]), (top[1]["x"], ys[-1]), (0, H + 150))   # pas 200 en x
    a = top[0]; b = next(r for r in rows if r["y"] == ys[-2] and r["x"] == a["x"] + 100)
    msp.add_aligned_dim(p1=(a["x"], a["y"]), p2=(b["x"], b["y"]), distance=-120, dimstyle="EZDXF",
                        override={**ds, "dimdec": 1}, dxfattribs={"layer": "COTES"}).render()
    col = [r for r in rows if r["x"] == xs[0]]
    col.sort(key=lambda r: -r["y"])
    dim((xs[0], col[0]["y"]), (xs[0], col[1]["y"]), (-150, 0), angle=90)  # pas 200 en y

    rows_y = sorted({(r["y"], r["id"][0]) for r in rows}, reverse=True)
    for y, letter in rows_y:
        msp.add_text(letter, height=30, dxfattribs={"layer": "REPERES"}).set_placement(
            (W + 60, y), align=ezdxf.enums.TextEntityAlignment.MIDDLE_LEFT)

    msp.add_mtext(
        f"LUSTRE CASCADE - PLATEAU {W/1000:.2f} x {H/1000:.2f} m - {len(rows)} SUSPENSIONS (VUE DE DESSOUS)\\P"
        "Trous en quinconce : 200 mm en rangée et en colonne, 141,4 mm en diagonale. Unités : mm.\\P"
        "Origine (0,0) = coin bas-gauche. Repère = lettre de rangée + n° de gauche à droite.\\P"
        f"Sous chaque trou : longueur de fil en cm, du plateau au haut de la suspension "
        f"({fmin/10:g} à {fmax/10:g} cm), hors réserve de fixation.",
        dxfattribs={"layer": "CARTOUCHE", "char_height": 45, "width": 3000}).set_location((0, -250))
    doc.saveas(os.path.join(HERE, "lustre_plan.dxf"))


def model3d(rows):
    doc = new_doc([("PLATEAU", 8), ("FILS", 9), ("CULOTS", 40), ("SUSPENSIONS", 51)])
    msp = doc.modelspace()
    plate = forms.cube().scale(W, H, PLATE_T).translate(W / 2, H / 2, PLATE_T / 2)
    plate.render_mesh(msp, dxfattribs={"layer": "PLATEAU"})
    body = forms.cylinder(count=16, radius=SUSP_D / 2, top_center=(0, 0, SUSP_H - CAP_H))
    cap = forms.cylinder(count=16, radius=SUSP_D / 2 - 2, top_center=(0, 0, CAP_H))
    for r in rows:
        x, y, top = r["x"], r["y"], -r["fil"]
        msp.add_line((x, y, 0), (x, y, top), dxfattribs={"layer": "FILS"})
        cap.copy().translate(x, y, top - CAP_H).render_mesh(msp, dxfattribs={"layer": "CULOTS"})
        body.copy().translate(x, y, top - SUSP_H).render_mesh(msp, dxfattribs={"layer": "SUSPENSIONS"})
    doc.set_modelspace_vport(height=8000, center=(W / 2, -3000))
    doc.saveas(os.path.join(HERE, "lustre_3d.dxf"))


def suspension_block(doc, path):
    """Copie suspension5.dxf dans un bloc SUSPENSION5 : axe vertical, origine = centre du sommet."""
    from ezdxf.addons import Importer
    from ezdxf import bbox
    src = ezdxf.readfile(path)
    ext = bbox.extents(src.modelspace())
    lo, hi = ext.extmin, ext.extmax
    size = hi - lo
    axis = max(range(3), key=lambda k: size[k])        # axe le plus long = axe de la suspension
    c = (lo + hi) / 2
    top = [c.x, c.y, c.z]; top[axis] = hi[axis]          # culot en haut (coordonnée max)
    m = Matrix44.translate(-top[0], -top[1], -top[2])
    if axis == 1:
        m @= Matrix44.x_rotate(math.pi / 2)              # +Y -> +Z
    elif axis == 0:
        m @= Matrix44.y_rotate(-math.pi / 2)             # +X -> +Z
    blk = doc.blocks.new("SUSPENSION5")
    imp = Importer(src, doc)
    imp.import_entities(src.modelspace(), blk)
    imp.finalize()
    for e in blk:
        e.transform(m)
    return size[axis], max(size[k] for k in range(3) if k != axis)


def model3d_real(rows, path):
    doc = new_doc([("PLATEAU", 8), ("FILS", 9), ("SUSPENSIONS", 51)])
    h, d = suspension_block(doc, path)
    msp = doc.modelspace()
    plate = forms.cube().scale(W, H, PLATE_T).translate(W / 2, H / 2, PLATE_T / 2)
    plate.render_mesh(msp, dxfattribs={"layer": "PLATEAU"})
    for r in rows:
        x, y, top = r["x"], r["y"], -r["fil"]
        msp.add_line((x, y, 0), (x, y, top), dxfattribs={"layer": "FILS"})
        msp.add_blockref("SUSPENSION5", (x, y, top), dxfattribs={"layer": "SUSPENSIONS"})
    doc.set_modelspace_vport(height=8000, center=(W / 2, -3000))
    doc.saveas(os.path.join(HERE, "lustre_3d_suspension5.dxf"))
    return h, d


LISP = r""";;; LUSTRE3D - construit le lustre cascade dans AutoCAD avec la suspension fournie.
;;; Utilisation : APPLOAD -> lustre_3d.lsp, puis taper LUSTRE3D dans un dessin vide (unités mm).
;;; Le fichier suspension5.dwg est cherché dans le dossier de ce .lsp, sinon il est demandé.
;;; La suspension est accrochée par le CENTRE DE SON SOMMET au bout de chaque fil.
;;; Mettre *LUSTRE-FLIP* a T si la suspension apparait la tete en bas.
(vl-load-com)
(setq *LUSTRE-FLIP* nil)
(setq *LUSTRE-DIR* (if (findfile "lustre_3d.lsp") (vl-filename-directory (findfile "lustre_3d.lsp")) ""))
;;; (repere x y fil) en mm - origine coin bas-gauche du plateau, fil = plateau -> haut de la suspension
(setq *LUSTRE-PTS* '(
__PTS__
))

(defun lustre:bbox (obj / mn mx)
  (vla-GetBoundingBox obj 'mn 'mx)
  (list (vlax-safearray->list mn) (vlax-safearray->list mx)))

(defun lustre:layer (name col / lay)
  (setq lay (vla-Add (vla-get-Layers (vla-get-ActiveDocument (vlax-get-acad-object))) name))
  (vla-put-Color lay col) name)

(defun c:LUSTRE3D (/ doc ms path ref bb ext h s top n line box base obj)
  (setq doc (vla-get-ActiveDocument (vlax-get-acad-object))
        ms  (vla-get-ModelSpace doc))
  (setq path (findfile (strcat *LUSTRE-DIR* "\\suspension5.dwg")))
  (if (not path) (setq path (findfile "suspension5.dwg")))
  (if (not path) (setq path (getfiled "Choisir le fichier de la suspension" "" "dwg" 0)))
  (if (not path) (progn (princ "\nAucune suspension choisie.") (exit)))
  (setvar "INSUNITS" 4)
  (lustre:layer "PLATEAU" 8) (lustre:layer "FILS" 9) (lustre:layer "SUSPENSIONS" 0)
  ;; 1. Gabarit : insertion du DWG comme bloc, mise a la verticale et a l'echelle
  (setq ref (vla-InsertBlock ms (vlax-3d-point 0 0 0) path 1.0 1.0 1.0 0.0))
  (setq bb (lustre:bbox ref)
        ext (mapcar '- (cadr bb) (car bb)))
  (cond ((and (> (cadr ext) (caddr ext)) (> (cadr ext) (car ext)))
         (vla-Rotate3D ref (vlax-3d-point 0 0 0) (vlax-3d-point 1 0 0) (/ pi 2)))
        ((and (> (car ext) (caddr ext)) (> (car ext) (cadr ext)))
         (vla-Rotate3D ref (vlax-3d-point 0 0 0) (vlax-3d-point 0 1 0) (/ pi 2))))
  (if *LUSTRE-FLIP* (vla-Rotate3D ref (vlax-3d-point 0 0 0) (vlax-3d-point 1 0 0) pi))
  (setq bb (lustre:bbox ref) h (- (caddr (cadr bb)) (caddr (car bb))))
  ;; detection des unites du fichier suspension (hauteur attendue 240 mm)
  (setq s (cond ((and (> h 150.0) (< h 400.0)) 1.0)
                ((and (> h 15.0) (< h 40.0)) 10.0)
                ((and (> h 1.5) (< h 4.0)) 100.0)
                ((and (> h 0.15) (< h 0.4)) 1000.0)
                (T (/ __SUSP_H__ h))))
  (if (/= s 1.0) (vla-ScaleEntity ref (vlax-3d-point 0 0 0) s))
  (setq bb (lustre:bbox ref)
        top (list (/ (+ (car (car bb)) (car (cadr bb))) 2.0)
                  (/ (+ (cadr (car bb)) (cadr (cadr bb))) 2.0)
                  (caddr (cadr bb))))
  (princ (strcat "\nSuspension : hauteur " (rtos (* h s) 2 1) " mm (echelle x" (rtos s 2 0) ")"))
  ;; 2. Plateau
  (setq box (vla-AddBox ms (vlax-3d-point (/ __W__ 2.0) (/ __H__ 2.0) (/ __T__ 2.0)) __W__ __H__ __T__))
  (vla-put-Layer box "PLATEAU")
  ;; 3. Fils + suspensions
  (setq n 0)
  (foreach p *LUSTRE-PTS*
    (setq base (list (cadr p) (caddr p) (- (cadddr p))))
    (setq line (vla-AddLine ms (vlax-3d-point (cadr p) (caddr p) 0.0) (vlax-3d-point base)))
    (vla-put-Layer line "FILS")
    (setq obj (vla-Copy ref))
    (vla-Move obj (vlax-3d-point top) (vlax-3d-point base))
    (vla-put-Layer obj "SUSPENSIONS")
    (setq n (1+ n)))
  (vla-Delete ref)
  (command "_.-VIEW" "_SEISO")
  (command "_.ZOOM" "_E")
  (command "_.VSCURRENT" "_R")
  (princ (strcat "\n" (itoa n) " suspensions placees. Enregistrer avec ENREGSOUS au format DWG."))
  (princ))
(princ "\nTaper LUSTRE3D pour construire le lustre.")
(princ)
"""


def lisp(rows):
    pts = "\n".join(f'("{r["id"]}" {r["x"]:.1f} {r["y"]:.1f} {r["fil"]:.1f})' for r in rows)
    src = (LISP.replace("__PTS__", pts).replace("__SUSP_H__", f"{SUSP_H:.1f}")
           .replace("__W__", f"{W:.1f}").replace("__H__", f"{H:.1f}").replace("__T__", f"{PLATE_T:.1f}"))
    src = unicodedata.normalize("NFKD", src).encode("ascii", "ignore").decode()   # LISP en ASCII pur
    with open(os.path.join(HERE, "lustre_3d.lsp"), "w", encoding="ascii", newline="\r\n") as f:
        f.write(src)


if __name__ == "__main__":
    rows = load()
    plan(rows)
    model3d(rows)
    lisp(rows)
    real = os.path.join(HERE, "suspension5.dxf")
    if os.path.exists(real):
        h, d = model3d_real(rows, real)
        print(f"suspension5.dxf : hauteur {h:.0f} mm, Ø hors tout {d:.0f} mm -> lustre_3d_suspension5.dxf")
    print(f"{len(rows)} suspensions -> lustre_plan.dxf, lustre_3d.dxf, lustre_3d.lsp")
