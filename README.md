[www.ccbb.psu.edu](http://www.ccbb.psu.edu) ![Build and Deploy](https://github.com/psu-ccbb/ccbb-site/actions/workflows/build-and-deploy.yml/badge.svg?branch=master)
===

### Hugo

We use [Hugo](https://gohugo.io/) to build our site.  Installation instructions can be found [here](https://gohugo.io/getting-started/installing/).

## Usage

You can clone the repo using:

```
$ git clone --recursive https://github.com/psu-ccbb/ccbb-site.git
```

or

```
$ git clone https://github.com/psu-ccbb/ccbb-site.git
$ cd ccbb-site
$ git submodule update --init --recursive
```

You can build the site using:

```
$ cd ccbb-site
$ hugo
```

You can test out the site using:

```
$ hugo server
```

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

