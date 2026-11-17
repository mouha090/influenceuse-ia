"""Monte la video d'un contenu de l'influenceuse IA.

Entree : contenus/<numero>/script.json et contenus/<numero>/scene-XX.png
Sortie : docs/videos/contenu-<numero>.mp4 (servi par GitHub Pages) et resultat.json

Format : 1080x1920, 30 i/s, voix off edge-tts, photos animees (zoom lent),
texte a l'ecran par scene, sous-titres, mention "Personnage virtuel IA".
"""
import json
import os
import subprocess
import sys
import textwrap
from pathlib import Path

LARGEUR, HAUTEUR, IPS = 1080, 1920, 30
VOIX = os.environ.get("VOIX", "fr-FR-DeniseNeural")
DEBIT_VOIX = os.environ.get("DEBIT_VOIX", "+6%")
POLICE = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
RACINE = Path(__file__).resolve().parent.parent


def lancer(cmd):
    print("+", " ".join(str(c) for c in cmd)[:300], flush=True)
    subprocess.run([str(c) for c in cmd], check=True)


def duree(fichier):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(fichier)],
        check=True, capture_output=True, text=True,
    ).stdout.strip()
    return float(out)


def horodatage(t):
    h, reste = divmod(t, 3600)
    m, s = divmod(reste, 60)
    return f"{int(h):02d}:{int(m):02d}:{s:06.3f}".replace(".", ",")


def sous_titres(narration, total, chemin):
    """Decoupe la narration en morceaux de 5 a 7 mots, temps proportionnel aux caracteres."""
    mots = narration.split()
    morceaux, courant = [], []
    for mot in mots:
        courant.append(mot)
        if len(courant) >= 6 or mot.endswith((".", "!", "?", ",")) and len(courant) >= 3:
            morceaux.append(" ".join(courant))
            courant = []
    if courant:
        morceaux.append(" ".join(courant))
    poids = [len(m) + 2 for m in morceaux]
    unite = total / sum(poids)
    t, lignes = 0.0, []
    for i, (texte, p) in enumerate(zip(morceaux, poids), 1):
        fin = t + p * unite
        lignes.append(f"{i}\n{horodatage(t)} --> {horodatage(fin)}\n{texte}\n")
        t = fin
    Path(chemin).write_text("\n".join(lignes), encoding="utf-8")


def voix_off(narration, dossier):
    texte = dossier / "narration.txt"
    texte.write_text(narration, encoding="utf-8")
    mp3 = dossier / "voix.mp3"
    if os.environ.get("VOIX_MUETTE") == "1":  # test local sans reseau
        mots = len(narration.split())
        lancer(["ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono", "-t", f"{mots / 2.7:.2f}", mp3])
    else:
        lancer(["edge-tts", "--voice", VOIX, f"--rate={DEBIT_VOIX}", "--file", texte, "--write-media", mp3])
    return mp3


def plan_anime(image, texte_ecran, secondes, index, sortie, dossier):
    images = max(1, round(secondes * IPS))
    if index % 2:
        zoom = "if(eq(on,0),1.12,max(zoom-0.0009,1.0))"
    else:
        zoom = "min(zoom+0.0009,1.12)"
    fichier_texte = dossier / f"texte-{index:02d}.txt"
    lignes = textwrap.wrap(texte_ecran.upper(), width=18) or [" "]
    fichier_texte.write_text("\n".join(lignes[:3]), encoding="utf-8")
    filtres = (
        f"scale={int(LARGEUR*1.2)}:{int(HAUTEUR*1.2)}:force_original_aspect_ratio=increase,"
        f"crop={int(LARGEUR*1.2)}:{int(HAUTEUR*1.2)},"
        f"zoompan=z='{zoom}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={images}:s={LARGEUR}x{HAUTEUR}:fps={IPS},"
        f"drawtext=fontfile={POLICE}:textfile={fichier_texte}:fontsize=66:fontcolor=white:line_spacing=12:"
        f"borderw=5:bordercolor=black:x=(w-text_w)/2:y=h*0.12:enable='lt(t,{min(3.0, secondes):.2f})',"
        f"format=yuv420p"
    )
    lancer([
        "ffmpeg", "-y", "-i", image, "-vf", filtres, "-frames:v", images,
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-r", IPS, sortie,
    ])


def main(numero):
    dossier = RACINE / "contenus" / numero
    script = json.loads((dossier / "script.json").read_text(encoding="utf-8"))
    travail = RACINE / "travail" / numero
    travail.mkdir(parents=True, exist_ok=True)

    scenes = []
    for sc in script["scenes"]:
        img = dossier / f"scene-{int(sc['index']):02d}.png"
        if img.exists():
            scenes.append((img, sc.get("texte_ecran", "")))
    if len(scenes) < 4:
        raise SystemExit(f"Seulement {len(scenes)} photos trouvees, il en faut au moins 4")

    mp3 = voix_off(script["narration"], travail)
    total = duree(mp3) + 0.8
    par_scene = total / len(scenes)

    clips = []
    for i, (img, texte) in enumerate(scenes, 1):
        clip = travail / f"plan-{i:02d}.mp4"
        plan_anime(img, texte, par_scene, i, clip, travail)
        clips.append(clip)
    liste = travail / "plans.txt"
    liste.write_text("".join(f"file '{c}'\n" for c in clips), encoding="utf-8")
    muet = travail / "muet.mp4"
    lancer(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", liste, "-c", "copy", muet])

    srt = travail / "sous-titres.srt"
    sous_titres(script["narration"], total - 0.8, srt)

    sortie = RACINE / "docs" / "videos" / f"contenu-{numero}.mp4"
    sortie.parent.mkdir(parents=True, exist_ok=True)
    style = (
        "FontName=DejaVu Sans,FontSize=13,Bold=1,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,"
        "BorderStyle=1,Outline=2,Shadow=0,Alignment=2,MarginV=70"
    )
    mention = travail / "mention.txt"
    mention.write_text("Personnage virtuel IA", encoding="utf-8")
    video_filtre = (
        f"subtitles={srt}:force_style='{style}',"
        f"drawtext=fontfile={POLICE}:textfile={mention}:fontsize=30:fontcolor=white@0.85:"
        f"borderw=2:bordercolor=black@0.6:x=w-text_w-30:y=40"
    )
    musique = RACINE / "assets" / "musique.mp3"
    cmd = ["ffmpeg", "-y", "-i", muet, "-i", mp3]
    if musique.exists():
        cmd += ["-stream_loop", "-1", "-i", musique, "-filter_complex",
                f"[0:v]{video_filtre}[v];[2:a]volume=0.12[m];[1:a][m]amix=inputs=2:duration=first:dropout_transition=0[a]",
                "-map", "[v]", "-map", "[a]"]
    else:
        cmd += ["-vf", video_filtre, "-map", "0:v", "-map", "1:a"]
    cmd += ["-c:v", "libx264", "-preset", "veryfast", "-crf", "23", "-c:a", "aac", "-b:a", "160k",
            "-ar", "44100", "-movflags", "+faststart", "-t", f"{total:.2f}", sortie]
    lancer(cmd)

    resultat = {"numero": numero, "duree_s": round(duree(sortie), 2), "fichier": str(sortie.relative_to(RACINE))}
    (RACINE / "resultat.json").write_text(json.dumps(resultat), encoding="utf-8")
    print(json.dumps(resultat))


if __name__ == "__main__":
    main(sys.argv[1])
