# Source de presets PrusaSlicer 3.0 — Jubilee Trident

Source locale (« local source ») pour **PrusaSlicer 3.0**, qui a remplacé les bundles
`.ini` par des **dépôts de presets en YAML**. Pour PrusaSlicer 2.7 → 2.9, c'est le
bundle `.ini` du dossier voisin `../prusaslicer/` qu'il faut utiliser.

> **3.0 est une alpha.** Le format bouge d'une alpha à l'autre — c'est la raison
> invoquée par Prusa pour avoir repoussé le portage des profils tiers. Ce dossier a été
> écrit contre **3.0.0-alpha11** : tenez la 2.9 pour la production.

## Chargement

```
python3 build_source.py     ->  ekozan-jubilee-source.zip
```

PrusaSlicer 3.0 → **Preset Sources & Updates** → **Local sources** → ajouter le zip.

Deux imprimantes apparaissent ensuite dans l'assistant : `Jubilee Trident - 1 outil`
et `Jubilee Trident - 5 outils`, avec les buses 0.4 et 0.6, trois profils d'impression
et quatre filaments.

N'ajoutez **pas** votre imprimante au zip de Prusa : les dépôts sont indexés par `id`,
un seul dépôt par `id` peut être sélectionné, et la synchronisation en ligne réécrit le
manifeste. Une source séparée cohabite proprement.

## Contenu

```
prusaslicer3/
├── build_source.py      assemble le zip (bibliothèque standard uniquement)
├── check_vendor.py      rejoue les invariants du chargeur (pyyaml)
├── make_thumbnail.py    régénère la vignette (Pillow)
├── Ekozan.idx           versions publiées + min_slic3r_version
└── vendor/
    ├── vendor.yaml                    déclaration matérielle
    ├── preset-printer-jubilee.yaml    réglages imprimante
    ├── preset-print-jubilee.yaml      0.15 / 0.20 / 0.30 mm
    ├── preset-tool-jubilee.yaml       surcharges par outil (ToolPrint)
    ├── preset-filament-jubilee.yaml   PLA / PETG / ABS-ASA / TPU
    └── assets/                        texture de plateau, vignette
```

`vendor.yaml` décrit le **matériel** (documents `kind:` séparés par `---`) :

| Document | Rôle |
|---|---|
| `vendor` | identité + déclaration des *features* |
| `printer` | un seul modèle, `Jubilee Trident` |
| `tool` ×2 | buses 0.4 et 0.6, offertes via leur `condition` |
| `sheet` | surface d'impression |
| `printer_config` ×2 | ce que l'utilisateur choisit : 1 outil ou 5 outils |

> **Piège** : `HwConfigEvaluator::create_printer_config` impose
> `len(tools) == tool_count` **ou** `len(tools) == 1`. La liste `tools` d'un
> `printer_config` n'est pas le catalogue des buses disponibles — c'est la tête par
> défaut, répliquée sur tous les emplacements. Le choix du diamètre vient des documents
> `tool` et de leur `condition`. Y mettre deux entrées pour `tool_count: 1` fait
> silencieusement disparaître l'imprimante de la liste. `check_vendor.py` vérifie ça.

Le nom affiché n'est pas celui du `printer_config` : `suggest_name` le reconstruit à
partir du `name` du modèle, du nombre d'outils et de la buse — d'où
« Jubilee Trident 0.4 » et « Jubilee Trident 5T 0.4 ».

Les `preset-*.yaml` portent les **valeurs**, avec des `variants` conditionnels
(`condition: tool.nozzle_diameter == 0.4`) au lieu de dupliquer des profils entiers.
Le nom de fichier est libre : tout `*.yaml` sauf `vendor.yaml` est chargé comme preset.

## Ce qui change par rapport au bundle 2.9

| | 2.9 (`.ini`) | 3.0 (`.yaml`) |
|---|---|---|
| Retraction | profil **imprimante** | profil **impression** |
| Position de la tour de purge | `wipe_tower_x` / `wipe_tower_y` | **supprimées** |
| Surcharges par outil | duplication de profils | type de profil **ToolPrint** |
| Diamètre de buse | `nozzle_diameter` dans le profil | *feature* du document `tool` |
| Variantes 1 / 5 outils | deux profils imprimante | deux `printer_config`, un `base_model` |

Inchangé : les noms d'options (`bed_shape`, `start_gcode`, `gcode_flavor: klipper`…),
donc les valeurs se transposent une par une. Inchangé aussi : **rien à modifier côté
Klipper**, `config/print_macros.cfg` ne dépend pas du slicer.

## Deux pièges de la 3.0 qui ne font aucun bruit

`BundleLoader::load` **attrape** les exceptions de parsing, les journalise et passe au
vendeur suivant. Une erreur dans un YAML ne provoque donc ni crash ni message : le
vendeur disparaît simplement de la liste des imprimantes. Deux causes rencontrées :

**1. YAML réinterprète les points.** `extruder_offset: [0x0]` non quoté est relu comme
l'**entier 0**, et `0x180` comme **384**. Prusa quote systématiquement ces valeurs —
et, dans `bed_shape`, quote exactement `'0x0'` et `'0x180'` en laissant `180x0` nu.
Écrivez toujours :

```yaml
extruder_offset:
- '0x0'
```

**2. Des options booléennes sont devenues des énumérations.** `support_material` vaut
désormais `none` / `enforcers_only` / `everywhere`, plus `0` / `1`.

`check_vendor.py` contrôle les deux.

## Modifier puis reconstruire

1. Éditez les YAML dans `vendor/`.
2. Bumpez `version:` dans `vendor.yaml` **et** ajoutez la ligne correspondante en tête
   de `Ekozan.idx` — `build_source.py` refuse de construire si les deux divergent.
3. `python3 build_source.py`, puis rechargez la source dans PrusaSlicer.

`build_source.py` lance `check_vendor.py` au passage (si pyyaml est installé). Celui-ci
rejoue les invariants du chargeur : références `printer` / `tool` / `sheet` résolues,
cardinalité de `tools`, cohérence des technologies, cibles d'`inherits` existantes,
`default_print` / `default_material` pointant sur des presets réellement nommés, et
assets présents. Il affiche aussi le nom tel qu'il apparaîtra dans la liste.

Le script recalcule à chaque build le SHA-256 de chaque fichier dans
`Ekozan/1.0.0/manifest.json` ; c'est obligatoire, l'updater compare ces empreintes.

## Ce qui est vérifié, et ce qui ne l'est pas

Vérifié contre les sources de 3.0.0-alpha11 :

- structure du zip conforme à `LocalPresetUpdaterRepository::extract_local_archive_repository`
  (`manifest.json` + `vendor_indices.zip` à la racine, presets sous `<Vendeur>/<version>/`) ;
- `vendor.yaml` valide contre `specs/presets/vendor-schema.json` — les fichiers de Prusa,
  eux, n'y passent pas entièrement ;
- **les 166 options utilisées existent toutes** dans le `PrintConfig` de la 3.0
  (c'est ce contrôle qui a fait tomber `wipe_tower_x/y` et `filament_retract_*`) ;
- `gcode_flavor: klipper` toujours présent ;
- invariants de `create_printer_config` rejoués par `check_vendor.py`.

Non vérifié, faute de pouvoir lancer l'alpha ici :

- le rendu réel dans l'assistant (vignette PNG — Prusa livre des SVG ; c'est cosmétique) ;
- l'évaluation des `condition:` sur un `base_model` custom ;
- l'absence de `bed_model` (aucun STL fourni) : le plateau devrait s'afficher plat avec
  la seule texture.

Si l'import échoue, le message de l'updater nomme le fichier fautif — envoyez-le moi.
