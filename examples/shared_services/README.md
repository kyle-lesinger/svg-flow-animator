# Example: Shared Data System Capabilities walkthrough

The shared-capabilities variant of `examples/managed_services/`. That example
is left as it is. This one tells the same story through **three** boxes, so
that nothing is drawn twice:

| box | holds |
| --- | --- |
| **Managed Services Account** (blue) | Authentication & Authorization, the User Dashboard (Algorithm Development Environment, Job Monitoring Dashboard), Data Processing System, Data Service APIs |
| **Shared Data System Capabilities** (purple) | the **only** Algorithm Catalog, Data Catalog and Visualization Tools |
| **Externally Managed Accounts** (red) | User Management, the project's own Algorithm Development Environment, File Storage |

Anything in purple appears nowhere else, so the second set of Visualization
Tools from the original is gone. `tests/test_shared_services.py` enforces
that, and reruns every managed_services check against this example too.

The captions keep the original wording and add snippets from Goal 1 ("Research
and Develop Innovative Data System Capabilities"). A new beat explains that
each of these capabilities can be centrally managed, externally owned by a
project, or shared.

A connector that crosses between two boxes is drawn **dashed**, except where
`layout.SOLID` says otherwise.

## Build

    ./build.sh                        # -> shared-services.gif (hand-drawn)
    FLOWGIF_STYLE=flat ./build.sh     # -> shared-services-flat.gif
    ./build.sh --list-sections        # the chapters
    ./build.sh --section=monitor      # -> sections/monitor.gif
    ./build.sh --all-sections
    ./build.sh --poster               # -> sections/overview.png, 3200x1920

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
The canvas is 1600x1170: the 1600x960 figure plus the band. The GIF is
1280x936, while the poster is the figure alone at 3200x1920.

## Move things by hand

    ./edit.sh              # or, from the repo root: ./edit.sh shared
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
| Data Processing System | Accesses | Algorithm Catalog (shared) | crosses boxes |
| Algorithm Development Env. | Triggers | Data Processing System | |
| Job Monitoring Dashboard | Reads | Data Processing System | the dashboard reads job status from the system (Lucid's arrow runs this way, labelled "Writes") |
| Data Processing System | Writes outputs | File Storage | crosses accounts, but drawn **solid** to pair with "Updates STAC collections" (`layout.SOLID`). **Corrected**: Lucid routes this through Compute Instances, dropped as redundant; Lucid's label is "Produces" |
| Data Processing System | Updates STAC collections | Data Catalog (shared) | crosses boxes, but drawn solid to pair with "Writes outputs" |
| Data Service APIs | Queries | Data Catalog | |
| Data Catalog | Indexes | File Storage | crosses boxes |
| Data Service APIs | Serves | Visualization Tools | |
| project Algorithm Development Env. | Publishes / Reads | Algorithm Catalog / File Storage | drawn, not narrated |
| Operator | Views | Visualization Tools (shared) | temporary |
| Science Investigator | Views / Accesses | Visualization Tools / project ADE | temporary |
| Applications Developer | Calls | Data Service APIs | temporary; not in the Lucid figure |
| Decision Maker / Analyst | Views | Visualization Tools (shared) | temporary; not in the Lucid figure |

**Users' lines are temporary** (`layout.TRANSIENT`). In the closing chapters
each user's set draws in, then fades once the next user's lines are in, so the
right side of the figure never fills up with curves. Every user but the
operator **appears** only at their first beat (`layout.LATE_PERSONAS`) and then
stays, so the closing frame shows all of them. The editor shows every line and
every user, so all of them can be dragged.

**The personas are sources only.** No flow may terminate on one, and
`tests/test_managed_services.py` enforces it.

## Files

    story.py       the narration -- edit the words here
    layout.py      every coordinate, each a handle
    gen_frames.py  draws the frames; builds GIFs, sections, poster, editor
    icons.py       vendored Lucide outline icons
    build.sh       the pipeline (wraps gen_frames.py)
    edit.sh        the live-preview editor (svg_flow_animator.serve)
