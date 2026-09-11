# Source de presets PrusaSlicer 3.0 — Jubilee Trident

Source locale (« local source ») pour **PrusaSlicer 3.0**, qui a remplacé les bundles
`.ini` par des **dépôts de presets en YAML**. Pour PrusaSlicer 2.7 → 2.9, c'est le
bundle `.ini` du dossier voisin `../prusaslicer/` qu'il faut utiliser.

> **3.0 est une alpha.** Le format bouge d'une alpha à l'autre — c'est la raison
> invoquée par Prusa pour avoir repoussé le portage des profils tiers. Ce dossier a été
> écrit contre **3.0.0-alpha11** : tenez la 2.9 pour la production.

> **⚠ alpha11 n'affiche aucun vendeur tiers dans « Add printer ».** Ce n'est pas un
> défaut de ce profil : l'assistant de configuration n'est pas encore écrit, et la
> liste des imprimantes est câblée sur deux vendeurs. Détails et contournement dans
> [« alpha11 : pourquoi l'imprimante n'apparaît pas »](#alpha11--pourquoi-limprimante-napparaît-pas).

## Chargement

```
python3 build_source.py     ->  ekozan-jubilee-source.zip
```

PrusaSlicer 3.0 → **Preset Sources & Updates** → **Local sources** → ajouter le zip.

La source s'installe et se charge correctement (le log le confirme, voir plus bas) ;
en revanche **alpha11 ne propose encore aucune imprimante tierce dans « Add printer »**.
Le contenu — buses 0.4 et 0.6, trois profils d'impression, quatre filaments — est prêt
et attend que Prusa branche l'assistant de configuration.

N'ajoutez **pas** votre imprimante au zip de Prusa : les dépôts sont indexés par `id`,
un seul dépôt par `id` peut être sélectionné, et la synchronisation en ligne réécrit le
manifeste. Une source séparée cohabite proprement.

## Contenu

```
prusaslicer3/
├── build_source.py      assemble le zip (bibliothèque standard uniquement)
├── check_vendor.py      rejoue les invariants du chargeur (pyyaml)
├── extract_config_keys.py  extrait config_keys.json des sources de PrusaSlicer
├── config_keys.json     options connues de la 3.0 et boite de chacune
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

## alpha11 : pourquoi l'imprimante n'apparaît pas

Le profil se charge. Le log (`~/Library/Application Support/PrusaSlicer3-dev/shared_runtime/log.txt`
sur macOS) le dit noir sur blanc :

```
[info] [BundleLoader.cpp:107] Loading preset bundle vendor dir:
       .../presets/local/ekozan-jubilee/Ekozan
```

…sans le `Loading bundle ... failed with error ...` qui suivrait un YAML invalide. Le
vendeur est donc bien lu, analysé et rangé dans le bundle.

Ce qui manque est ailleurs. Dans `PresetInteractor::load_preset_bundle`, les
`printer_config` déclarés par un vendeur ne sont transformés en imprimantes
sélectionnables que pour **deux vendeurs codés en dur** :

```cpp
// TODO: remove this when config wizard is ready
{
    HwConfigEvaluator config_eval;
    for (const auto& vendor : {"PrusaResearch", "PrusaResearchSLA"}) {
        ...
        auto printer_config = config_eval.create_printer_config(...);
        preset_bundle.printer_configs.emplace(printer_config.id, printer_config);
    }
}
```

*(`src/slic3r-shared/src/Slic3r/Biz/Preset/PresetInteractor.cpp`, ligne 321.)*

`AddPrinterPanel` liste `preset_bundle.printer_configs` — la barre latérale du
sélecteur affiche d'ailleurs un unique bouton « Prusa3D », lui aussi en dur. Le seul
autre chemin de remplissage, la relecture des configurations sauvegardées, est
commenté dans `BundleLoader.cpp` :

```cpp
// TODO read/append user printer configs
//vendor_bundle.printer_configs = load_vendor_user_configs(...);
```

**Aucun vendeur tiers ne peut donc apparaître dans « Add printer » en alpha11**, quel
que soit le contenu de son `vendor.yaml`. Rien à corriger de notre côté : il faut
attendre l'assistant de configuration.

### Le contournement : ouvrir un projet 2.x

Un seul chemin instancie la configuration matérielle d'un vendeur **quelconque** :
l'ouverture d'un projet PrusaSlicer 2.x. `load_legacy_preset_metadata` parcourt tous
les vendeurs installés et cherche celui qui revendique le `printer_model` inscrit dans
le 3MF :

```cpp
for (const auto& vendor_bundle : preset_bundle.vendor_bundles | std::views::values) {
    const auto* printer_config_template =
        vendor_bundle.vendor_data.find_printer_config_template_by_legacy_printer_model(
            printer_model
        );
    ...
}
```

D'où, depuis la 1.0.3, le `legacy_printer_model: [Jubilee Trident]` porté par le
`printer_config` `jubilee-1t` — il reprend exactement le `printer_model` du bundle 2.9
voisin. En pratique :

1. dans PrusaSlicer **2.9**, avec le profil Jubilee, enregistrez un projet (`.3mf`) ;
2. dans la **3.0**, ouvrez-le par **File → Open Project** ;
3. la Jubilee devient l'imprimante sélectionnée, avec ses outils, sa surface et sa
   vignette ; les profils d'impression et de filament de cette source deviennent
   sélectionnables.

Il faut bien **ouvrir le projet**, pas importer la géométrie : seul
`load_file_as_project` transmet le bundle des vendeurs à `load_legacy_project`, l'import
d'objet appelle `load_from_project(path, std::nullopt)` et saute toute la résolution de
l'imprimante. Et il faut un `.3mf` : `extract_legacy_preset_metadata` n'est atteignable
que depuis `_3MF_Importer` (l'entrée `Metadata/Slic3r_PE.config` de l'archive), donc ni
un `.ini` de configuration ni un G-code ne conviennent.

Deux limites : la configuration ainsi obtenue n'est pas persistée au redémarrage
(`save_bundle_configs` est également désactivé), et un seul `printer_config` peut
revendiquer un `printer_model` donné — le premier trouvé gagne, d'où le choix de la
configuration 1 outil.

## Une troisième cause de silence : la mauvaise boîte

Les options ne sont pas validées en bloc : `PresetEvaluator` confronte chaque clé à la
classe de réglages correspondant au `kind` du preset, et **jette celles qui n'y
appartiennent pas** sans faire échouer quoi que ce soit :

```
[error] [PresetEvaluator.cpp:312] Invalid key <option> for Slic3r::Domain::ToolPrintSettings
```

Le réglage est simplement ignoré. La correspondance vient de `ConfigBoxesFDM.cpp` :

| `kind:` du preset | classe | `FDMConfigLocation` |
|---|---|---|
| `printer` | `PrinterSettings` | `Printer` |
| `print` | `PrintSettings` | `Print` |
| `tool_print` | `ToolPrintSettings` | `Tool` |
| `material` / `filament` | `FilamentSettings` | `Filament` |

Une boîte accepte les options dont la `location` est la sienne, **plus** celles dont
l'`overrides_in` la contient. `retract_length`, par exemple, vit dans `Print` et se
surcharge dans `Filament` et `Tool`.

La référence n'est pas `Biz/Config/Legacy/PrintConfig.cpp` — celui-là ne sert qu'à
relire les profils 2.x — mais `src/slic3r-domain/.../ConfigDefsFDM.cpp` et
`ConfigCommon.cpp`. `extract_config_keys.py` en extrait la table complète :

```
python3 extract_config_keys.py /chemin/vers/PrusaSlicer > config_keys.json
```

`check_vendor.py` s'en sert pour refuser toute option inconnue ou mal rangée. C'est ce
contrôle qui a déplacé `min_layer_height` / `max_layer_height` du profil imprimante
vers le profil d'impression en 1.0.3.

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
- **toutes les options utilisées existent et sont dans la bonne boîte**, table extraite
  de `ConfigDefsFDM.cpp` / `ConfigCommon.cpp` (c'est ce contrôle qui a fait tomber
  `wipe_tower_x/y`, `filament_retract_*`, puis déplacé `min/max_layer_height`) ;
- chargement du bundle sans erreur, **confirmé sur une installation réelle** par le log
  de 3.0.0-alpha11 ;
- `gcode_flavor: klipper` toujours présent ;
- invariants de `create_printer_config` rejoués par `check_vendor.py`.

Non vérifié, faute de pouvoir lancer l'alpha ici :

- le rendu réel dans l'assistant (vignette PNG — Prusa livre des SVG ; c'est cosmétique) ;
- l'évaluation des `condition:` sur un `base_model` custom ;
- l'absence de `bed_model` (aucun STL fourni) : le plateau devrait s'afficher plat avec
  la seule texture ;
- le contournement par projet 2.x décrit plus haut : lu dans le code, pas encore essayé
  sur l'application.

Si quelque chose cloche, le fichier `shared_runtime/log.txt` du dossier de données est
la source de vérité — c'est lui qui a permis d'écarter le parsing et de remonter au
verrou de l'alpha11.
