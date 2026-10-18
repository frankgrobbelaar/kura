"""A video in full through the API: what it holds, where it is, the episode it is, and what
converting it does; and an episode's own details, the library's or not."""

import sqlite3
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from tests.shelf import library


@pytest.fixture
def shelf(conn: sqlite3.Connection, tmp_path: Path) -> Path:
    """Two episodes of a made-up series, read: the first with English and German subtitle files
    beside it, the English ones Kura's."""
    root = tmp_path / "Anime"
    names = [f"Starfall (2019)/Season 01/Starfall (2019) - S01E0{n}.mkv" for n in (1, 2)]
    library(conn, root, names)
    season = root / "Starfall (2019)" / "Season 01"
    english = season / "Starfall (2019) - S01E01.en.srt"
    english.write_text("1\n00:00:01,000 --> 00:00:02,000\nOver here!\n", "utf-8")
    (season / "Starfall (2019) - S01E01.de.srt").write_text("Hallo", "utf-8")
    written = english.stat()
    with conn:
        conn.execute("INSERT INTO titles (id, kind, name) VALUES (1, 'series', 'Starfall')")
        conn.execute("UPDATE files SET title_id = 1, season = 1, episode = id, matched = 'sure'")
        conn.execute(
            """INSERT INTO episodes (title_id, season, number, name, aired, overview, minutes)
               VALUES (1, 1, 1, 'The First Night', '2019-04-03', 'Mira arrives.', 24),
                      (1, 1, 2, 'Lanterns Over the Lake', '2019-04-10', NULL, 24),
                      (1, 1, 3, 'The Café at Dawn', '2019-04-17', 'A quiet morning.', 23)"""
        )
        conn.execute(
            """INSERT INTO made_subtitles (file_id, name, language, size, modified, made_at, sound)
               VALUES (1, '.en.srt', 'ja', ?, ?, 'then', 0)""",
            (written.st_size, written.st_mtime_ns),
        )
    return season


def test_a_video_says_what_it_holds_and_what_converting_it_does(client: TestClient, shelf: Path):
    found = client.get("/files/1").json()

    assert found["path"] == str(shelf / "Starfall (2019) - S01E01.mkv")
    assert (found["title"], found["season"], found["episode"]) == ("Starfall", 1, 1)
    assert (found["episodeName"], found["aired"], found["overview"]) == (
        "The First Night",
        "2019-04-03",
        "Mira arrives.",
    )
    assert found["picture"] == {
        "codec": "hevc",
        "width": 720,
        "height": 540,
        "bitDepth": 10,
        "frameRate": pytest.approx(23.976, abs=0.001),
    }
    assert found["sound"] == [{"language": "jpn", "codec": "aac", "channels": 2, "lossless": False}]
    assert [(s["language"], s["beside"], s["made"]) for s in found["subtitles"]] == [
        ("de", True, False),
        ("en", True, True),
    ]
    assert found["duration"] == pytest.approx(1440)
    assert found["converted"] is False
    converting = found["converting"]
    assert (converting["state"], converting["method"]) == ("to convert", "best")
    assert converting["reasons"][0].startswith("SD 540p")


def test_a_video_kura_doesnt_have_is_404(client: TestClient, shelf: Path):
    assert client.get("/files/99").status_code == 404


def test_an_episode_says_what_happens_in_it_and_where_its_video_is(client: TestClient, shelf: Path):
    held = client.get("/titles/1/episodes/1/2").json()
    lacking = client.get("/titles/1/episodes/1/3").json()

    assert (held["name"], held["overview"], held["fileId"]) == (
        "Lanterns Over the Lake",
        None,
        2,
    )
    assert (lacking["name"], lacking["overview"], lacking["minutes"], lacking["fileId"]) == (
        "The Café at Dawn",
        "A quiet morning.",
        23,
        None,
    )
    assert client.get("/titles/1/episodes/2/1").status_code == 404
