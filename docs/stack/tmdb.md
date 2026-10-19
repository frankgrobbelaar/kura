# TMDB (episode lists, titles and artwork)

[TMDB](https://www.themoviedb.org) is the database Plex uses. Kura asks it for what anime
databases don't have in Plex's shape: every season with its episodes, their titles and air dates,
the specials in season 0, films, and posters. It's how Kura knows which episodes are missing, and
what to name files so Plex agrees. AniList ([anilist.md](anilist.md)) works out which anime a file
is; TMDB fills in the episodes.

## The key

TMDB needs a key, and it's the owner's own (the repo is public, so no key is ever in the code).
A free TMDB account has two under **Settings › API**; Kura takes either:

- the **API Read Access Token** (long, the one Setup asks for), sent as
  `Authorization: Bearer …`;
- the shorter **API Key** (32 hexadecimal characters), sent as `?api_key=…`.

Setup's Tools step and later Settings have the box for it (`app/src/components/tmdb-key.tsx`).
`PUT /tmdb` checks the key with TMDB (`GET /3/authentication`) and keeps it only if TMDB accepts
it; offline, nothing is kept and Kura says to try again online. A key added after the library was
scanned has every file AniList alone matched identified again (`identify_again`), by a scan Kura
starts then, so they land in TMDB's seasons; the owner's own choices keep their anime.
`DELETE /tmdb` forgets the key: titles found on TMDB keep their lists, and new files of their
anime still join them.

[kura/credentials.py](../../engine/src/kura/credentials.py) keeps it in the data folder's
`credentials.json`, encrypted by Windows for the signed-in user (DPAPI, `CryptProtectData`): it is
never in `kura.db`, so no export or backup carries it, and the file is useless on another PC or
account (Kura then asks for the key again). Home shows "TMDB connected · key ending ab12", and
Kura works without a key: it still identifies each anime with AniList, without episode titles.

## What Kura asks

[kura/tmdb.py](../../engine/src/kura/tmdb.py), through [kura/web.py](../../engine/src/kura/web.py):

| Request | For |
| --- | --- |
| `GET /3/authentication` | Checking a key |
| `GET /3/search/tv?query=…&first_air_date_year=…` | Finding a show |
| `GET /3/search/movie?query=…&primary_release_year=…` | Finding a film |
| `GET /3/tv/{id}`, then again with `append_to_response=season/0,season/1,…` (20 at most per request) | A show with every episode of every season |
| `GET /3/movie/{id}` | A film |
| `GET /3/tv/{id}/alternative_titles`, `GET /3/movie/{id}/alternative_titles` | The other names a show or film goes by, when a name AniList can't find leads TMDB to it |
| `GET /3/tv/{id}/images`, `GET /3/movie/{id}/images` with `include_image_language=en,ja,null` | The posters to choose from for a title (kept a day) |
| `https://image.tmdb.org/t/p/w342{poster_path}` | A poster |

[kura/core/catalog.py](../../engine/src/kura/core/catalog.py) turns the answers into plain
values (`Show`, `Episode`, `Film`, `Hit`). Besides the episode list, a show's and a film's
answers carry what a title's About panel shows, which Kura keeps on the title's row: its
synopsis (`overview`), genres (animation goes without saying), the first of its
`production_companies`, its status in Kura's words (finished, airing, coming, cancelled; a film
being made is coming), its latest episode so far (of its seasons: `last_air_date` can be a
special's, years on) and its `episode_run_time` (a film's `runtime`), and each episode's own
`overview` and `still_path`, which an episode's details show: the still comes from the image
server at its own size (`original`; TMDB's other sizes of a still are 300 wide at most), once,
when a card first shows it. Films are looked up again weekly, as finished
shows' lists are, so what's kept of them stays current too.

## When AniList can't find a name

AniList's search needs every word of a name in one of an entry's names; TMDB's search is more
forgiving and knows names in more languages (its alternative titles). So when nothing AniList
finds for a group of files is sure, `_through_tmdb` in
[kura/identify.py](../../engine/src/kura/identify.py) asks TMDB for the ways the name reads (three
at most; films as films, a show's episodes as shows, specials as both), and scores the best
three of each answer against the files (`tmdb_fit` in
[kura/core/identify.py](../../engine/src/kura/core/identify.py)): the names, the year, film or
show, Japanese animation. The first one's alternative titles are fetched when its own names fit
less than surely: `Bola de Dragon Z` is one of Dragon Ball Z's. Each that fits well enough is
asked of AniList by TMDB's names for it, and AniList's entries become guesses scored as if the
files bore TMDB's name, no surer than TMDB's fit (`through_tmdb`), with "TMDB knows it as …"
first among their reasons. A sure one is matched; the rest wait on the review screen, whose
search asks TMDB the same way. TMDB away or refusing the key leaves AniList's guesses as they are.

## Limits and errors

TMDB allows dozens of requests a second; Kura asks far fewer. `kura/web.py` gives a busy (429) or
briefly failing (5xx) service a few more tries, waiting as long as it asks (Retry-After) up to two
minutes, and turns everything else into a sentence: "TMDB didn't accept the key (…)", "Kura
couldn't reach api.themoviedb.org (…)".

## Terms and credit

TMDB's API is free for non-commercial use with attribution. Kura shows "This product uses the TMDB
API but is not endorsed or certified by TMDB" with TMDB's logo beside it, smaller than Kura's own,
in Settings, under About and under Titles and artwork: `components/tmdb-credit.tsx`.
The logo is TMDB's "alt short" file from its logos page, unchanged (`app/src/assets/README.md`);
it's the one picture the repo carries that isn't Kura's own (the owner's call, 2026-10-12), and
the third-party notices say it's TMDB's.

## Tests

No test reaches TMDB: `tests/fake_web.py` answers instead, and `tests/tmdb_data.py` builds TMDB's
answers in TMDB's shape (Dragon Ball Z's nine seasons, a 22-season show, films, searches).
