"""The health check: every video test-played overnight, a few at a time, the ones that didn't play
listed for the owner, and nothing changed till they say."""

import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from kura import checkup
from kura.care import Care
from kura.config import DataPaths
from kura.scan import Scanner
from kura.tools import Tools
from tests.converting import programs, report
from tests.shelf import library

NIGHT = datetime(2026, 10, 18, 1, 30).astimezone()
DAY = datetime(2026, 10, 18, 14, 0).astimezone()


@pytest.fixture
def shelf(conn: sqlite3.Connection, tmp_path: Path) -> Path:
    """Three made-up episodes, read."""
    root = tmp_path / "Anime"
    names = [f"Starfall (2019)/Season 01/Starfall (2019) - S01E0{n}.mkv" for n in (1, 2, 3)]
    library(conn, root, names)
    with conn:
        conn.execute("INSERT INTO titles (id, kind, name) VALUES (1, 'series', 'Starfall')")
        conn.execute("UPDATE files SET title_id = 1, season = 1, episode = id")
    return root


def care(paths: DataPaths, at: list[datetime], told: list[tuple[str, str]]) -> Care:
    return Care(
        paths,
        Scanner(paths, Tools(paths, items=())).hold,
        now=lambda: at[0],
        programs=lambda: programs(report(1920, 1080)),
        notify=lambda title, body, link=None: told.append((title, body)),
    )


def test_at_night_every_video_is_played_and_kept_as_played(
    paths: DataPaths, conn: sqlite3.Connection, shelf: Path
):
    told: list[tuple[str, str]] = []

    assert care(paths, [NIGHT], told).check_health() == 0

    found = checkup.checkup(conn, NIGHT)
    assert (found.on, found.checked, found.total, found.unplayed) == (True, 3, 3, [])
    assert told == []


def test_nothing_is_played_by_day_or_when_the_owner_turned_it_off(
    paths: DataPaths, conn: sqlite3.Connection, shelf: Path
):
    care(paths, [DAY], []).check_health()
    assert checkup.checkup(conn, DAY).checked == 0

    with conn:
        conn.execute("INSERT INTO settings (key, value) VALUES ('health_check', 'false')")
    care(paths, [NIGHT], []).check_health()
    assert checkup.checkup(conn, NIGHT).checked == 0


def test_a_video_that_doesnt_play_is_listed_and_told_of_once(
    paths: DataPaths, conn: sqlite3.Connection, shelf: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv("KURA_FAKE_FAIL", "play")
    told: list[tuple[str, str]] = []
    looks = care(paths, [NIGHT], told)

    assert looks.check_health() == 3
    assert looks.check_health() == 0  # checked tonight already

    found = checkup.checkup(conn, NIGHT)
    assert [each.file_id for each in found.unplayed] == [1, 2, 3]
    assert found.unplayed[0].problem.startswith("It didn't play at ")
    assert told == [
        ("3 videos didn't play", "Tonight's health check found them: Home lists what didn't play.")
    ]
    # Nothing changed: the videos aren't broken till the owner says.
    assert conn.execute("SELECT COUNT(*) FROM files WHERE problem IS NOT NULL").fetchone()[0] == 0


def test_a_month_on_a_video_is_played_again(
    paths: DataPaths, conn: sqlite3.Connection, shelf: Path
):
    care(paths, [NIGHT], []).check_health()
    later = NIGHT + timedelta(days=31)

    assert len(checkup.due(conn, later, 10)) == 3
    assert len(checkup.due(conn, NIGHT + timedelta(days=2), 10)) == 0


def test_a_video_whose_drive_isnt_connected_waits(
    paths: DataPaths, conn: sqlite3.Connection, shelf: Path
):
    with conn:
        conn.execute("UPDATE files SET path = 'Z:\\\\Away\\\\S01E01.mkv' WHERE id = 1")

    care(paths, [NIGHT], []).check_health()

    found = checkup.checkup(conn, NIGHT)
    assert (found.checked, found.unplayed) == (2, [])


def test_the_owner_says_whats_broken_and_what_plays_after_all(
    client: TestClient, conn: sqlite3.Connection, shelf: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv("KURA_FAKE_FAIL", "play")
    with conn:
        conn.execute(
            "UPDATE files SET health_at = ?, health_problem = 'It didn''t play at 12:05 (bad)'",
            (NIGHT.isoformat(),),
        )

    listed = client.get("/checkup").json()
    assert [each["fileId"] for each in listed["unplayed"]] == [1, 2, 3]
    assert listed["unplayed"][0]["title"] == "Starfall"

    assert client.post("/files/1/broken").status_code == 204
    assert client.post("/files/2/plays").status_code == 204
    assert client.post("/files/1/broken").status_code == 404  # broken now, off the list
    rows = conn.execute("SELECT id, problem, health_problem FROM files ORDER BY id").fetchall()
    assert [(row["problem"], row["health_problem"]) for row in rows] == [
        ("It didn't play at 12:05 (bad)", None),
        (None, None),
        (None, "It didn't play at 12:05 (bad)"),
    ]
    assert [each["fileId"] for each in client.get("/checkup").json()["unplayed"]] == [3]
    assert client.post("/checkup/again").status_code == 204
    assert client.get("/checkup").json()["checked"] == 0


def test_a_video_is_played_again_now_when_asked(
    client: TestClient, conn: sqlite3.Connection, shelf: Path, monkeypatch: pytest.MonkeyPatch
):
    client.app.state.programs = lambda: programs(report(1920, 1080))  # type: ignore[attr-defined]

    assert client.post("/files/1/check").json() == {"problem": None}
    monkeypatch.setenv("KURA_FAKE_FAIL", "play")
    assert client.post("/files/1/check").json()["problem"].startswith("It didn't play at")
    assert client.post("/files/99/check").status_code == 404
