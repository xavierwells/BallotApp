#!/usr/bin/env python3
"""Fail if a direct application dependency lacks a recorded approval."""

from __future__ import print_function

import json
import os
import re
import sys


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def requirement_names(path):
    names = set()
    with open(path) as handle:
        for line in handle:
            line = line.strip()
            if not line or line.startswith("#") or line.startswith("-r"):
                continue
            match = re.match(r"([A-Za-z0-9_.-]+)", line)
            if match:
                names.add(match.group(1).lower().replace("_", "-"))
    return names


def main():
    with open(os.path.join(ROOT, "governance", "dependency-approvals.json")) as handle:
        approved = set(item.lower() for item in json.load(handle)["approvedDirectDependencies"])

    required = set()
    required.update(requirement_names(os.path.join(ROOT, "apps", "api", "requirements.txt")))
    required.update(requirement_names(os.path.join(ROOT, "apps", "api", "requirements-dev.txt")))
    with open(os.path.join(ROOT, "apps", "web", "package.json")) as handle:
        package = json.load(handle)
    required.update(package.get("dependencies", {}).keys())
    required.update(package.get("devDependencies", {}).keys())

    unapproved = sorted(name for name in required if name.lower() not in approved)
    if unapproved:
        print("Unapproved direct dependencies: {}".format(", ".join(unapproved)))
        return 1
    print("All {} direct dependencies have approval records.".format(len(required)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
