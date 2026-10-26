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
    "users": "Other users",
}

BEATS = [
    dict(chapter="operator", anchor="node.operator", dur=55,
         flows=["op_dash"], pulse=["ade", "jmd"], glow=["box.dashboard"],
         text="Science Investigators and Data Production Operators would access the user dashboard where they could access the algorithm development environment to access compute resources and a job monitoring dashboard to view statuses and track and manage compute costs."),
    dict(chapter="accounts", anchor="box.managed", dur=40,
         glow=["box.managed"],
         text="The blue box includes managed services that would be operated and maintained by a data processing system operations team."),
    dict(chapter="accounts", anchor="box.external", dur=40,
         glow=["box.external"],
         text="The red box includes potential tools and services managed by the projects. File storage would be maintained and funded by the projects."),
    dict(chapter="access", anchor="node.auth", dur=60,
         flows=["auth_dash", "auth_users"], pulse=["auth", "users"],
         text="Sign-in runs through a managed Authentication & Authorization service, "
              "which verifies users against each project's own User "
              "Management."),
    dict(chapter="develop", anchor="node.ade", dur=45,
         pulse=["ade"],
         text="In the Algorithm Development Environment, the operator/investigator builds "
              "and tests algorithms before running them at scale."),
    dict(chapter="run", anchor="node.dps", dur=110,
         flows=["ade_dps", "dps_algcat", ["dps_files", "dps_catalog"]],
         pulse=["dps", "algcat", "files", "catalog"],
         text="The Algorithm Development Environment accesses defined algorithm(s) in the project's Standards-compliant Algorithm Catalog and calls on the data processing system to produce output data and catalog it in the managed Data Catalog."),
    dict(chapter="monitor", anchor="node.jmd", dur=90,
         flows=["jmd_dps"], pulse=["jmd"], shots=["jobs"],
         text="As jobs run, the Job Monitoring Dashboard reads their status from "
              "the Data Processing System: queued, started, successful, or failed."),
    dict(chapter="data", anchor="node.catalog", dur=45,
         flows=["cat_files"], pulse=["catalog", "files"],
         text="The Data Catalog indexes the data in File Storage."),
    dict(chapter="data", anchor="node.api", dur=45,
         flows=["api_cat", "api_viz"], pulse=["api", "viz"],
         text="The interoperable Data Service APIs query the Data Catalog and serve data "
              "to the Visualization Tools."),
    dict(chapter="view", anchor="node.viz", dur=50,
         pulse=["viz", "orgviz"],
         text="The operator views and assesses data results in compatible Visualization Tools or Services"),
    dict(chapter="users", anchor="node.investigator", dur=55,
         flows=[["inv_managed", "inv_external"]], pulse=["investigator"],
         text="Beyond the Data Production Operator, other users such as a "
              "Science Investigator can work in the centrally managed account "
              "or in their project's externally managed account."),
    dict(chapter="users", anchor="node.orgade", dur=50,
         flows=["orgade_algcat", "orgade_files"], pulse=["orgade"],
         text="In their project's account, they can use its own Algorithm "
              "Development Environment, publishing to the Algorithm Catalog and "
              "reading from File Storage."),
]
