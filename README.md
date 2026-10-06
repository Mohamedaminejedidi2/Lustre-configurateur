# Lustre-configurateur

## Lustre cascade 350 suspensions (`lustre/`)

| Fichier | Contenu |
|---|---|
| `lustre/lustre.html` | Plan interactif du plateau, vues de face et de côté, tableau de montage |
| `lustre/plan_plateau.svg` | Plan 2D du plateau 3,00 × 2,40 m à l'échelle (unités en mm), imprimable |
| `lustre/suspensions.csv` | Repère, x, y (cm depuis le coin bas-gauche, vue de dessous), longueur de fil (cm) |
| `lustre/generate.py` | Générateur, Python 3 standard. Paramètres en tête de fichier |

Régénérer : `python3 lustre/generate.py` (changer `SEED` pour une autre répartition aléatoire).

Hypothèses : fil mesuré du plateau au haut de la suspension ; 1,00 m de fil nu minimum ;
zone de suspension de 5,50 m, donc fil de 1,00 m à 6,26 m et bas de la suspension la plus basse à 6,50 m sous le plateau.
