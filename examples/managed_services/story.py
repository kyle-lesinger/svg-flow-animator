"""
The narration: every word the animation says, and in what order.

Edit freely -- nothing here is geometry. Positions live in layout.py and are
tuned in the editor; this file only decides WHAT is said and WHAT moves while
it is said.

One entry per beat:

    chapter  the section it belongs to (./build.sh --section=<chapter>).
             Consecutive beats may share one.
    text     the pop-up caption
    anchor   the node or box the beat is ABOUT. Captions sit in the band
             under the figure, never on it; the pulse and the dimming are what
             point at the subject.
    flows    connectors that draw themselves in during the beat, in order
             (keys of layout.FLOWS). A nested list draws in together:
             ["a", ["b", "c"]] is a, then b and c at once.
    pulse    nodes that pulse while the beat runs
    glow     boxes that light up while the beat runs
    shots    screenshots that pop in, one after another (keys of SHOTS). In
             a beat that also has flows, they wait for the flows to draw in
             first -- an inset would otherwise cover the line being drawn.
    dur      frames of motion (15 fps). Captions are held for at least
             MIN_CAPTION_SEC whatever this says, so a short beat stays readable.

Everything a beat touches stays at full strength while it runs; the rest of
the figure recedes, so a viewer always knows where to look.
"""

MIN_CAPTION_SEC = 7.0

# Screenshots for the Job Monitoring chapter. Files go in assets/ (gitignored).
# Each one appears in the caption band, beside the caption; its position and
# size is a handle -- shot.<key> in the editor.
# A missing file draws a labelled placeholder and warns; it never vanishes.
SHOTS = {
    "jobs": dict(file="jobs-list.png",
                 caption="Job Monitoring Dashboard: every job, its status and timing"),
}

CHAPTER_TITLES = {
    "operator": "The operator's two tools",
    "access": "Sign-in and users",
    "develop": "Developing an algorithm",
    "run": "Running jobs",
    "monitor": "Job Monitoring Dashboard",
    "data": "Finding the outputs",
    "view": "Seeing the results",
    "accounts": "Who manages what",
    "investigator": "The Science Investigator",
}

BEATS = [
    dict(chapter="operator", anchor="node.operator", dur=55,
         flows=["op_dash"], pulse=["ade", "jmd"], glow=["box.dashboard"],
         text="The journey starts with the Data Production Operator and two "
              "tools on the User Dashboard: the Algorithm Development "
              "Environment and the Job Monitoring Dashboard."),
    dict(chapter="accounts", anchor="box.managed", dur=40,
         glow=["box.managed"],
         text="Everything in blue is the Managed Services Account, managed by "
              "NASA ESD."),
    dict(chapter="accounts", anchor="box.external", dur=40,
         glow=["box.external"],
         text="Everything in red sits in Externally Managed Accounts, each "
              "managed by its own organization: its users, algorithms, data and "
              "tools."),
    dict(chapter="access", anchor="node.auth", dur=60,
         flows=["auth_dash", "auth_users"], pulse=["auth", "users"],
         text="Sign-in runs through NASA ESD's Authentication & Authorization, "
              "which checks users against each organization's own User "
              "Management."),
    dict(chapter="develop", anchor="node.ade", dur=45,
         pulse=["ade"],
         text="In the Algorithm Development Environment, the operator builds "
              "and tests algorithms before running them."),
    dict(chapter="run", anchor="node.dps", dur=110,
         flows=["ade_dps", "dps_algcat", ["dps_files", "dps_catalog"]],
         pulse=["dps", "algcat", "files", "catalog"],
         text="The Algorithm Development Environment triggers jobs on the Data "
              "Processing System. It accesses each algorithm in the Algorithm "
              "Catalog, then writes outputs to File Storage and updates STAC "
              "collections in the Data Catalog."),
    dict(chapter="monitor", anchor="node.jmd", dur=90,
         flows=["dps_jmd"], pulse=["jmd"], shots=["jobs"],
         text="As jobs run, the Data Processing System writes their status to "
              "the Job Monitoring Dashboard: queued, started, completed, and "
              "whether they succeeded."),
    dict(chapter="data", anchor="node.catalog", dur=45,
         flows=["cat_files"], pulse=["catalog", "files"],
         text="The Data Catalog indexes the outputs held in File Storage, so "
              "they can be found where they sit."),
    dict(chapter="data", anchor="node.api", dur=45,
         flows=["api_cat", "api_viz"], pulse=["api", "viz"],
         text="The Data Service APIs query the Data Catalog and serve results "
              "to the Visualization Tools."),
    dict(chapter="view", anchor="node.viz", dur=50,
         flows=["op_viz", "op_orgviz"], pulse=["viz", "orgviz"],
         text="The operator views results in the managed Visualization Tools, "
              "or in the organization's own."),
    dict(chapter="investigator", anchor="node.investigator", dur=60,
         flows=["inv_orgade", "orgade_algcat", "orgade_files"],
         pulse=["investigator", "orgade"],
         text="A Science Investigator works in their organization's own "
              "Algorithm Development Environment, publishing to the Algorithm "
              "Catalog and reading from File Storage."),
    dict(chapter="investigator", anchor="node.investigator", dur=40,
         flows=["inv_orgviz", "inv_viz"], pulse=["orgviz", "viz"],
         text="They view results in both sets of Visualization Tools."),
]
