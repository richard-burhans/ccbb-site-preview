#!/usr/bin/env python3
"""Apply a seminar issue-form submission to the data files.

Reads the rendered issue body on stdin (or --body-file) and writes/updates/
deletes files under data/. Prints a human-readable summary on stdout, which the
workflow posts back as a comment.

The point of this script is that nobody hand-writes YAML. The form supplies
named fields, so a key cannot be misspelled -- it is never typed. Values are
serialised with a real YAML emitter, so a colon in a talk title ("Bird
Evolution: from dinosaurs to DNA") is ordinary text rather than a parse error.
Both of those were recurring failures in this repo's history.

Exit codes: 0 applied, 1 rejected with an explanation, 2 internal error.

Usage: python3 scripts/seminar_bot.py [--body-file F] [--repo-root D] [--dry-run]
"""

import argparse
import calendar  # noqa: F401  (kept for date helpers used by callers)
import collections
import datetime as dt
import os
import re
import sys

import yaml

NO_RESPONSE = "_No response_"

# Labels as they appear in .github/ISSUE_TEMPLATE/*.yml. GitHub renders a form
# response as "### <label>" followed by the value, so these are the contract
# between the forms and this script. Keep them in sync.
FIELD_LABELS = {
    "Record ID": "record",
    "Season": "season",
    "Status": "status",
    "Date": "seminar_date",
    "Time": "seminar_time",
    "Presenter(s)": "presenters",
    "Affiliation(s)": "affiliations",
    "Talk title": "title",
    "Host": "host",
    "Location": "location",
    "Zoom URL": "zoom_url",
    "Slides URL": "slides",
    "Note": "note",
    "Confirm": "confirm",
    # season-start form
    "Season start": "start",
    "Season end": "end",
    "Weekday": "default_weekday",
    "Create slots from": "slots_from",
    "Create slots until": "slots_to",
}

STATUS_FROM_LABEL = {
    "Scheduled": "scheduled",
    "Cancelled": "cancelled",
    "To be rescheduled": "rescheduled",
    "No seminar this week": "no_seminar",
}

FIELD_ORDER = [
    "season", "seminar_date", "status", "presenters", "affiliations",
    "title", "host", "location", "zoom_url", "slides", "note",
]
ALWAYS = {"season", "seminar_date", "status"}

WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday",
            "Saturday", "Sunday"]


class Reject(Exception):
    """A submission we refuse, with an explanation aimed at a non-programmer."""


# ----------------------------------------------------------------- parsing


def parse_issue_body(body):
    """Turn a rendered issue-form body into {field: value}.

    GitHub renders each answer as a level-3 heading with the field's label,
    followed by the value. Unanswered fields render as "_No response_".
    """
    out = {}
    chunks = re.split(r"^###[ \t]+(.+?)[ \t]*$", body, flags=re.M)
    # chunks[0] is any preamble; then (label, value) pairs.
    for i in range(1, len(chunks) - 1, 2):
        label, value = chunks[i].strip(), chunks[i + 1].strip()
        field = FIELD_LABELS.get(label)
        if not field:
            continue
        out[field] = "" if value == NO_RESPONSE else value
    return out


def checked_boxes(value):
    """Return the set of ticked checkbox labels from a checkboxes answer."""
    return {m.group(1).strip()
            for m in re.finditer(r"^- \[[xX]\][ \t]*(.+?)[ \t]*$", value, re.M)}


# ------------------------------------------------------------------ helpers


def load_seasons(root):
    path = os.path.join(root, "data", "seasons.yml")
    with open(path, encoding="utf-8") as fh:
        return yaml.safe_load(fh) or []


def season_by_slug(seasons, slug):
    for s in seasons:
        if s["slug"] == slug:
            return s
    return None


def parse_date(text, what="Date"):
    text = (text or "").strip()
    if not text:
        raise Reject(f"**{what}** is required.")
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%m/%d/%Y"):
        try:
            return dt.datetime.strptime(text, fmt).date()
        except ValueError:
            pass
    raise Reject(
        f"**{what}** could not be read as a date: `{text}`.\n\n"
        "Please write it as year-month-day, for example `2026-09-02`."
    )


def parse_time(text, default="15:00"):
    text = (text or "").strip()
    if not text:
        return default
    m = re.fullmatch(r"(\d{1,2}):(\d{2})\s*([ap]\.?m\.?)?", text, re.I)
    if not m:
        raise Reject(
            f"**Time** could not be read: `{text}`.\n\n"
            "Please use a 24-hour clock, for example `15:00` for 3 pm."
        )
    hour, minute, ampm = int(m.group(1)), int(m.group(2)), m.group(3)
    if ampm:
        ampm = ampm.lower().replace(".", "")
        if ampm == "pm" and hour < 12:
            hour += 12
        elif ampm == "am" and hour == 12:
            hour = 0
    if hour > 23 or minute > 59:
        raise Reject(f"**Time** is not a valid time of day: `{text}`.")
    return f"{hour:02d}:{minute:02d}"


def record_path(root, record_id):
    return os.path.join(root, "data", "seminars", f"{record_id}.yml")


def write_record(path, record):
    ordered = {k: record[k] for k in FIELD_ORDER
               if k in ALWAYS or record.get(k)}
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(yaml.safe_dump(ordered, sort_keys=False, allow_unicode=True,
                                width=10**9, default_flow_style=False))


def free_record_id(root, date_str):
    """First unused id for a date: 2026-09-02, then -2, -3 ..."""
    if not os.path.exists(record_path(root, date_str)):
        return date_str
    n = 2
    while os.path.exists(record_path(root, f"{date_str}-{n}")):
        n += 1
    return f"{date_str}-{n}"


def apply_fields(record, fields):
    """Copy the editable text fields from a submission onto a record."""
    for key in ("presenters", "affiliations", "title", "host", "location",
                "zoom_url", "slides", "note"):
        if key in fields:
            record[key] = fields[key].strip()
    return record


# ------------------------------------------------------------------ actions


def do_season(root, fields, dry):
    slug = (fields.get("season") or "").strip().lower()
    if not re.fullmatch(r"(spring|summer|fall|winter)-\d{4}", slug):
        raise Reject(
            f"**Season** should look like `fall-2027`, but got `{slug}`.\n\n"
            "Use a lower-case season name, a hyphen, then the four-digit year."
        )
    seasons = load_seasons(root)
    if season_by_slug(seasons, slug):
        raise Reject(f"Season `{slug}` already exists.")

    start, end = parse_date(fields.get("start"), "Season start"), \
        parse_date(fields.get("end"), "Season end")
    if end < start:
        raise Reject("**Season end** is before **Season start**.")

    weekday = (fields.get("default_weekday") or "Wednesday").strip()
    if weekday not in WEEKDAYS:
        raise Reject(f"**Weekday** `{weekday}` is not a day of the week.")
    time_s = parse_time(fields.get("seminar_time"))

    part, year = slug.split("-")
    entry = {
        "slug": slug,
        "label": f"{part.capitalize()} {year}",
        "start": start.isoformat(),
        "end": end.isoformat(),
        "default_weekday": weekday,
        "default_time": time_s,
    }
    seasons.append(entry)
    seasons.sort(key=lambda s: s["start"], reverse=True)

    # Optional: pre-create the recurring slots for the whole season.
    created = []
    sf, st = fields.get("slots_from", ""), fields.get("slots_to", "")
    if sf.strip() or st.strip():
        first = parse_date(sf, "Create slots from")
        last = parse_date(st, "Create slots until")
        if last < first:
            raise Reject("**Create slots until** is before **Create slots from**.")
        want = WEEKDAYS.index(weekday)
        day = first + dt.timedelta(days=(want - first.weekday()) % 7)
        while day <= last:
            rid = free_record_id(root, day.isoformat())
            rec = {
                "season": slug,
                "seminar_date": f"{day.isoformat()}T{time_s}:00",
                "status": "scheduled",
            }
            if not dry:
                write_record(record_path(root, rid), rec)
            created.append(rid)
            day += dt.timedelta(days=7)

    if not dry:
        with open(os.path.join(root, "data", "seasons.yml"), "w",
                  encoding="utf-8") as fh:
            fh.write(yaml.safe_dump(seasons, sort_keys=False,
                                    allow_unicode=True, width=10**9))

    msg = [f"Created season **{entry['label']}** (`{slug}`), "
           f"{entry['start']} to {entry['end']}, "
           f"{weekday}s at {time_s}."]
    if created:
        msg.append(f"\nAlso created **{len(created)} empty slots**, "
                   f"{created[0]} through {created[-1]}. "
                   "Fill each one in with its Edit link as speakers are confirmed.")
    else:
        msg.append("\nNo slots were created. Add talks with **Add a seminar**.")
    return f"season:{slug}", "\n".join(msg)


def do_add(root, fields, dry):
    seasons = load_seasons(root)
    slug = (fields.get("season") or "").strip().lower()
    season = season_by_slug(seasons, slug)
    if not season:
        known = ", ".join(f"`{s['slug']}`" for s in seasons[:6])
        raise Reject(
            f"There is no season called `{slug}`.\n\n"
            f"Existing seasons include: {known}.\n\n"
            "If this is a new semester, use **Start a new season** first."
        )

    date = parse_date(fields.get("seminar_date"))
    time_s = parse_time(fields.get("seminar_time"), season.get("default_time", "15:00"))
    status = STATUS_FROM_LABEL.get(fields.get("status", "").strip(), "scheduled")

    rid = free_record_id(root, date.isoformat())
    record = apply_fields({
        "season": slug,
        "seminar_date": f"{date.isoformat()}T{time_s}:00",
        "status": status,
    }, fields)

    if not dry:
        write_record(record_path(root, rid), record)

    who = record.get("presenters") or "no speaker yet"
    return f"add:{rid}", (
        f"Added a seminar on **{date:%B %-d, %Y}** at {time_s} "
        f"to {season['label']} — {who}.\n\n"
        f"It will appear on the site in a couple of minutes."
    )


def do_edit(root, fields, dry):
    rid = (fields.get("record") or "").strip()
    if not rid:
        raise Reject("**Record ID** was empty, so there is nothing to change.")
    path = record_path(root, rid)
    if not os.path.exists(path):
        raise Reject(
            f"There is no seminar with the ID `{rid}`.\n\n"
            "Use the **Edit** link next to the talk on the seminar page — it "
            "fills this in for you."
        )

    with open(path, encoding="utf-8") as fh:
        record = yaml.safe_load(fh) or {}

    label = (fields.get("status") or "No change").strip()
    ticked = checked_boxes(fields.get("confirm", ""))

    if label == "Delete this record":
        return do_delete(root, rid, path, record, ticked, dry)

    # Snapshot before anything is applied, so the summary reports status and
    # date changes too -- not just the free-text fields.
    before = dict(record)

    if label != "No change":
        if label not in STATUS_FROM_LABEL:
            raise Reject(f"**Status** `{label}` is not one I recognise.")
        record["status"] = STATUS_FROM_LABEL[label]

    if fields.get("seminar_date", "").strip():
        date = parse_date(fields["seminar_date"])
        old_time = (record.get("seminar_date") or "T15:00:00").split("T")[1][:5]
        time_s = parse_time(fields.get("seminar_time"), old_time)
        record["seminar_date"] = f"{date.isoformat()}T{time_s}:00"
    elif fields.get("seminar_time", "").strip():
        day = (record.get("seminar_date") or "").split("T")[0]
        record["seminar_date"] = f"{day}T{parse_time(fields['seminar_time'])}:00"

    apply_fields(record, fields)
    changed = [k for k in FIELD_ORDER
               if (before.get(k) or "") != (record.get(k) or "")]

    if not dry:
        write_record(path, record)

    when = (record.get("seminar_date") or "")[:10]
    if not changed:
        return f"edit:{rid}", (
            f"Nothing changed for the seminar on **{when}** — the details "
            "submitted match what was already there."
        )
    return f"edit:{rid}", (
        f"Updated the seminar on **{when}**.\n\n"
        f"Changed: {', '.join('`' + c + '`' for c in changed)}."
    )


def do_delete(root, rid, path, record, ticked, dry):
    if not any("permanently delete" in t for t in ticked):
        raise Reject(
            "To delete a seminar you also have to tick "
            "**“Yes, permanently delete this record”** under *Confirm*.\n\n"
            "If the talk was called off but the date should still show, choose "
            "**Cancelled** instead. If it is a break week with no talk at all, "
            "choose **No seminar this week** — that keeps the date visible with "
            "a reason, which is usually more useful to readers than a gap."
        )

    when = (record.get("seminar_date") or "")[:10]
    is_past = False
    try:
        is_past = dt.date.fromisoformat(when) < dt.date.today()
    except ValueError:
        pass

    if is_past and not any("archive" in t for t in ticked):
        raise Reject(
            f"The seminar on **{when}** has already happened, so deleting it "
            "removes it from the archive.\n\n"
            "If you are sure, tick the second *Confirm* box as well. If you "
            "just want to record that it did not take place, choose "
            "**Cancelled** instead."
        )

    if not dry:
        os.remove(path)
    return f"delete:{rid}", (
        f"Deleted the seminar record for **{when}**"
        f"{' (' + record['presenters'] + ')' if record.get('presenters') else ''}."
    )


# --------------------------------------------------------------------- main


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--body-file")
    ap.add_argument("--repo-root", default=os.path.dirname(
        os.path.dirname(os.path.abspath(__file__))))
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    body = (open(args.body_file, encoding="utf-8").read()
            if args.body_file else sys.stdin.read())
    fields = parse_issue_body(body)

    if not fields:
        print("REJECT\nThis issue doesn't look like one of the seminar forms, "
              "so nothing was changed.")
        return 1

    try:
        if "start" in fields and "end" in fields:
            action, message = do_season(args.repo_root, fields, args.dry_run)
        elif "record" in fields:
            action, message = do_edit(args.repo_root, fields, args.dry_run)
        else:
            action, message = do_add(args.repo_root, fields, args.dry_run)
    except Reject as e:
        print(f"REJECT\n{e}")
        return 1

    print(f"OK {action}")
    print(message)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:  # noqa: BLE001 - surfaced to the issue thread
        print(f"REJECT\nSomething went wrong applying this change: `{e}`\n\n"
              "Nothing was modified. Please tell Richard.")
        sys.exit(2)
