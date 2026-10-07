# Fabrication — Lustre spirale 1200 × 800 × H3500 (30 boîtes)

Généré par `scripts/generer_fabrication.py` (à partir du modèle 3D
`lustres/lustre-spirale-1200x800-H3500-30boites.dxf`). Unités : mm.

## Fichiers

| Fichier | Contenu | Usage |
|---|---|---|
| `01-plateau-inox-1mm.dxf` | flan déplié du plateau inox | **laser** (calque `DECOUPE`), plis sur calque `PLIAGE` |
| `02-galvin-1.5mm.dxf` | plaque galvin | **laser** (calque `DECOUPE`) |
| `00-dossier-fabrication.dxf` | les 2 pièces annotées + vue de contrôle + nomenclature + table des câbles | atelier / montage |
| `apercu-fabrication.png` | aperçu visuel | contrôle |

Calques : `DECOUPE` (rouge, à couper) · `PLIAGE` (bleu pointillé, **ne pas couper**) ·
`TEXTE` / `COTATION` (annotations) · `CONTROLE` (galvin superposé, ne pas couper).
Tous les contours sont des polylignes fermées (arcs vrais), les trous des cercles.

## Nomenclature

| Rep | Pièce | Qté | Détail |
|---|---|---|---|
| 01 | Plateau inox 1 mm | 1 | Fond 1200 × 800 + ceinture 30 mm intégrée (4 bords pliés à 90° vers le haut). Flan 1256,18 × 856,18 (1290,18 × 890,18 avec pattes). 30 oblongs 6 × 4 (fils), 6 trous Ø6 (écrous), 14 pattes avec trou Ø3,2 (profil repris du fichier ceinture SI8-50) |
| 02 | Galvin 1,5 mm | 1 | 1196 × 796 (1 mm de jeu par côté dans la ceinture), coins R3. 1 trou Ø7 central (fixation plafond), 6 trous Ø10,4 (R5,2) superposés aux Ø6 de l'inox, 14 trous Ø4 en face des pattes repliées |
| 03 | Boîte (modèle 1750-1 : cylindre Ø50 × 65 + 7 profilés 611+2020) | 30 | identique au lustre 725 |
| 04 | Câble de suspension | 30 | longueurs ci-dessous |
| 05 | Vis M6 + écrou + entretoise ≈ 27,5 mm | 6 | fond inox → galvin |
| 06 | Vis M3 + écrou | 14 | pattes → galvin |

## Pliage (plateau inox)

Inox 1 mm, rayon intérieur 1 mm, facteur K 0,33 → déduction **1,91 mm par pli**,
axe de pli à 0,955 mm de la cote extérieure.

1. Plier les 4 bords à 90° **vers le haut** (côté face dessinée) → caisson
   1200 × 800 × 30 extérieur. Les angles sont dégagés (encoche carrée) pour que
   les bords ne se chevauchent pas.
2. Poser le galvin dans la ceinture (sur les entretoises M6).
3. Replier les 14 pattes à 90° **vers l'intérieur** sur le galvin : leur trou
   Ø3,2 tombe à 12,96 mm de la face extérieure de la ceinture, soit sur les
   trous Ø4 du galvin (à 10,96 mm de son bord). Le Ø4 laisse ±0,4 mm de
   tolérance de pliage.

Si la plieuse utilise d'autres paramètres (rayon / K), changer `R_INT` et `K`
en tête du script et relancer : tout est recalculé.

## Câbles (longueur visible, du fond inox au haut de la boîte)

Numérotation le long de la double hélice (1 = le plus haut). X / Y depuis le
centre du plateau. Prévoir en plus la surlongueur de raccordement.

| n° | X | Y | Longueur |
|---|---|---|---|
| 1 | -540 | -340 | 420 |
| 2 | 540 | 340 | 420 |
| 3 | -540 | -170 | 750 |
| 4 | 540 | 170 | 750 |
| 5 | -540 | 0 | 1050 |
| 6 | 540 | 0 | 1050 |
| 7 | -540 | 170 | 1330 |
| 8 | 540 | -170 | 1330 |
| 9 | -540 | 340 | 1585 |
| 10 | 540 | -340 | 1585 |
| 11 | -324 | 340 | 1820 |
| 12 | 324 | -340 | 1820 |
| 13 | -108 | 340 | 2035 |
| 14 | 108 | -340 | 2035 |
| 15 | -108 | -340 | 2235 |
| 16 | 108 | 340 | 2235 |
| 17 | -324 | -340 | 2415 |
| 18 | 324 | 340 | 2415 |
| 19 | -324 | -170 | 2585 |
| 20 | 324 | 170 | 2585 |
| 21 | -324 | 0 | 2735 |
| 22 | 324 | 0 | 2735 |
| 23 | -324 | 170 | 2880 |
| 24 | 324 | -170 | 2880 |
| 25 | -108 | 170 | 3010 |
| 26 | 108 | -170 | 3010 |
| 27 | -108 | -170 | 3125 |
| 28 | 108 | 170 | 3125 |
| 29 | -108 | 0 | 3237 |
| 30 | 108 | 0 | 3237 |
