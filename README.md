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

## Starting a new season

Add one entry to `data/seasons.yml`:

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
