"""Identifying the library: which anime, and which episode, every video is.

The scan's third stage. Files are grouped and looked up on AniList; with the owner's TMDB key the
same show or film is found on TMDB, whose episode lists say where each file sits and what's
missing. What AniList's search can't find by a file's name, TMDB's is asked for too, and AniList
for the names TMDB gives what it finds; what AniList doesn't list at all is TMDB's alone, a title
with no AniList entry. A series' special its show's list doesn't name the way
the file does is looked up by its own name, as an OVA or special of its own. kura/core/identify.py
and kura/core/placing.py decide, this module asks the services and keeps the answers. A file Kura
isn't sure about waits for the owner, and files the owner placed by hand (pinned) are never
identified again.
"""

import json
import logging
import sqlite3
from collections import defaultdict
from collections.abc import Callable, Collection, Iterable, Sequence
from dataclasses import dataclass, replace
from datetime import date, datetime, timedelta
from pathlib import PurePath, PureWindowsPath
from typing import Literal

from kura import credentials
from kura.anilist import AniList
from kura.cache import Cache
from kura.config import DataPaths
from kura.core.catalog import Anime, Film, Hit, Show, TitleKind, TmdbRef, tmdb_only
from kura.core.identify import (
    SURE,
    FileFacts,
    Group,
    Guess,
    base_title,
    group_files,
    guesses,
    merged,
    names,
    respelled,
    searches,
    through_tmdb,
    tmdb_alone,
    tmdb_fit,
)
from kura.core.identify import pick_hit as pick_tmdb
from kura.core.names import Kind, ParsedName, parse_name
from kura.core.placing import (
    How,
    Placement,
    lists_special,
    named_special,
    numbered_through,
    place,
)
from kura.titles import show_of
from kura.tmdb import Tmdb
from kura.web import Send, WebError

log = logging.getLogger(__name__)

AIRING_EVERY = timedelta(hours=1)  # how often a show still airing has its episode list refreshed
FINISHED_EVERY = timedelta(days=7)  # and a finished one
_SHOWN_GUESSES = 3  # how many guesses the review screen offers
_PART_OF = ("PARENT", "SIDE_STORY")  # how AniList ties an OVA or special to its show
_TMDB_TRIES = 3  # how many of the ways a name reads TMDB is asked for
_TMDB_HITS = 3  # of what TMDB finds for each, the best this many are looked at
_TMDB_FIT = 40  # what fits the files less well than this isn't asked of AniList


@dataclass(frozen=True)
class Identified:
    sure: int  # files placed without asking
    unsure: int  # files waiting for the owner
    note: str | None  # what couldn't be done this time, in words


class UnplacedError(ValueError):
    """The owner's choice for a file Kura can't place as an episode: it needs the number."""


@dataclass(frozen=True)
class Placed:
    """What the owner's choice did."""

    placed: int  # files placed as chosen
    waiting: int  # files that didn't fit it, waiting for the owner now


@dataclass(frozen=True)
class _Home:
    """Where an entry's files go: a title, with its TMDB show when it has one."""

    title_id: int
    show: Show | None = None
    film: bool = False  # the title is a film: a file is the whole of it
    specials: bool = False  # the show's specials hold the entry: an OVA or special, in season 0


class Identifier:
    def __init__(
        self,
        paths: DataPaths,
        transport: Send,
        *,
        now: Callable[[], datetime],
        anilist: AniList | None = None,
    ) -> None:
        """`anilist` is the engine's one AniList client, whose limit every lookup shares."""
        self._paths = paths
        self._transport = transport
        self._now = now
        cache = Cache(paths.cache)
        self._anilist = anilist or AniList(transport, cache=cache)
        self._cache = cache

    def run(
        self,
        conn: sqlite3.Connection,
        *,
        stop: Callable[[], bool] = lambda: False,
        looking_at: Callable[[str], None] = lambda _: None,
    ) -> Identified | None:
        """Identifies every file still to identify. None when `stop` asked to stop."""
        try:
            self._choose_again(conn)
        except WebError as error:
            log.warning("The owner's choices couldn't be placed again: %s", error)
            return Identified(0, 0, _waiting("AniList or TMDB", error))
        try:
            self._link_unlinked(conn)
        except WebError as error:  # the franchises form at the next scan
            log.warning("AniList couldn't say how entries relate: %s", error)
        files, others = _to_identify(conn)
        stamp = self._now().isoformat()
        _mark_unlookable(conn, others, stamp)
        tmdb = self._tmdb()

        found: list[tuple[Group, list[Guess]]] = []
        for group in group_files(files):
            if stop():
                return None
            looking_at(group.query)
            try:
                found.append((group, self._look_up(group, tmdb)))
            except WebError as error:
                log.warning("AniList couldn't be asked about %s: %s", group.query, error)
                return Identified(0, 0, _waiting("AniList", error))

        sure = unsure = 0
        note: str | None = None
        # Series first, so the specials and OVAs after them find their show already there.
        found.sort(key=lambda item: _series_last(item[1]))
        for group, ranked in found:
            if stop():
                return None
            looking_at(group.query)
            try:
                placed, waiting = self._settle(conn, group, ranked, tmdb)
            except WebError as error:
                log.warning("TMDB couldn't be asked about %s: %s", group.query, error)
                note = _waiting("TMDB", error)
                break
            sure, unsure = sure + placed, unsure + waiting
        return Identified(sure, unsure, note)

    def _look_up(
        self, group: Group, tmdb: Tmdb | None = None, *, series: bool = True
    ) -> list[Guess]:
        """AniList's entries for a group, as guesses. While none is sure, shorter forms of a
        numbered film's name are asked for too (core/identify.py's `searches`; its series alone
        unless `series` is False). When nothing at all is found, the name may be one AniList
        writes otherwise ("Dragonball GT"): what its first word finds says how ("Dragon Ball"),
        and the name is asked for that way. While nothing is sure still, TMDB is asked too
        (`_through_tmdb`)."""
        entries: dict[int, Anime] = {}
        ranked: list[Guess] = []
        for text in searches(group, series=series):
            for entry in self._anilist.search(text):
                entries.setdefault(entry.id, entry)
            ranked = guesses(group, list(entries.values()))
            if ranked and ranked[0].confidence >= SURE:
                return ranked
        first, *rest = group.query.split()
        if not ranked and rest and (again := respelled(group.query, self._anilist.search(first))):
            ranked = guesses(group, self._anilist.search(again))
        if tmdb is not None and not (ranked and ranked[0].confidence >= SURE):
            ranked = merged(ranked, self._through_tmdb(group, tmdb))
        return ranked

    def _through_tmdb(self, group: Group, tmdb: Tmdb) -> list[Guess]:
        """Guesses from what TMDB finds by a group's name, which AniList's search didn't: TMDB
        knows names in more languages and spellings. Each show or film that fits the files well
        enough (by its own names, or else by the other names TMDB knows it by) is asked of AniList
        by TMDB's names for it, and AniList's entries are guesses no surer than that fit; when
        none of them is that show or film or goes by its name, AniList doesn't list it, and an
        animated one is a guess of TMDB's own (core/identify.py's `tmdb_alone`). TMDB being away,
        or refusing the key, leaves the guesses AniList gave."""
        media: tuple[Literal["tv", "movie"], ...] = ("movie",) if group.movie else ("tv",)
        if all(facts.parsed.kind is Kind.SPECIAL for facts in group.files):
            media = ("tv", "movie")  # TMDB has a special as its show's, or as a film
        found: list[Guess] = []
        for text in names(group)[:_TMDB_TRIES]:
            for kind in media:
                try:
                    hits = tmdb.search(kind, text)[:_TMDB_HITS]
                except WebError as error:
                    log.warning("TMDB couldn't be asked about %s: %s", text, error)
                    return found
                for rank, hit in enumerate(hits):
                    fit = tmdb_fit(group, hit, rank)
                    others: list[str] = []
                    if fit < SURE and rank == 0:  # the name may be one of its others
                        try:
                            others = tmdb.alternative_titles(hit.media, hit.id)
                        except WebError as error:
                            log.warning("TMDB couldn't say %s's other names: %s", hit.title, error)
                        else:
                            fit = tmdb_fit(group, hit, rank, others)
                    if fit < _TMDB_FIT:
                        continue
                    entries: dict[int, Anime] = {}
                    for name in dict.fromkeys((hit.title, hit.original_title)):
                        for entry in self._anilist.search(name):
                            entries.setdefault(entry.id, entry)
                    listed = list(entries.values())
                    found = merged(found, through_tmdb(group, hit, fit, listed))
                    found = merged(found, tmdb_alone(group, hit, fit, listed, others))
                    if found and found[0].confidence >= SURE:
                        return found
        return found

    def choose(
        self,
        conn: sqlite3.Connection,
        file_id: int,
        chosen: int | TmdbRef,
        as_kind: Kind,
        *,
        also: Sequence[int] = (),
        episode: int | None = None,
    ) -> int:
        """The owner's choice: this file, and the others that are the same anime (`also`), are
        this AniList entry (`chosen`, its number) or this show or film only TMDB knows (TMDB's
        kind and number), as episodes, a film, or specials. `episode` is the file's number when
        its name has none Kura can use. It's pinned, so no rescan undoes it. Returns how many
        files it placed; one of `also` that Kura can't place keeps waiting. A special Kura can't
        number still belongs to its show (an extra, say).

        Raises UnplacedError when the file is an episode Kura can't place, LookupError when AniList
        or TMDB has no such entry (or TMDB has no key), and WebError when a service can't be asked
        right now.
        """
        ids = [file_id, *(other for other in also if other != file_id)]
        return self._place(conn, file_id, chosen, dict.fromkeys(ids, as_kind), episode).placed

    def rematch(
        self,
        conn: sqlite3.Connection,
        title_id: int,
        file_id: int,
        chosen: int | TmdbRef,
        as_kind: Kind,
        *,
        episode: int | None = None,
    ) -> Placed:
        """The owner's new match for a whole title, chosen for one of its files (`file_id`, its
        first episode as kura/review.py shows it): every file of the title is this AniList entry
        (or TMDB's show or film, as `choose` takes it).
        The files of that file's kind become `as_kind`; the others keep theirs, so a series'
        specials stay specials. A file that doesn't fit the entry waits for the owner.

        Raises LookupError when the file isn't the title's, and otherwise as `choose` does.
        """
        rows = conn.execute(
            """SELECT f.id, f.season, t.kind FROM files AS f
               JOIN titles AS t ON t.id = f.title_id
               WHERE f.title_id = ? AND f.gone_at IS NULL""",
            (title_id,),
        ).fetchall()
        now = {row["id"]: _kind_of(row) for row in rows}
        if file_id not in now:
            raise LookupError("That file isn't one of the title's.")
        shown = now[file_id]
        kept = {other for other, kind in now.items() if kind is not shown}
        kinds = {file_id: as_kind} | {
            other: kind if other in kept else as_kind for other, kind in now.items()
        }
        return self._place(conn, file_id, chosen, kinds, episode, kept=kept)

    def _place(
        self,
        conn: sqlite3.Connection,
        file_id: int,
        chosen: int | TmdbRef,
        kinds: dict[int, Kind],
        episode: int | None,
        *,
        kept: Collection[int] = (),
    ) -> Placed:
        """Places the files (`kinds`, the owner's file first) in the entry chosen, pinned. An
        episode Kura can't place keeps waiting, or waits now; so does a file that keeps its own
        kind (`kept`, in a whole title's change) and doesn't fit."""
        entry, home = self._chosen(conn, chosen)
        film = home.film or entry.kind is TitleKind.MOVIE or kinds[file_id] is Kind.MOVIE
        files = _facts(conn, list(kinds))
        through: set[int] = set() if film else _numbered_through(conn, files, home)
        placing: list[tuple[FileFacts, Placement | None, Kind]] = []
        unfit: list[int] = []
        for facts in files:
            as_kind = kinds[facts.id]
            parsed = replace(facts.parsed, kind=as_kind)
            if facts.id == file_id and episode is not None:
                parsed = replace(parsed, episode=episode, episode_end=None)
                if as_kind is Kind.SPECIAL:
                    parsed = replace(parsed, season=0)
            elif facts.id in through:
                parsed = replace(parsed, folder_season=None)  # its number places it
            where = None if film else _placement(parsed, entry, home)
            if where is None and not film and (as_kind is Kind.EPISODE or facts.id in kept):
                if facts.id == file_id:
                    raise UnplacedError(_which_episode(entry, parsed.episode))
                unfit.append(facts.id)
                continue
            placing.append((facts, where, as_kind))
        stamp = self._now().isoformat()
        with conn:
            for facts, where, as_kind in placing:
                conn.execute(
                    """UPDATE files SET title_id = ?, anilist_id = ?, season = ?, episode = ?,
                              episode_end = ?, matched = 'sure', confidence = 100,
                              pinned = 1, identified_at = ?
                       WHERE id = ?""",
                    (
                        home.title_id,
                        entry.anilist_id,
                        where.season if where else (0 if as_kind is Kind.SPECIAL else None),
                        where.episode if where else None,
                        where.last if where else None,
                        stamp,
                        facts.id,
                    ),
                )
            for unplaced in unfit:  # one placed before (in a title changed whole) waits now
                conn.execute(
                    """UPDATE files SET title_id = NULL, season = NULL, episode = NULL,
                              episode_end = NULL, matched = 'unsure', pinned = 0,
                              identified_at = ?
                       WHERE id = ? AND matched = 'sure'""",
                    (stamp, unplaced),
                )
        return Placed(len(placing), len(unfit))

    def _chosen(self, conn: sqlite3.Connection, chosen: int | TmdbRef) -> tuple[Anime, _Home]:
        """The entry the owner chose, and its title, made or refreshed: an AniList entry by its
        number, or a show or film only TMDB knows, by TMDB's kind and number. Raises LookupError
        when there's no such entry, or no TMDB key to look one up with."""
        tmdb = self._tmdb()
        if isinstance(chosen, int):
            entry = self._anilist.entry(chosen)
            if entry is None:
                raise LookupError(f"AniList has no entry {chosen}.")
            return entry, self._title_for(conn, entry, tmdb)
        if tmdb is None:
            raise LookupError("TMDB isn't connected: add your key in Settings to choose this.")
        media, number = chosen
        if media == "movie":
            film = tmdb.film(number)
            if film is None:
                raise LookupError("TMDB doesn't have that film any more.")
            names = (film.title, film.original_title)
            entry = tmdb_only(media, number, names, film.released, film.poster, film.minutes)
            return entry, _Home(save_film(conn, film, None, self._now()), film=True)
        show = tmdb.show(number)
        if show is None:
            raise LookupError("TMDB doesn't have that show any more.")
        names = (show.title, show.original_title)
        entry = tmdb_only(media, number, names, show.first_aired, show.poster)
        return entry, _Home(save_show(conn, show, TitleKind.SERIES, None, self._now()), show)

    def ignore(self, conn: sqlite3.Connection, file_id: int) -> None:
        """The owner says it isn't anime: Kura leaves it out, and no rescan asks again."""
        with conn:
            conn.execute(
                """UPDATE files SET title_id = NULL, season = NULL, episode = NULL,
                          episode_end = NULL, matched = 'ignored', pinned = 1, identified_at = ?
                   WHERE id = ?""",
                (self._now().isoformat(), file_id),
            )

    def unignore(self, conn: sqlite3.Connection, file_id: int) -> None:
        """The owner takes back "not anime": the file waits for a match again, and the next scan
        looks it up afresh."""
        with conn:
            conn.execute(
                """UPDATE files SET matched = 'none', pinned = 0, identified_at = NULL
                   WHERE id = ? AND matched = 'ignored'""",
                (file_id,),
            )

    def search(self, conn: sqlite3.Connection, file_id: int, text: str) -> list[Guess]:
        """AniList's entries for `text`, scored against one file, for the owner to pick from."""
        facts = _facts(conn, [file_id])
        if not facts or not text.strip():
            return []
        group = Group(
            text.strip(), facts[0].parsed.year, facts[0].parsed.kind is Kind.MOVIE, tuple(facts)
        )
        found = guesses(group, self._anilist.search(text.strip()))
        tmdb = self._tmdb()
        if tmdb is not None and not (found and found[0].confidence >= SURE):
            found = merged(found, self._through_tmdb(group, tmdb))  # a name AniList hasn't
        return found

    def _choose_again(self, conn: sqlite3.Connection) -> None:
        """The owner's choices made before Kura had TMDB's lists, placed again by them (see
        identify_again), with the same anime and kind. One that doesn't fit them waits for the
        owner again."""
        rows = conn.execute(
            """SELECT f.id, f.path, f.anilist_id, f.season, f.episode, t.kind
               FROM files AS f JOIN titles AS t ON t.id = f.title_id
               WHERE f.pinned = 1 AND f.identified_at IS NULL AND f.matched = 'sure'
                 AND f.gone_at IS NULL AND f.anilist_id IS NOT NULL"""
        ).fetchall()
        for row in rows:
            kind = _kind_of(row)
            named = parse_name(PureWindowsPath(row["path"])).episode
            episode = row["episode"] if row["episode"] != named else None
            try:
                self.choose(conn, row["id"], row["anilist_id"], kind, episode=episode)
            except UnplacedError, LookupError:
                with conn:
                    conn.execute(
                        """UPDATE files SET title_id = NULL, season = NULL, episode = NULL,
                                  episode_end = NULL, matched = 'unsure', pinned = 0,
                                  identified_at = ?
                           WHERE id = ?""",
                        (self._now().isoformat(), row["id"]),
                    )

    def _link_unlinked(self, conn: sqlite3.Connection) -> None:
        """The entries files are matched to that Kura has no links of (matched before it kept
        how AniList relates them), linked now so their franchises form. An entry related to no
        other anime is asked about again, from the cache while that lasts."""
        rows = conn.execute(
            """SELECT DISTINCT anilist_id FROM files
               WHERE anilist_id IS NOT NULL AND gone_at IS NULL
                 AND anilist_id NOT IN (SELECT anilist_id FROM anilist_links)"""
        ).fetchall()
        for row in rows:
            if entry := self._anilist.entry(row["anilist_id"]):
                save_links(conn, entry)

    def _tmdb(self) -> Tmdb | None:
        key = credentials.load(self._paths, "tmdb")
        return Tmdb(key, self._transport, cache=self._cache) if key else None

    def _settle(
        self,
        conn: sqlite3.Connection,
        group: Group,
        ranked: list[Guess],
        tmdb: Tmdb | None,
    ) -> tuple[int, int]:
        """Matches one group's files, or leaves them for the owner. Returns (sure, unsure)."""
        stamp = self._now().isoformat()
        best = ranked[0] if ranked else None
        if best is None or best.confidence < SURE:
            _mark_unsure(conn, group.files, ranked, stamp)
            return 0, len(group.files)

        entry = best.anime
        try:
            home = self._title_for(conn, entry, tmdb)
        except LookupError:  # TMDB lost the show or film only it knew, since finding it
            _mark_unsure(conn, group.files, ranked, stamp)
            return 0, len(group.files)
        film = home.film or entry.kind is TitleKind.MOVIE  # a file is the whole title
        through: set[int] = set() if film else _numbered_through(conn, group.files, home)
        placements: dict[int, Placement | None] = {}
        for facts in group.files:
            parsed = facts.parsed
            if facts.id in through:
                parsed = replace(parsed, folder_season=None)  # its number places it
            placements[facts.id] = None if film else _placement(parsed, entry, home)
        clashing = _clashes(group.files, placements)
        own = (
            {} if film else self._by_own_names(conn, group, home, placements, clashing, entry, tmdb)
        )

        sure = unsure = 0
        with conn:
            for facts in group.files:
                where = placements[facts.id]
                if facts.id in own:
                    found, home_of, ranked_of, where = own[facts.id]
                    _place(conn, facts, home_of, found, where, ranked_of, stamp)
                    sure += 1
                    continue
                if facts.id in clashing or (where is None and not film):
                    _mark_unsure(conn, [facts], ranked, stamp, commit=False)
                    unsure += 1
                    continue
                _place(conn, facts, home, best, where, ranked, stamp)
                sure += 1
        return sure, unsure

    def _by_own_names(
        self,
        conn: sqlite3.Connection,
        group: Group,
        home: _Home,
        placements: dict[int, Placement | None],
        clashing: set[int],
        series: Anime,
        tmdb: Tmdb | None,
    ) -> dict[int, tuple[Guess, _Home, list[Guess], Placement | None]]:
        """The group's specials its show's list doesn't name the way the files do ("Special 05
        (GT) - A Hero's Legacy"), each looked up by its own name: the OVA or special AniList (or
        TMDB) knows it as, sure, and where that goes (its show's specials, by the day it aired,
        or a title of its own). A special that two files land on stays with neither."""
        found: dict[int, tuple[Guess, _Home, list[Guess], Placement | None]] = {}
        for facts in group.files:
            title = facts.parsed.episode_title
            if placements[facts.id] is not None or facts.id in clashing or not title:
                continue
            if facts.parsed.kind is not Kind.SPECIAL:
                continue
            try:
                lookup = self._own_name(conn, group, facts, title, series, tmdb)
            except WebError as error:
                log.warning("Couldn't look %s up by its own name: %s", title, error)
                continue
            if lookup is not None:
                found[facts.id] = lookup
        taken: dict[tuple[int, int, int], list[int]] = defaultdict(list)
        for file_id, where in placements.items():  # what the show's list placed already
            if where is not None:
                taken[(home.title_id, where.season, where.episode)].append(file_id)
        for file_id, (_, its_home, _, where) in found.items():
            if where is not None:
                taken[(its_home.title_id, where.season, where.episode)].append(file_id)
        crowded = {file_id for spot in taken.values() if len(spot) > 1 for file_id in spot}
        return {file_id: lookup for file_id, lookup in found.items() if file_id not in crowded}

    def _own_name(
        self,
        conn: sqlite3.Connection,
        group: Group,
        facts: FileFacts,
        title: str,
        series: Anime,
        tmdb: Tmdb | None,
    ) -> tuple[Guess, _Home, list[Guess], Placement | None] | None:
        """One special looked up by its own name, read as the series' ("Dragon Ball Z: A Hero's
        Legacy"). The release's count of its specials ("Special 05", or "03" in a specials
        folder) says nothing of the entry's, so only a one-off, or a film, is placed: it's
        its show's special that first aired on its day, or a title of its own."""
        parsed = replace(facts.parsed, episode=None, episode_end=None, folder_season=None)
        alone = replace(facts, parsed=parsed)
        named = Group(f"{group.query}: {title}", parsed.year, False, (alone,), group.query)
        ranked = self._look_up(named, tmdb, series=False)
        best = ranked[0] if ranked else None
        if best is None or best.confidence < SURE or best.anime.id == series.id:
            return None
        if best.anime.kind is not TitleKind.MOVIE and best.anime.episodes != 1:
            return None  # which of its episodes the file is, its name doesn't say
        try:
            home = self._title_for(conn, best.anime, tmdb)
        except LookupError:  # TMDB lost the show or film only it knew, since finding it
            return None
        if home.film or best.anime.kind is TitleKind.MOVIE:
            return best, home, ranked, None
        where = _placement(parsed, best.anime, home)
        if where is None and home.specials and home.show is not None:
            where = named_special(best.anime.titles, home.show)  # TMDB names it as AniList does
        return (best, home, ranked, where) if where is not None else None

    def _title_for(self, conn: sqlite3.Connection, entry: Anime, tmdb: Tmdb | None) -> _Home:
        """The library's title for an AniList entry, made or refreshed, with its TMDB show.
        Without a key, an entry whose files already sit in a TMDB title joins them there. A show
        or film only TMDB knows is a title of TMDB's alone: LookupError when there's no key to
        ask TMDB with, or TMDB doesn't have it any more."""
        if entry.tmdb is not None:
            if tmdb is None:
                raise LookupError("TMDB isn't connected: add your key in Settings to choose this.")
            return self._tmdb_title(conn, entry, *entry.tmdb, tmdb)
        save_links(conn, entry)
        if tmdb is None:
            return _known_home(conn, entry) or self._anilist_title(conn, entry)
        if entry.kind in (TitleKind.OVA, TitleKind.SPECIAL):
            parent = _parent_show(conn, entry)
            if parent is not None:
                return parent  # the show's specials hold it, in season 0
        media = "movie" if entry.kind is TitleKind.MOVIE else "tv"
        hit = _find(tmdb, entry, media)
        if hit is None and media == "tv" and entry.kind is not TitleKind.SERIES:
            hit = _find(tmdb, entry, "movie")  # a one-off OVA is often a film on TMDB
        if hit is not None:
            return self._tmdb_title(conn, entry, hit.media, hit.id, tmdb)
        return self._anilist_title(conn, entry)

    def _anilist_title(self, conn: sqlite3.Connection, entry: Anime) -> _Home:
        """The title of an entry Kura knows only from AniList. A list the library already has
        stays until it's due; a show still airing is asked about afresh, since a search answer
        can be days old."""
        row = conn.execute(
            "SELECT * FROM titles WHERE anilist_id = ? AND tmdb_id IS NULL", (entry.id,)
        ).fetchone()
        film = entry.kind is TitleKind.MOVIE
        if row is not None and not due(row, self._now()):
            return _Home(row["id"], film=film)
        if entry.airing:
            entry = self._anilist.entry(entry.id, fresh=True) or entry
        return _Home(save_anilist_title(conn, entry, self._now()), film=film)

    def _tmdb_title(
        self,
        conn: sqlite3.Connection,
        entry: Anime,
        media: Literal["tv", "movie"],
        number: int,
        tmdb: Tmdb,
    ) -> _Home:
        """The TMDB title for an entry, made or refreshed. A title only TMDB knew till now takes
        the entry's AniList number (the one it was found by is kept)."""
        if media == "movie":
            film = tmdb.film(number)
            if film is None:
                return self._without_tmdb(conn, entry)
            return _Home(save_film(conn, film, entry.anilist_id, self._now()), film=True)
        row = conn.execute(
            "SELECT * FROM titles WHERE tmdb_type = 'tv' AND tmdb_id = ?", (number,)
        ).fetchone()
        if row is not None and not due(row, self._now()):
            if row["anilist_id"] is None and entry.anilist_id is not None:
                with conn:
                    conn.execute(
                        "UPDATE titles SET anilist_id = ? WHERE id = ?",
                        (entry.anilist_id, row["id"]),
                    )
            return _Home(row["id"], show_of(conn, row["id"]))
        found = tmdb.show(number)
        if found is None:
            return self._without_tmdb(conn, entry)
        kind = _kind_for(entry, media)
        return _Home(save_show(conn, found, kind, entry.anilist_id, self._now()), found)

    def _without_tmdb(self, conn: sqlite3.Connection, entry: Anime) -> _Home:
        """The title of an entry whose show or film TMDB doesn't have any more: AniList's own.
        One only TMDB knew has none: LookupError."""
        if entry.tmdb is not None:
            raise LookupError(f"TMDB doesn't have {entry.title} any more.")
        return self._anilist_title(conn, entry)


def save_show(
    conn: sqlite3.Connection,
    show: Show,
    kind: TitleKind,
    anilist_id: int | None,
    now: datetime,
) -> int:
    """Stores a TMDB show and its whole episode list. A title's kind is never narrowed: a show
    first found as a series stays one when its OVAs turn up."""
    with conn:
        row = conn.execute(
            f"""INSERT INTO titles (kind, name, year, released, tmdb_type, tmdb_id, anilist_id,
                                    airing, poster, backdrop, checked_at, {_ABOUT})
                VALUES (?, ?, ?, ?, 'tv', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT (tmdb_type, tmdb_id) DO UPDATE SET
                    name = excluded.name, year = excluded.year, released = excluded.released,
                    airing = excluded.airing, poster = excluded.poster,
                    backdrop = excluded.backdrop, checked_at = excluded.checked_at,
                    anilist_id = COALESCE(titles.anilist_id, excluded.anilist_id),
                    kind = CASE WHEN titles.kind = 'series' THEN 'series' ELSE excluded.kind END,
                    {_ABOUT_UPDATED}
                RETURNING id""",  # noqa: S608 - only column names go in
            (
                kind.value,
                show.title,
                show.year,
                show.first_aired.isoformat() if show.first_aired else None,
                show.id,
                anilist_id,
                int(show.airing),
                show.poster,
                show.backdrop,
                now.isoformat(),
                *_about(
                    show.overview,
                    show.genres,
                    show.studio,
                    show.status,
                    show.last_aired,
                    show.minutes,
                ),
            ),
        ).fetchone()
        title_id: int = row["id"]
        conn.execute("DELETE FROM episodes WHERE title_id = ?", (title_id,))
        conn.executemany(
            "INSERT INTO episodes (title_id, season, number, name, aired, minutes, overview, still)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            [
                (
                    title_id,
                    e.season,
                    e.number,
                    e.title,
                    e.aired.isoformat() if e.aired else None,
                    e.minutes,
                    e.overview,
                    e.still,
                )
                for e in show.episodes
            ],
        )
    return title_id


# What a title's About panel shows, as kept on its row (migration 23).
_ABOUT = "overview, genres, studio, status, ended, minutes"
_ABOUT_UPDATED = ", ".join(f"{column} = excluded.{column}" for column in _ABOUT.split(", "))


def _about(
    overview: str | None,
    genres: tuple[str, ...],
    studio: str | None,
    status: str | None,
    ended: date | None,
    minutes: int | None,
) -> tuple[str | None, str | None, str | None, str | None, str | None, int | None]:
    """A title's About columns, as stored."""
    return (
        overview,
        json.dumps(list(genres), ensure_ascii=False) if genres else None,
        studio,
        status,
        ended.isoformat() if ended else None,
        minutes,
    )


def save_film(conn: sqlite3.Connection, film: Film, anilist_id: int | None, now: datetime) -> int:
    """Stores a TMDB film, as identifying finds it or a weekly look again brings it up to date.
    The AniList entry it was found by is kept; one found on TMDB alone takes `anilist_id`."""
    with conn:
        saved = conn.execute(
            f"""INSERT INTO titles (kind, name, year, released, tmdb_type, tmdb_id, anilist_id,
                                    poster, backdrop, checked_at, {_ABOUT})
                VALUES ('movie', ?, ?, ?, 'movie', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT (tmdb_type, tmdb_id) DO UPDATE SET
                    name = excluded.name, year = excluded.year, released = excluded.released,
                    poster = excluded.poster, backdrop = excluded.backdrop,
                    checked_at = excluded.checked_at,
                    anilist_id = COALESCE(titles.anilist_id, excluded.anilist_id),
                    {_ABOUT_UPDATED}
                RETURNING id""",  # noqa: S608 - only column names go in
            (
                film.title,
                film.year,
                film.released.isoformat() if film.released else None,
                film.id,
                anilist_id,
                film.poster,
                film.backdrop,
                now.isoformat(),
                *_about(film.overview, film.genres, film.studio, film.status, None, film.minutes),
            ),
        ).fetchone()
    title_id: int = saved["id"]
    return title_id


def save_anilist_title(conn: sqlite3.Connection, entry: Anime, now: datetime) -> int:
    """A title known only from AniList (no TMDB key, or TMDB doesn't have it): its episodes are
    the ones aired so far, numbered 1 to N as AniList counts them. AniList doesn't date them."""
    kind = entry.kind or TitleKind.SERIES
    with conn:
        row = conn.execute(
            f"""INSERT INTO titles (kind, name, year, released, anilist_id, airing, poster,
                                    backdrop, checked_at, {_ABOUT})
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT (anilist_id) WHERE tmdb_id IS NULL DO UPDATE SET
                    name = excluded.name, year = excluded.year, released = excluded.released,
                    airing = excluded.airing, poster = excluded.poster,
                    backdrop = excluded.backdrop, checked_at = excluded.checked_at,
                    {_ABOUT_UPDATED}
                RETURNING id""",  # noqa: S608 - only column names go in
            (
                kind.value,
                entry.title,
                entry.year,
                entry.start.isoformat() if entry.start else None,
                entry.id,
                int(entry.airing),
                entry.cover,
                entry.banner,
                now.isoformat(),
                *_about(
                    entry.description,
                    entry.genres,
                    entry.studio,
                    entry.standing,
                    entry.end,
                    entry.minutes,
                ),
            ),
        ).fetchone()
        title_id: int = row["id"]
        aired = _aired(entry)
        if kind is not TitleKind.MOVIE and aired is not None:
            conn.execute("DELETE FROM episodes WHERE title_id = ?", (title_id,))
            conn.executemany(
                "INSERT INTO episodes (title_id, season, number) VALUES (?, 1, ?)",
                [(title_id, number) for number in range(1, aired + 1)],
            )
    return title_id


def _aired(entry: Anime) -> int | None:
    """How many of an entry's episodes have aired, or None when AniList can't say just now
    (the list Kura has stays as it is)."""
    if not entry.airing:
        return entry.episodes
    return entry.next_episode - 1 if entry.next_episode else None


def save_links(conn: sqlite3.Connection, entry: Anime) -> None:
    """Remembers how AniList relates an entry to others: what ties a franchise together
    (kura/core/franchise.py)."""
    with conn:
        write_links(conn, entry)


def write_links(conn: sqlite3.Connection, entry: Anime) -> None:
    """`save_links`, within the caller's transaction."""
    conn.execute("DELETE FROM anilist_links WHERE anilist_id = ?", (entry.id,))
    conn.executemany(
        """INSERT OR IGNORE INTO anilist_links (anilist_id, related_id, relation)
           VALUES (?, ?, ?)""",
        [(entry.id, related.id, related.relation) for related in entry.related],
    )


def identify_again(conn: sqlite3.Connection) -> int:
    """With a TMDB key just added: every file matched on AniList alone is identified again by
    the next scan, so it lands in TMDB's seasons (the owner's own choices keep their anime).
    Returns how many files that is."""
    with conn:
        return conn.execute(
            """UPDATE files SET identified_at = NULL
               WHERE gone_at IS NULL AND matched = 'sure'
                 AND title_id IN (SELECT id FROM titles WHERE tmdb_id IS NULL)"""
        ).rowcount


def _known_home(conn: sqlite3.Connection, entry: Anime) -> _Home | None:
    """The TMDB title an entry's files already sit in, with the episode list Kura kept."""
    row = conn.execute(
        """SELECT * FROM titles
           WHERE tmdb_id IS NOT NULL
             AND (anilist_id = ? OR id IN (SELECT title_id FROM files WHERE anilist_id = ?))
           ORDER BY id LIMIT 1""",
        (entry.id, entry.id),
    ).fetchone()
    if row is None:
        return None
    if row["tmdb_type"] == "movie":
        return _Home(row["id"], film=True)
    part = entry.kind in (TitleKind.OVA, TitleKind.SPECIAL) and row["kind"] == "series"
    return _Home(row["id"], show_of(conn, row["id"]), specials=part)


def _parent_show(conn: sqlite3.Connection, entry: Anime) -> _Home | None:
    """The TMDB show an OVA or special is part of, when the library has it and the show's
    specials (season 0) list it on the day it first aired. Otherwise it's a title of its own."""
    if entry.start is None:
        return None
    for related in entry.related:
        if related.kind is not TitleKind.SERIES or related.relation not in _PART_OF:
            continue
        row = conn.execute(
            "SELECT id FROM titles WHERE anilist_id = ? AND tmdb_type = 'tv'", (related.id,)
        ).fetchone()
        if row is None:
            continue
        show = show_of(conn, row["id"])
        if show is not None and lists_special(show, entry.start):
            return _Home(row["id"], show, specials=True)
    return None


def _kind_of(row: sqlite3.Row) -> Kind:
    """What a placed file is now, from its record and its title's (`season` and `kind`): a film,
    a special (season 0), or an episode."""
    if row["kind"] == "movie" or row["season"] is None:
        return Kind.MOVIE
    return Kind.SPECIAL if row["season"] == 0 else Kind.EPISODE


def _placement(parsed: ParsedName, entry: Anime, home: _Home) -> Placement | None:
    """Where a file of `entry` sits in its title, or None when Kura can't tell surely."""
    if home.specials and home.show is not None:
        return place(replace(parsed, kind=Kind.SPECIAL), home.show, entry)
    if entry.kind in (TitleKind.OVA, TitleKind.SPECIAL) and parsed.kind is Kind.SPECIAL:
        parsed = replace(parsed, kind=Kind.EPISODE)  # the title is the OVA or special itself
    if parsed.kind is Kind.EPISODE and parsed.episode is None and entry.episodes == 1:
        parsed = replace(parsed, episode=1)  # a one-off: its only episode
    if home.show is not None:
        return place(parsed, home.show, entry)
    return _by_anilist_number(parsed, entry)


def _numbered_through(
    conn: sqlite3.Connection, files: Sequence[FileFacts], home: _Home
) -> set[int]:
    """The files in a season's folder that count straight through their show (see
    numbered_through), told by every video of the show in their release's season folders: those
    placed before too, so a file identified on its own goes as they did."""
    if home.show is None or home.specials:
        return set()
    ids = {facts.id for facts in files}
    releases = {  # the folders above a season's whose files go without it: "S01E05" says all
        facts.path.parent.parent
        for facts in files
        if facts.parsed.folder_season and facts.parsed.season is None
    }
    beside: list[FileFacts] = []
    for release in releases:
        beside += [facts for facts in _placed_in(conn, release, home) if facts.id not in ids]
    return numbered_through([*files, *beside], home.show) & ids


def _placed_in(conn: sqlite3.Connection, release: PurePath, home: _Home) -> list[FileFacts]:
    """The title's videos in the folders of a release's folder ("[Group] Show (S01-S07)\\Show
    Season 02"), by their names. Only the title's: other shows' share a library's folder."""
    inside = str(release).rstrip("\\/") + "\\"
    rows = conn.execute(
        """SELECT id, path FROM files
           WHERE gone_at IS NULL AND title_id = ? AND lower(substr(path, 1, ?)) = lower(?)""",
        (home.title_id, len(inside), inside),
    ).fetchall()
    paths = [(row["id"], PureWindowsPath(row["path"])) for row in rows]
    return [
        FileFacts(file_id, path, parse_name(path), None)
        for file_id, path in paths
        if str(path.parent.parent).casefold() == str(release).casefold()
    ]


def _which_episode(entry: Anime, number: int | None) -> str:
    if number is None:
        return "Which episode is it? Kura can't tell from its name."
    return f"Which episode is it? {entry.title} has no episode {number}."


def _find(tmdb: Tmdb, entry: Anime, media: str) -> Hit | None:
    """The TMDB show or film for an entry, searched by its name without the season or part."""
    kind = "movie" if media == "movie" else "tv"
    tried: set[str] = set()
    for name in (entry.title, *entry.titles[:2]):
        query = base_title(name)
        if query.casefold() in tried:
            continue
        tried.add(query.casefold())
        year = entry.year if kind == "movie" else None
        picked = pick_tmdb(entry, tmdb.search(kind, query, year))
        if picked is not None:
            return picked[0]
    return None


def _kind_for(entry: Anime, media: Literal["tv", "movie"]) -> TitleKind:
    if media == "movie":
        return TitleKind.MOVIE
    if entry.kind is TitleKind.OVA or entry.kind is TitleKind.SPECIAL:
        return entry.kind
    return TitleKind.SERIES


def due(row: sqlite3.Row, now: datetime) -> bool:
    """Whether a show's episode list is old enough to ask TMDB again."""
    checked = row["checked_at"]
    if checked is None:
        return True
    every = AIRING_EVERY if row["airing"] else FINISHED_EVERY
    return now - datetime.fromisoformat(checked) >= every


def _by_anilist_number(parsed: ParsedName, entry: Anime) -> Placement | None:
    """Without TMDB, a file sits at its own number among the entry's episodes."""
    number = parsed.episode
    if number is None or parsed.kind is not Kind.EPISODE or number < 1:
        return None
    if entry.episodes and number > entry.episodes:
        return None
    return Placement(1, number, parsed.episode_end, How.NUMBERED)


def _clashes(files: Sequence[FileFacts], placements: dict[int, Placement | None]) -> set[int]:
    """Files placed on the same episode though their own numbers differ: one of them is placed
    wrongly, so neither is trusted. Copies of one episode carry the same numbers, and stay."""
    by_spot: dict[tuple[int, int], list[FileFacts]] = defaultdict(list)
    for facts in files:
        where = placements.get(facts.id)
        if where is not None:
            by_spot[(where.season, where.episode)].append(facts)
    clashing: set[int] = set()
    for together in by_spot.values():
        numbers = {(_season(f.parsed), f.parsed.episode, f.parsed.part) for f in together}
        if len(numbers) > 1:
            clashing.update(f.id for f in together)
    return clashing


def _season(parsed: ParsedName) -> int | None:
    """A file's season, from its name or else its folder ("Season 01/05.mkv")."""
    return parsed.season if parsed.season is not None else parsed.folder_season


def _facts(conn: sqlite3.Connection, file_ids: Sequence[int]) -> list[FileFacts]:
    """What Kura knows about these files, whatever their state."""
    marks = ",".join("?" * len(file_ids))
    rows = conn.execute(
        f"SELECT id, path, duration FROM files WHERE id IN ({marks}) AND gone_at IS NULL",  # noqa: S608 - only question marks
        tuple(file_ids),
    ).fetchall()
    return [
        FileFacts(
            row["id"],
            PureWindowsPath(row["path"]),
            parse_name(PureWindowsPath(row["path"])),
            row["duration"] / 60 if row["duration"] else None,
        )
        for row in rows
    ]


def _to_identify(conn: sqlite3.Connection) -> tuple[list[FileFacts], list[tuple[int, Kind]]]:
    """Files read and not yet identified (the owner's own choices excepted): the ones to look up,
    and the extras and disc files that can't be."""
    rows = conn.execute(
        """SELECT id, path, duration FROM files
           WHERE gone_at IS NULL AND probed_at IS NOT NULL AND identified_at IS NULL
             AND pinned = 0
           ORDER BY path"""
    ).fetchall()
    files: list[FileFacts] = []
    others: list[tuple[int, Kind]] = []
    for row in rows:
        path = PureWindowsPath(row["path"])
        parsed = parse_name(path)
        if parsed.kind in (Kind.EXTRA, Kind.DVD) or not parsed.best_title:
            others.append((row["id"], parsed.kind))
            continue
        minutes = row["duration"] / 60 if row["duration"] else None
        files.append(FileFacts(row["id"], path, parsed, minutes))
    return files, others


def _mark_unlookable(
    conn: sqlite3.Connection, others: Iterable[tuple[int, Kind]], stamp: str
) -> None:
    with conn:
        conn.executemany(
            "UPDATE files SET matched = ?, identified_at = ? WHERE id = ?",
            [
                ("extra" if kind is Kind.EXTRA else "none", stamp, file_id)
                for file_id, kind in others
            ],
        )


def _place(
    conn: sqlite3.Connection,
    facts: FileFacts,
    home: _Home,
    best: Guess,
    where: Placement | None,
    ranked: list[Guess],
    stamp: str,
) -> None:
    """A file matched surely: its title, entry and place there (none for a film). Part of the
    caller's transaction."""
    conn.execute(
        """UPDATE files SET title_id = ?, anilist_id = ?, season = ?, episode = ?,
                  episode_end = ?, matched = 'sure', confidence = ?, guesses = ?,
                  identified_at = ?
           WHERE id = ? AND pinned = 0""",
        (
            home.title_id,
            best.anime.anilist_id,
            where.season if where else None,
            where.episode if where else None,
            where.last if where else None,
            best.confidence,
            _guesses_json(ranked),
            stamp,
            facts.id,
        ),
    )


def _mark_unsure(
    conn: sqlite3.Connection,
    files: Iterable[FileFacts],
    ranked: list[Guess],
    stamp: str,
    *,
    commit: bool = True,
) -> None:
    state = "unsure" if ranked else "none"
    rows = [
        (state, ranked[0].confidence if ranked else None, _guesses_json(ranked), stamp, f.id)
        for f in files
    ]
    sql = """UPDATE files SET title_id = NULL, season = NULL, episode = NULL, episode_end = NULL,
                    matched = ?, confidence = ?, guesses = ?, identified_at = ?
             WHERE id = ? AND pinned = 0"""
    if commit:
        with conn:
            conn.executemany(sql, rows)
    else:
        conn.executemany(sql, rows)


def _guesses_json(ranked: list[Guess]) -> str:
    return json.dumps([_saved(guess) for guess in ranked[:_SHOWN_GUESSES]])


def _saved(guess: Guess) -> dict[str, object]:
    """A guess as the review screen shows it (api/review.py's Guess)."""
    entry = guess.anime
    media, number = entry.tmdb or (None, None)  # a show or film only TMDB knows
    return {
        "anilistId": entry.anilist_id,
        "tmdbType": media,
        "tmdbId": number,
        "title": entry.title,
        "kind": entry.kind.value if entry.kind else None,
        "year": entry.year,
        "episodes": entry.episodes,
        "minutes": entry.minutes,
        "cover": entry.cover,
        "confidence": guess.confidence,
        "reasons": list(guess.reasons),
    }


def _series_last(ranked: list[Guess]) -> int:
    """Sort key: series first (0), everything else after (1)."""
    best = ranked[0].anime.kind if ranked else None
    return 0 if best is TitleKind.SERIES else 1


def _waiting(service: str, error: WebError) -> str:
    return f"Titles wait for the next scan: {service} couldn't be asked ({error})"
