# influenceuse-ia : montage automatique des vidéos de Nala

Ce dépôt reçoit, chaque matin, le script et les 8 photos générés par n8n
(workflow « Influenceuse - Production quotidienne »). Il monte une vidéo verticale
de plus d'une minute et la publie sur GitHub Pages. Il prévient ensuite n8n,
qui passe le contenu au statut `a_valider`.

## Lancer un montage à la main

Onglet Actions → « Montage d'un contenu » → Run workflow → numéro sur 3 chiffres (ex. `001`).

## Tester en local sans réseau

```bash
VOIX_MUETTE=1 python scripts/render.py 001
```

## Réglages

- Voix : variable `VOIX` (par défaut `fr-FR-DeniseNeural`) et `DEBIT_VOIX` (`+6%`).
- Musique de fond facultative : `assets/musique.mp3` (libre de droits).
- Chaque vidéo affiche la mention « Personnage virtuel IA » en haut à droite. Ne la retire pas.
