#!/usr/bin/env python3
"""Check data/seasons.yml and data/seminars/ before the site is built.

This exists because the dangerous failures in this repo's history were silent
ones. A misspelled key -- `seiminar_date`, `semester_date`, `presenter`,
`Title` all appear in the history -- is not an error to Hugo. It renders the
missing field as empty, the build goes green, html-proofer goes green, and the
site deploys with a speaker's name quietly absent. Nobody is told.

Anything the seminar bot writes is already well-formed, so this mainly guards
direct commits made outside the forms.

Exit codes: 0 clean, 1 problems found.

Usage: python3 scripts/validate_seminars.py [--repo-root D]
"""

import argparse
import datetime as dt
import os
import re
import sys

import yaml

KNOWN_FIELDS = {
    "season", "seminar_date", "status", "presenters", "affiliations",
    "title", "host", "location", "zoom_url", "slides", "note",
}
REQUIRED_FIELDS = {"season", "seminar_date", "status"}
VALID_STATUS = {"scheduled", "cancelled", "rescheduled", "no_seminar"}

SEASON_FIELDS = {"slug", "label", "start", "end", "default_weekday", "default_time"}
SLUG_RE = re.compile(r"^(spring|summer|fall|winter)-\d{4}$")


def near(word, options):
    """Cheap did-you-mean, so a typo names its own fix."""
    word_l = word.lower()
    for o in options:
        if o.lower() == word_l:
            return o
    best, best_score = None, 0
    for o in options:
        common = len(set(word_l) & set(o.lower()))
        score = common / max(len(set(word_l) | set(o.lower())), 1)
        if score > best_score:
            best, best_score = o, score
    return best if best_score >= 0.6 else None


def check_form_contract(root):
    """Every issue-form field label must be one the bot knows how to read.

    GitHub renders a form answer as "### <label>", and that label is the only
    link between the form and scripts/seminar_bot.py. Rename a label without
    updating the bot and that field is silently dropped -- the submission
    appears to work and the value never lands. Same failure shape as a
    misspelled data key, so it gets caught the same way.
    """
    tpl_dir = os.path.join(root, ".github", "ISSUE_TEMPLATE")
    if not os.path.isdir(tpl_dir):
        return []

    sys.path.insert(0, os.path.join(root, "scripts"))
    try:
        from seminar_bot import FIELD_LABELS
    except ImportError:
        return ["scripts/seminar_bot.py could not be imported to check the "
                "issue-form field labels against it."]

    problems = []
    for fn in sorted(os.listdir(tpl_dir)):
        if not fn.endswith((".yml", ".yaml")) or fn == "config.yml":
            continue
        with open(os.path.join(tpl_dir, fn), encoding="utf-8") as fh:
            form = yaml.safe_load(fh) or {}
        for block in form.get("body", []):
            if block.get("type") == "markdown":
                continue
            label = (block.get("attributes") or {}).get("label")
            if label and label not in FIELD_LABELS:
                problems.append(
                    f".github/ISSUE_TEMPLATE/{fn}: the field labelled "
                    f"'{label}' has no match in FIELD_LABELS in "
                    "scripts/seminar_bot.py, so anything entered there would "
                    "be silently ignored.")
    return problems


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo-root", default=os.path.dirname(
        os.path.dirname(os.path.abspath(__file__))))
    args = ap.parse_args()

    problems = []
    root = args.repo_root
    seasons_path = os.path.join(root, "data", "seasons.yml")
    seminars_dir = os.path.join(root, "data", "seminars")

    # ---------------------------------------------------------- seasons.yml
    try:
        with open(seasons_path, encoding="utf-8") as fh:
            seasons = yaml.safe_load(fh) or []
    except FileNotFoundError:
        print("data/seasons.yml is missing. Every season must be listed there.")
        return 1
    except yaml.YAMLError as e:
        print(f"data/seasons.yml is not valid YAML:\n  {e}")
        return 1

    if not isinstance(seasons, list):
        print("data/seasons.yml should be a list of seasons.")
        return 1

    slugs = set()
    for i, season in enumerate(seasons):
        where = f"data/seasons.yml entry {i + 1}"
        if not isinstance(season, dict):
            problems.append(f"{where}: should be a season, not {type(season).__name__}.")
            continue
        missing = SEASON_FIELDS - set(season)
        if missing:
            problems.append(f"{where}: missing {', '.join(sorted(missing))}.")
        slug = season.get("slug", "")
        if slug in slugs:
            problems.append(f"{where}: '{slug}' is listed more than once.")
        slugs.add(slug)
        if slug and not SLUG_RE.match(str(slug)):
            problems.append(
                f"{where}: slug '{slug}' should look like 'fall-2026' -- "
                "lower-case season, hyphen, four-digit year.")
        for key in ("start", "end"):
            if key in season:
                try:
                    dt.date.fromisoformat(str(season[key]))
                except ValueError:
                    problems.append(
                        f"{where}: {key} '{season[key]}' is not a date "
                        "in year-month-day form.")

    # ---------------------------------------------------------- seminars/
    if not os.path.isdir(seminars_dir):
        print("data/seminars/ is missing.")
        return 1

    files = sorted(f for f in os.listdir(seminars_dir) if not f.startswith("."))
    count = 0
    for fn in files:
        rel = f"data/seminars/{fn}"
        if not fn.endswith(".yml"):
            problems.append(
                f"{rel}: every file in data/seminars/ must be a .yml seminar "
                "record. Hugo parses everything under data/ and a stray file "
                "fails the build.")
            continue

        path = os.path.join(seminars_dir, fn)
        try:
            with open(path, encoding="utf-8") as fh:
                rec = yaml.safe_load(fh)
        except yaml.YAMLError as e:
            problems.append(f"{rel}: not valid YAML.\n      {e}")
            continue

        if not isinstance(rec, dict):
            problems.append(f"{rel}: should be a set of fields.")
            continue
        count += 1

        for key in rec:
            if key not in KNOWN_FIELDS:
                hint = near(key, KNOWN_FIELDS)
                suffix = f" Did you mean '{hint}'?" if hint else ""
                problems.append(
                    f"{rel}: '{key}' is not a field this site knows about, so "
                    f"it would be ignored silently.{suffix}")

        for key in sorted(REQUIRED_FIELDS - set(rec)):
            problems.append(f"{rel}: '{key}' is required.")

        status = rec.get("status")
        if status is not None and status not in VALID_STATUS:
            problems.append(
                f"{rel}: status '{status}' is not one of "
                f"{', '.join(sorted(VALID_STATUS))}.")

        when = rec.get("seminar_date")
        if when is not None:
            try:
                dt.datetime.fromisoformat(str(when))
            except ValueError:
                problems.append(
                    f"{rel}: seminar_date '{when}' is not a date and time, "
                    "e.g. 2026-09-02T15:00:00.")

        season = rec.get("season")
        if season is not None and season not in slugs:
            problems.append(
                f"{rel}: season '{season}' is not listed in data/seasons.yml, "
                "so this talk would not appear anywhere on the site.")

    problems.extend(check_form_contract(root))

    if problems:
        print(f"Found {len(problems)} problem(s) in the seminar data:\n")
        for p in problems:
            print(f"  - {p}")
        print("\nNothing was deployed.")
        return 1

    print(f"Seminar data is valid: {count} seminars across {len(slugs)} seasons.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
