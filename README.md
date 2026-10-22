# Storm Austin – baan van de lagedrukkern (ICON-D2)

Animatie van de positie en de baan van de lagedrukkern (**L**) van storm Austin,
geplaatst boven de **maximale windstoten** van het ICON-D2-model. De kaart focust
op België en het (oostelijke) Kanaal. Alles is in het Nederlands, in de Downburst
Daan-huisstijl.

| Bestand | Inhoud |
|---|---|
| `output/storm_austin_icon_d2.mp4` | Animatie 1080×1350 (4:5), 30 fps |
| `output/storm_austin_icon_d2.gif` | Lichtere GIF-versie (720 px) |
| `output/storm_austin_icon_d2_preview.png` | Stilstaand beeld: kern aan de Belgische kust |
| `data/track_austin.csv` | Uurlijkse kernposities en kerndruk |

## Data

- Model: **ICON-D2** (DWD), run **donderdag 22 oktober 2026, 09 UTC**.
- Bron: het publieke Open-Meteo-archief op AWS Open Data
  (`s3://openmeteo/data_spatial/dwd_icon_d2/`), regulier rooster van 0,02°.
- Velden: `pressure_msl` (MSLP) en `wind_gusts_10m`. Dat laatste is de
  hoogste windstoot van het afgelopen uur, omgerekend van m/s naar km/u.
- Kaartlagen: Natural Earth (10m).

**Domeinrand:** ICON-D2 reikt aan de Kanaalkust maar tot ongeveer 1,8° W. Het
westelijke Kanaal ligt dus buiten het model en wordt op de kaart als
"buiten ICON-D2-domein" weergegeven. De kern komt het domein binnen rond
vrijdag 23 oktober 09:00 Belgische tijd (07 UTC). Daarvoor bepaalt het spoor
geen betrouwbare kern, dus de animatie start op dat moment.

## Werkwijze

1. `scripts/fetch_icon_d2.sh` haalt de run op en knipt per uur MSLP en windstoten
   uit voor het focusgebied (`data/icon_d2/*.npz`).
2. `scripts/track_low.py` volgt het drukminimum uur per uur (afgevlakt veld,
   zoekvenster rond de verwachte positie, sub-roosterpuntverfijning) en
   stopt aan de domeinrand.
3. `scripts/render_animation.py` tekent de beelden en maakt met ffmpeg MP4 en GIF.

### Interpolatie

Tussen twee modeluren worden 16 tussenbeelden berekend.

- **L-positie en kerndruk:** een kubische spline door de uurposities, zodat de L
  vloeiend beweegt.
- **Windstoten en isobaren:** bewegingsgecompenseerde interpolatie. Beide uurvelden
  worden langs de verplaatsing van de kern naar het tussentijdstip geschoven en
  dan gemengd. De verschuiving neemt af met de afstand tot de kern. Zo glijdt
  het windveld mee met de storm in plaats van uit- en in te faden.

De tussenbeelden zijn een visuele interpolatie. De echte modelwaarden horen bij
de hele uren.

## Opnieuw maken

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
PYTHON=python scripts/fetch_icon_d2.sh 2026/10/22/0900Z data/icon_d2   # optioneel: data staat al in de repo
python scripts/track_low.py data/icon_d2 data/track_austin.csv
python scripts/render_animation.py             # of --preview-only
```

Lettertypen: Montserrat en Roboto (SIL Open Font License, Google Fonts),
statische instanties in `assets/fonts/`.
