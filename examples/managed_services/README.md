# Example: Managed Services / Externally Managed Accounts walkthrough

A narrated GIF of page 2 of the Lucid architecture figure. It starts with the
**Data Production Operator** working through the Algorithm Development
Environment and the Job Monitoring Dashboard, then follows the work through
processing, storage, cataloging and viewing. Who manages what comes second,
right after the operator, and the story closes on the Science Investigator.

The figure's two account boundaries carry ownership throughout:

| box | managed by |
| --- | --- |
| **Managed Services Account** (blue) | NASA ESD |
| **Externally Managed Accounts** (red) | each organization, for itself |

A connector that crosses between them is drawn **dashed**, except where
`layout.SOLID` says otherwise.

## Build

    ./build.sh                        # -> managed-services.gif (hand-drawn)
    FLOWGIF_STYLE=flat ./build.sh     # -> managed-services-flat.gif
    ./build.sh --list-sections        # the chapters
    ./build.sh --section=monitor      # -> sections/monitor.gif
    ./build.sh --all-sections
    ./build.sh --poster               # -> sections/overview.png, 3200x1800

Needs `rsvg-convert`, `ffmpeg` and `magick`. No Python packages.

Every section shows the whole canvas. Sections differ in which beats are
narrated and which frames they cover; the rest of the figure stays in place,
receding while a beat runs.

## Change the words

All narration lives in **`story.py`**: one entry per beat, giving

- its caption,
- what it points at,
- which connectors draw in, and which nodes pulse,
- how long it runs.

Nothing in it is geometry. Captions appear as a card in a **band under the
figure**, never on top of it, and the font steps down if a caption is long,
so rewording never needs a layout change. The card's position and size are
handles (`box.caption`, and `box.caption_shot` for a beat with a screenshot).
The canvas is 1600x1110: the 1600x900 figure plus the band. The GIF is
1280x888, while the poster is the figure alone at 16:9.

## Move things by hand

    ./edit.sh              # or, from the repo root: ./edit.sh managed
    ./edit.sh flat
    ./edit.sh --stop

Drag anything and the real render redraws behind it after a moment. **Save to
project** writes `overrides.json` here; then `./build.sh`.

| handle | what it moves |
| --- | --- |
| blue dot | a node; the corner square resizes its icon |
| green dot | a label, independently of its icon (it stays attached) |
| orange dot | a connector vertex. **Double-click a line to add a bend**; right-click a bend to remove it |
| dashed box | an account box, the User Dashboard, a **caption card** or a **screenshot**; grab it by the border, resize by the corner |
| side panel | `flowlabel.*.t` slides an edge label along its line (0 = source, 1 = target) |

Both views share one geometry, so a saved `overrides.json` applies to the
hand-drawn and flat renders alike. It stores only what differs from the
defaults: delete a key to revert one thing, or the file to revert everything.

## Screenshots

The Job Monitoring chapter shows screenshots in the caption band, beside the
caption. Put the files in
`assets/` (gitignored, since they are of a live system) and list them in
`story.SHOTS`. Each inset is a `shot.<key>` handle, so drag it to place and
size it.

A missing file draws a labelled placeholder and prints a warning. It never
renders as a silent gap.

## Icons

Outline icons from [Lucide](https://lucide.dev), vendored into `icons.py` under
their ISC licence. They are inline vectors, so they need no asset staging. To
swap one, change its name in `layout._NODES`.

## What the diagram asserts

The arrow directions are **claims about the architecture**, transcribed from
the Lucid source and then corrected where a row says so. They are not visual
choices.

| from | label | to | note |
| --- | --- | --- | --- |
| Data Production Operator | Accesses | User Dashboard | |
| Authentication & Authorization | Authenticates | User Dashboard | |
| Authentication & Authorization | Reads | User Management | crosses accounts |
| Data Processing System | Accesses | Algorithm Catalog | crosses accounts. **Corrected**: Lucid draws this from the managed ADE, which does not reach the catalog |
| Algorithm Development Env. | Triggers | Data Processing System | |
| Data Processing System | Writes | Job Monitoring Dashboard | **Corrected**: reversed from Lucid; the system writes job status to the dashboard |
| Data Processing System | Writes outputs | File Storage | crosses accounts, but drawn **solid** to pair with "Updates STAC collections" (`layout.SOLID`). **Corrected**: Lucid routes this through Compute Instances, dropped as redundant; Lucid's label is "Produces" |
| Data Processing System | Updates STAC collections | Data Catalog | **Added**: not in the Lucid figure |
| Data Service APIs | Queries | Data Catalog | |
| Data Catalog | Indexes | File Storage | crosses accounts |
| Data Service APIs | Serves | Visualization Tools | |
| Operator | Views | both Visualization Tools | |
| Science Investigator | Accesses | org Algorithm Development Env. | |
| org Algorithm Development Env. | Publishes / Reads | Algorithm Catalog / File Storage | |
| Science Investigator | Views | both Visualization Tools | |

**The personas are sources only.** No flow may terminate on one, and
`tests/test_managed_services.py` enforces it.

## Files

    story.py       the narration -- edit the words here
    layout.py      every coordinate, each a handle
    gen_frames.py  draws the frames; builds GIFs, sections, poster, editor
    icons.py       vendored Lucide outline icons
    build.sh       the pipeline (wraps gen_frames.py)
    edit.sh        the live-preview editor (svg_flow_animator.serve)
