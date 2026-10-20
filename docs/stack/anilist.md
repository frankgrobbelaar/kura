# AniList (which anime a file is)

[AniList](https://anilist.co) knows anime best: every entry's English, romaji and native titles
and its nicknames ("DBZ"), whether it's a TV series, a film, an OVA or a special, its episode count
and dates, what's airing, and how seasons, films and specials connect (sequel, prequel, side
story). Kura searches it to work out which anime a file is; TMDB ([tmdb.md](tmdb.md)) then gives
the episodes in Plex's shape.

It replaced the manami offline database, the first plan, whose repository was archived in 2026:
AniList is always current and needs no download.

## No key, about 30 requests a minute

AniList's API is free for non-commercial use and needs no key or account. Its rate limit is
90 requests a minute, currently lowered to 30 (it says so in `X-RateLimit-Limit`). When a minute's
requests run out (`X-RateLimit-Remaining: 0`), [kura/web.py](../../engine/src/kura/web.py) waits
for `X-RateLimit-Reset` before the next one, and a 429 is retried after its `Retry-After`. The
engine has one AniList client (`create_app` makes it), so scans, the hourly check and the match
screen's search share the minute's requests; the search asks once the owner stops typing. Kura
asks once per anime (a few times for a name that finds nothing, see below), with everything it
needs in that one answer, and keeps the answers, so a library of a hundred anime costs a few
minutes on the first scan and nothing after.

## What Kura asks

One GraphQL endpoint, `POST https://graphql.anilist.co`, from
[kura/anilist.py](../../engine/src/kura/anilist.py):

- a search: `Page(perPage: N) { media(search: $search, type: ANIME) { … } }`;
- one entry: `Media(id: $id, type: ANIME) { … }`.

Both ask for the same fields: `id format episodes duration status startDate endDate
title { romaji english native } synonyms description(asHtml: false) genres
studios(isMain: true) { nodes { name } } coverImage { large extraLarge } bannerImage
nextAiringEpisode relations { edges { relationType node { … } } }`. The synopsis comes with
markup and notes Kura takes out (`plain_text` in kura/core/catalog.py): line breaks stay,
tags and `~!spoilers!~` go, and so does the note of where it came from, "(Source: …)". A change
to the fields asked for raises `SHAPE` in kura/anilist.py, which is part of every answer's key
in the cache, so answers kept from before aren't read for fields they don't have.
[kura/core/catalog.py](../../engine/src/kura/core/catalog.py) reads them into `Anime` and
`Related` values, with Kura's kinds: TV, TV short and web series (ONA) are a series, MOVIE a
movie, OVA an OVA, SPECIAL and MUSIC a special. Relations to manga and novels are dropped. The
relations of every entry the library matched are kept (`anilist_links`), and they tie franchises
together: sequels, prequels, alternative versions, films and side stories do, crossovers
(`CHARACTER`) and loose links (`OTHER`) don't.

## The rest of a franchise

To show what a franchise lacks, Kura follows those same story links out from the library's
entries and asks about each entry it reaches (`Media(id: …)`), keeping its name, format, status,
first and last day, episode count and length, cover, synopsis, genres and main studio in
`anilist_entries` and its links with the rest
([kura/franchises.py](../../engine/src/kura/franchises.py)). It asks three at each of the
watcher's look-arounds, every 15 seconds while no scan runs and no change waits for one: about
12 a minute, leaving most of the limit to scans and the match screen. What the library lacks
comes first, since that's what a franchise's page shows, and the library's own entries after
(Kura has their links from identifying them); franchises take turns, so a new one isn't kept
waiting behind a big one. Dragon Ball's franchise is 43 entries (nine
series, 21 films, three OVAs, nine specials and one not given a format yet), so it's known about
four minutes after Kura first looks. Each entry is asked about afresh weekly, or daily while it
airs or is still to come (and daily, too, while AniList gives nothing for it), and that's how a
new one turns up: AniList links Dragon Ball Super: Beerus from Dragon Ball Z and Super, so the
next look at either finds it. A franchise is followed 200 entries out at most, and never into
another franchise the library has (through a crossover AniList ties to both). What's looked up
this way never changes which titles make a franchise on Home: only the links of the library's
own entries do. Music videos, cancelled entries and ones without a format yet aren't listed.

Answers are kept a week in the data folder's `cache/`, so a rescan asks nothing again. A show
still airing is the exception: whenever its episode list is due (every hour), a scan or the hourly
check asks AniList afresh, or a new episode would go unnoticed for a week.

## When a name finds nothing

AniList's search finds an entry only when every word asked for is in one of its names, so a
release's own words empty the answer: `Dragon Ball Z - Movie 03 - The Tree of Might` finds
nothing, `Dragon Ball Z: The Tree of Might` (how Kura reads that name) finds the film. While
nothing found is sure, a numbered film is asked for again by its name up to a comma, its own name
alone, those with the series' initials written out (`DB Super BROLY` among Dragon Ball Z's
films is `Dragon Ball Super BROLY`, `spelled_out`), and its series (`searches` in
[kura/core/identify.py](../../engine/src/kura/core/identify.py)); entries are scored against the
best of those readings (`names`). When nothing at all is found, the name may be one AniList
writes otherwise: what its first word finds says how ("Dragonball" finds "Dragon Ball"), and
`Dragonball GT` is asked for as `dragon ball gt` (`respelled`). Every answer is kept a week, like
any other. While nothing found is sure still, and the owner has a TMDB key, TMDB's search is
asked too, and AniList for TMDB's names for what it finds (see [tmdb.md](tmdb.md), "When AniList
can't find a name"). A series' special its show's list doesn't name is looked up the same way by
its own name read as the series' ("Dragon Ball Z: A Hero's Legacy"); a one-off found so goes
into its show's specials by the day it first aired, or by its names there, or is a title of its
own (`_by_own_names` in [kura/identify.py](../../engine/src/kura/identify.py)). A name with
another after it in brackets, as releases give both (`Ore dake Level Up na Ken (Solo Leveling)`),
finds nothing as it is, so each is asked for too. Names are compared without accents on Latin
letters ("Pokémon" is "pokemon"), and a name that is the main part of an entry's, before its
subtitle, fits it nearly as well as the whole (`name_fit`): "Demon Slayer" is "Demon Slayer:
Kimetsu no Yaiba" more than it is Onigiri, a series of four-minute episodes also known as
"Demon Slayer". Not for a film: a series' films share its name before theirs, so a film named
for its series alone could be any of them, and waits for the owner.

## A show numbered straight through its seasons

AniList keeps every season apart (My Hero Academia is nine entries), but a release may number the
whole show straight through: `My Hero Academia - 159` is season 7's last. A season's episode
count alone would count against it ("only 13 episodes, files go up to 159"), so its sequels among
the entries found are counted with it, the first to air at each step (`_run` in
[kura/core/identify.py](../../engine/src/kura/core/identify.py)). When the files go no further
than those together, or the sequels go on past what the search found, nothing counts against
them; nothing counts for them either, or a remake whose seasons hold as many would fit as well as
the series the files fit alone (Fruits Basket's 2019 remake and its sequels hold the 2001
series' 26). The last season, with no sequels to carry the count, still doesn't fit. TMDB's
seasons then place each file by its number (see [tmdb.md](tmdb.md)), a season's folder that
counts on from the seasons before it too: a folder whose numbers would fit either way (14 to 25
in season 2's) goes as the release's other seasons' folders do, the show's videos placed there
before counted with the files being placed, so one identified later on its own goes as they did.

## Without a TMDB key

AniList's count stands in for TMDB's episode list: the episodes aired so far, numbered 1 to N in
one season (`save_anilist_title` in [kura/identify.py](../../engine/src/kura/identify.py)). For a
show still airing that's every episode before `nextAiringEpisode`; when AniList can't say, the list
stays as it was. AniList doesn't date old episodes, so they carry no air date, and all of them
count as aired when Kura looks for gaps.

## Tests

`tests/data/anilist/` holds real AniList answers (Dragon Ball Z, Cowboy Bebop, Attack on Titan
Season 3 Part 2, One Piece, My Hero Academia, Seraph of the End, Demon Slayer, Fruits Basket, and
the searches
for The Tree of Might, "Dragonball" and Dragon Ball GT), saved once with their synopses left out,
so parsing is tested against what AniList really sends. No test reaches AniList
itself: `tests/fake_web.py` answers instead, with `tests/services.py`'s answers to exact searches
first (as AniList, a search with a word no name has finds nothing) and kinder ones after.
