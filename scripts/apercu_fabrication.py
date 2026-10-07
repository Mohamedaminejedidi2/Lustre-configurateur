"""Aperçu PNG des plans de découpe (vérification visuelle)."""
import ezdxf
import matplotlib
from ezdxf import path

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

COUL = {"DECOUPE": "#d62728", "PLIAGE": "#1f77b4", "CONTROLE": "#c000c0"}


def tracer(ax, fichier, calques=("DECOUPE", "PLIAGE"), textes=False, couleur=None):
    doc = ezdxf.readfile(fichier)
    for e in doc.modelspace():
        lay = e.dxf.layer
        if e.dxftype() == "TEXT" and textes and lay == "TEXTE":
            ax.text(e.dxf.insert.x, e.dxf.insert.y, e.dxf.text, fontsize=5,
                    ha="center", va="center")
            continue
        if lay not in calques or e.dxftype() not in ("LWPOLYLINE", "CIRCLE", "LINE"):
            continue
        v = list(path.make_path(e).flattening(0.05))
        ax.plot([p.x for p in v], [p.y for p in v], color=couleur or COUL[lay],
                lw=0.6, ls="--" if lay == "PLIAGE" else "-")
    ax.set_aspect("equal")
    ax.axis("off")


fig, axs = plt.subplots(2, 2, figsize=(22, 15))
tracer(axs[0, 0], "fabrication/01-plateau-inox-1mm.dxf")
doc = ezdxf.readfile("fabrication/00-dossier-fabrication.dxf")
for e in doc.modelspace().query("TEXT[layer=='TEXTE']"):
    x, y = e.dxf.insert.x, e.dxf.insert.y
    if abs(x) < 700 and abs(y) < 460 and e.dxf.height < 10:
        axs[0, 0].text(x, y + (3 if e.dxf.height > 5 else -3), e.dxf.text,
                       fontsize=7 if e.dxf.height > 5 else 6, ha="center",
                       va="bottom" if e.dxf.height > 5 else "top",
                       color="k" if e.dxf.height > 5 else "#555")
axs[0, 0].set_title("01 - Plateau inox 1 mm (flan déplié) - n° de trou / longueur câble mm")
tracer(axs[0, 1], "fabrication/02-galvin-1.5mm.dxf")
axs[0, 1].set_title("02 - Galvin 1,5 mm - 1196 x 796")
tracer(axs[1, 0], "fabrication/01-plateau-inox-1mm.dxf", couleur="#bbbbbb")
tracer(axs[1, 0], "fabrication/02-galvin-1.5mm.dxf", calques=("DECOUPE",), couleur="#c000c0")
axs[1, 0].set_title("Contrôle : galvin (magenta) sur le plateau - trous superposés")
tracer(axs[1, 1], "fabrication/01-plateau-inox-1mm.dxf")
tracer(axs[1, 1], "fabrication/02-galvin-1.5mm.dxf", calques=("DECOUPE",), couleur="#c000c0")
axs[1, 1].set_xlim(-490, -410)
axs[1, 1].set_ylim(-450, -370)
axs[1, 1].axis("on")
axs[1, 1].grid(alpha=0.3)
axs[1, 1].set_title("Détail patte (rouge, à plat) + trou Ø4 galvin (magenta, après pliage)")
fig.tight_layout()
fig.savefig("fabrication/apercu-fabrication.png", dpi=90)
