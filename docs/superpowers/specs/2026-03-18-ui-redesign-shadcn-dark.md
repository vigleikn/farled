# UI-redesign: Shadcn dark floating card

## Kontekst
Eksisterende UI har et nautisk mørkt sidepanel med animert kompass, gull-aksenter, Cormorant Garamond-font og rutenett-bakgrunn. Bruker vil ha alt dette fjernet til fordel for en nøytral shadcn/ui-estetikk, og panelet skal bli et flytende kort over fullt kart.

## Designbeslutninger
- **Designsystem:** shadcn/ui zinc dark palette
- **Tittel:** h1 → "Farled", `<title>` → "Farled", undertittel → "Distanser til sjøs i Norge"
- **Layout:** flytende kort øverst til venstre over fullskjermkart
- **Posisjon:** `position: absolute; top: 16px; left: 16px; z-index: 900`

## Hva fjernes
- Animert kompass (SVG + CSS-animasjon)
- Rutenett-bakgrunn (`.panel::before` pseudo-element)
- Cormorant Garamond / Space Mono fonter
- Gull-aksenter (`--gold`, `--gold-lt`)
- Sidepanel-layout (fast bredde venstre, kart høyre)
- Gradient-bakgrunn på panel
- Dekorative field-labels med horisontal strek (`::after`-linje)
- `.connector`-div (vertikal gradient-linje mellom fra/til)
- Horisontale hairlines generelt

## Hva bygges

### Layout
```
body  → position: relative; overflow: hidden; height: 100vh; background: #000
#map  → position: absolute; inset: 0 (fullskjerm)
.card → position: absolute; top: 16px; left: 16px; z-index: 900; width: 280px
        max-height: calc(100vh - 32px); overflow-y: auto
```

### Fargepalett (zinc dark)
```css
--bg:       #09090b   /* zinc-950 — kortbakgrunn */
--surface:  #18181b   /* zinc-900 — input og resultat-card */
--border:   #27272a   /* zinc-800 — alle borders */
--input-bd: #3f3f46   /* zinc-700 — input-border */
--text:     #fafafa   /* zinc-50  — primærtekst */
--muted:    #e4e4e7   /* zinc-200 — labels (lysere) */
--subtle:   #d4d4d8   /* zinc-300 — undertittel, resultat-labels (lysere) */
--dim:      #a1a1aa   /* zinc-400 — placeholder (lysere) */
--accent:   #3ecfcc   /* teal — rutestrek, pip-markører, pinned-state */
--error:    #f87171   /* red-400 — feilmeldinger */
```

### Komponenter

**Kort:**
- `background: rgba(9,9,11,0.92)`, `backdrop-filter: blur(12px)`, `border-radius: 12px`
- `border: 1px solid #27272a`
- `box-shadow: 0 8px 32px rgba(0,0,0,0.4)`

**Header:**
- Ingen border-bottom — ingen horisontale hairlines
- h1: `font-size: 18px; font-weight: 600; color: #fafafa`
- Undertittel: `font-size: 12px; color: #71717a`

**Input:**
- `background: #18181b; border: 1px solid #3f3f46; border-radius: 8px`
- Focus: `border-color: #71717a; box-shadow: 0 0 0 2px rgba(113,113,122,0.2)`
- Pinned state: `border-color: #3ecfcc; color: #3ecfcc`

**Knapp primær:**
- `background: #fafafa; color: #09090b; border-radius: 8px`
- Hover: `background: #e4e4e7`
- Disabled: `opacity: 0.4`

**Separator mellom fra/til:**
- Enkel `1px solid #27272a` linje — erstatter den gradient-animerte connectoren

**Resultat-card:**
- `background: #18181b; border: 1px solid #27272a; border-radius: 8px`
- Distanse-tall: `font-size: 32px; font-weight: 600`
- Font-vekter: distanse 600, labels/knapper 500, brødtekst 400

**Statusbar:**
- Beholdes med zinc-farger: `border-color: #27272a; color: #52525b`
- Pip-farger: aktiv → `#3ecfcc`, inaktiv → `#3f3f46`

**Feilmelding:**
- Beholdes med semantisk rød: `background: rgba(248,113,113,0.08); color: #f87171`

**Dropdown:**
- `z-index: 1000` (over kortet på 900)
- `background: #18181b; border: 1px solid #3f3f46`

### Font
`Inter` (Google Fonts, weights 400/500/600) — erstatter Cormorant Garamond og Space Mono

### JS-logikk
Uendret. `--accent` (#3ecfcc) brukes videre for rutestrek og markørfarger — ingen JS-endringer nødvendig.

## Fil som endres
`templates/index.html` — kun CSS-variabler, HTML-struktur og Google Fonts-import. All JS er uendret.

## Verifisering
1. Start server: `python3 app.py`
2. Kart tar fullskjerm, kort flyter øverst til venstre
3. Ingen gull, ingen kompass, ingen nautisk dekor
4. Søk og ruteberegning fungerer som før
5. Dropdowns vises over kortet (z-index 1000 > 900)
6. Pin-modus: input-border og tekst skifter til teal
7. Feilmelding vises med rød bakgrunn ved ugyldig rute
