"""
svg-flow-animator -- build animated diagram GIFs by generating SVG frames.

The idea: describe a diagram once as coordinates, emit one standalone SVG per
frame, rasterise the lot with librsvg, and assemble with ffmpeg. Every frame is
a real file you can open and inspect, the whole thing is deterministic, and
re-rendering at a different size or frame rate is a flag change.

Typical shape of a project built on this:

    from svg_flow_animator import assets, geometry, render, svg, timeline

    # once: recover artwork from a design-tool export
    assets.extract_rasters("export.svg", "assets/")

    # per frame: compose a scene
    body = scene_static() + timeline.flow(path, prog, phase, GREEN, AMBER)
    open(f"frames/f{n:04d}.svg", "w").write(svg.document(1600, 900, body, "#fff"))

    # then: render and assemble
    render.stage_assets("assets/", "frames/")
    render.render_frames("frames/", 1600, 900)
    render.build_gif("frames/", "out.gif", fps=15, width=1280, height=720)

No third-party Python packages. Requires `rsvg-convert` and `ffmpeg` on PATH.
"""

__version__ = "0.1.0"

from . import (assets, geometry, overrides, render, rough, styles, svg,  # noqa: F401
               timeline)

__all__ = ["assets", "geometry", "overrides", "render", "rough", "styles",
           "svg", "timeline", "__version__"]
