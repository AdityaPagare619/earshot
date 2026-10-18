#!/usr/bin/env python3
"""EARSHOT phone-channel dev server.

Serves the phone page AND the test gateway from ONE origin — required because
BroadcastChannel splits across origins (file:// vs localhost). Run:

    python3 mock_gateway.py [--port 8077]

Then open in two tabs:
    http://localhost:8077/index.html            (the phone)
    http://localhost:8077/dev/test_gateway.html (the gateway / simulator stand-in)

Pair both to the same room code (default "demo"). No data leaves the machine.
Stdlib only.
"""
import argparse
import functools
import http.server
import os

HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8077)
    args = ap.parse_args()
    handler = functools.partial(
        http.server.SimpleHTTPRequestHandler, directory=HERE
    )
    # Threading so the two tabs don't block each other.
    with http.server.ThreadingHTTPServer(("127.0.0.1", args.port), handler) as srv:
        print("earshot phone dev server: http://127.0.0.1:%d/" % args.port)
        print("  phone:   http://127.0.0.1:%d/index.html" % args.port)
        print("  gateway: http://127.0.0.1:%d/dev/test_gateway.html" % args.port)
        srv.serve_forever()


if __name__ == "__main__":
    main()
