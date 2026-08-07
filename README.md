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

## Adding a seminar

Seminars live in `data/seminar/<season>-<year>/`, one file per seminar, named
`YYYY-MM-DD.yml`. For example, `data/seminar/fall-2026/2026-09-02.yml`:

```yaml
seminar_date: 2026-09-02T15:00:00
presenters: "Jane Doe"
affiliations: "PSU"
title: "Title of the talk"
host: "CCBB (Some Host)"
location: ""
zoom_url: ""
```

To add one through the GitHub web interface, use **Add file → Create new file**
and type the full path into the filename box, including the slashes:

```
data/seminar/fall-2026/2026-09-02.yml
```

GitHub creates any missing folders as you type each `/`. There is no need to
create the folder first.

**Do not add placeholder files to hold a folder open.** Hugo parses *every* file
under `data/` as structured data, so a stray `.txt`, `.md`, or `.gitkeep` there
will fail the build with an error like:

```
unmarshal of format "" is not supported
```

A season folder only needs to exist once it has a real seminar file in it.

## Starting a new season

A season needs **two** things. Adding seminar data without the page will build
successfully and show nothing on the site, so do not skip the second one.

1. The data files, as described above:
   `data/seminar/fall-2026/2026-09-02.yml`

2. A page for the season: `content/seminar/fall-2026.md`

   ```yaml
   ---
   title: 'Fall 2026'
   pre: "<i class='fa fa-bell-o'></i> "
   weight: 20263
   layout: 'seminar-table'
   ---
   ```

`layouts/seminar/seminar-table.html` matches the two by filename, so
`content/seminar/fall-2026.md` renders whatever is in
`data/seminar/fall-2026/`. The names must agree exactly.

The `weight` controls where the season sits in the left-hand navigation.
It is the year followed by a season digit:

| Season | Digit | Example (2026) |
| ------ | ----- | -------------- |
| Spring | 1     | `20261`        |
| Summer | 2     | `20262`        |
| Fall   | 3     | `20263`        |

(Seasons before 2020 use `2` for fall, from before summer sessions existed.
Leave those alone; use the table above for anything new.)

