#!/usr/bin/env python3
"""
Run the whole suite and print a summary that names what was skipped and why.

    python3 tests/run.py             # everything
    python3 tests/run.py -v          # per-test names
    python3 tests/run.py test_rough  # one module (or Class.method)

Equivalent to `python3 -m unittest discover tests`; this wrapper exists only
for the skip report, because a green run that quietly skipped half the suite
looks exactly like a green run that did not.
"""
import os
import sys
import time
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from tests import _support as sup  # noqa: E402


def say(msg):
    """Print onto the same stream the runner uses, so the order is the order."""
    print(msg, file=sys.stderr, flush=True)


def main(argv):
    verbosity = 2 if "-v" in argv else 1
    names = [a for a in argv if not a.startswith("-")]

    loader = unittest.TestLoader()
    if names:
        suite = loader.loadTestsFromNames(
            ["tests.%s" % n if not n.startswith("tests.") else n for n in names])
    else:
        suite = loader.discover(os.path.join(ROOT, "tests"), top_level_dir=ROOT)

    say("environment: rsvg-convert=%s ffmpeg=%s magick=%s node=%s "
        "disasters-assets=%s slow=%s"
        % (sup.HAVE_RSVG, sup.HAVE_FFMPEG, sup.HAVE_MAGICK, sup.HAVE_NODE,
           sup.HAVE_DISASTERS_ASSETS, not sup.SLOW_DISABLED))

    started = time.time()
    result = unittest.TextTestRunner(verbosity=verbosity).run(suite)
    elapsed = time.time() - started

    total = result.testsRun
    failed = len(result.failures) + len(result.errors)
    xfail = len(result.expectedFailures)
    skipped = len(result.skipped)
    say("\n%-22s %d" % ("tests run", total))
    say("%-22s %d" % ("passed", total - failed - skipped - xfail
                      - len(result.unexpectedSuccesses)))
    say("%-22s %d" % ("failed", failed))
    say("%-22s %d" % ("skipped", skipped))
    say("%-22s %d" % ("known bugs (xfail)", xfail))
    say("%-22s %d" % ("unexpected passes", len(result.unexpectedSuccesses)))
    say("%-22s %.2fs" % ("elapsed", elapsed))

    if result.skipped:
        say("\nskipped:")
        reasons = {}
        for test, reason in result.skipped:
            reasons.setdefault(reason, []).append(str(test).split(" ")[0])
        for reason, tests in sorted(reasons.items()):
            say("  %-46s %d test(s)" % (reason, len(tests)))
    if result.expectedFailures:
        say("\nknown bugs kept as expected failures (see the test docstring):")
        for test, _tb in result.expectedFailures:
            say("  %s" % test)
    if result.unexpectedSuccesses:
        say("\nA known bug now PASSES -- it was fixed. Drop the "
            "@unittest.expectedFailure from:")
        for test in result.unexpectedSuccesses:
            say("  %s" % test)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
