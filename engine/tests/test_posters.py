"""Choosing a title's poster: TMDB's and AniList's to choose from, the owner's choice kept over
the one found as the episode list is refreshed, and the poster next to the show following it."""

import sqlite3
from datetime import UTC, date, datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from kura import credentials, posters
from kura.anilist import API as ANILIST
from kura.config import DataPaths
from kura.core.catalog import TitleKind, show
from kura.identify import save_show
from kura.tmdb import API as TMDB
from tests.fake_web import Asked, FakeWeb
from tests.tmdb_data import tv_details

COVER = "https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx9-starfall.jpg"


@pytest.fixture
def title(conn: sqlite3.Connection, paths: DataPaths, web: FakeWeb) -> None:
    """A made-up show TMDB has three posters of, and AniList one cover."""
    credentials.save(paths, "tmdb", "0123456789abcdef0123456789abcdef")
    with conn:
        conn.execute(
            """INSERT INTO titles (id, kind, name, tmdb_type, tmdb_id, anilist_id, poster)
               VALUES (1, 'series', 'Starfall', 'tv', 9, 90, '/found.jpg')"""
        )
    web.answers[f"GET {TMDB}/tv/9/images"] = {
        "posters": [
            {
                "file_path": "/plain.jpg",
                "iso_639_1": None,
                "width": 1000,
                "height": 1500,
                "vote_average": 5.2,
            },
            {
                "file_path": "/found.jpg",
                "iso_639_1": "en",
                "width": 680,
                "height": 1000,
                "vote_average": 5.6,
            },
            {
                "file_path": "/ja.jpg",
                "iso_639_1": "ja",
                "width": 1000,
                "height": 1500,
                "vote_average": 4.0,
            },
        ]
    }

    def entry(asked: Asked) -> object:
        return {
            "data": {
                "Media": {
                    "id": 90,
                    "format": "TV",
                    "title": {"romaji": "Starfall"},
                    "coverImage": {"large": COVER, "extraLarge": COVER},
                }
            }
        }

    web.answers[f"POST {ANILIST}"] = entry


def test_the_posters_to_choose_from_put_the_one_it_has_first(client: TestClient, title: None):
    found = client.get("/titles/1/posters").json()

    assert [(each["poster"], each["source"], each["language"]) for each in found["options"]] == [
        ("/found.jpg", "tmdb", "en"),
        ("/plain.jpg", "tmdb", None),
        ("/ja.jpg", "tmdb", "ja"),
        (COVER, "anilist", None),
    ]
    assert found["options"][0]["address"] == "https://image.tmdb.org/t/p/w342/found.jpg"
    assert (found["found"], found["chosen"], found["problem"]) == ("/found.jpg", None, None)


def test_the_owners_choice_is_every_readers_poster_and_survives_a_refresh(
    client: TestClient, conn: sqlite3.Connection, title: None
):
    assert client.put("/titles/1/poster", json={"poster": "/ja.jpg"}).status_code == 204

    row = conn.execute("SELECT poster, poster_choice FROM titles WHERE id = 1").fetchone()
    assert (row["poster"], row["poster_choice"]) == ("/found.jpg", "/ja.jpg")
    refreshed = show(tv_details(9, "Starfall", (2,), first_aired=date(2019, 4, 3)))
    assert refreshed is not None
    save_show(conn, refreshed, TitleKind.SERIES, 90, datetime.now(UTC))
    row = conn.execute("SELECT poster, poster_choice FROM titles WHERE id = 1").fetchone()
    assert (row["poster"], row["poster_choice"]) == ("/poster-9.jpg", "/ja.jpg")
    assert client.get("/titles/1").json()["hasPoster"] is True
    assert client.get("/titles/1/posters").json()["options"][0]["poster"] == "/ja.jpg"
    assert client.put("/titles/1/poster", json={"poster": None}).status_code == 204
    assert conn.execute("SELECT poster_choice FROM titles WHERE id = 1").fetchone()[0] is None


def test_anilists_cover_is_offered_once_whatever_size_the_title_has_of_it(
    client: TestClient, conn: sqlite3.Connection, title: None
):
    with conn:
        conn.execute(
            "UPDATE titles SET poster = ? WHERE id = 1", (COVER.replace("/large/", "/medium/"),)
        )

    options = client.get("/titles/1/posters").json()["options"]

    assert [each["source"] for each in options] == ["anilist", "tmdb", "tmdb", "tmdb"]


def test_only_tmdbs_or_anilists_pictures_are_kept(client: TestClient, title: None):
    answer = client.put("/titles/1/poster", json={"poster": "https://example.com/x.jpg"})

    assert answer.status_code == 400
    assert client.put("/titles/99/poster", json={"poster": "/ja.jpg"}).status_code == 400


def test_the_poster_kura_wrote_next_to_the_show_makes_way(
    conn: sqlite3.Connection, tmp_path: Path, title: None
):
    picture = tmp_path / "Starfall" / "poster.jpg"
    picture.parent.mkdir()
    picture.write_bytes(b"a poster")
    owners = tmp_path / "Starfall" / "fanart.jpg"
    owners.write_bytes(b"kura's background")
    with conn:
        conn.executemany(
            "INSERT INTO artwork_files (path, title_id, size, written_at) VALUES (?, 1, ?, 'then')",
            [(str(picture), 8), (str(owners), 17)],
        )

    assert posters.choose(conn, 1, "/ja.jpg")

    assert not picture.exists()
    assert owners.exists()  # the background isn't the poster
    assert [row[0] for row in conn.execute("SELECT path FROM artwork_files")] == [str(owners)]


def test_offline_the_choice_says_why_tmdbs_are_missing(
    client: TestClient, web: FakeWeb, title: None
):
    web.offline = True

    found = client.get("/titles/1/posters").json()

    assert found["problem"].startswith("TMDB's posters couldn't be asked for now")
    assert [each["poster"] for each in found["options"]] == ["/found.jpg"]
