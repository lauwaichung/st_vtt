# Writing a content pack

A content pack tells st_vtt what game it is running: the stats, how rolls
work, the shared moves, each playbook, the village sheet, follower rules, and
a library of arcana. The engine renders sheets from it and never needs code
changes for new content.

`content/schema.json` is a JSON Schema generated from the server models; point
your editor at it for autocomplete and validation. `uv run st-vtt validate
<path>` checks a pack and reports errors with the file and field involved.
`content/example/` is a small pack that uses every feature.

## Files

A pack is a **directory** (recommended) or a single JSON file. In a directory,
every `*.json` file is merged:

- `pack` and `followers` are objects and may appear in exactly one file each.
- `playbooks`, `arcana` and `shared_sheets` are lists; lists from several
  files concatenate. A file placed directly inside a `playbooks/`, `arcana/`
  or `shared_sheets/` sub-directory is a single entry.
- `moves` is an object of `group name -> list of moves`; groups from several
  files concatenate.

All text fields marked *markdown* support a small subset: paragraphs, `**bold**`,
`*italic*`, `` `code` `` and `- ` bullet lists.

Unknown keys are errors, so typos are caught.

## `pack`

```json
{
  "pack": {
    "id": "mygame",
    "name": "My Game",
    "description": "optional",
    "stats": [{"id": "str", "label": "STR", "min": -1, "max": 3}, ...],
    "stat_array": [2, 1, 1, 0, 0, -1],
    "debilities": [{"id": "battered", "label": "Battered", "affects": ["str", "dex"], "text": "..."}],
    "roll": {
      "base": "2d6", "advantage": "3d6kh2", "disadvantage": "3d6kl2",
      "tiers": [{"label": "10+", "min": 10}, {"label": "7-9", "min": 7, "max": 9}, {"label": "6-", "max": 6}],
      "mark_xp_on": ["6-"]
    },
    "xp": {"level_up_cost": "6 + 2*level", "start_level": 1},
    "dice_presets": [{"label": "Damage", "expr": "{damage_die}"}, {"label": "d6", "expr": "1d6"}],
    "load": {"light": 3, "normal": 6, "heavy": 9},
    "gear_tags": ["hand", "close", "piercing"],
    "hold_names": ["Guard"]
  }
}
```

| field | meaning |
|---|---|
| `stats` | The stat blocks on every sheet. `id` is what moves refer to. |
| `stat_array` | Values to distribute at creation; the checklist compares the sheet against it. A playbook can override with its own `stat_array`. |
| `debilities` | Checkboxes on the sheet. `affects` lists stat ids that roll with disadvantage while marked; the roll dialog applies it automatically. |
| `roll` | Dice expressions for a normal / advantage / disadvantage roll, and the result tiers. Tier labels are the keys used in a move's `outcomes`. |
| `xp.level_up_cost` | Arithmetic in `level`, e.g. `6 + 2*level`. |
| `dice_presets` | Buttons in the dice bar. `{damage_die}` and `{<stat id>}` resolve against the rolling character. |
| `load` | Optional. Load thresholds; the gear section sums item weights and labels the load. |
| `hold_names` | Hold counters shown on every sheet in addition to those introduced by moves. |

## Moves

Moves appear in `moves` (shared by everyone, grouped), in a playbook's
`moves`, in an arcanum's `moves`, and in a shared sheet's `moves`. Move ids must be
unique across the whole pack.

```json
{
  "id": "brawl",
  "name": "Brawl",
  "trigger": "When you trade blows with something up close...",
  "text": "...roll +STR.",
  "roll": {"stat": "str", "bonus": 0},
  "outcomes": {"10+": "...", "7-9": "...", "6-": "..."},
  "hold": {"name": "Guard", "note": "Spend 1 Guard to..."},
  "pips": 3,
  "requires": {"level": 2, "moves": ["other_move_id"]},
  "replaces": "other_move_id",
  "tags": ["starting"]
}
```

| field | meaning |
|---|---|
| `roll.stat` | A stat id; a list of stat ids the player chooses between; `"choose"` for any stat; or `null` for a "+nothing" roll. Omit `roll` for moves that do not roll. |
| `roll.bonus` | Flat bonus added to the roll. |
| `outcomes` | Text per tier label; shown on the roll card. |
| `hold` | Declares a hold currency; a counter for it appears in the sheet's Hold row. |
| `pips` | Number of ◇ boxes tracked on the move. |
| `requires` | Level gate and/or prerequisite moves. Shown as a warning in the move picker, not enforced. |
| `replaces` | Taking this move removes the named one. |

## Playbooks

```json
{
  "id": "wanderer",
  "name": "The Wanderer",
  "blurb": "Knows every road.",
  "hp_max": 18,
  "damage_die": "1d8",
  "armor": 0,
  "stat_array": null,
  "inserts": ["gear", "followers", "arcana"],
  "hold_names": [],
  "sections": [ ... ],
  "starting_moves": {"fixed": ["well_traveled"], "choose": [{"n": 1, "from": ["watchful", "iron_gut"]}]},
  "moves": [ ... ]
}
```

- `inserts` picks which core sections the sheet shows: `gear`, `followers`,
  `arcana`. Stats, moves and notes always appear.
- `starting_moves.fixed` are added on creation; each `choose` group shows up in
  the creation checklist until `n` of `from` are taken.
- The expected number of playbook moves is starting moves plus one per level
  above `start_level`; the Moves header hints when more can be picked.

### Sections

Everything playbook-specific that is not a move is a **section**. Sections
render in order, above the Moves section, and store their value in the
character document under `sections.<id>`.

| type | value stored | fields |
|---|---|---|
| `choose` | option id or null | `options` |
| `multichoose` | list of option ids | `options`, `min`, `max` |
| `checklist` | list of option ids | `options` |
| `pips` | number | `max` |
| `text` | string (markdown) | `placeholder` |
| `table` | list of row objects | `columns` |
| `names` | chosen name | `lists` — clicking a name also sets the character's name |

Common fields: `id`, `title`, `help` (shown under the title), `required`
(default `true`; unfilled required sections appear in the creation checklist).

Options: `{"id", "label", "text", "effects", "pips"}`. `pips` gives the
option a row of ◇ boxes on the sheet while it is selected (uses, charges,
doses). `effects` lets a choice change the sheet without engine support:

```json
{"id": "trailhand", "label": "Trailhand", "text": "You learned the roads by walking them.", "effects": {"moves": ["trailsense"], "armor": 1, "hp": 2, "tags": ["respected"]}}
```

Selecting the option adds the moves and adds to armor / max HP; deselecting
reverses it. (`checklist` sections do not apply effects.)

Table columns: `{"id", "label", "type"}` with type `text` (default), `number`,
`check`, `select` (with `options`), or `dice`. A `dice` cell holds a dice
expression such as `1d8+1` and gets a Roll button; the roll is labelled with
the row's first text column, so an NPC table rolls "Bandit · Damage".

## `shared_sheets`

Shared sheets are edited by the whole table (or only by the GM). The village
is one; a GM screen is another. The pack defines **templates**; the GM creates
instances in the app.

```json
{
  "shared_sheets": [
    {
      "id": "village",
      "name": "The Village",
      "blurb": "The home everyone shares.",
      "auto_create": true,
      "visibility": "table",
      "stats": [{"id": "luck", "label": "Luck", "start": 1, "min": -3, "max": 3, "help": "..."}],
      "sizes": ["camp", "hamlet", "village", "town"],
      "size_start": "village",
      "debilities": [{"id": "hungry", "label": "Hungry", "text": "..."}],
      "sections": [ ...same section types as playbooks... ],
      "moves": [ ... ]
    },
    {
      "id": "gm_screen",
      "name": "GM Screen",
      "visibility": "gm",
      "sections": [{"id": "npcs", "title": "NPCs", "type": "table",
                    "columns": [{"id": "name", "label": "Name"}, {"id": "hp", "label": "HP", "type": "number"}, {"id": "damage", "label": "Damage", "type": "dice"}]}]
    }
  ]
}
```

| field | meaning |
|---|---|
| `auto_create` | Create one instance the first time the campaign starts (once; deleting it does not bring it back). |
| `visibility` | `table` (default): everyone sees and edits it. `gm`: only GMs see it, edit it, or receive its updates. |
| `stats`, `sizes`, `debilities` | Optional. Omit them for a sheet that is just sections. |

Shared-sheet moves get Roll buttons too; use `"roll": {"stat": null}` and let
players add the sheet's stat as a bonus in the dialog.

## `followers`

```json
{
  "followers": {
    "loyalty_max": 3,
    "tags": ["loyal", "brave", "cunning", "green"],
    "costs": ["coin", "respect"],
    "instincts": ["to look after their own"],
    "fields": [{"id": "origin", "label": "Origin"}]
  }
}
```

Followers are created on the sheet. `tags`, `costs` and `instincts` are
suggestions offered while typing; `fields` adds extra text fields to every
follower. Followers already carry name, tags, HP, armor, damage die, instinct,
cost, loyalty, moves, gear, notes, and optional group members.

## `arcana`

```json
{
  "id": "wayfinding_stone",
  "name": "The Wayfinding Stone",
  "kind": "minor",
  "tags": ["small", "fragile"],
  "description": "markdown",
  "questions": ["Who lost it before you?"],
  "prerequisites": "Spend a night meditating on what you have lost.",
  "moves": [ ...moves... ],
  "trackers": [{"id": "charges", "label": "Charges", "type": "pips", "max": 3}, {"id": "attuned", "label": "Attuned", "type": "toggle"}]
}
```

Library arcana are copied onto a sheet when added, so later edits to the pack
do not rewrite what a player already has. Players can also write custom arcana
directly on the sheet. Tracker types: `pips`, `counter`, `toggle`.

## Character JSON

An exported character is the raw document the server stores:

```json
{
  "pack_id": "mygame", "playbook": "wanderer", "name": "...", "pronouns": "", "look": "",
  "stats": {"str": 2}, "hp": {"current": 18, "max": 18}, "armor": 1, "xp": 0, "level": 1,
  "debilities": {"battered": false},
  "moves": {"taken": ["well_traveled"], "pips": {"iron_gut": 2}, "hold": {"Focus": 1}},
  "sections": {"background": "trailhand", "appearance": ["weathered"]},
  "option_pips": {"possessions": {"kit": 1}},
  "gear": {"load": 0, "items": [{"id": "x", "name": "Walking staff", "tags": ["reach"], "weight": 1, "uses": null, "notes": ""}]},
  "followers": [], "arcana": [], "custom_moves": [],
  "notes": "", "gm_notes": "", "creation_done": false
}
```

You can write one by hand and import it. Missing fields are filled with
defaults; unknown playbooks or move ids are reported as warnings and kept.
