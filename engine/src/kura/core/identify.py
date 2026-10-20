"""Working out which anime each video is: grouping files that look like the same anime, scoring
AniList's entries against them, and picking the same show or film on TMDB. What AniList's search
can't find by a name, TMDB's may: its shows and films are scored against the files too, and
AniList's entries for them are guesses no surer than that.

Every guess gets a confidence from 0 to 100 and the reasons for it, in the words the review screen
shows. Kura accepts a guess on its own only when it's sure; the rest wait for the owner.
"""

import itertools
import re
import statistics
import unicodedata
from collections import Counter
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, replace
from datetime import date
from difflib import SequenceMatcher
from pathlib import PurePath

from kura.core.catalog import Anime, Hit, TitleKind
from kura.core.names import Kind, ParsedName, film_part

SURE = 75  # a guess at least this confident is taken without asking
WORTH_SHOWING = 15  # guesses below this aren't shown on the review screen


@dataclass(frozen=True)
class FileFacts:
    """What Kura knows about one video before identifying it."""

    id: int
    path: PurePath
    parsed: ParsedName
    minutes: float | None  # its length, once ffprobe has read it


@dataclass(frozen=True)
class Group:
    """Files that look like the same anime, looked up together."""

    query: str  # the name to search for: "Dragon Ball Z"
    year: int | None
    movie: bool  # every file looks like a film
    files: tuple[FileFacts, ...]
    series: str | None = None  # a numbered film's series, whose name its own follows

    @property
    def longest_episode(self) -> int | None:
        numbers = [f.parsed.episode_end or f.parsed.episode for f in self.files]
        known = [n for n in numbers if n is not None]
        return max(known) if known else None

    @property
    def minutes(self) -> float | None:
        lengths = [f.minutes for f in self.files if f.minutes]
        if not lengths:
            return None
        parts = {film_part(f.path.stem) for f in self.files} - {None}
        if self.movie and len(parts) > 1:
            return sum(lengths)  # a film in parts (CD1, CD2) is as long as they are together
        return statistics.median(lengths)


@dataclass(frozen=True)
class Guess:
    anime: Anime
    confidence: int  # 0 to 100
    reasons: tuple[str, ...]  # "Title matches", "1989 fits", …


def group_files(files: Iterable[FileFacts]) -> list[Group]:
    """Files that look like the same anime, by their title (from the name or the folder), by
    whether they're films, and by part: "Season 3 Part 2" numbers its episodes from 1 again, so
    it is looked up on its own. Files without any title can't be looked up, so they're left out."""
    grouped: dict[tuple[str, str | None, bool], list[FileFacts]] = {}
    names: dict[tuple[str, str | None, bool], Counter[str]] = {}
    for facts in files:
        title = facts.parsed.best_title
        if not title or facts.parsed.kind in (Kind.EXTRA, Kind.DVD):
            continue
        key = (normalize(title), _part_words(facts.parsed), facts.parsed.kind is Kind.MOVIE)
        grouped.setdefault(key, []).append(facts)
        names.setdefault(key, Counter())[title] += 1
    groups: list[Group] = []
    for key, members in grouped.items():
        years = Counter(f.parsed.year for f in members if f.parsed.year)
        series = Counter(f.parsed.series for f in members if f.parsed.series)
        title = names[key].most_common(1)[0][0]  # the spelling most files use
        groups.append(
            Group(
                query=f"{title} {key[1]}" if key[1] else title,
                year=years.most_common(1)[0][0] if years else None,
                movie=key[2],
                files=tuple(members),
                series=series.most_common(1)[0][0] if series else None,
            )
        )
    return sorted(groups, key=lambda group: (group.query.casefold(), group.movie))


def names(group: Group) -> list[str]:
    """The ways a group's name reads, to score what's found against: its name; each of two names
    when it gives one in brackets after the other ("Kimetsu no Yaiba (Demon Slayer)"); and for a
    numbered film ("Dragon Ball Z: Battle of Gods, UNCut", or a series' special looked up by its
    own name) also its name up to a comma and its own name alone, with the series' initials
    written out: "DB Super BROLY" among Dragon Ball Z's films is "Dragon Ball Super BROLY"."""
    texts = [group.query]
    if both := _OTHER_NAME.match(group.query):
        texts += [both["name"], both["other"]]
    own = group.query.removeprefix(f"{group.series}: ") if group.series else group.query
    if group.series and own != group.query:
        first = own.split(",")[0].strip()
        texts += [f"{group.series} {first}", own, first]
        texts += [text for part in (own, first) if (text := spelled_out(part, group.series))]
    return _unique(texts)


# A name with another after it in brackets: "Ore dake Level Up na Ken (Solo Leveling)".
_OTHER_NAME = re.compile(r"^(?P<name>[^()]+?)\s*\((?P<other>[^()]*[^\W\d_][^()]*)\)$")


def searches(group: Group, *, series: bool = True) -> list[str]:
    """What to ask AniList for a group, in turn while nothing it finds is sure: the ways its name
    reads (`names`), then a numbered film's series (unless `series` is False). AniList finds
    nothing for a name with a word none of an entry's names has, such as a release's own
    "UNCut" or "DB" for Dragon Ball."""
    texts = names(group)
    if series and group.series and len(texts) > 1:
        texts.append(group.series)
    return _unique(texts)


def spelled_out(text: str, series: str) -> str | None:
    """`text` with the series' initials at its start written out: "DB Super BROLY" in Dragon
    Ball Z is "Dragon Ball Super BROLY", "DBZ Kai" "Dragon Ball Z Kai". None without them."""
    first, _, rest = text.partition(" ")
    words = series.split()
    if not (first.isalpha() and first.isupper() and 2 <= len(first) <= len(words)):
        return None
    if first != "".join(word[0] for word in words[: len(first)]).upper():
        return None
    return " ".join([*words[: len(first)], rest]).strip()


def _unique(texts: Iterable[str]) -> list[str]:
    unique: dict[str, str] = {}
    for text in texts:
        if words := normalize(text):  # each asked once, and nothing asked for no name
            unique.setdefault(words, text)
    return list(unique.values())


def respelled(text: str, entries: Sequence[Anime]) -> str | None:
    """`text` with a word that the entries' names write as two written their way: "Dragonball
    GT" is "dragon ball gt" beside an entry called "Dragon Ball". None when nothing changes."""
    split: dict[str, str] = {}
    for entry in entries:
        for title in entry.titles:
            for first, second in itertools.pairwise(normalize(title).split()):
                split.setdefault(first + second, f"{first} {second}")
    words = normalize(text).split()
    put = [split.get(word, word) for word in words]
    return " ".join(put) if put != words else None


def _part_words(parsed: ParsedName) -> str | None:
    """ "Season 3 Part 2" for a file from a later part, else None."""
    if parsed.part is None or parsed.part < 2:
        return None
    season = parsed.season if parsed.season is not None else parsed.folder_season
    return f"Season {season} Part {parsed.part}" if season else f"Part {parsed.part}"


def guesses(group: Group, entries: Sequence[Anime]) -> list[Guess]:
    """AniList's entries as guesses for a group, most confident first. Each is scored with the
    others found beside it: a season's sequels among them count for files numbered straight
    through the show."""
    found = [_guess(group, entry, rank, entries) for rank, entry in enumerate(entries)]
    found.sort(key=lambda guess: guess.confidence, reverse=True)
    return [guess for guess in found if guess.confidence >= WORTH_SHOWING]


def merged(*rankings: Sequence[Guess]) -> list[Guess]:
    """Guesses from several lookups as one ranking, most confident first: each entry once, at its
    surest."""
    best: dict[int, Guess] = {}
    for ranking in rankings:
        for guess in ranking:
            known = best.get(guess.anime.id)
            if known is None or guess.confidence > known.confidence:
                best[guess.anime.id] = guess
    return sorted(best.values(), key=lambda guess: guess.confidence, reverse=True)


def tmdb_fit(group: Group, hit: Hit, rank: int, aliases: Sequence[str] = ()) -> int:
    """How well a show or film TMDB found fits a group's files, from 0 to 100: its names (and the
    other names TMDB knows it by, `aliases`) against the ways the files' name reads, its year,
    whether it's a film as they are, and whether it's Japanese animation."""
    known = [title for title in (hit.title, hit.original_title, *aliases) if title]
    name = name_fit(names(group), known, main_part=not group.movie)
    score = name * 70
    if group.year and hit.year:
        if group.year == hit.year:
            score += 15
        elif abs(group.year - hit.year) == 1:
            score += 5
        else:
            score -= 25
    # TMDB has a special as its show's, or as a film of its own.
    specials = all(f.parsed.kind is Kind.SPECIAL for f in group.files)
    score += 10 if specials or (hit.media == "movie") == group.movie else -20
    score += 8 if hit.animation else -15
    score += 7 if hit.japanese else -5
    score += 5 if rank == 0 else 0
    return max(0, min(100, round(score)))


def through_tmdb(group: Group, hit: Hit, fit: int, entries: Sequence[Anime]) -> list[Guess]:
    """AniList's entries for a show or film TMDB found by a group's name, as guesses: scored as if
    the files bore TMDB's names for it, and no surer than it fits them (`fit`)."""
    said = f"TMDB knows it as {hit.title}"
    found: list[Guess] = []
    for title in dict.fromkeys((hit.title, hit.original_title)):
        found = merged(found, guesses(replace(group, query=title, series=None), entries))
    capped = [Guess(g.anime, min(g.confidence, fit), (said, *g.reasons)) for g in found]
    return [guess for guess in capped if guess.confidence >= WORTH_SHOWING]


def _guess(group: Group, entry: Anime, rank: int, found: Sequence[Anime] = ()) -> Guess:
    name = name_fit(names(group), entry.titles, main_part=not group.movie)
    score = name * 70
    reasons: list[str] = ["Title matches" if name >= 0.95 else f"Title {round(name * 100)}% alike"]
    # A series' specials came after it began, and are as long as they are.
    its_specials = entry.kind is TitleKind.SERIES and all(
        f.parsed.kind is Kind.SPECIAL for f in group.files
    )

    if group.year and entry.year:
        if group.year == entry.year:
            score += 15
            reasons.append(f"{entry.year} fits")
        elif abs(group.year - entry.year) == 1:
            score += 5
        elif not (its_specials and group.year > entry.year):
            score -= 25
            reasons.append(f"From {entry.year}, not {group.year}")

    score += _kind_fit(group, entry, reasons)

    longest = group.longest_episode
    if longest is not None and entry.episodes and not group.movie:
        run, goes_on = _run(entry, found)
        if longest <= entry.episodes:
            score += 10
            reasons.append(
                f"{_episodes(entry.episodes)} {'fits' if entry.episodes == 1 else 'fit'}"
            )
        # Files numbered on through its later seasons fit it, but no better than they'd fit a
        # remake whose seasons hold as many: nothing's added, nothing's taken away.
        elif longest <= run:
            reasons.append(f"{_episodes(run)} with its later seasons fit")
        elif goes_on:
            reasons.append("Its later seasons may hold the rest")  # past what AniList found
        elif not entry.airing:
            score -= 20
            reasons.append(f"Only {_episodes(entry.episodes)}, files go up to {longest}")

    minutes = group.minutes
    if minutes and entry.minutes and not its_specials:
        if abs(minutes - entry.minutes) <= max(3, entry.minutes * 0.25):
            score += 5
            reasons.append(f"{round(minutes)} min fits")
        else:
            score -= 15
            reasons.append(f"{round(minutes)} min, not {entry.minutes}")

    if rank == 0:
        score += 5  # AniList ranked it first
    return Guess(entry, max(0, min(100, round(score))), tuple(reasons))


def _run(entry: Anime, found: Sequence[Anime]) -> tuple[int, bool]:
    """How many episodes a series and the seasons after it have together, as far as the entries
    found (`found`) know them, and whether more follow that they don't: AniList keeps every
    season apart, a release can number the whole show straight through ("My Hero Academia -
    159"). A season with several sequels goes on with the first to air."""
    known = {each.id: each for each in found}
    total, at, seen = 0, entry, {entry.id}
    while True:
        if at.episodes is None:
            return total, True  # still airing, or its count not known yet
        total += at.episodes
        sequels = sorted(
            (
                related
                for related in at.related
                if related.relation == "SEQUEL"
                and related.kind is TitleKind.SERIES
                and related.id not in seen
            ),
            key=lambda related: related.start or date.max,
        )
        if not sequels:
            return total, False
        following = known.get(sequels[0].id)
        if following is None:
            return total, True
        at = following
        seen.add(at.id)


def _kind_fit(group: Group, entry: Anime, reasons: list[str]) -> float:
    if entry.kind is None:
        return -10
    if group.movie:
        if entry.kind is TitleKind.MOVIE:
            reasons.append("A film, like the file")
            return 10
        return -30 if entry.kind is TitleKind.SERIES else -10
    if entry.kind is TitleKind.MOVIE:
        return -40
    specials = all(f.parsed.kind is Kind.SPECIAL for f in group.files)
    if entry.kind in (TitleKind.OVA, TitleKind.SPECIAL):
        return 10 if specials else -10
    return -5 if specials else 5


def pick_hit(entry: Anime, found: Sequence[Hit]) -> tuple[Hit, int] | None:
    """The TMDB show or film that is `entry`, and how sure Kura is, or None when none fits.

    A later season or part on AniList is the same show on TMDB, so names are compared without
    "Season 3 Part 2", and the show may have started before the entry did.
    """
    names = {base_title(title) for title in entry.titles} | set(entry.titles)
    best: tuple[Hit, int] | None = None
    for rank, hit in enumerate(found):
        name = max(
            similarity(own, theirs) for own in names for theirs in (hit.title, hit.original_title)
        )
        score = name * 70
        if entry.year and hit.year:
            if hit.year == entry.year:
                score += 15
            elif hit.year < entry.year and hit.media == "tv":
                score += 5  # the show began with an earlier season
            elif abs(hit.year - entry.year) > 1:
                score -= 20
        score += 8 if hit.animation else -15
        score += 7 if hit.japanese else -5
        score += 5 if rank == 0 else 0
        confidence = max(0, min(100, round(score)))
        if best is None or confidence > best[1]:
            best = (hit, confidence)
    return best if best and best[1] >= _TMDB_SURE else None


_TMDB_SURE = 60

# "Season 3 Part 2", "2nd Season", "Part 2", "Cour 2", "The Final Season", "Final Chapters".
_SEASON_WORDS = re.compile(
    r"[\s:\-]*(?:\b(?:season|series)\s*\d+\b.*|\b\d+(?:st|nd|rd|th)\s+season\b.*|\bpart\s*\d+\b.*"
    r"|\bcour\s*\d+\b.*|\b(?:the\s+)?final\s+(?:season|chapters?)\b.*)$",
    re.IGNORECASE,
)


def base_title(title: str) -> str:
    """The show's name without the season or part: "Attack on Titan Season 3 Part 2" is
    "Attack on Titan"."""
    stripped = _SEASON_WORDS.sub("", title).strip(" :-")
    return stripped or title


def normalize(text: str) -> str:
    """A name reduced to what matters for comparing: letters and digits in lower case, without
    the accents of Latin letters ("Pokémon" is "pokemon", "Gokū" is "goku")."""
    decomposed = unicodedata.normalize("NFKD", text)
    plain = "".join(char for char in decomposed if not _ACCENT.match(char))
    folded = unicodedata.normalize("NFKC", plain).casefold().replace("&", " and ")
    folded = re.sub(r"['\u2019`]", "", folded)  # apostrophes, straight or curly: "Heaven's"
    return " ".join(re.sub(r"[^\w]+", " ", folded).split())


_ACCENT = re.compile("[\u0300-\u036f]")  # the marks Latin letters carry


def name_fit(texts: Sequence[str], titles: Sequence[str], *, main_part: bool = True) -> float:
    """How alike the files' names (`texts`) and a show's (`titles`) are, the closest two. A name
    that is a title's main part, before its subtitle, is nearly the title: "Demon Slayer" is
    "Demon Slayer: Kimetsu no Yaiba" at least `_MAIN_PART` alike, more the closer the rest. Not
    for a film (`main_part` False): a series' films share its name before theirs, so a film
    named for its series alone is any of them."""
    best = 0.0
    for title in titles:
        main = normalize(title.split(":", 1)[0]) if main_part and ":" in title else ""
        for text in texts:
            alike = similarity(text, title)
            if len(main) > 3 and main == normalize(text):  # not "Re" of "Re:ZERO"
                alike = _MAIN_PART + (1 - _MAIN_PART) * alike
            best = max(best, alike)
    return best


_MAIN_PART = 0.75


def similarity(a: str, b: str) -> float:
    """How alike two names are, from 0 to 1. One name's words all inside the other's count too:
    "Bebop" is in "Cowboy Bebop", though less than the full name."""
    left, right = normalize(a), normalize(b)
    if not left or not right:
        return 0.0
    if left == right:
        return 1.0
    ratio = SequenceMatcher(None, left, right).ratio()
    words_left, words_right = set(left.split()), set(right.split())
    shorter, longer = sorted((words_left, words_right), key=len)
    contained = 0.9 * len(shorter) / len(longer) if shorter <= longer else 0.0
    return max(ratio, contained)


def _episodes(count: int) -> str:
    return f"{count} episode" if count == 1 else f"{count} episodes"
