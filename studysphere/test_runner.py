"""
Custom test runner that shows "ok" in green when tests pass.
"""
import os
import unittest

from django.test.runner import DiscoverRunner
from django.utils.termcolors import colorize

# Force green output when TERM suggests colour support or STUDYSPHERE_FORCE_COLOR=1
FORCE_COLOR = os.environ.get('STUDYSPHERE_FORCE_COLOR', '').lower() in ('1', 'true', 'yes')


def _supports_color(stream):
    """Check if the stream supports ANSI colour codes."""
    if FORCE_COLOR:
        return True
    try:
        stream = getattr(stream, 'stream', stream)
    except AttributeError:
        pass
    if not hasattr(stream, 'isatty'):
        return False
    try:
        return stream.isatty()
    except Exception:
        return False


class GreenOKTextTestResult(unittest.TextTestResult):
    """TextTestResult that prints 'ok' in green when tests pass."""

    def _write_status(self, test, status):
        from unittest.runner import _SubTest
        is_subtest = isinstance(test, _SubTest)
        if is_subtest or self._newline:
            if not self._newline:
                self.stream.writeln()
            if is_subtest:
                self.stream.write("  ")
            self.stream.write(self.getDescription(test))
            self.stream.write(" ... ")
        if status == "ok" and _supports_color(self.stream.stream):
            self.stream.write(colorize("ok", fg="green"))
        else:
            self.stream.write(status)
        self.stream.writeln()
        self.stream.flush()
        self._newline = True


class ColoredDiscoverRunner(DiscoverRunner):
    """Django test runner that shows passing tests with green 'ok'."""

    def get_resultclass(self):
        resultclass = super().get_resultclass()
        if resultclass is not None:
            return resultclass
        return GreenOKTextTestResult
