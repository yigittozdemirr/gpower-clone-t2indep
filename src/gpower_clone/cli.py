"""Command line front end: argv -> engine -> one JSON line on stdout (SPEC 5)."""

from __future__ import annotations

import sys

from . import engine


def main(argv: list[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]
    obj, code = engine.run_argv(argv)
    line = engine.to_json(obj) + "\n"
    out = getattr(sys.stdout, "buffer", None)
    if out is not None:          # bytes: no CRLF translation on Windows
        sys.stdout.flush()
        out.write(line.encode("ascii"))
        out.flush()
    else:                        # pragma: no cover
        sys.stdout.write(line)
        sys.stdout.flush()
    return code


if __name__ == "__main__":
    sys.exit(main())
