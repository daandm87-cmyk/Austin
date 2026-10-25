# Downburst Daan — werkafspraken en huisstijl

Dit document legt de keuzes vast die tijdens het maken van de storm-Austen-grafieken
zijn gemaakt, zodat een volgende sessie (mens of Claude) niet opnieuw moet beginnen.
De code staat in `scripts/`, de uitleg per script in `README.md`. **Dit bestand gaat over
het waarom**: huisstijl, formats, drempels en wat werkte.

---

## 1. Huisstijl

Afgeleid uit de bestaande waarschuwingskaarten (`assets/logo_downburst_daan.png`,
`assets/footer_socials.png` zijn daar rechtstreeks uit geknipt).

| Element | Waarde |
|---|---|
| Achtergrond / panelen | `#173f51` (navy), donkerder `#0e2d40` |
| Accent | `#f1c40f` (goud) — titels, kerncijfers, scheidingslijn onder de header |
| Tekst | wit `#ffffff`, secundair `#c3d0d8` |
| Zee / land op kaart | `#122230` / `#1d3443` |
| Titelfont | Montserrat ExtraBold (kop), Montserrat Bold (tussenkop) |
| Tekstfont | Roboto Bold / Regular |
| Formaat | 1080 × 1350 (4:5) — het staande formaat dat Facebook het meeste scherm geeft |

Fonts staan als statische instanties in `assets/fonts/` (SIL OFL, Google Fonts).
Gebruik ze via het pad, niet via de systeemnaam.

**Vaste opbouw van een kaart of animatie** (hoogtes in px):
header 190 · goudlijn 5 · kaart 830 · statistiekenpaneel 225 · footer 100.

De footer met de sociale-media-iconen hoort op élke post. De logo-afbeelding
rechtsboven in de header.

### Kleurenschaal windstoten

**Meteociel-schaal** (ICON-D2 "Rafales de vent max"), 30 klassen van 0 tot 240+ km/u —
zie `GUST_BOUNDS` / `GUST_COLORS` in `scripts/render_animation.py`.

- Elke klasse krijgt haar kleur in het **midden**, daartussen vloeiend overvloeien.
  Geen harde grenzen: dat was een expliciete vraag.
- De klassen zijn ongelijk breed (5 → 10 → 20 km/u), maar staan **even breed** op de
  kleurenbalk, net als bij Meteociel. Daarom gaat alles via `gust_index()`.
- Niet zelf een palet verzinnen. Een eerder zelfbedacht palet is vervangen door deze.

**Waarde-tekst in het statistiekenpaneel blijft wit**, niet in de schaalkleur. De
waarden die België haalt (100–135 km/u) vallen in de donkerste klassen (donkerrood,
wijnrood, paars) en zijn op het navy paneel niet leesbaar.

---

## 2. Kaartkeuzes

- **Isobaren om de 2 hPa**, wit, dun (lw 0.8, alpha 0.5). 4 hPa is te grof voor dit
  gebied.
- **Provinciegrenzen** van België meetekenen bij de ingezoomde kaart.
- **Steden**: Nederlandstalige namen (Rijsel, Duinkerke, Bergen, Doornik, Aken,
  Luik, Namen, Keulen, Londen).
- **De L**: rood `#e5262b` met witte rand en schaduw, kerndruk eronder. Alleen tekenen
  als de kern binnen de kaart valt; daarbuiten een pijl aan de kaartrand met
  `L <druk> hPa` in een zwart kadertje.
- **Geen cirkel** rond de hoogste windstoot in België. Dat is geprobeerd en oogde
  te chaotisch. De waarde staat in het paneel.
- **Buiten het modeldomein** grijs afdekken met een label, niet wit laten.

### Twee presets (`scripts/render_animation.py`)

| Preset | Gebied | Windveld |
|---|---|---|
| `kanaal` | België + oostelijk Kanaal | max. windstoot van het **afgelopen uur**, schuift mee met de storm |
| `belgie` | strak op België (2.12–6.82°E, 49.36–51.66°N) | **cumulatief maximum** sinds de start → windstootsporen (swaths) |

De `belgie`-preset met swaths is het sterkste product. Zie §4.

### Interpolatie

16 tussenbeelden per modeluur. De L volgt een kubische spline; de wind- en drukvelden
worden **bewegingsgecompenseerd** verschoven langs de verplaatsing van de kern (afnemend
met de afstand tot de kern) en dan gemengd. Zo glijdt het veld mee in plaats van uit- en
in te faden. Alleen de hele uren zijn echte modelwaarden — dat hoort in de toelichting.

---

## 3. Data

- **Bron**: het publieke Open-Meteo-archief op AWS S3,
  `https://openmeteo.s3.amazonaws.com/data_spatial/<model>/...`.
  `latest.json` per model geeft de laatst voltooide run.
- **Let op**: `opendata.dwd.de`, `api.open-meteo.com`, Meteociel, Météo-France, KMI,
  KNMI, METAR-bronnen en Meteoalarm zijn in de cloudomgeving **geblokkeerd**. Alleen
  de S3-bucket werkt. Wil je waarnemingen of de lichte punt-API, dan moeten die hosts
  eerst bij *Allowed domains* in de netwerkinstellingen van de omgeving.
- **Eenheden**: `wind_gusts_10m` staat in m/s → ×3.6 voor km/u. Het is het maximum
  van het **afgelopen uur**; op analysetijd (+0 u) ontbreekt het veld.
- **ICON-D2 domeinrand**: aan de Kanaalkust tot ongeveer 1,8° W. Het westelijke Kanaal
  valt erbuiten. Voor de ontwikkelingsfase van een storm boven de oceaan heb je een
  globaal model nodig (ECMWF, GFS, UKMO, ICON) — zie `scripts/models/`.
- **Kernvolging**: `scripts/track_low.py` (ICON-D2) en `scripts/models/track_global.py`
  (globale modellen). Beide zoeken het drukminimum in een venster rond de verwachte
  positie en stoppen aan de domeinrand.

### Welk model wanneer

| Bereik | Model |
|---|---|
| 0–48 u, hoge resolutie boven België | ICON-D2 (0.02°) |
| 0–48 u, tweede mening | KNMI HARMONIE, Météo-France AROME (beide nog niet gebruikt) |
| 2–5 dagen | ICON-EU, ARPEGE |
| 2–7 dagen, kansen | ensembles: ECMWF ENS, GEFS, ICON-EU EPS |
| ontwikkeling boven de Atlantische Oceaan | ECMWF IFS, GFS, UKMO, ICON globaal |

---

## 4. Wat werkte op Facebook

Storm Austen, pagina met ~660 volgers:

| Post | Weergaven |
|---|---|
| Animatie baan lagedrukkern (Kanaal-preset) + tekst | 32.000 |
| Windstootsporen boven België (`belgie`-preset) | 28.000 |

Veel verder dan het eigen bereik, dus het format werkt. Lessen:

- **Apart posten, niet als reactie onder een vorige post.** Een reactie bereikt alleen
  wie de eerste post opent; een nieuwe post komt opnieuw in de feed. Video in reacties
  wordt bovendien slecht weergegeven. Een paar uur ertussen laten.
- **Vroeg zijn is het hele punt.** De modellen lieten de explosieve verdieping al
  woensdag zien; de officiële stormnaam kwam pas donderdag. Wie op de naam wacht,
  post hetzelfde als iedereen op hetzelfde moment.
- **De swath beantwoordt de vraag die mensen echt hebben**: "hoe hard waait het bij
  mij?" De baan van de kern beantwoordt "waar gaat hij heen?". De eerste scoort beter.
- Bij een storm die noordelijk langs trekt (kern niet over het land): alleen de swath
  maken, eventueel als stilstaand beeld. Een baan-animatie waarin de L nooit in beeld
  komt, voegt niets toe.

### Opbouw van een posttekst (Nederlands)

Werkende structuur, zie de Austen-posts:

1. **Emoji + korte kop** met de kern van het verhaal.
2. Eén zin over wat je ziet en welk model/run het is.
3. 📍 **Timing van de kern**: waar en wanneer.
4. 💨 **Verwachte waarden per zone**, met gekleurde bolletjes 🔴🟠🟡🟢 van hard naar
   zacht, telkens met het tijdvenster erbij.
5. ⏰ **Wanneer het het hardst is**, in gewone taal ("midden in de avondspits").
6. 🌳 **Impact en advies**, concreet (bomen nog in blad, losse spullen, verkeer).
7. Hashtags: `#Storm<Naam> #Storm #België #Windstoten #Weer`.

Extra afspraken:

- **Nuanceer bij een afzwakkende voorspelling.** Als een nieuwe run lager uitkomt dan
  wat je gisteren postte, zet dat er expliciet bij (📉 "Iets minder fel dan gisteren")
  met de reden. Anders lijkt het alsof je jezelf tegenspreekt.
- **Altijd Belgische tijd** in de tekst én op de beelden. UTC er klein bij op het beeld.
- Vermeld model en run; dat geeft geloofwaardigheid en dekt je in bij een bijstelling.

---

## 5. Drempels voor "is dit een post waard?"

Per gevaar, met het bereik waarop het model er iets zinnigs over zegt. Kansen zijn
ensemblekansen (aandeel leden boven de drempel).

| Gevaar | Bruikbaar bereik | Voorlopige drempel |
|---|---|---|
| Wind | 5–7 dagen | ≥30% van de leden boven 90 km/u binnenland / 100 km/u kust |
| Regen | 3–5 dagen | ≥30% boven 30 mm/24 u |
| Sneeuw | 3–5 dagen, wisselt sterk | ≥30% boven 5 cm in het laagland |
| Onweer | **1–2 dagen** | ICON-D2 CAPE + lightning potential |

- Onweer is het buitenbeentje: ensembles zeggen er voorbij ~2 dagen niets zinnigs over.
  Die controle is altijd een "morgen"-controle.
- **Sneeuw is ondergewaardeerd.** 5 cm in Vlaanderen is zeldzaam en doet het op
  Belgische Facebook beter dan dezelfde moeite in wind.
- Deze getallen zijn **inschattingen, geen klimatologie**. Beter zou zijn ze te koppelen
  aan de officiële waarschuwingsdrempels van het KMI en het KNMI, zodat een melding
  betekent "dit gaat richting code geel/oranje". Dat is nog niet gedaan.
- Eén deterministische run op dag 4 is ruis. Gebruik voorbij 48 uur altijd kansen.

---

## 6. Monitoring (ontwerp, nog niet gebouwd)

Afspraken uit het ontwerpgesprek, voor wie dit bouwt:

- **Eén controle per dag op de 00Z-run, rond 09:15 UTC.** Dan is de volledige
  00Z-ensembleset binnen (ECMWF ENS verschijnt rond 08–09 UTC). 12Z komt te laat op de
  dag, 18Z nog later. Vastzetten in **UTC**, want de publicatietijd van ECMWF is de
  beperking, niet iemands wekker.
- **Een geplande taak die bij elke uitvoering een verse sessie start**, geen doorlopend
  gesprek.
- **Screening via de punt-API** (`api.open-meteo.com`, `ensemble-api.open-meteo.com`)
  voor een handvol punten in de Benelux: enkele kB JSON. De zware ruimtelijke velden uit
  S3 pas ophalen als er iets boven de drempel komt en er een kaart gemaakt moet worden.
  Vereist dat die twee hosts zijn vrijgegeven.
- **Een toestandsbestand in de repo**, zodat dezelfde situatie niet vijf dagen na elkaar
  opnieuw gemeld wordt. Wel melden als het signaal duidelijk sterker of zwakker wordt.
- **Wekelijks een "alles rustig"-bericht**, anders is stilte niet te onderscheiden van
  een kapotte controle.
- **De melding bevat een conceptpost**, niet alleen cijfers. Het tijdsverschil met
  België maakt het klaarliggen van de tekst belangrijker dan de melding zelf.
- **Officiële waarschuwingen (Meteoalarm) zijn een bevestigingslaag, geen trigger.**
  Ze lopen achter op de modellen. DWD's namen zeggen niets: dat programma benoemt élk
  hoog- en lagedrukgebied, tientallen per maand. Alleen de namen van de groep
  Met Office / Met Éireann / KNMI zeggen iets over ernst.

---

## 7. Praktische valkuilen

- **Renderen duurt lang**: ~320 beelden op 4 cores is 12–15 minuten. Start het op de
  achtergrond met ruim tijdslimiet. `render_one()` slaat bestaande beelden over, dus een
  onderbroken render hervat — maar de beeldenmap wordt na het coderen opgeruimd.
- **Een run overschrijven**: `ICON_DATA`, `ICON_TRACK`, `RUN_LABEL` en `SWATH_START` als
  omgevingsvariabelen meegeven. `PREVIEW_H` kiest het uur van het previewbeeld.
- **GIF's worden groot.** 12 fps op 540 px met 128 kleuren houdt het onder ~15 MB.
- Controleer een render altijd met een paar losse beelden (`ffmpeg -vf select=...`)
  voordat je hem deelt; labels kunnen over elkaar vallen.
