#!/usr/bin/env python3
"""Migrate data/seminar/<season>/<date>.yml -> data/seminars/<date>.yml

This is deliberately a repeatable script rather than a one-time bulk edit.
Seminars keep being added to the old layout on master while this work sits on a
branch, so re-running it immediately before merge picks up everything that
landed in the meantime. It also makes the migration reviewable: you read the
rules once instead of checking a 322-file diff.

What changes:

  - Season membership becomes an explicit `season:` field instead of being
    encoded in the directory name. Directory and file names stop being
    load-bearing entirely. The old layout could not represent spring-2021 and
    fall-2021 both containing a 2021-09-22.yml; an explicit field can.

  - Filenames are derived from `seminar_date`, which is authoritative, so they
    can no longer disagree with the record (fall-2021/2021-09-22.yml actually
    held a talk on 2021-10-27). Collisions get a numeric suffix -- three dates
    genuinely have two talks.

  - Five ad-hoc ways of saying "no talk happened" collapse into one `status`
    field. See derive_status().

Usage: python3 scripts/migrate_seminars.py [--dry-run]
"""

import argparse
import calendar
import collections
import datetime as dt
import os
import re
import shutil
import sys

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OLD = os.path.join(ROOT, "data", "seminar")
NEW = os.path.join(ROOT, "data", "seminars")
SEASONS = os.path.join(ROOT, "data", "seasons.yml")

# Emitted in this order so the files read consistently.
FIELD_ORDER = [
    "season", "seminar_date", "status", "presenters", "affiliations",
    "title", "host", "location", "zoom_url", "slides", "note",
]
ALWAYS = {"season", "seminar_date", "status"}

CANCEL_PREFIX = re.compile(r"^(?:CANCELLED|CANCELED)\b:?\s*", re.I)
BRACKET_NOTE = re.compile(r"^\[(.+)\]$")
# Leading whitespace is allowed: two files indent every key by one space.
DATE_LINE = re.compile(r"^[ \t]*seminar_date:[ \t]*(.+?)[ \t]*$", re.M)
PLAIN_NAME = re.compile(r"^\d{4}-\d{2}-\d{2}$")

SEASON_DEFAULT_RANGE = {
    "spring": ((1, 1), (5, 31)),
    "summer": ((5, 1), (8, 31)),
    "fall": ((8, 1), (12, 31)),
}


def load_record(path):
    """Parse one legacy seminar file.

    seminar_date is taken from the raw text rather than from the parsed value.
    These timestamps carry no timezone, so YAML readers produce a naive
    datetime and any round-trip through strftime can re-render it in another
    zone -- shifting every seminar by the UTC offset. The times are wall-clock
    times for a room in State College and must survive verbatim, so the literal
    text is authoritative.
    """
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    try:
        rec = yaml.safe_load(text) or {}
    except yaml.YAMLError as e:
        sys.exit(f"FATAL: {path} is not valid YAML: {e}")
    if not isinstance(rec, dict):
        sys.exit(f"FATAL: {path} is not a mapping")

    m = DATE_LINE.search(text)
    if m:
        rec["seminar_date"] = m.group(1).strip("'\"")
    return rec


def s(v):
    return "" if v is None else str(v).strip()


def derive_status(rec):
    """Collapse the five historical conventions into one status.

    reschedule: true              -> rescheduled  (10 records)
    reschedule: <blank> / false   -> scheduled; the field never did anything.
                                     `if not .reschedule` treats null and false
                                     as falsy, so these 14 rendered as ordinary
                                     seminars. All carry a real presenter and
                                     title.
    presenters: "No seminar"      -> no_seminar
    title: "[No seminar]" / "[... break]"
                                  -> no_seminar, bracket text kept as note
    presenters: "CANCELLED <name>"-> cancelled, prefix stripped from every field
                                     carrying it (2018-03-14 has it on
                                     presenters, affiliations AND title)
    """
    presenters, title = s(rec.get("presenters")), s(rec.get("title"))

    if rec.get("reschedule") is True:
        return "rescheduled"
    if presenters.lower() == "no seminar":
        return "no_seminar"
    m = BRACKET_NOTE.match(title)
    if m and re.search(r"no seminar|break|holiday", m.group(1), re.I):
        return "no_seminar"
    if CANCEL_PREFIX.match(presenters):
        return "cancelled"
    return "scheduled"


def format_date(v):
    """seminar_date passes through untouched; only its syntax is validated."""
    text = s(v)
    if not text:
        sys.exit(f"FATAL: missing seminar_date {v!r}")
    try:
        dt.datetime.fromisoformat(text)
    except ValueError:
        sys.exit(f"FATAL: seminar_date {text!r} is not a valid date")
    return text


def convert(rec, season):
    status = derive_status(rec)
    presenters = s(rec.get("presenters"))
    affiliations = s(rec.get("affiliations"))
    title = s(rec.get("title"))
    note = ""

    if status == "cancelled":
        presenters = CANCEL_PREFIX.sub("", presenters)
        affiliations = CANCEL_PREFIX.sub("", affiliations)
        title = CANCEL_PREFIX.sub("", title)

    if status == "no_seminar":
        m = BRACKET_NOTE.match(title)
        if m:
            note = "" if m.group(1).lower() == "no seminar" else m.group(1)
        if presenters.lower() == "no seminar":
            presenters = ""
        title = ""

    out = {
        "season": season,
        "seminar_date": format_date(rec.get("seminar_date")),
        "status": status,
        "presenters": presenters,
        "affiliations": affiliations,
        "title": title,
        "host": s(rec.get("host")),
        "location": s(rec.get("location")),
        "zoom_url": s(rec.get("zoom_url")),
        "slides": s(rec.get("slides")),
        "note": note,
    }
    return {k: out[k] for k in FIELD_ORDER if k in ALWAYS or out.get(k)}


def dump(record):
    """Emit YAML with a real emitter, so quoting is never hand-rolled.

    width is set very high because the default folds long lines; talk titles are
    long, and folded scalars make diffs unreadable.
    """
    return yaml.safe_dump(
        record, sort_keys=False, allow_unicode=True, width=10**9,
        default_flow_style=False,
    )


def build_seasons(records):
    by_season = collections.defaultdict(list)
    for r in records:
        by_season[r["record"]["season"]].append(r)

    slugs = sorted(
        {d for d in os.listdir(OLD) if os.path.isdir(os.path.join(OLD, d))}
        | set(by_season)
    )

    seasons = []
    for slug in slugs:
        part, _, year_s = slug.partition("-")
        year = int(year_s)
        dates = [dt.datetime.fromisoformat(r["record"]["seminar_date"])
                 for r in by_season.get(slug, [])]

        if dates:
            lo, hi = min(dates), max(dates)
            start = dt.date(lo.year, lo.month, 1)
            end = dt.date(hi.year, hi.month,
                          calendar.monthrange(hi.year, hi.month)[1])
        else:
            (sm, sd), (em, ed) = SEASON_DEFAULT_RANGE.get(part, ((1, 1), (12, 31)))
            start, end = dt.date(year, sm, sd), dt.date(year, em, ed)

        # Default slot = the weekday and time most used that season.
        weekdays = collections.Counter(d.strftime("%A") for d in dates)
        times = collections.Counter(
            d.strftime("%H:%M") for d in dates if (d.hour, d.minute) != (0, 0)
        )

        seasons.append({
            "slug": slug,
            "label": f"{part.capitalize()} {year}",
            "start": start.isoformat(),
            "end": end.isoformat(),
            "default_weekday": weekdays.most_common(1)[0][0] if weekdays else "Wednesday",
            "default_time": times.most_common(1)[0][0] if times else "15:00",
        })

    seasons.sort(key=lambda x: x["start"], reverse=True)
    return seasons


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--out", default=NEW, help="output directory (for testing)")
    args = ap.parse_args()

    records = []
    for season in sorted(os.listdir(OLD)):
        sdir = os.path.join(OLD, season)
        if not os.path.isdir(sdir):
            continue
        for fn in sorted(os.listdir(sdir)):
            if not fn.endswith(".yml"):
                continue
            path = os.path.join(sdir, fn)
            records.append({
                "record": convert(load_record(path), season),
                "source": os.path.join(season, fn),
            })

    # Filenames come from seminar_date, not from the old filename.
    #
    # Within a date, keep whichever file was already named plainly
    # (2016-10-24.yml) ahead of improvised second-talk names (-2, -talk2).
    # Without this, ASCII ordering puts "-2" before "." and the two simply swap
    # names, which shows up as a rename in review while meaning nothing.
    records.sort(key=lambda r: (
        r["record"]["seminar_date"],
        0 if PLAIN_NAME.match(os.path.splitext(os.path.basename(r["source"]))[0]) else 1,
        r["source"],
    ))

    used = collections.Counter()
    for r in records:
        base = r["record"]["seminar_date"][:10]
        used[base] += 1
        r["name"] = f"{base}.yml" if used[base] == 1 else f"{base}-{used[base]}.yml"

    seasons = build_seasons(records)

    if args.dry_run:
        print("DRY RUN -- nothing written\n")
    else:
        shutil.rmtree(args.out, ignore_errors=True)
        os.makedirs(args.out, exist_ok=True)
        for r in records:
            with open(os.path.join(args.out, r["name"]), "w", encoding="utf-8") as fh:
                fh.write(dump(r["record"]))
        if args.out == NEW:
            with open(SEASONS, "w", encoding="utf-8") as fh:
                fh.write(yaml.safe_dump(seasons, sort_keys=False,
                                        allow_unicode=True, width=10**9))

    statuses = collections.Counter(r["record"]["status"] for r in records)
    renamed = [r for r in records if os.path.basename(r["source"]) != r["name"]]

    print(f"seminars migrated : {len(records)}")
    print(f"seasons           : {len(seasons)}")
    print("statuses          : " +
          ", ".join(f"{k}={v}" for k, v in sorted(statuses.items())))
    print(f"renamed files     : {len(renamed)}")
    for r in renamed[:12]:
        print(f"    {r['source']}  ->  {r['name']}")
    if len(renamed) > 12:
        print(f"    ... and {len(renamed) - 12} more")

    others = [r for r in records if r["record"]["status"] != "scheduled"]
    if others:
        print("\nnon-scheduled records:")
        for r in sorted(others, key=lambda r: r["record"]["seminar_date"]):
            rec = r["record"]
            note = f" ({rec['note']})" if rec.get("note") else ""
            print(f"    {rec['status']:<11} {rec['seminar_date'][:10]}  "
                  f"{rec.get('presenters') or '-'}{note}")


if __name__ == "__main__":
    main()
