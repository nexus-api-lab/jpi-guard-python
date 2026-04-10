"""
CLI entry point for jpi-guard.

Usage:
    python -m jpi_guard get-key
    python -m jpi_guard get-key --email you@example.com
"""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request

_TRIAL_URL = "https://api.nexus-api-lab.com/v1/auth/trial"


def cmd_get_key(email: str | None = None) -> None:
    payload: dict = {}
    if email:
        payload["email"] = email

    from . import __version__

    req = urllib.request.Request(
        _TRIAL_URL,
        data=json.dumps(payload).encode(),
        headers={
            "Content-Type": "application/json",
            "User-Agent": f"jpi-guard-python/{__version__}",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            result: dict = json.loads(resp.read())
    except urllib.error.HTTPError as e:
        print(f"Error: {e.code} {e.reason}", file=sys.stderr)
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"Network error: {e.reason}", file=sys.stderr)
        sys.exit(1)

    api_key: str = result["api_key"]
    quota: int = result.get("quota_limit", 2000)
    expires: int = result.get("expires_in_days", 30)
    new_trial: bool = result.get("new_trial", True)

    label = "Your trial API key:" if new_trial else "Your existing trial API key:"
    print(f"\n{label}\n")
    print(f"  {api_key}\n")
    print(f"Quota  : {quota:,} requests")
    print(f"Expires: {expires} days\n")
    print("Next step — set the environment variable:\n")
    print(f"  export JPI_GUARD_API_KEY={api_key}\n")
    print("Upgrade at: https://nexus-api-lab.com/#pricing")


def main() -> None:
    args = sys.argv[1:]

    if not args or args[0] == "get-key":
        email: str | None = None
        if "--email" in args:
            idx = args.index("--email")
            if idx + 1 < len(args):
                email = args[idx + 1]
            else:
                print("Error: --email requires a value", file=sys.stderr)
                sys.exit(1)
        cmd_get_key(email)
    else:
        print(
            "Usage: python -m jpi_guard get-key [--email your@email.com]",
            file=sys.stderr,
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
