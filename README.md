# Lustre-configurateur

## Lustre cascade 334 suspensions en quinconce (`lustre/`)

Trous en quinconce : 20 cm entre deux trous d'une même rangée ou colonne, 14,14 cm en diagonale.
23 rangées (A à W, tous les 10 cm) de 15 et 14 trous, pourtour de 10 cm entre les trous extérieurs et le bord du plateau.

| Fichier | Contenu |
|---|---|
| `lustre/lustre.html` | Plan interactif du plateau, vues de face et de côté, tableau de montage |
| `lustre/plan_plateau.svg` | Plan 2D du plateau 3,00 × 2,40 m à l'échelle (unités en mm), imprimable |
| `lustre/suspensions.csv` | Repère (rangée + numéro), x, y (cm depuis le coin bas-gauche, vue de dessous), longueur de fil (cm) |
| `lustre/lustre_plan.dxf` | Plan AutoCAD 2D coté (mm) : plateau, perçages, repères, longueurs de fil, calques séparés |
| `lustre/lustre_3d.dxf` | Modèle AutoCAD 3D (mm) : plateau, fils, suspensions à leur hauteur |
| `lustre/lustre_3d_suspension5.dxf` | Modèle AutoCAD 3D avec la suspension réelle (`suspension5.dxf` en bloc `SUSPENSION5`, 334 insertions) |
| `lustre/suspension5.dxf` | Modèle de la suspension (fourni) : 233 mm, Ø 62 mm hors tout |
| `lustre/lustre_3d.lsp` | AutoLISP `LUSTRE3D` : construit le lustre 3D dans AutoCAD avec `suspension5.dwg` |
| `lustre/suspension5.dwg` | Modèle de la suspension (fourni) |
| `lustre/export_dxf.py` | Export DXF depuis `suspensions.csv` (`pip install ezdxf`) |
| `lustre/generate.py` | Générateur, Python 3 standard. Paramètres en tête de fichier |

Régénérer : `python3 lustre/generate.py && python3 lustre/export_dxf.py` (changer `SEED` pour une autre répartition aléatoire).

Hypothèses : fil mesuré du plateau au haut de la suspension ; 1,00 m de fil nu minimum ;
zone de suspension de 5,50 m, donc fil de 1,00 m à 6,26 m et bas de la suspension la plus basse à 6,50 m sous le plateau.

DWG : ouvrir le `.dxf` dans AutoCAD puis `ENREGSOUS` / `SAVEAS` au format DWG.

Lustre 3D avec la vraie suspension : mettre `lustre_3d.lsp` et `suspension5.dwg` dans le même dossier, nouveau dessin en mm, `APPLOAD` → `lustre_3d.lsp`, taper `LUSTRE3D`, puis `ENREGSOUS` en DWG.
