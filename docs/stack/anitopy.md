# anitopy (reading file names)

[anitopy](https://github.com/igorcmoura/anitopy) 2.1.1 turns an anime file name into its parts:
title, episode number, season, year, release group, resolution. It is a Python port of Anitomy,
the parser behind Taiga, and knows fansub and scene naming. Kura wraps it in
[`kura/core/names.py`](../../engine/src/kura/core/names.py) and adds its own rules.

## Why anitopy

On 2026-10-10 three parsers read the same 33 real-world names (the design boards' examples plus
common fansub and scene patterns):

| | Good at | Wrong on |
| --- | --- | --- |
| **anitopy 2.1.1** (chosen) | Absolute numbers (`Yu Yu Hakusho 112`, `HxH (2011) - 148`, `Dragon Ball - 001`), groups, resolutions | Type words left in titles (`Hellsing Ultimate OVA`, `Cowboy Bebop - Session`), bare `05.mkv` |
| guessit 4.4 | Scene names, stripping type words | Turns absolute numbers into seasons (`112` → S01E12, `001` → season 0, `(2011)` → season 2011): dangerous for anime |
| aniparse 2.0 | Uses folder names | Loses episodes in `Death_Note_07`, scene `S01E131`, and `Kai - 98 - The Final Battle` |

anitopy hasn't had a release since 2022, but it is small, pure Python, and does the hard part best.
Kura's rules cover its gaps, and the tests pin the behaviour, so swapping parsers later is safe.

## What Kura adds

- **Folders.** A `Season 03` or `Specials` folder gives `folder_season`; the show folder above it
  (`Dragon Ball Z (1989)`) gives `folder_title` and the year. A season's folder named after its
  show gives both: `[Anime Time] My Hero Academia Season 02`, `Kimetsu no Yaiba 2nd Season` and
  `Kimetsu no Yaiba S2` are the show and its season, and so is `Attack on Titan (Season 2)`
  (`Attack on Titan S01-S04` holds several, so it gives none). A folder of a show's films or
  specials (`My Hero Academia Movies`, `OVA`, a release's `3. TV Specials`) is passed over for the
  folder above, its own first words the show only when that one names none (they needn't be a
  show's: `Anime Movies`). A bare number in one is a special, and among films a film no name says
  which of, which waits for the owner; a file with a name of its own keeps it. A release counts
  its films and OVAs its own way, so such a folder is no season 0, and `Toradora! + OVA` holds
  the show as well, so it isn't one. A folder name's tags at its end go when they hold a release's
  words or a number
  (`[Anime Time] Boku No Hero Academia (My Hero Academia) (S01-S07+Movies+OVAs) [BD]` is `Boku
  No Hero Academia (My Hero Academia)`), a year among them kept; a name's own brackets stay
  (`Fate stay night [Unlimited Blade Works]`). General folders (`Downloads`, `Extras`, `TV`…)
  never count as titles.
- **Copies.** `(copy)`, ` - Copy` and ` (2)` are removed before parsing and set `is_copy`.
- **Kinds.** Episode, special (OVA, season 0, a PSA), movie (no episode number), extra (NCOP,
  NCED, PV, and a creditless opening or ending anywhere in the name, as `[SP02] NCED - 01`) or
  DVD file (`VTS_01_1.VOB`).
- **Clean titles.** Type and release words at the end of the title (`OVA`, `Movie`, `Session`,
  `final`) are removed, but not `End`, which anitopy reads as a release's wherever it is and
  titles end with (`Seraph of the End`); a title that is only a number becomes the episode.
  Scene names' dots are spaces (`Spy.x.Family.S01E01.1080p.WEB` is `Spy x Family`), and their
  source words (`WEB`, `BluRay`) are never an episode's title.
- **Numbered films.** A whole series' release numbers its films: `Dragon Ball Z - Movie 03 - The
  Tree of Might`, or without the dash, `My Hero Academia Movie 01 - Two Heroes`. anitopy reads no
  number after `Movie`, so that's all title to it; with a letter (`Movie 14b`) it takes the number
  for an episode's and the film's name for the episode's title. Either way Kura makes it a film
  titled `Dragon Ball Z: The Tree of Might`, with `series` `Dragon Ball Z`, leaving out what the
  release adds after the name (`aka Frieza`, a comma). The release's number counts its own films,
  not AniList's.
- **Named OVAs.** `My Hero Academia OVA - Training of the Dead!` (or `OVA 2 - ...`, `Special
  - ...`) is a special of `My Hero Academia` named `Training of the Dead!`, which places it among
  the show's specials by name; `OVA - Kuro no Keiyakusha Gaiden - 03` is that OVA's third.
- **A film named as its folder.** `Jujutsu Kaisen 0 (2021)\Jujutsu Kaisen 0 (2021).mkv` is that
  film, number and all, not episode 0 of Jujutsu Kaisen; a numbered film so filed is read as one.
- **Japanese names.** Full-width letters, digits and marks read as plain ones (`Re：ゼロ` is
  `Re:ゼロ`), and nothing else changes (`Ranma ½`). `第01話` or `第1回` is the episode (`第01集`
  and `第01话` too, as Chinese subtitle groups write them), `第2期` or `シーズン2` the season,
  `総集編`, `特別編` and `番外編` a special. A name that starts with them (`第01話 冒険の終わり`)
  takes its show from its folder. `劇場版` or `Gekijouban` starting a name is a film, the
  series' name in corner brackets after it read as part of the film's (`劇場版「鬼滅の刃」無限列車編`
  is `鬼滅の刃 無限列車編`). A show's name in lenticular brackets (`【推しの子】`), which anitopy
  takes for a group's, is the title when nothing else is.
- **Years in brackets.** `(1990 BluRay - 1080p)` gives the year, which anitopy passes over; a span
  (`1989-2019`) or a checksum doesn't.
- File-name values (`title`, `season`) and folder values (`folder_title`, `folder_season`) stay
  apart, because they can disagree: `Season 07\Naruto Shippuden - 143.mkv` has an absolute episode
  number. Matching decides: a season's folder whose files count on from the seasons before it
  places them by their numbers (`numbered_through` in
  [kura/core/placing.py](../../engine/src/kura/core/placing.py)).

## Things to know

- anitopy keeps its state in module globals, so `parse_name` takes a lock; never call
  `anitopy.parse` directly.
- anitopy 2.1.1's search for an episode's own title went round forever on a name whose only words
  after its episode are a dash and one more mark (`Dragon Ball Z - 01 - .x`), holding that lock:
  Kura puts in its own search, ending there as Anitomy's does (`_search_for_episode_title`). When
  anitopy moves past 2.1.1, the hang test in `tests/core/test_names.py` says whether it's still
  needed.
- `Part 2` as an episode's title is the part of a season it names (`S3 Part 2 - 03`), but not after
  an episode code (`S01E05 - Part 2`), which says where the file goes.
- anitopy ships no types; `engine/typings/anitopy/__init__.pyi` declares the one function Kura uses.
- Add every name that parses wrongly to `engine/tests/core/test_names.py` before fixing it.
