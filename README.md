[www.ccbb.psu.edu](http://www.ccbb.psu.edu) ![Build and Deploy](https://github.com/psu-ccbb/ccbb-site/actions/workflows/build-and-deploy.yml/badge.svg?branch=master)
===

### Hugo

We use [Hugo](https://gohugo.io/) to build our site.  Installation instructions can be found [here](https://gohugo.io/getting-started/installing/).

The build is pinned to the Hugo version in `HUGO_VERSION` in
`.github/workflows/build-and-deploy.yml`. Use the **extended** build.

## Usage

There are no submodules, so a plain clone is enough:

```
$ git clone https://github.com/psu-ccbb/ccbb-site.git
$ cd ccbb-site
$ hugo
```

You can preview the site with live reload using:

```
$ hugo server
```

To run the link checker the way CI does:

```
$ bundle install
$ hugo
$ cd public && bundle exec ../ccbb-htmlproofer
```

## Layouts

The site has **no third-party theme**. Everything it renders lives in this repo:

- `layouts/` — templates
- `assets/css/main.css` — styles

It previously used the `docdock` theme as a git submodule. That theme was
unmaintained after 2019 and did not build on current Hugo, which is what froze
the site on Hugo 0.50 (released 2018) for years. Owning the layouts means
nothing can go stale out from under us again.

The seminar table is the part most worth understanding:

| File | Does |
| --- | --- |
| `layouts/seminar/seminar-table.html` | one season's page |
| `layouts/seminar/list.html` | `/seminar/` — newest season plus an index of the rest |
| `layouts/partials/seminar-table.html` | the table, and works out which talk is next |
| `layouts/partials/seminar-row.html` | one talk |
| `layouts/partials/seminar-notice.html` | the standing WWWGLS notice above every table |

The table is a real `<table>` so it keeps its schedule semantics for screen
readers; CSS restacks it into labelled cards below 700px, which is why every
`<td>` carries a `data-label`.

## Changing the schedule

**You do not need to edit any files.** Everything is done through forms.

Go to the season's page on the site and add `?edit=1` to the address, e.g.

```
https://www.ccbb.psu.edu/seminar/fall-2026/?edit=1
```

Bookmark that. In edit mode the page grows the controls you need:

| To do this | Use |
| --- | --- |
| Find any talk, past or future | `/seminar/search/?edit=1` — one box over all of them |
| Change a talk's speaker, title, time, Zoom link | the **Edit** link on that talk's row |
| Cancel a talk, or mark a break week | the **Edit** link, then change **Status** |
| Add a talk | **Add a seminar to …** at the bottom |
| Start a new semester | **Start a new season** at the bottom |

Each opens a form. The **Edit** form arrives **already filled in** with that
talk's current details, so you change what is wrong and submit.

A bot applies the change, replies on the issue, and closes it. The site updates
a couple of minutes later. Every change is an ordinary commit, so anything can
be undone — the bot's reply links to it.

Punctuation in titles is fine. Colons, apostrophes, quotes and dashes all work,
because the form never asks you to write YAML.

### If the bot refuses

It replies explaining what to fix and leaves the issue open. Correct the issue
and it tries again. Nothing is changed until it succeeds.

Only people with write access to this repository can change the site this way.

### Removing a talk

Prefer **Cancelled** (the date still shows, marked) or **No seminar this week**
(the date shows with a reason, e.g. "Thanksgiving break"). Both are more useful
to a reader than a silent gap in the schedule.

**Delete this record** removes it entirely and needs the confirmation box
ticked. Deleting a talk that has already happened needs a second tick, because
it removes it from the archive.

## Seminar data

Seminars live in `data/seminars/`, one file per talk:

```yaml
season: fall-2026
seminar_date: '2026-09-02T15:00:00'
status: scheduled
presenters: Jane Doe
affiliations: Penn State
title: 'Title of the talk: subtitles are fine'
host: CCBB (Some Host)
```

Three things are deliberately different from how this used to work:

**The filename does not matter.** Nothing parses it. `seminar_date` inside the
file is authoritative and `season` says which season the talk belongs to. The
old layout encoded both in the path, so `Fall-2026` instead of `fall-2026`, or
`2026-02-10,yml` instead of `.yml`, silently produced a page with nothing on it.

**There are no season directories**, so there is no empty-directory problem and
no placeholder files. A `.placeholder` used to be required to keep a directory
in git, while any *non*-dot file under `data/` crashed the build.

**`status` replaces five different conventions** for "no talk happened":

| `status` | Means |
| --- | --- |
| `scheduled` | a normal talk (the default) |
| `cancelled` | called off; the row still shows, marked |
| `rescheduled` | being moved; no date shown |
| `no_seminar` | a break week — put the reason in `note` |

## Finding a seminar

`/seminar/search/` lists every talk the centre has hosted with a filter box.
Type a speaker, a topic, an affiliation or a year; rows filter as you type.

There is **no search index and no search library**. All 322 talks are rendered
into the page and the filter hides rows that don't match. At this size that is
faster than fetching and querying an index, it cannot drift out of sync with the
data the way a generated index can, and it adds no dependency. With JavaScript
off the box is hidden and the full list still renders, so find-in-page works.

Accents are folded, so `llinas` finds `Llinás`. Multiple words all have to match,
in any order. `?q=chikhi` filters on load, so you can link to a search.

This page is also the most useful one for maintainers, because you can find a
talk without knowing which season it is in:

```
https://www.ccbb.psu.edu/seminar/search/?edit=1
```

Search for the talk, click **Edit**. Add and season buttons are at the bottom.

## How the schedule stays current

The site is time-aware, and all of it is worked out at build time from the
build's own clock:

- which talk is flagged **Next**
- the **Upcoming seminars** list on the home page
- which seasons are recent and which have been archived

So the build runs on a daily schedule as well as on every push. Without that,
"upcoming" would freeze at whenever someone last pushed and a talk would stay
listed as upcoming after it had happened.

**Archiving needs no job and no commit.** A season is *recent* if it has not
finished yet, or if it is one of the `recent_seasons` most recently finished
(see `config.yml`). Everything older moves to `/seminar/archive/` on its own as
the calendar moves — there is nothing to run, nothing to forget, and no stored
state that can drift.

Archiving is presentation only. Nothing is deleted and no URL changes:
`/seminar/fall-2016/` keeps resolving forever. This is a scholarly record with
inbound links, and html-proofer checks the links still work on every build.

To show more or fewer seasons before archiving, change `recent_seasons` in
`config.yml`.

## Seasons

Normally you start a season with the **Start a new season** form (above), which
can also pre-create the whole semester's weekly slots in one go. This is what it
does underneath: adds one entry to `data/seasons.yml`.

```yaml
- slug: spring-2027
  label: Spring 2027
  start: '2027-01-01'
  end: '2027-05-31'
  default_weekday: Wednesday
  default_time: '15:00'
```

That is the whole job. The season's page is generated from this entry by
`content/seminar/_content.gotmpl`, so there is no second file to create and no
`weight` to work out — ordering comes from `start`.

Previously a season needed **two** files whose names had to match exactly, and
getting only the data file right produced a green build that displayed nothing.

`start` and `end` only pre-select the season when adding a talk; a seminar's
`season` field is always what counts. Seasons may overlap, and historically they
have — `spring-2021` and `fall-2021` both contained a talk dated 2021-09-22.

## Re-running the migration

`scripts/migrate_seminars.py` converts the old `data/seminar/<season>/` layout to
the current one. It is repeatable, so if seminars were added to the old layout
after this branch was cut, pick them up with:

```
$ git checkout master -- data/seminar
$ python3 scripts/migrate_seminars.py
$ git rm -r --cached data/seminar && rm -rf data/seminar
```

Requires PyYAML (`apt install python3-yaml` or `pip install pyyaml`).
