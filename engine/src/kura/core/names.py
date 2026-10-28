"""Reading anime file names: the show, the season and episode, and what kind of file it is.

anitopy knows fansub and scene naming. Kura adds rules for what it gets wrong, and for
what only the folders know, such as the "Season 03" folder above a bare "05.mkv". Names in
Japanese mark their episodes and seasons their own way (第01話, 第2期, 劇場版), and full-width
letters and digits read as plain ones.
Names are hints: matching against the anime databases confirms them.
"""

import importlib
import re
import threading
from dataclasses import dataclass
from enum import StrEnum
from pathlib import PurePath

import anitopy


class Kind(StrEnum):
    EPISODE = "episode"
    SPECIAL = "special"  # OVA, OAD, ONA and season 0
    MOVIE = "movie"
    EXTRA = "extra"  # creditless openings and endings, previews, menus
    DVD = "dvd"  # raw DVD files (VTS_01_1.VOB): unknown until matched


@dataclass(frozen=True)
class ParsedName:
    kind: Kind
    title: str | None = None  # from the file name
    series: str | None = None  # a numbered film's series: "Dragon Ball Z" in "… - Movie 03 - …"
    folder_title: str | None = None  # from the show's folder
    season: int | None = None  # from the file name
    folder_season: int | None = None  # from a "Season 03" or "Specials" folder
    part: int | None = None  # "Season 3 Part 2": a part numbered from 1 again
    episode: int | None = None  # within its season, or absolute when there is none
    episode_end: int | None = None  # the last episode, when a file holds several
    episode_title: str | None = None
    year: int | None = None
    group: str | None = None
    height: int | None = None
    version: int | None = None
    is_copy: bool = False  # "(copy)", " - Copy", or Kura's own " (2)"

    @property
    def best_title(self) -> str | None:
        return self.title or self.folder_title


def parse_name(path: PurePath) -> ParsedName:
    folder_title, folder_year, folder_season, folder_kind = _folder_context(path)
    if _DVD_FILE.match(path.name):
        return ParsedName(Kind.DVD, folder_title=folder_title, folder_season=folder_season)

    stem, is_copy = _without_copy_marker(_plain(path.stem))
    stem = _DISC.sub("", stem)  # "Akira (1988) CD2" is Akira's second part, not an episode 2
    # A film in a folder of its own, named as it is ("Jujutsu Kaisen 0 (2021)"), the way films
    # are filed: the name is the film's, its number too.
    own_folder = bool(folder_title and folder_year) and stem == _plain(path.parent.name)
    stem, theatrical = _without_theatrical(stem)
    stem, recap = _japanese_markers(stem)
    found = _anitopy(stem + path.suffix)
    year = _number(_first(found, "anime_year")) or _bracket_year(stem) or folder_year

    if film := _numbered_film(found):
        series, name = film
        return ParsedName(
            kind=Kind.MOVIE,
            title=f"{series}: {name}",
            series=series,
            folder_title=folder_title,
            folder_season=folder_season,
            year=year,
            group=_first(found, "release_group"),
            height=_height(_first(found, "video_resolution")),
            version=_number(_first(found, "release_version")),
            is_copy=is_copy,
        )
    if own_folder:
        return ParsedName(
            Kind.MOVIE,
            title=folder_title,
            folder_title=folder_title,
            year=folder_year,
            group=_first(found, "release_group"),
            height=_height(_first(found, "video_resolution")),
            version=_number(_first(found, "release_version")),
            is_copy=is_copy,
        )

    if special := _named_special(found):
        series, number, name = special
        if number is None:  # "OVA - Kuro no Keiyakusha Gaiden - 03": the named OVA's third
            number = _number(_first(found, "episode_number"))
        return ParsedName(
            kind=Kind.EXTRA if _CREDITLESS.search(stem) else Kind.SPECIAL,
            title=series,
            folder_title=folder_title,
            folder_season=folder_season,
            episode=number,
            episode_title=name,
            year=year,
            group=_first(found, "release_group"),
            height=_height(_first(found, "video_resolution")),
            version=_number(_first(found, "release_version")),
            is_copy=is_copy,
        )

    types = {value.casefold() for value in _all(found, "anime_type")} | _type_at_end(found)
    if theatrical:
        types.add("movie")
    if recap:
        types.add("special")
    episodes = [_number(value) for value in _all(found, "episode_number")]
    numbers = [number for number in episodes if number is not None]
    title = _clean_title(_first(found, "anime_title"), drop=types | _release_words(found))
    if title and title.isdecimal() and not numbers:
        numbers, title = [int(title)], None  # "05.mkv": the name is the episode
    if numbers or _episode_words(found):
        title = _clean_title(title, drop=_EPISODE_WORDS)  # "Cowboy Bebop - Session 05"
    title = _spaced(title, stem)
    if not title and folder_kind and not types & (_SPECIAL_TYPES | _MOVIE_TYPES | _EXTRA_TYPES):
        # "05" in a folder of a show's OVAs is its fifth OVA. Which of its films it is, nothing
        # says: that waits for the owner.
        types.add(folder_kind.value)
        if folder_kind is Kind.MOVIE:
            folder_title = None
    if not title and not folder_title and (named := _LENTICULAR.search(stem)):
        title = named["title"].strip()  # anitopy took 【推しの子】, the show's name, for a group's

    season = _number(_first(found, "anime_season"))
    episode = numbers[0] if numbers else None
    episode_title, part = _title_and_part(stem, _first(found, "episode_title"))
    kind = _kind(types, season if season is not None else folder_season, episode)
    return ParsedName(
        kind=Kind.EXTRA if _CREDITLESS.search(stem) else kind,
        title=title,
        folder_title=folder_title,
        season=season,
        folder_season=folder_season,
        part=part,
        episode=episode,
        episode_end=numbers[-1] if len(numbers) > 1 else None,
        episode_title=_episode_title(episode_title),
        year=year,
        group=_first(found, "release_group"),
        height=_height(_first(found, "video_resolution")),
        version=_number(_first(found, "release_version")),
        is_copy=is_copy,
    )


def _anitopy(name: str) -> dict[str, str | list[str]]:
    """What anitopy reads in a name. It trips over a few names, such as a bare "Episode.mkv"
    (a keyword with nothing after it): those are read from their folders alone."""
    with _anitopy_lock:
        try:
            return anitopy.parse(name) or {}
        except AttributeError, IndexError, TypeError, ValueError:
            return {}


# anitopy keeps its working state in module globals, so only one thread may use it at a time.
_anitopy_lock = threading.Lock()

# anitopy 2.1.1's search for an episode's own title (Parser.search_for_episode_title) went round
# forever, holding the lock every other name waits on, on a name whose only words after its
# episode are a dash and one more mark ("Dragon Ball Z - 01 - .x"): ported from Anitomy, it takes
# "no token left" for "start again from the first". Kura puts in the same search, ending there as
# Anitomy's does. anitopy ships no types, hence the import by name. When anitopy moves past
# 2.1.1, the hang test in tests/core/test_names.py says whether its own search still needs this.
_anitopy_parser = importlib.import_module("anitopy.parser")


def _search_for_episode_title(_parser: object) -> None:
    tokens, flags = _anitopy_parser.Tokens, _anitopy_parser.TokenFlags
    helper = _anitopy_parser.parser_helper
    token_end = None
    while True:
        # The first unknown token outside brackets, after the last one tried.
        if token_end:
            token_begin = tokens.find_next(token_end, flags.NOT_ENCLOSED | flags.UNKNOWN)
        else:
            token_begin = tokens.find(flags.NOT_ENCLOSED | flags.UNKNOWN)
        if token_begin is None:
            return
        # On until a bracket or a word anitopy knows.
        token_end = tokens.find_next(token_begin, flags.BRACKET | flags.IDENTIFIER)
        if tokens.distance(token_begin, token_end) <= 2 and helper.is_dash_character(
            token_begin.content
        ):
            if token_end is None:
                return  # a dash and nothing after it: no title (anitopy's own went round again)
            continue  # only a dash
        if token_end and token_end.category == _anitopy_parser.TokenCategory.BRACKET:
            token_end = tokens.find_previous(token_end, flags.VALID)
        helper.build_element(
            _anitopy_parser.ElementCategory.EPISODE_TITLE,
            token_begin,
            token_end,
            keep_delimiters=False,
        )
        return


_anitopy_parser.Parser.search_for_episode_title = _search_for_episode_title

_DVD_FILE = re.compile(r"^(?:VTS_\d{2}_\d|VIDEO_TS)\.(?:VOB|IFO|BUP)$", re.IGNORECASE)
_COPY_MARKER = re.compile(
    r"\s*(?:\(copy\)|-\s*copy(?:\s*\(\d+\))?|\((?:[2-9]|[1-9]\d)\))\s*$", re.IGNORECASE
)
_SEASON_FOLDER = re.compile(r"^(?:season|series|s)[\s._-]*0*(\d{1,3})$", re.IGNORECASE)
_SPECIALS_FOLDER = re.compile(r"^specials?$", re.IGNORECASE)
# A season's folder named after its show: "[Group] My Hero Academia Season 02", "Boku no Hero
# Academia 2nd Season", "Kimetsu no Yaiba S2".
_TITLED_SEASON = re.compile(
    r"^(?P<title>.+?)[\s._-]+(?:(?:season|series)[\s._-]*0*(?P<season>\d{1,2})"
    r"|(?P<nth>\d{1,2})(?:st|nd|rd|th)[\s._-]+season|s0*(?P<s>\d{1,2}))$",
    re.IGNORECASE,
)
# A folder of a show's films, specials or OVAs: "My Hero Academia Movies", "3. TV Specials", "OVA".
_KIND_FOLDER = re.compile(
    r"^(?:(?P<title>.+?)[\s._-]+)?(?P<kind>movies|films|specials|ovas?|oads?)$", re.IGNORECASE
)
# A show and more than its films or OVAs: "Toradora! + OVA", "Clannad and Specials".
_AND_MORE = re.compile(r"(?:[+&,]|\b(?:and|with|plus|incl|including))\.?$", re.IGNORECASE)
# A season in a folder's brackets: "Attack on Titan (Season 2)", "[S2]", "(2nd Season)".
_SEASON_TAG = re.compile(
    r"^(?:(?:season|series|s)[\s._-]*0*(?P<season>\d{1,2})|(?P<nth>\d{1,2})(?:st|nd|rd|th)\s+season)$",
    re.IGNORECASE,
)
# A release's tags around a folder's name: "[Anime Time] Show (Other Name) (S01-S07) [BD] [1080p]".
# A tag at the end goes when it holds a release's words or a number, never a name's own brackets
# ("Fate stay night [Unlimited Blade Works]").
_LEADING_TAGS = re.compile(r"^(?:\s*\[[^\]]*\])+\s*")
_TRAILING_TAG = re.compile(r"\s*[\[(](?P<inside>[^\[\]()]*)[\])]\s*$")
_RELEASE_TAG = re.compile(
    r"\d|\b(?:bd|blu-?ray|web|dvd|dual|multi|audio|aac|flac|eng|english|subs?|subbed|dub|dubbed"
    r"|raw|batch|complete|uncensored|uncut|remux|hevc|avc|tv)\b",
    re.IGNORECASE,
)
_SEASON_RANGE = re.compile(  # a folder of a show's seasons: "Attack on Titan S01-S04"
    r"[\s._-]+(?:s|seasons?[\s._-]*)\d{1,2}\s*-\s*(?:s|seasons?[\s._-]*)?\d{1,2}$", re.IGNORECASE
)
_YEAR = re.compile(r"(?:19|20)\d{2}")
_LIST_NUMBER = re.compile(r"^\d{1,2}[a-z]?\.\s+", re.IGNORECASE)  # "2a. Movies": a list's order
_ARTICLES = frozenset({"the", "a", "an"})
_FILM_PART = re.compile(r"(?:^|[\s._-])(?:cd|dis[ck]|dvd|part|pt)[\s._-]?(\d{1,2})$", re.IGNORECASE)
_DISC = re.compile(r"[\s._-]*\b(?:cd|dis[ck]|dvd)[\s._-]?\d{1,2}$", re.IGNORECASE)
# "S3 Part 2", "Season 3 Part 2": anitopy drops the part, which numbers its episodes from 1 again.
_PART = re.compile(r"\b(?:s\d{1,2}|season\s*\d{1,2})\s*[-:]?\s*part\s*(\d)\b", re.IGNORECASE)
_PART_ALONE = re.compile(r"part\s*(\d)", re.IGNORECASE)
# An episode code: "S01E05", "1x05".
_EPISODE_CODE = re.compile(r"\bs\d{1,2}e\d{1,4}\b|\b\d{1,2}x\d{2,4}\b", re.IGNORECASE)
_CODEC_WORDS = re.compile(r"\b(?:x26[45]|h\.?26[45]|hevc|avc|xvid|divx)\b", re.IGNORECASE)
_EPISODE_WORDS = frozenset({"session", "episode", "ep", "eps"})

_EXTRA_TYPES = frozenset(
    {"ncop", "nced", "op", "ed", "opening", "ending", "pv", "preview", "menu", "cm", "trailer"}
)
# A creditless opening or ending, wherever its name says so: "[SP02] NCED - 01", "NC OP 2".
_CREDITLESS = re.compile(
    r"\bnc[\s._-]?(?:op|ed)\d*\b|\bcreditless\b|\bnon[\s-]?credit(?:ed)?\b", re.IGNORECASE
)
# A public service announcement ("Dragon Ball - PSA 01") is a special too.
_SPECIAL_TYPES = frozenset({"ova", "oad", "ona", "sp", "special", "specials", "psa"})
_MOVIE_TYPES = frozenset({"movie", "gekijouban", "film"})
# A whole series' release numbers its films: "Dragon Ball Z - Movie 03 - The Tree of Might".
# anitopy reads no number after "Movie", so that's all title to it; with a letter ("Movie 14b")
# it takes the number for an episode's, the title ending at the word, and the film's name for the
# episode's title.
_NUMBERED_FILM = re.compile(
    r"^(?P<series>.+?)\s+(?:-\s+)?(?:the\s+)?(?:movie|film|gekijouban)\s*\d{0,3}[a-z]?\s*[-:]\s+"
    r"(?P<name>.+)$",
    re.IGNORECASE,
)
# A show's OVA or special named after it: "My Hero Academia OVA - Training of the Dead!",
# "... OVA 2 - All Might Rising" (anitopy leaves it all for the title).
_NAMED_SPECIAL = re.compile(
    r"^(?P<series>.+?)\s+(?:-\s+)?(?:ova|oad|ona|sp|special)\s*(?P<number>\d{1,3})?\s*[-:]\s+"
    r"(?P<name>.+)$",
    re.IGNORECASE,
)
# "Gekijouban", 劇場版, starting a name: a theatrical version, a film, its series' name often in
# corner brackets after it (劇場版「鬼滅の刃」無限列車編).
_THEATRICAL = re.compile(
    r"^(?P<tags>(?:\s*\[[^\]]*\])*)\s*(?:gekij[oō]u?[\s-]?ban\b|劇場版)\s*[:-]?\s*"
    r"(?:「(?P<series>[^」]+)」)?",
    re.IGNORECASE,
)
# Japanese marks: 第01話 or 第1回 the episode (第01集 or 第01话 from Chinese subtitle groups), 第2期
# or シーズン2 the season, 総集編 a recap.
_JAPANESE_EPISODE = re.compile(
    r"\s*第\s*(?P<number>\d{1,4}|[〇一二三四五六七八九十百]{1,5})\s*[話回集话]\s*"
)
_JAPANESE_SEASON = re.compile(
    r"\s*(?:第\s*(?P<number>\d{1,2}|[一二三四五六七八九十]{1,3})\s*期|シーズン\s*(?P<plain>\d{1,2}))\s*"
)
_JAPANESE_SPECIAL = re.compile(r"総集編|特別編|特別篇|番外編")
_NO_SHOW = re.compile(r"(?:[\[【][^\]】]*[\]】]\s*)*(?:S\d{1,2})?")  # what may come before 第01話
# A show's name in lenticular brackets, as Japanese names write some: 【推しの子】.
_LENTICULAR = re.compile(r"【(?P<title>[^【】]+)】")
_KANJI_DIGITS = {
    "\u3007": 0,  # the ideographic zero, as its code: it looks like a letter O
    "一": 1,
    "二": 2,
    "三": 3,
    "四": 4,
    "五": 5,
    "六": 6,
    "七": 7,
    "八": 8,
    "九": 9,
}
# Scene words where an episode title would be: "Spy.x.Family.S01E01.1080p.WEB.h264".
_SCENE_WORDS = frozenset(
    {"web", "webrip", "web-dl", "webdl", "bluray", "bdrip", "brrip", "hdtv", "dvdrip", "remux"}
)
_FILM_AT_END = re.compile(r"^(?P<series>.+?)\s+-\s+(?:movie|film|gekijouban)$", re.IGNORECASE)
_TYPE_AT_END = re.compile(r"\s+-\s+(?P<word>[a-z]+)$", re.IGNORECASE)
_AKA = re.compile(r"\s+aka\s+", re.IGNORECASE)
# A year opening brackets with more in them, "(1990 BluRay - 1080p)", which anitopy passes over;
# not a span of years ("1989-2019") or a checksum ("[2016ABCD]").
_BRACKET_YEAR = re.compile(r"[(\[]\s*((?:19|20)\d{2})\b(?!-\d)[^)\]]*[)\]]")

# Folders that say where files are kept, not which show they are.
_GENERAL_FOLDERS = frozenset(
    {
        "anime",
        "animes",
        "tv",
        "tv shows",
        "shows",
        "series",
        "movies",
        "films",
        "downloads",
        "download",
        "completed",
        "complete",
        "torrents",
        "incoming",
        "unsorted",
        "videos",
        "video",
        "media",
        "library",
        "new folder",
        "extras",
        "extra",
        "bonus",
        "featurettes",
        "misc",
        "other",
        "others",
        "temp",
        "tmp",
        "ova",
        "ovas",
        "oad",
        "oads",
        "omake",
    }
)


def _folder_context(path: PurePath) -> tuple[str | None, int | None, int | None, Kind | None]:
    """The show folder's title and year, the season folder's number, and what a folder of a
    show's films or specials says its files are. A season's folder named after its show ("My
    Hero Academia Season 02") names it, over a release's folder above. A folder of films or
    specials ("My Hero Academia Movies", "OVA") is passed over for the one above, as a season's
    is, its own first words the show only when that one names none: they needn't be a show's
    ("Anime Movies"). A release counts its films and OVAs its own way, so it's no season 0."""
    folder = path.parent
    name = _plain(folder.name)
    own: str | None = None  # the show a season's or a kind's folder names
    own_year: int | None = None
    kind: Kind | None = None
    cleaned, _, tagged = _folder_name(name)
    season = season_of_folder(cleaned) if cleaned else tagged  # "Season 02 [1080p]", "(Season 2)"
    if season is None and (titled := _titled_season(name)) is not None:
        own, own_year, season = titled
    elif season is None and (holds := _kind_folder(name)) is not None:
        own, own_year, kind = holds
    if season is not None or kind is not None:
        folder = folder.parent
    title, year, _ = _folder_name(_plain(folder.name))  # empty at the top of a drive
    if title is None or title.casefold() in _GENERAL_FOLDERS or season_of_folder(title) is not None:
        title, year = None, None
    if own is not None and not _a_name(own):
        own = None  # "TV Season 2", "The OVA": no show's name
    if kind is not None and title is not None:
        return title, year, season, kind  # the folder above names the show
    if own is not None:
        return own, own_year or year, season, kind
    return title, year, season, kind


def _titled_season(name: str) -> tuple[str, int | None, int] | None:
    """A season's folder named after its show, as the show, its year and the season: "[Group] My
    Hero Academia Season 02" and "Attack on Titan (Season 2)" are seasons 2. None for any other
    folder."""
    title, year, tagged = _folder_name(name)
    if title is None:
        return None
    if tagged is not None:
        return title, year, tagged
    if not (match := _TITLED_SEASON.match(title)):
        return None
    show, show_year, _ = _folder_name(match["title"])  # "Show (2019) Season 2"
    if show is None:
        return None
    return show, show_year or year, int(match["season"] or match["nth"] or match["s"])


def _kind_folder(name: str) -> tuple[str | None, int | None, Kind] | None:
    """A folder of a show's films or specials: the show its name gives, if it gives one, its
    year, and what its files are. "My Hero Academia Movies" holds films, "OVA" specials, and so
    does a release's "2a. Movies". A bare "Movies" is a library's, any film's, and "Toradora! +
    OVA" holds the show as well: neither is one of these."""
    title, year, _ = _folder_name(name)
    numbered = _LIST_NUMBER.match(title or "")
    if numbered and title:
        title = title[numbered.end() :]  # "3. TV Specials": the release's order
    if title is None or not (match := _KIND_FOLDER.match(title)):
        return None
    films = match["kind"].casefold() in ("movies", "films")
    if films and not match["title"] and not numbered:
        return None
    show = (match["title"] or "").strip(" ._-")
    if _AND_MORE.search(show):
        return None
    show_name, show_year, _ = _folder_name(show) if show else (None, None, None)
    return show_name, show_year or year, Kind.MOVIE if films else Kind.SPECIAL


def _a_name(words: str) -> bool:
    """Whether a folder's words can be a show's name: not a library's ("TV") nor an article."""
    return words.casefold() not in _GENERAL_FOLDERS | _ARTICLES


def _folder_name(name: str) -> tuple[str | None, int | None, int | None]:
    """A folder's name without a release's tags around it ("[Anime Time] Boku No Hero Academia
    (My Hero Academia) (S01-S07+Movies+OVAs) [BD]" is "Boku No Hero Academia (My Hero
    Academia)"), and the year and the season its tags give: "Dragon Ball Z (1989)" is Dragon Ball
    Z of 1989, "Attack on Titan (Season 2)" its season 2. A name all in brackets is the name
    ("[Oshi no Ko]")."""
    cleaned, year, season = name, None, None
    while (tag := _TRAILING_TAG.search(cleaned)) and _RELEASE_TAG.search(tag["inside"]):
        inside = tag["inside"].strip()
        if year is None and _YEAR.fullmatch(inside):
            year = int(inside)
        if season is None and (found := _SEASON_TAG.match(inside)):
            season = int(found["season"] or found["nth"])
        cleaned = cleaned[: tag.start()]
    cleaned = _SEASON_RANGE.sub("", cleaned)
    cleaned = _bare(_LEADING_TAGS.sub("", cleaned)) or _bare(re.sub(r"[\[\]()]", " ", cleaned))
    return (cleaned or None), year, season


def _bare(name: str) -> str:
    """A name without the spaces and separators a tag taken off left at its ends ("Show - "), its
    own marks kept: "Re ZERO -Starting Life in Another World-". Underscores in a name without
    spaces are its spaces ("_Cowboy_Bebop_")."""
    if " " not in name:
        name = name.replace("_", " ")
    return re.sub(r"^[\s._-]*\s|\s[\s._-]*$", "", " ".join(name.split()))


# Full-width letters, digits and marks (U+FF01 to U+FF5E), as Japanese names have them, and the
# ideographic space: the plain ones they stand for.
_FULL_WIDTH = {code: code - 0xFEE0 for code in range(0xFF01, 0xFF5F)} | {0x3000: 0x20}


def _plain(text: str) -> str:
    """Full-width letters, digits and marks as plain ones: a full-width colon is a colon,
    full-width digits are digits. Nothing else changes: "Ranma ½" stays as AniList writes it."""
    return text.translate(_FULL_WIDTH)


def _without_theatrical(stem: str) -> tuple[str, bool]:
    """The name without "Gekijouban" or 劇場版 at its start (a theatrical version), and whether it
    had it: "劇場版「鬼滅の刃」無限列車編" is "鬼滅の刃 無限列車編". A series' numbered films keep
    the word, which says what their number counts ("Dragon Ball Z - Gekijouban 03 - ...")."""
    found = _THEATRICAL.match(stem)
    if found is None:
        return stem, False
    series = found["series"] or ""
    return " ".join(f"{found['tags']} {series} {stem[found.end() :]}".split()), True


def _japanese_markers(stem: str) -> tuple[str, bool]:
    """A name's Japanese marks written as anitopy reads them: "鬼滅の刃 第2期 第05話 タイトル" is
    "鬼滅の刃 S2 - 05 - タイトル". A name that starts with them ("第01話 タイトル") names no show,
    its folder does, and what follows is the episode's own title, left out. True when it says
    it's a recap or a special (総集編, 特別編)."""
    special = bool(_JAPANESE_SPECIAL.search(stem))
    stem = _JAPANESE_SPECIAL.sub(" ", stem)
    stem = _JAPANESE_SEASON.sub(
        lambda found: f" S{_japanese_number(found['number'] or found['plain'])} ", stem
    )
    if found := _JAPANESE_EPISODE.search(stem):
        before, after = stem[: found.start()].strip(), stem[found.end() :]
        if _NO_SHOW.fullmatch(before):
            after = ""
        stem = f"{before} - {_japanese_number(found['number']):02d} - {after}"
    return " ".join(stem.split()).strip(" -"), special


def _japanese_number(text: str) -> int:
    """A number in digits or in kanji: "05" is 5, "二十三" is 23, "百" is 100."""
    if text.isdecimal():
        return int(text)
    total = current = 0
    for char in text:
        if char == "十":
            total, current = total + (current or 1) * 10, 0
        elif char == "百":
            total, current = total + (current or 1) * 100, 0
        else:
            current = current * 10 + _KANJI_DIGITS[char]
    return total + current


def _numbered_film(found: dict[str, str | list[str]]) -> tuple[str, str] | None:
    """A film a release numbers among its series' films, as its series and its own name:
    "Dragon Ball Z - Movie 03 - The Tree of Might" is ("Dragon Ball Z", "The Tree of Might").
    The number counts the release's films, not AniList's, so it's left out."""
    title = _first(found, "anime_title")
    if title is None:
        return None
    if match := _NUMBERED_FILM.match(title):
        series, name = match["series"], match["name"]
    elif (match := _FILM_AT_END.match(title)) and _all(found, "episode_number"):
        series, name = match["series"], _first(found, "episode_title") or ""
    else:
        return None
    # What a release adds after the name: "Resurrection 'F' aka Frieza", "Battle of Gods, UNCut"
    # (anitopy takes "UNCut" off, but not the comma).
    name = _AKA.split(name, maxsplit=1)[0].strip(" ,-:")
    series = series.strip(" ,-:")
    if not name or series.casefold() in _ARTICLES:  # "The Movie - Name" names no series
        return None
    return series, name


def _named_special(found: dict[str, str | list[str]]) -> tuple[str, int | None, str] | None:
    """An OVA or special named after its show, as its show, its number if it has one, and its own
    name: "My Hero Academia OVA - Training of the Dead!" is ("My Hero Academia", None,
    "Training of the Dead!")."""
    title = _first(found, "anime_title")
    if title is None or not (match := _NAMED_SPECIAL.match(title)):
        return None
    number = match["number"]
    return match["series"].strip(" -:"), int(number) if number else None, match["name"].strip()


def _spaced(title: str | None, stem: str) -> str | None:
    """A scene name's title with its dots as spaces: anitopy can leave one between short words
    ("Spy.x Family")."""
    if title is None or " " in stem or "." not in title:
        return title
    return re.sub(r"(?<=\w)\.(?=\w)", " ", title)


def _type_at_end(found: dict[str, str | list[str]]) -> set[str]:
    """A kind of file named at the end of the title, "Dragon Ball - PSA", which anitopy doesn't
    know for one."""
    title = _first(found, "anime_title") or ""
    if (match := _TYPE_AT_END.search(title)) and (word := match["word"].casefold()) in (
        _SPECIAL_TYPES | _MOVIE_TYPES
    ):
        return {word}
    return set()


def _bracket_year(stem: str) -> int | None:
    found = _BRACKET_YEAR.search(stem)
    return int(found[1]) if found else None


def _title_and_part(stem: str, episode_title: str | None) -> tuple[str | None, int | None]:
    """The episode title and the part number. anitopy takes "S3 Part 2 - 03" to have the episode
    title "Part 2"; a real title with "part" in it ("Part of It") is no part, and nor is "Part 2"
    after an episode code ("S01E05 - Part 2"), which says where the file goes."""
    before = stem[: stem.find(episode_title)] if episode_title and episode_title in stem else stem
    alone = episode_title and _PART_ALONE.fullmatch(episode_title.strip())
    if alone and not _EPISODE_CODE.search(before):
        return None, int(alone[1])
    found = _PART.search(before)
    return episode_title, int(found[1]) if found else None


def film_part(stem: str) -> int | None:
    """Which part of a film in several files this is, from the end of its name: "CD1", "cd2",
    "pt1", "Part 2", "disc 2". None for a film in one file."""
    if found := _FILM_PART.search(_without_copy_marker(stem)[0]):
        return int(found[1])
    return None


def season_of_folder(folder: str) -> int | None:
    """The season a folder's name gives: "Season 02", "S02" or "Season_02" is 2, "Specials" is
    0. None for any other folder."""
    if _SPECIALS_FOLDER.match(folder):
        return 0
    if match := _SEASON_FOLDER.match(folder):
        return int(match[1])
    return None


def _without_copy_marker(stem: str) -> tuple[str, bool]:
    cleaned = _COPY_MARKER.sub("", stem)
    return cleaned, cleaned != stem


def _clean_title(title: str | None, drop: set[str] | frozenset[str]) -> str | None:
    """Removes trailing words that describe the file rather than name the show."""
    if title is None:
        return None
    words = title.split()
    dropped = False
    while words and words[-1].strip(" -:").casefold() in drop:
        words.pop()
        dropped = True
    if dropped and words and words[-1].casefold() == "the":
        words.pop()  # "Cowboy Bebop - The Movie": the article goes with the word it named
    cleaned = " ".join(words).strip(" -:")
    return cleaned or None


def _release_words(found: dict[str, str | list[str]]) -> set[str]:
    """The words anitopy reads as the release's ("Batch", "Final"), which don't name the show.
    Not "End": anitopy reads it so wherever it is, and titles end with it ("Seraph of the End")."""
    return {value.casefold() for value in _all(found, "release_information")} - {"end"}


def _episode_words(found: dict[str, str | list[str]]) -> bool:
    return any(value.casefold() in _EPISODE_WORDS for value in _all(found, "episode_prefix"))


def _kind(types: set[str], season: int | None, episode: int | None) -> Kind:
    if types & _EXTRA_TYPES:
        return Kind.EXTRA
    if types & _SPECIAL_TYPES or season == 0:
        return Kind.SPECIAL
    if types & _MOVIE_TYPES or episode is None:
        return Kind.MOVIE
    return Kind.EPISODE


def _episode_title(title: str | None) -> str | None:
    if title is None or _CODEC_WORDS.search(title) or title.casefold() in _SCENE_WORDS:
        return None  # scene names leave codec, source and group tags where the title would be
    return title


def _height(resolution: str | None) -> int | None:
    if resolution is None:
        return None
    if resolution.casefold() == "4k":
        return 2160
    if match := re.search(r"\d{3,4}x(\d{3,4})", resolution) or re.search(
        r"(\d{3,4})[pi]?$", resolution
    ):
        return int(match[1])
    return None


def _number(value: str | None) -> int | None:
    return int(value) if value is not None and value.isdecimal() else None


def _all(found: dict[str, str | list[str]], key: str) -> list[str]:
    value = found.get(key)
    if value is None:
        return []
    return [value] if isinstance(value, str) else value


def _first(found: dict[str, str | list[str]], key: str) -> str | None:
    values = _all(found, key)
    return values[0].strip() if values else None
