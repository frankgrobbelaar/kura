"""Identifying the library, the scan's third stage, with AniList and TMDB stood in for."""

import json
import sqlite3
from dataclasses import replace
from datetime import timedelta
from pathlib import Path
from typing import cast

import pytest

from kura import credentials
from kura.anilist import API as ANILIST
from kura.config import DataPaths
from kura.core.catalog import anime_list
from kura.core.names import Kind
from kura.identify import Identifier, UnplacedError, identify_again, save_anilist_title
from kura.library import find_files, folders, read_file, unread
from kura.titles import title
from kura.tmdb import API as TMDB
from tests.fake_ffprobe import REPORT
from tests.fake_web import reply
from tests.services import SAVED, internet
from tests.shelf import NOW, identify, library

COWBOY_BEBOP = json.loads((SAVED / "cowboy-bebop.json").read_text(encoding="utf-8"))
YOSEATSUME = next(m for m in COWBOY_BEBOP["data"]["Page"]["media"] if m["id"] == 4037)


def placed(conn: sqlite3.Connection) -> dict[str, tuple[object, ...]]:
    rows = conn.execute(
        """SELECT f.path, f.matched, t.name, t.kind, f.season, f.episode
           FROM files f LEFT JOIN titles t ON t.id = f.title_id"""
    )
    return {Path(row["path"]).name: tuple(row)[1:] for row in rows}


@pytest.fixture
def root(tmp_path: Path) -> Path:
    return tmp_path / "Anime"


def test_with_a_tmdb_key_every_episode_lands_in_tmdbs_seasons(
    paths: DataPaths, conn: sqlite3.Connection, root: Path
):
    credentials.save(paths, "tmdb", "a-test-key")
    library(
        conn,
        root,
        [
            "Dragon Ball Z (1989)/Dragon Ball Z - 001.mkv",
            "Dragon Ball Z (1989)/Dragon Ball Z - 150.mkv",
            "Downloads/[Group] DBZ - 291 [480p].mkv",
        ],
    )

    done = identify(paths, conn, internet())

    assert placed(conn) == {
        "Dragon Ball Z - 001.mkv": ("sure", "Dragon Ball Z", "series", 1, 1),
        "Dragon Ball Z - 150.mkv": ("sure", "Dragon Ball Z", "series", 5, 11),
        "[Group] DBZ - 291 [480p].mkv": ("sure", "Dragon Ball Z", "series", 9, 38),
    }
    title = conn.execute("SELECT * FROM titles").fetchone()
    assert (title["tmdb_type"], title["tmdb_id"], title["anilist_id"]) == ("tv", 12971, 813)
    assert (title["year"], title["released"]) == (1989, "1989-04-26")
    assert (title["poster"], title["backdrop"]) == ("/poster-12971.jpg", "/backdrop-12971.jpg")
    assert conn.execute("SELECT COUNT(*) FROM episodes").fetchone()[0] == 291
    still = "SELECT still FROM episodes WHERE season = 5 AND number = 11"
    assert conn.execute(still).fetchone()[0] == "/still-12971-5-11.jpg"
    assert done.sure == 3


def test_a_film_is_its_own_title(paths: DataPaths, conn: sqlite3.Connection, root: Path):
    credentials.save(paths, "tmdb", "a-test-key")
    library(conn, root, ["Movies/Cowboy Bebop - The Movie (2001).mkv"], minutes=115)

    identify(paths, conn, internet())

    assert placed(conn) == {
        "Cowboy Bebop - The Movie (2001).mkv": (
            "sure",
            "Cowboy Bebop: The Movie",
            "movie",
            None,
            None,
        )
    }


def test_without_a_key_anilist_numbers_the_episodes(
    paths: DataPaths, conn: sqlite3.Connection, root: Path
):
    library(conn, root, ["Dragon Ball Z/Dragon Ball Z - 150.mkv"])
    web = internet(tmdb=False)

    identify(paths, conn, web)

    assert placed(conn) == {"Dragon Ball Z - 150.mkv": ("sure", "Dragon Ball Z", "series", 1, 150)}
    title = conn.execute("SELECT * FROM titles").fetchone()
    assert (title["tmdb_id"], title["anilist_id"]) == (None, 813)
    assert conn.execute("SELECT COUNT(*) FROM episodes").fetchone()[0] == 291
    assert all(path.startswith("POST https://graphql") for path in web.paths())


def test_without_a_key_a_show_still_airing_lists_what_has_aired(
    paths: DataPaths, conn: sqlite3.Connection, root: Path
):
    library(conn, root, ["One Piece/One Piece - 1000.mkv"])

    identify(paths, conn, internet(tmdb=False))

    row = conn.execute("SELECT id, airing FROM titles").fetchone()
    episodes = conn.execute("SELECT COUNT(*), COUNT(aired) FROM episodes").fetchone()
    assert (row["airing"], tuple(episodes)) == (1, (1180, 0))  # aired so far, never dated
    found = title(conn, row["id"], NOW.date())
    assert found is not None
    assert found.gaps is not None
    assert (len(found.gaps.missing), len(found.gaps.upcoming)) == (1179, 0)


def test_a_show_still_airing_is_saved_from_what_anilist_says_now(
    paths: DataPaths, conn: sqlite3.Connection, root: Path
):
    library(conn, root, ["One Piece/One Piece - 1000.mkv"])
    identify(paths, conn, internet(tmdb=False))  # the search is kept a week
    with conn:
        conn.execute("DELETE FROM titles")
        conn.execute("UPDATE files SET identified_at = NULL, title_id = NULL")

    identify(paths, conn, internet(tmdb=False, airing={21: 1183}))

    assert conn.execute("SELECT COUNT(*) FROM episodes").fetchone()[0] == 1182


def test_a_scan_leaves_a_list_from_anilist_until_its_due(
    paths: DataPaths, conn: sqlite3.Connection, root: Path
):
    library(conn, root, ["One Piece/One Piece - 1000.mkv"])
    identify(paths, conn, internet(tmdb=False))
    library(conn, root, ["One Piece/One Piece - 1001.mkv"])
    web = internet(tmdb=False, airing={21: 1185})

    identify(paths, conn, web)  # within the hour

    assert conn.execute("SELECT COUNT(*) FROM episodes").fetchone()[0] == 1180
    assert all("search" in str(asked.payload["variables"]) for asked in web.asked)


def test_a_list_anilist_cant_count_now_is_kept_as_it_was(conn: sqlite3.Connection):
    answer = json.loads((SAVED / "one-piece.json").read_text(encoding="utf-8"))
    one_piece = next(entry for entry in anime_list(answer) if entry.id == 21)
    save_anilist_title(conn, one_piece, NOW)

    save_anilist_title(conn, replace(one_piece, next_episode=None), NOW)

    assert conn.execute("SELECT COUNT(*) FROM episodes").fetchone()[0] == 1180


def test_a_key_added_later_moves_what_anilist_alone_matched_into_tmdbs_seasons(
    paths: DataPaths, conn: sqlite3.Connection, root: Path
):
    library(conn, root, ["Dragon Ball Z/Dragon Ball Z - 150.mkv", "Old DVDs/VTS_01_1.VOB"])
    identify(paths, conn, internet(tmdb=False))
    [dvd] = [row[0] for row in conn.execute("SELECT id FROM files WHERE path LIKE '%.VOB'")]
    owner = Identifier(paths, internet(tmdb=False), now=lambda: NOW)
    owner.choose(conn, dvd, 813, Kind.EPISODE, episode=151)
    assert placed(conn)["VTS_01_1.VOB"] == ("sure", "Dragon Ball Z", "series", 1, 151)
    credentials.save(paths, "tmdb", "a-test-key")

    assert identify_again(conn) == 2
    identify(paths, conn, internet())

    assert placed(conn) == {
        "Dragon Ball Z - 150.mkv": ("sure", "Dragon Ball Z", "series", 5, 11),
        "VTS_01_1.VOB": ("sure", "Dragon Ball Z", "series", 5, 12),  # the owner's choice
    }
    homes = conn.execute(
        "SELECT DISTINCT t.tmdb_id, f.pinned FROM files f JOIN titles t ON t.id = f.title_id"
    ).fetchall()
    assert sorted(tuple(row) for row in homes) == [(12971, 0), (12971, 1)]


def test_without_the_key_new_files_join_the_title_their_anime_has(
    paths: DataPaths, conn: sqlite3.Connection, root: Path
):
    credentials.save(paths, "tmdb", "a-test-key")
    library(conn, root, ["Dragon Ball Z/Dragon Ball Z - 001.mkv"])
    identify(paths, conn, internet())
    credentials.forget(paths, "tmdb")
    library(conn, root, ["Dragon Ball Z/Dragon Ball Z - 150.mkv"])

    identify(paths, conn, internet(tmdb=False))

    assert placed(conn)["Dragon Ball Z - 150.mkv"] == ("sure", "Dragon Ball Z", "series", 5, 11)
    assert conn.execute("SELECT COUNT(*) FROM titles").fetchone()[0] == 1


def test_a_name_kura_cant_match_waits_for_the_owner(
    paths: DataPaths, conn: sqlite3.Connection, root: Path
):
    library(conn, root, ["Downloads/Mystery Show - 03.mkv"])

    identify(paths, conn, internet())

    row = conn.execute("SELECT matched, title_id, guesses FROM files").fetchone()
    assert (row["matched"], row["title_id"], json.loads(row["guesses"])) == ("none", None, [])


def test_a_numbered_film_is_found_by_its_own_name(
    paths: DataPaths, conn: sqlite3.Connection, root: Path
):
    film = "Dragon Ball Z - Movie 03 - The Tree of Might (1990 BluRay - 1080p TRI AUDIO).mkv"
    library(conn, root, [f"DRAGON BALL Z (1989-2019)/2a. Movies (1989-2018)/{film}"], minutes=61)

    identify(paths, conn, internet(tmdb=False))

    assert placed(conn) == {film: ("sure", "Dragon Ball Z: The Tree of Might", "movie", None, None)}


def test_a_film_named_with_its_series_initials_is_found_by_them_written_out(
    paths: DataPaths, conn: sqlite3.Connection, root: Path
):
    film = "Dragon Ball Z - Movie 16 - DB Super BROLY, MangaUK Version (2018 BluRay - 1080p).mkv"
    library(conn, root, [f"DRAGON BALL Z (1989-2019)/2a. Movies (1989-2018)/{film}"], minutes=100)

    identify(paths, conn, internet(tmdb=False))

    assert placed(conn) == {film: ("sure", "Dragon Ball Super: Broly", "movie", None, None)}


def test_a_name_only_tmdb_knows_is_found_through_it(
    paths: DataPaths, conn: sqlite3.Connection, root: Path
):
    credentials.save(paths, "tmdb", "a-test-key")
    library(conn, root, ["Bola de Dragon Z/Bola de Dragon Z - 001.mkv"])  # its Spanish name
    web = internet()

    identify(paths, conn, web)

    assert placed(conn) == {"Bola de Dragon Z - 001.mkv": ("sure", "Dragon Ball Z", "series", 1, 1)}
    [guess, *_] = json.loads(conn.execute("SELECT guesses FROM files").fetchone()[0])
    assert guess["reasons"][0] == "TMDB knows it as Dragon Ball Z"
    assert f"GET {TMDB}/tv/12971/alternative_titles" in web.paths()


def test_tmdb_turning_the_key_away_leaves_what_anilist_found(
    paths: DataPaths, conn: sqlite3.Connection, root: Path
):
    credentials.save(paths, "tmdb", "a-test-key")
    library(conn, root, ["Downloads/Mystery Show - 03.mkv"])
    web = internet()
    web.answers[f"GET {TMDB}/search/tv"] = reply({"status_message": "Invalid API key"}, 401)

    done = identify(paths, conn, web)

    row = conn.execute("SELECT matched, title_id FROM files").fetchone()
    assert (row["matched"], row["title_id"]) == ("none", None)
    assert done.note is None


def test_a_special_its_shows_list_doesnt_name_is_found_by_its_own_name(
    paths: DataPaths, conn: sqlite3.Connection, root: Path
):
    credentials.save(paths, "tmdb", "a-test-key")
    special = "Cowboy Bebop - Special 07 - Yoseatsume Blues.mkv"  # the release's own count
    library(conn, root, ["Cowboy Bebop/Cowboy Bebop - 01.mkv", f"Cowboy Bebop/{special}"])

    identify(paths, conn, internet())

    assert placed(conn) == {
        "Cowboy Bebop - 01.mkv": ("sure", "Cowboy Bebop", "series", 1, 1),
        special: ("sure", "Cowboy Bebop", "series", 0, 2),  # by the day it first aired
    }
    row = conn.execute("SELECT anilist_id FROM files WHERE path LIKE '%Special 07%'").fetchone()
    assert row["anilist_id"] == 4037


def test_a_series_anilist_writes_otherwise_is_asked_for_its_way(
    paths: DataPaths, conn: sqlite3.Connection, root: Path
):
    names = [
        "Dragonball.GT.01.Ein.fataler.Wunsch.mkv",
        "Dragonball.GT.02.Ein.blinder.Passagier.mkv",
        "Dragonball.GT.64.Das.grosse.Finale.mkv",
    ]
    library(conn, root, [f"DragonBall GT Remastered Uncut/{name}" for name in names], minutes=21)
    web = internet(tmdb=False)

    identify(paths, conn, web)

    assert placed(conn) == {
        names[0]: ("sure", "Dragon Ball GT", "series", 1, 1),
        names[1]: ("sure", "Dragon Ball GT", "series", 1, 2),
        names[2]: ("sure", "Dragon Ball GT", "series", 1, 64),
    }
    searched = [
        variables["search"]
        for asked in web.asked
        if "search" in (variables := cast("dict[str, object]", asked.payload["variables"]))
    ]
    assert searched == ["Dragonball GT", "Dragonball", "dragon ball gt"]


def test_extras_are_marked_and_never_looked_up(
    paths: DataPaths, conn: sqlite3.Connection, root: Path
):
    library(conn, root, ["Cowboy Bebop/Extras/NCOP01.mkv"])
    web = internet()

    identify(paths, conn, web)

    assert placed(conn) == {"NCOP01.mkv": ("extra", None, None, None, None)}
    assert web.asked == []


def test_offline_the_files_wait_for_the_next_scan(
    paths: DataPaths, conn: sqlite3.Connection, root: Path
):
    library(conn, root, ["Dragon Ball Z/Dragon Ball Z - 001.mkv"])
    web = internet()
    web.offline = True

    done = identify(paths, conn, web)

    assert "Titles wait for the next scan: AniList couldn't be asked" in str(done.note)
    row = conn.execute("SELECT matched, identified_at FROM files").fetchone()
    assert (row["matched"], row["identified_at"]) == (None, None)


def test_a_file_the_owner_placed_is_left_alone(
    paths: DataPaths, conn: sqlite3.Connection, root: Path
):
    library(conn, root, ["Dragon Ball Z/Dragon Ball Z - 001.mkv"])
    with conn:
        conn.execute("UPDATE files SET pinned = 1")
    web = internet()

    identify(paths, conn, web)

    assert web.asked == []
    assert conn.execute("SELECT matched FROM files").fetchone()[0] is None


def test_a_second_scan_asks_nobody_again(paths: DataPaths, conn: sqlite3.Connection, root: Path):
    credentials.save(paths, "tmdb", "a-test-key")
    library(conn, root, ["Dragon Ball Z/Dragon Ball Z - 001.mkv"])
    identify(paths, conn, internet())
    (root / "Dragon Ball Z" / "Dragon Ball Z - 002.mkv").write_bytes(b"new")
    [folder] = folders(conn)
    find_files(conn, folder, stamp=(NOW + timedelta(hours=1)).isoformat())
    for file_id, path in unread(conn):
        read_file(conn, file_id, path, lambda _: REPORT, now=NOW)
    web = internet()

    identify(paths, conn, web)

    assert placed(conn)["Dragon Ball Z - 002.mkv"] == ("sure", "Dragon Ball Z", "series", 1, 2)
    assert web.asked == []  # AniList's and TMDB's searches were kept; the episode list is fresh


def test_an_ova_goes_into_its_shows_specials_by_date(
    paths: DataPaths, conn: sqlite3.Connection, root: Path
):
    credentials.save(paths, "tmdb", "a-test-key")
    library(conn, root, ["Cowboy Bebop/Cowboy Bebop - 01.mkv"])
    identify(paths, conn, internet())

    entries = json.loads((SAVED / "cowboy-bebop.json").read_text(encoding="utf-8"))
    yoseatsume = next(
        m for m in entries["data"]["Page"]["media"] if m["id"] == 4037
    )  # first aired 26 June 1998
    web = internet()
    web.answers[f"POST {ANILIST}"] = lambda asked: {"data": {"Page": {"media": [yoseatsume]}}}
    (root / "Cowboy Bebop" / "Cowboy Bebop - Yoseatsume Blues - OVA.mkv").write_bytes(b"ova")
    [folder] = folders(conn)
    find_files(conn, folder, stamp=(NOW + timedelta(hours=1)).isoformat())
    for file_id, path in unread(conn):
        read_file(conn, file_id, path, lambda _: REPORT, now=NOW)

    identify(paths, conn, web)

    assert placed(conn)["Cowboy Bebop - Yoseatsume Blues - OVA.mkv"] == (
        "sure",
        "Cowboy Bebop",
        "series",
        0,
        2,
    )


def test_an_ovas_numbered_files_go_into_its_shows_specials_not_its_episodes(
    paths: DataPaths, conn: sqlite3.Connection, root: Path
):
    credentials.save(paths, "tmdb", "a-test-key")
    library(conn, root, ["Cowboy Bebop/Cowboy Bebop - 01.mkv"])
    identify(paths, conn, internet())
    web = internet()
    web.answers[f"POST {ANILIST}"] = lambda asked: {"data": {"Page": {"media": [YOSEATSUME]}}}
    library(conn, root, ["Cowboy Bebop/Cowboy Bebop - Yoseatsume Blues - 01.mkv"])

    identify(paths, conn, web)

    found = placed(conn)
    assert found["Cowboy Bebop - Yoseatsume Blues - 01.mkv"] == (
        "sure",
        "Cowboy Bebop",
        "series",
        0,
        2,
    )
    assert found["Cowboy Bebop - 01.mkv"] == ("sure", "Cowboy Bebop", "series", 1, 1)


def test_an_ova_goes_under_a_show_only_if_its_part_of_it(
    paths: DataPaths, conn: sqlite3.Connection, root: Path
):
    credentials.save(paths, "tmdb", "a-test-key")
    library(conn, root, ["Cowboy Bebop/Cowboy Bebop - 01.mkv"])
    identify(paths, conn, internet())
    edges = YOSEATSUME["relations"]["edges"]
    crossover = {  # only its characters appear in Cowboy Bebop
        **YOSEATSUME,
        "relations": {"edges": [{**edge, "relationType": "CHARACTER"} for edge in edges]},
    }
    web = internet()
    web.answers[f"POST {ANILIST}"] = lambda asked: {"data": {"Page": {"media": [crossover]}}}
    library(conn, root, ["Cowboy Bebop/Cowboy Bebop - Yoseatsume Blues - 01.mkv"])

    identify(paths, conn, web)

    where = placed(conn)["Cowboy Bebop - Yoseatsume Blues - 01.mkv"]
    assert where[1:] != ("Cowboy Bebop", "series", 0, 2)


def test_the_same_episode_named_two_ways_isnt_a_clash(
    paths: DataPaths, conn: sqlite3.Connection, root: Path
):
    credentials.save(paths, "tmdb", "a-test-key")
    library(
        conn,
        root,
        [
            "Dragon Ball Z (1989)/Season 01/05.mkv",
            "Dragon Ball Z (1989)/Dragon Ball Z - S01E05.mkv",
        ],
    )

    identify(paths, conn, internet())

    assert set(placed(conn).values()) == {("sure", "Dragon Ball Z", "series", 1, 5)}


def test_the_owner_says_which_episode_when_its_name_doesnt(
    paths: DataPaths, conn: sqlite3.Connection, root: Path
):
    credentials.save(paths, "tmdb", "a-test-key")
    library(conn, root, ["Old DVDs/VTS_01_1.VOB"])
    identify(paths, conn, internet())
    [file_id] = [row[0] for row in conn.execute("SELECT id FROM files")]
    owner = Identifier(paths, internet(), now=lambda: NOW)

    with pytest.raises(UnplacedError, match="Which episode is it"):
        owner.choose(conn, file_id, 813, Kind.EPISODE)
    assert placed(conn)["VTS_01_1.VOB"] == ("none", None, None, None, None)

    assert owner.choose(conn, file_id, 813, Kind.EPISODE, episode=150) == 1
    assert placed(conn)["VTS_01_1.VOB"] == ("sure", "Dragon Ball Z", "series", 5, 11)


def test_look_alikes_kura_cant_place_keep_waiting(
    paths: DataPaths, conn: sqlite3.Connection, root: Path
):
    credentials.save(paths, "tmdb", "a-test-key")
    library(conn, root, ["Downloads/[subs] ep03 final.mkv", "Downloads/[subs] ep999 final.mkv"])
    identify(paths, conn, internet())
    ids = {Path(row["path"]).name: row["id"] for row in conn.execute("SELECT id, path FROM files")}
    owner = Identifier(paths, internet(), now=lambda: NOW)

    count = owner.choose(
        conn,
        ids["[subs] ep03 final.mkv"],
        813,
        Kind.EPISODE,
        also=[ids["[subs] ep999 final.mkv"]],
    )

    assert count == 1
    assert placed(conn)["[subs] ep03 final.mkv"] == ("sure", "Dragon Ball Z", "series", 1, 3)
    assert placed(conn)["[subs] ep999 final.mkv"][0] != "sure"


def test_a_special_or_extra_kura_cant_number_still_belongs_to_its_show(
    paths: DataPaths, conn: sqlite3.Connection, root: Path
):
    credentials.save(paths, "tmdb", "a-test-key")
    library(conn, root, ["Old DVDs/VTS_02_1.VOB"])
    identify(paths, conn, internet())
    [file_id] = [row[0] for row in conn.execute("SELECT id FROM files")]

    Identifier(paths, internet(), now=lambda: NOW).choose(conn, file_id, 1, Kind.SPECIAL)

    assert placed(conn)["VTS_02_1.VOB"] == ("sure", "Cowboy Bebop", "series", 0, None)


def test_without_a_key_a_special_is_numbered_as_its_own_title(
    paths: DataPaths, conn: sqlite3.Connection, root: Path
):
    library(conn, root, ["Downloads/Yoseatsume Blues.mkv"])
    identify(paths, conn, internet(tmdb=False))
    [file_id] = [row[0] for row in conn.execute("SELECT id FROM files")]

    Identifier(paths, internet(tmdb=False), now=lambda: NOW).choose(
        conn, file_id, 4037, Kind.SPECIAL
    )

    assert placed(conn)["Yoseatsume Blues.mkv"] == (
        "sure",
        "Cowboy Bebop: Yoseatsume Blues",
        "special",
        1,
        1,
    )


def test_two_files_claiming_one_episode_with_different_numbers_wait_for_the_owner(
    paths: DataPaths, conn: sqlite3.Connection, root: Path
):
    credentials.save(paths, "tmdb", "a-test-key")
    library(
        conn,
        root,
        [
            "Dragon Ball Z/Dragon Ball Z - 040.mkv",  # straight through: season 2, episode 1
            "Dragon Ball Z/Season 02/Dragon Ball Z - 01.mkv",  # season 2, episode 1 by number
        ],
    )

    identify(paths, conn, internet())

    assert {row[0] for row in conn.execute("SELECT matched FROM files")} == {"unsure"}
