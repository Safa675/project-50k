"""Exercise only opt-in synthetic endpoints in the isolated smoke project."""

from __future__ import annotations

import argparse
import http.cookiejar
import json
import time
import urllib.error
import urllib.request


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=3071)
    args = parser.parse_args()
    if args.port != 3071:
        parser.error("The synthetic proxy check is restricted to smoke port 3071")
    for host in ("127.0.0.1", "localhost"):
        origin = f"http://{host}:{args.port}"
        jar = http.cookiejar.CookieJar()
        opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
        login = urllib.request.Request(f"{origin}/api/p/__test__/login", method="POST", headers={"Origin": origin})
        with opener.open(login, timeout=10) as response:
            csrf = json.load(response)["csrf"]
            assert len(response.headers.get_all("Set-Cookie", [])) == 2, "Separate Set-Cookie headers were lost"
        assert len(jar) == 2, "Browser-equivalent cookie jar did not receive both cookies"
        post = urllib.request.Request(f"{origin}/api/p/__test__/csrf", method="POST", headers={"Origin": origin, "X-CSRF-Token": csrf})
        with opener.open(post, timeout=10) as response:
            assert json.load(response)["accepted"] is True
        rejected = urllib.request.Request(f"{origin}/api/p/__test__/csrf", method="POST", headers={"Origin": "http://evil.invalid:3071", "X-CSRF-Token": csrf})
        try:
            opener.open(rejected, timeout=10)
        except urllib.error.HTTPError as error:
            assert error.code == 403
        else:
            raise AssertionError("Foreign Origin was accepted")
        print(f"PASS {host}: Cookie, both Set-Cookie headers, Origin and CSRF; foreign Origin rejected")
        timestamps = []
        with opener.open(f"{origin}/api/p/__test__/sse", timeout=10) as response:
            # localhost can retry IPv6 before reaching the loopback IPv4 binding.
            # Measure streaming after headers; the event span also catches full-body buffering.
            started = time.monotonic()
            for line in response:
                if line.startswith(b"data:"):
                    timestamps.append(time.monotonic() - started)
        assert len(timestamps) == 10, "SSE event count differs"
        assert timestamps[0] < 1.0, "First SSE event was buffered"
        assert timestamps[-1] - timestamps[0] >= 8.0, "SSE arrived as a buffered batch"
        print(f"PASS {host}: 10 SSE events streamed separately ({timestamps[-1] - timestamps[0]:.2f}s span)")


if __name__ == "__main__":
    main()
