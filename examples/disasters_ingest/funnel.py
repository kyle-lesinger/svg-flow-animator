#!/usr/bin/env python3
"""
A queue behind a narrow neck that later opens -- the bottleneck, as geometry
and a schedule, shared by every slide that tells it.

The queue is computed, not simulated: every dot's position is a pure function
of the frame. The neck serves one dot per `service` frames, so departures are
fixed before anything is drawn; a dot waits in the funnel in arrival order, and
its place in line slides forward smoothly as the ones ahead leave. Any frame can
be rendered alone, in any order -- what the parallel rasteriser and the tests
both rely on.

Dots enter at `src_x` at their `spawn` frame, on their own `lane`. What they
look like, and where they were before `src_x`, is the caller's business.
"""
import gen_frames as G
from journey import ramp


class Funnel:
    def __init__(self, src_x, mouth_x, neck_x, neck_end, mid_y, mouth_h, neck_h,
                 open_h, decide_x, open_at, morph, spawn, lane, neck_path,
                 v=5.0, v_open=11.0, service=22, drain=0.4, move=10):
        self.src_x, self.mouth_x, self.neck_x = src_x, mouth_x, neck_x
        self.neck_end, self.mid_y, self.decide_x = neck_end, mid_y, decide_x
        self.mouth_h, self.neck_h, self.open_h = mouth_h, neck_h, open_h
        self.open_at, self.morph_frames = open_at, morph
        self.spawn, self.lane, self.neck_path = list(spawn), list(lane), neck_path
        self.v, self.v_open, self.service = v, v_open, service
        self.drain, self.move = drain, move
        self.n = len(self.spawn)
        self.neck_t = sum(seg[0] for seg in neck_path)
        self.slots = self._slots()
        self.dep, self.mode = self._departures()
        self.arrivals = sorted(self.arrival(i) for i in range(self.n))

    # ------------------------------------------------------------ geometry --
    def morph(self, f):
        """0 while the neck is shut, 1 once it has opened."""
        return ramp(f, self.open_at, self.open_at + self.morph_frames)

    def half_height(self, x, m):
        h = self.neck_h + (self.open_h - self.neck_h) * m
        if x <= self.mouth_x:
            return self.mouth_h
        if x < self.neck_x:
            return (self.mouth_h + (h - self.mouth_h) * (x - self.mouth_x)
                    / float(self.neck_x - self.mouth_x))
        return h

    def inside(self, x, y, m):
        """y pulled inside the walls at x -- a dot never crosses the funnel."""
        h = self.half_height(x, m) - 7
        return self.mid_y + max(-h, min(h, y - self.mid_y))

    def walls(self, m):
        """(top, bottom) wall polylines: m=0 the bottleneck, m=1 a channel."""
        h = self.neck_h + (self.open_h - self.neck_h) * m
        c = self.mid_y
        return ([(self.mouth_x, c - self.mouth_h), (self.neck_x, c - h),
                 (self.neck_end, c - h)],
                [(self.mouth_x, c + self.mouth_h), (self.neck_x, c + h),
                 (self.neck_end, c + h)])

    def _slots(self):
        """Places in line, nearest the neck first: the funnel's cone, column by
        column, centre outward, then spilling back out of the mouth."""
        out, step = [], 11
        x = self.neck_x - 8
        while x > self.src_x + 20:
            h = self.half_height(x, 0.0)
            k = 0
            while k * step <= h - 7:
                out.append((x, self.mid_y + k * step))
                if k:
                    out.append((x, self.mid_y - k * step))
                k += 1
            x -= step
        return out

    # ------------------------------------------------------------ schedule --
    def _departures(self):
        """When each dot leaves the line, and whether it took the neck or the
        opened architecture. FIFO: nobody overtakes."""
        dep, mode, last = [], [], -10 ** 9
        for i in range(self.n):
            at_neck = self.spawn[i] + (self.neck_x - self.src_x) / self.v
            d = max(at_neck, last + self.service)
            if d < self.open_at:
                dep.append(d)
                mode.append("neck")
                last = d
            else:
                dep.append(None)
                mode.append("open")
        # Once it opens, everything already in the system -- in line or still on
        # its way to it -- is released in order, and dots that arrive later never
        # queue. Releasing only the ones already in line let the rest race
        # through the funnel while it was still shut.
        queued = 0
        for i in range(self.n):
            if mode[i] == "open":
                if self.spawn[i] < self.open_at:
                    dep[i] = self.open_at + self.morph_frames * 0.5 + self.drain * queued
                    queued += 1
                else:
                    dep[i] = self.spawn[i]
        return dep, mode

    def waiting(self, f):
        """Dots in line at frame f (entered, not yet departed)."""
        return [i for i in range(self.n) if self.spawn[i] <= f < self.dep[i]]

    def _rank(self, i, f):
        """Places ahead of dot i, fractional while the line shuffles up."""
        r = 0.0
        for j in range(i):
            d = self.dep[j]
            if d > f:
                r += 1
            elif f - d < self.move:
                r += 1 - (f - d) / float(self.move)
        return r

    def _slot(self, r):
        s = self.slots
        a = min(int(r), len(s) - 1)
        b = min(a + 1, len(s) - 1)
        t = r - int(r)
        return (s[a][0] + (s[b][0] - s[a][0]) * t, s[a][1] + (s[b][1] - s[a][1]) * t)

    def _queued_pos(self, i, f):
        sx, sy = self._slot(self._rank(i, f))
        fx = self.src_x + self.v * (f - self.spawn[i])
        lane = self.inside(fx, self.lane[i], self.morph(f))
        if fx <= sx - 30:
            return fx, lane
        if fx < sx:
            t = (fx - (sx - 30)) / 30.0
            return fx, lane + (sy - lane) * t
        return sx, sy

    def _neck_pos(self, t):
        """(x, split?) t frames after leaving the line by the neck."""
        for dur, x0, x1, split in self.neck_path:
            if t < dur:
                return x0 + (x1 - x0) * G.smooth(t / float(dur)), split
            t -= dur
        return None, False

    def position(self, i, f):
        """[(x, y)] for dot i at frame f -- one dot, three copies, or none."""
        if f < self.spawn[i]:
            return []
        if f < self.dep[i]:
            return [self._queued_pos(i, f)]
        t = f - self.dep[i]
        if self.mode[i] == "neck":
            x, split = self._neck_pos(t)
            if x is None:
                return []
            return [(x, self.mid_y + d) for d in ((-13, 0, 13) if split else (0,))]
        x0, y0 = self._start_open(i)
        x = x0 + self.v_open * t
        if x >= self.decide_x:
            return []
        y = y0 + (self.lane[i] - y0) * min(1.0, t / 20.0)
        return [(x, self.inside(x, y, self.morph(f)))]

    def _start_open(self, i):
        if self.dep[i] > self.spawn[i]:
            return self._queued_pos(i, self.dep[i])
        return self.src_x, self.lane[i]

    def arrival(self, i):
        """Frame dot i reaches the decision makers."""
        if self.mode[i] == "neck":
            return self.dep[i] + self.neck_t
        return self.dep[i] + (self.decide_x - self._start_open(i)[0]) / self.v_open
