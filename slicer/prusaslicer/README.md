# Profil PrusaSlicer — Jubilee (toolchanger) + Trident (3 Z) sous Klipper

Bundle de configuration PrusaSlicer généré à partir de la configuration Klipper
réelle de cette imprimante (`config/printer.cfg`, `config/axis.cfg`,
`config/tools.cfg`, `config/tools_macro.cfg`).

| | |
|---|---|
| Cinématique | CoreXY |
| Carte | Duet2 Wifi/Eth + Duex5 (SAM4E8E) |
| Toolchanger | Jubilee, piloté par **KTCC** (`[toollock]`, `[tool n]`, `M568`, `KTCC_Tn`) |
| Nivellement | **Trident** : 3 moteurs Z indépendants → `Z_TILT_ADJUST` (3 points, tolérance 0.02) |
| Maillage | `[bed_mesh]` 12×12, de 50,5 à 290,180 |
| Interface | Mainsail / Fluidd (Moonraker) |
| Outils configurés | **T0 uniquement** aujourd'hui (`[tool 0]`, Rapido, buse 0.4) |

> ### ⚠️ À lire avant tout : PrusaSlicer 3.0 vs 2.9
>
> **Ce bundle cible PrusaSlicer 2.9.x**, pas la 3.0 — et c'est volontaire.
>
> PrusaSlicer 3.0 est aujourd'hui une **préversion publique (alpha)**, une réécriture
> complète. Deux points la rendent inutilisable pour cette imprimante en l'état :
>
> - **elle ne contient que les profils Prusa.** Le portage des autres a été repoussé
>   (« The alpha only contains profiles for Prusa printers. Porting of the others was
>   postponed for practical reasons ») ;
> - **les configurations custom ne sont pas gérées** : « Loading projects using custom
>   printers or projects from other slicers is not fully supported yet. You may
>   encounter errors in these cases. »
>
> Le format de profil a aussi changé : la 3.0 introduit un **4ᵉ type de profil,
> `ToolPrint`**, qui porte les surcharges de réglages d'impression *par outil* — exactement
> ce dont un toolchanger a besoin, mais qui n'a aucun équivalent dans le `.ini` 2.9.
> Un bundle 2.9 ne se transpose donc pas mécaniquement.
>
> Bonne nouvelle : **la 3.0 utilise un dossier de configuration séparé**, les deux
> versions cohabitent sans conflit. Installez la 3.0 pour l'essayer, gardez la 2.9.x
> pour produire. Voir §7 pour la marche à suivre le jour où la 3.0 accueillera les
> imprimantes tierces.

---

## 1. Côté Klipper — à faire en premier

Votre configuration ne contenait **aucune macro `PRINT_START` / `PRINT_END`** : sans
elles, le profil slicer ne sert à rien. Elles ont été ajoutées ici :

- `config/print_macros.cfg` — nouveau fichier : `PRINT_START`, `PRINT_END`,
  `_PRIME_LINE`, `SET_TOOL_PRESSURE_ADVANCE`, `[exclude_object]` + `M486`,
  et un bloc de réglages `_PRINT_VARS`.
- `config/printer.cfg` — ligne `[include print_macros.cfg]` ajoutée.

Copiez ces deux fichiers sur le Pi (`~/printer_data/config/`) puis
**FIRMWARE_RESTART**. Vérifiez dans la console qu'il n'y a pas d'erreur, et testez
à froid, imprimante allumée mais sans filament :

```gcode
PRINT_START BED=60 TOOL=0 T0=215 MESH=0
```

### Ce que fait `PRINT_START`

1. `CLEAR_PAUSE`, `BED_MESH_CLEAR`, init des stats KTCC.
2. **Range l'outil éventuellement verrouillé** (`KTCC_TOOL_DROPOFF_ALL`) — un Jubilee
   ne doit pas faire son origine avec un outil en main. Si l'outil courant est inconnu
   (`-2`), la macro s'arrête avec un message explicite plutôt que de risquer une casse.
3. `SET_GCODE_OFFSET X=0 Y=0 Z=0` — **indispensable** : les offsets d'outil KTCC
   fausseraient `Z_TILT_ADJUST` et `BED_MESH_CALIBRATE`.
4. Chauffe du plateau + **préchauffe en standby** (`M568 Pn Sx Ry A1`) de tous les
   outils utilisés dans le G-code : ils montent en température pendant le palpage.
5. `G28` (si nécessaire) → `M190` (attente plateau, dilatation faite) → `Z_TILT_ADJUST`
   → `G28 Z` → `BED_MESH_CALIBRATE`.
6. `T<n>` : KTCC verrouille l'outil, applique ses offsets, attend la température.
7. Ligne d'amorce (`_PRIME_LINE`).

### Ce que fait `PRINT_END`

Rétraction → relevage Z (borné par `axis_maximum.z`) → coupure ventilateur et chauffes
→ **`TOOL_DROPOFF`** (l'outil retourne dans son dock, obligatoire sur un Jubilee) →
remise à zéro des offsets → `BED_MESH_CLEAR` → `M84` → stats KTCC.

### Réglages à ajuster — bloc `_PRINT_VARS`

Tout ce qui est susceptible de bouger est regroupé en haut de `print_macros.cfg` :

```ini
variable_prime_x_start: 55.0    variable_prime_x_end: 275.0
variable_prime_y: 41.0          variable_prime_z: 0.3
variable_prime_purge: 8.0       variable_prime_flow: 0.055
variable_end_z_hop: 10.0        variable_standby_delta: 60.0
```

---

## 2. Côté PrusaSlicer

`Fichier` → `Importer` → **`Importer une configuration (bundle)`** →
`Jubilee_Trident_bundle.ini`.

Le bundle installe :

**Imprimantes**
- `Jubilee Trident - 1 outil (T0)` ← à utiliser aujourd'hui
- `Jubilee Trident - 5 outils (T0-T4)` ← prêt pour quand les autres têtes seront montées

**Impression** : `0.15mm DETAIL @JT`, `0.20mm QUALITY @JT`, `0.30mm DRAFT @JT`

**Filaments** : `Generic PLA / PETG / ABS-ASA / TPU 95A @JT`

### Choix structurants

| Réglage | Valeur | Pourquoi |
|---|---|---|
| `gcode_flavor` | `klipper` | émet `SET_VELOCITY_LIMIT` au lieu de `M201/M203/M205`, que Klipper refuse |
| `machine_limits_usage` | `time_estimate_only` | les limites machine servent à l'estimation, elles ne sont pas envoyées à l'imprimante |
| `autoemit_temperature_commands` | `0` | PrusaSlicer n'émet plus de `M104/M190` parasites : tout part dans `PRINT_START`, puis KTCC gère actif/standby |
| `extruder_offset` | `0x0` pour tous | **critique** : les offsets d'outil sont appliqués par KTCC (`SET_GCODE_OFFSET` au pickup). Les renseigner ici les appliquerait deux fois |
| `ooze_prevention` | `0` | entrerait en conflit avec la gestion standby de KTCC (`M568 A1`) |
| `toolchange_gcode` | vide | PrusaSlicer émet `T0`/`T1`… qui sont déjà des macros KTCC dans `tools_macro.cfg` |
| `use_relative_e_distances` | `1` | recommandé par Klipper |
| `single_extruder_multi_material` | `0` | un toolchanger = une hotend par outil, pas un MMU |
| `gcode_label_objects` | `octoprint` | marqueurs `; printing object` → annulation d'objet dans Mainsail (voir §5) |

### Texture du plateau

`bed_texture.png` (1920 × 1400 px, soit exactement 240 × 175 mm) se charge dans
`Réglages imprimante` → `Général` → `Forme du plateau` → `Définir…` →
`Texture personnalisée` → `Charger…`. PrusaSlicer enregistre un **chemin absolu** dans
le profil : posez le fichier à un endroit stable avant de le charger.

Elle reprend les coordonnées machine réelles — graduations tous les 10 / 50 mm,
coordonnées des 4 coins (celles du test du §3), ligne d'amorce de `PRINT_START` en
Y 41, emprise de la tour de purge, et rappel du côté des docks.

`make_bed_texture.py` la régénère : si vous changez `bed_shape`, la ligne d'amorce dans
`_PRINT_VARS` ou la position de la tour, ajustez les constantes en tête du script et
relancez `python3 make_bed_texture.py` (nécessite Pillow).

---

## 3. ⚠️ Zone d'impression — à vérifier avant la première impression

C'est le seul point que je n'ai pas pu valider sans la machine, **lisez-le**.

`[tool 0]` déclare `offset: 0,-34,22.70`, appliqué par KTCC via
`SET_GCODE_OFFSET X=0 Y=-34 Z=22.70` au moment du pickup. En sémantique Klipper,
`position_chariot = position_gcode + offset`. Donc, **outil chargé** :

| | limites chariot (`axis.cfg`) | contrainte | plage en coordonnées G-code |
|---|---|---|---|
| X | 30 → 300 | maillage 50 → 290 | **50 → 290** |
| Y | −10 → 240 | docks à partir de Y 190 ; maillage 5 → 180 | **39 → 214** |
| Z | −5 → 250 | offset Z 22.70 | **0 → 227** (profil : 220) |

D'où `bed_shape = 50x39,290x39,290x214,50x214` (240 × 175 mm) et
`max_print_height = 220`.

**Test à faire, à froid, plateau nu :**

```gcode
G28
T0                      ; charge l'outil, KTCC applique les offsets
G90
G1 Z20 F1000
G1 X50  Y39  F6000      ; coin avant gauche
G1 X290 Y39  F6000      ; coin avant droit
G1 X290 Y214 F6000      ; coin arrière droit
G1 X50  Y214 F6000      ; coin arrière gauche
G1 X170 Y120 F6000
TOOL_DROPOFF
```

Aucun message `Move out of range`, la buse reste au-dessus du plateau et ne s'approche
d'aucun dock → la zone est bonne. Sinon, corrigez `bed_shape` dans
`Réglages imprimante → Général → Forme du plateau`, et alignez
`_PRINT_VARS.prime_y` sur le nouveau bord avant (`prime_y` ≈ Y minimum + 2).

---

## 4. Ajouter les outils T1 à T4

Les docks (`docks/T0..T4.cfg`) et les têtes (`tools/*.cfg`) existent dans l'ancien
dépôt `klipper_config`, mais seul `[tool 0]` est actif dans la config courante.
Pour chaque outil ajouté :

1. **Klipper** — décommentez / dupliquez le bloc `[tool n]` dans `config/tools.cfg`
   (`extruder`, `fan`, `zone`, `park`, `offset`), plus l'`[extruder n]`, son
   `[tmc2660]`, son `[heater_fan]` et son `[fan_generic]`.
2. **`tools_macro.cfg`** — ajoutez le `[gcode_macro Tn]` correspondant et la ligne
   `SET_GCODE_VARIABLE MACRO=Tn VARIABLE=active VALUE=0` dans
   `SUB_SET_ALL_TOOLS_DEACTIVE` (aujourd'hui seul T0 y figure).
3. **Offsets** — mesurez-les et mettez-les dans `[tool n] offset:`, **pas** dans
   PrusaSlicer.
4. **PrusaSlicer** — basculez sur le profil `Jubilee Trident - 5 outils (T0-T4)`,
   et retirez les extrudeurs non montés via
   `Réglages imprimante → Général → Extrudeurs`.

`PRINT_START` gère déjà T0→T4 : il ignore proprement (avec un message) un outil
demandé par le G-code mais absent de la config.

### Tour de purge

`wipe_tower = 1` est actif dans les profils d'impression
(`x=222, y=140, largeur 60`, à l'arrière-droit pour ne pas croiser la ligne d'amorce en Y41) mais n'a d'effet qu'avec plusieurs extrudeurs. KTCC fait
déjà une pré-extrusion de la zone de fusion au pickup (`meltzonelength: 18`) ; la tour
complète le nettoyage. Si vous avez un bac de purge, passez `wipe_tower` à 0.

---

## 5. Annulation d'objet dans Mainsail (optionnel)

`[exclude_object]` est activé dans `print_macros.cfg` et le slicer émet les marqueurs
`; printing object`. Pour que Moonraker les convertisse, ajoutez dans `moonraker.conf` :

```ini
[file_manager]
enable_object_processing: True
```

Si vous préférez le mode `M486`, passez `gcode_label_objects` à `firmware` dans le
profil imprimante — la macro `M486` est déjà fournie.

---

## 6. Calibrations restant à votre charge

Les profils partent des valeurs de votre `printer.cfg`, mais rien ne remplace une
calibration :

- **Pressure advance** — `0.068` (votre valeur mesurée) est repris pour le PLA.
  PETG `0.08`, ABS `0.05`, TPU `0.4` sont des points de départ. Ils sont appliqués
  par outil via `SET_TOOL_PRESSURE_ADVANCE TOOL={current_extruder} ADVANCE=…` dans le
  `start_filament_gcode`, ce qui évite d'avoir à connaître le nom Klipper de
  l'extrudeur (`extruder`, `extruder1`, …).
- **Input shaper** — déjà par outil dans `[tool 0]`
  (`shaper_freq_x: 55.2 / shaper_freq_y: 46.6`, mzv) ; refaites-le pour chaque tête.
- **Débit / multiplicateur d'extrusion** — `extrusion_multiplier = 1` partout.
- **Vitesse Z** — `max_z_velocity: 5` dans `printer.cfg` rend les changements de
  couche lents ; `travel_speed_z` du profil est aligné dessus. Si votre mécanique
  le permet, montez les deux ensemble.
- **Accélérations** — les profils vont jusqu'à 10 000 mm/s², soit le `max_accel` de
  votre `[printer]`. Baissez si des ghosting apparaissent.

---

## 7. Versions de PrusaSlicer

### Version cible : 2.9.x (et 2.7 / 2.8)

Le bundle utilise la syntaxe `.ini` introduite en **2.7**. Pour PrusaSlicer **2.6**,
éditez `Jubilee_Trident_bundle.ini` avant import :

| Clé | 2.7 → 2.9 (dans le fichier) | 2.6 |
|---|---|---|
| `thumbnails` | `32x32/PNG, 400x300/PNG` | `32x32,400x300` + ligne `thumbnails_format = PNG` |
| `gcode_label_objects` | `octoprint` | `1` |
| `binary_gcode` | `0` | supprimer la ligne |

Sur 2.5 et antérieur, `gcode_flavor = klipper` n'existe pas : utilisez `marlin2`
(`machine_limits_usage = time_estimate_only` est déjà positionné, ce qui évite
l'émission de `M201`/`M203` que Klipper refuse).

### Et la 3.0 ?

État à ce jour : **alpha publique, profils Prusa uniquement**, chargement de
configurations custom « not fully supported yet ». Ce bundle `.ini` **n'est pas
importable** tel quel : la 3.0 a remplacé les presets `.ini` par du **YAML** et les
« vendor bundles » par des **sources de presets** (dépôts).

Il existe bien un chemin pour une imprimante custom, mais ce n'est pas « ajouter la
sienne au zip de Prusa » : l'updater accepte une **source locale**, c'est-à-dire un zip
à vous (`add_local_repository()` dans le code ; section « Local sources » dans
`Preset Sources & Updates`). Structure du zip, relevée dans les sources de
l'alpha11 :

```
ma_source.zip
├── manifest.json            # { "name", "id", "url" } obligatoires (+ "index_url")
├── vendor_indices.zip       # contient <Vendeur>.idx  (min_slic3r_version + versions)
└── <Vendeur>/<version>/
    ├── manifest.json        # [ { "filename", "filehash" (SHA-256) }, ... ]
    ├── vendor.yaml          # kind: vendor  + features
    ├── preset-printer-*.yaml, preset-tool-*.yaml,
    │   preset-print-*.yaml,   preset-filament-*.yaml
    └── assets/              # bed_texture, bed_model, thumbnail
```

Les presets sont des documents YAML typés par `kind:` (`vendor`, `printer`,
`printer_config`, `tool`, `sheet`, …) ; les noms d'options restent ceux qu'on connaît
(`bed_shape`, `start_gcode`, `nozzle_diameter`…), donc les valeurs du §2 se
reportent, mais la structure autour est entièrement nouvelle. Le hash SHA-256 de
chaque fichier doit être recalculé dans le manifeste de version à chaque
modification.

Ce n'est pas une piste à suivre tout de suite : le format bouge d'une alpha à l'autre —
c'est exactement la raison invoquée par Prusa pour avoir repoussé le portage des
profils tiers. Documentation officielle pointée par l'application :
<https://help.prusa3d.com/slicer-profiles/3>

Ce qui est acquis et qui ne changera pas :

- **Rien à refaire côté Klipper.** `config/print_macros.cfg` est indépendant du slicer.
  `PRINT_START` / `PRINT_END` / `SET_TOOL_PRESSURE_ADVANCE` resteront valables tels quels.
- **La 3.0 s'installe à côté de la 2.9** (dossier de configuration distinct), sans
  toucher à vos profils actuels.
- **Un projet 3.0 ouvert en 2.x perd sa configuration** (géométrie et peinture couleur
  seulement). Ne migrez pas un projet en cours de route.

Quand la 3.0 acceptera les imprimantes tierces, la reprise consistera à :

1. recréer l'imprimante `Jubilee Trident` dans l'assistant 3.0, en y reportant les
   valeurs du tableau §2 (`bed_shape`, `max_print_height`, `gcode_flavor = klipper`,
   `extruder_offset = 0`, `autoemit_temperature_commands = 0`) et les G-code
   personnalisés — ils sont, eux, inchangés ;
2. répartir les réglages d'impression entre le profil `Print` (commun) et les nouveaux
   profils **`ToolPrint`** (surcharges par outil). C'est le gain réel de la 3.0 pour
   ce Jubilee : largeur d'extrusion, vitesses et rétraction par tête, ce que le `.ini`
   2.9 ne sait pas exprimer autrement qu'en dupliquant des profils entiers ;
3. déclarer les 5 outils via le nouveau système de profils « à branches » (choix du
   nombre d'outils et des diamètres de buse dans un menu déroulant) plutôt qu'en
   éditant `nozzle_diameter = 0.4,0.4,0.4,0.4,0.4` à la main.

Sources : [PrusaSlicer 3.0.0-alpha11 (release notes)](https://github.com/prusa3d/PrusaSlicer/discussions/15592) ·
[PrusaSlicer 3.0 (Public Preview) — Prusa Knowledge Base](https://help.prusa3d.com/product/prusaslicer/prusaslicer-3-0-public-preview_2348) ·
[PrusaSlicer 3.0 Preview — blog Prusa](https://blog.prusa3d.com/prusaslicer-3-0-preview-built-for-the-future-of-3d-printing_137672/)
