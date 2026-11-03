# Example: Sentinel-2 & Landsat algorithm review

Who reviews what, and when, as two hand-drawn animations.

| picture | shows |
| --- | --- |
| `review-workflow.apng` / `.png` | reviewers -> review tasks -> the algorithms; the animation walks the tasks in schedule order |
| `review-timeline.apng` / `.png` | a Gantt of the same tasks, bars growing in date order, reviewers named on each |

The `.apng` files are the animations, and the `.png` files are 3200x1800
stills. Both are build products, so they are not committed.

## Build

    ./build.sh            # sketch (the default)
    ./build.sh flat       # clean render, saved with a -flat suffix

Needs `rsvg-convert` and `ffmpeg`. No Python packages. Takes about 30 seconds.

## Change who does what

Edit the two tables at the top of `review.py`:

- `TASKS`: each review task's title, detail line and colour.
- `PEOPLE`: each reviewer and the tasks they take.

The diagram is built from them, so adding a person or reassigning one is a
one-line change. Nothing in the drawing code knows any names.

The names committed in `PEOPLE` are **placeholders** (Reviewer A to G), because
this repository is public. Put the real table in `people.local.json` next to
`review.py`, in the same shape, and it is used instead:

    {
      "Ada": ["proc", "out"],
      "Grace": ["io", "nb"]
    }

That file is gitignored. Reviewers are keyed by their place in the table
(`p1`, `p2`, ...), never by name, so `overrides.json` carries no names
either.

## Change when

Run `./edit.sh` (or `./edit.sh review` from the repo root). It opens the
**timeline editor** in your browser:

- drag a bar to move it in time, or drag either end to change its start or end;
- or type the dates in the table;
- untick **Draft** once the dates are real, which removes the DRAFT stamp.

**Save** writes `schedule.json`. Then `./build.sh`. The workflow's animation
follows the schedule too: it walks the tasks in start-date order.

The dates in `schedule.json` start out as **placeholders**, in the agreed
order: test samples first, then the code and notebook reviews in parallel,
then the data output review.

## Move things by hand

The timeline editor links to the **workflow layout editor**, which runs on the
same server. Grab any box by its dashed border to move it, or by its corner to
resize it. The real render redraws behind it, and the lines and group frames
follow. **Save to project** writes `overrides.json`. Delete that file to go
back to the automatic layout.

The layout is automatic until you do. Columns come from the arrows, each
column is ordered to keep lines from crossing, and the canvas is 16:9. With
these assignments the only crossings left are ones no order can avoid: two
reviewers who take the same two tasks always cross once.

## Files

    review.py       the tables, and the build / editor entry points
    people.local.json   real names, if you have them (gitignored)
    schedule.json   when: {task: [start, end]}, inclusive, plus the draft flag
    build.sh        the APNGs and stills
    edit.sh         both browser editors, live (Ctrl-C to stop)
