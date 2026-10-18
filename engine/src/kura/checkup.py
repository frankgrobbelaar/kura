"""The health check: every video test-played overnight, a few at a time, the way each converted
result is (kura/convert.py's test play, at three points), so a file damaged since Kura read it
shows before it's wanted. A video is played again a month on, or once it changes; one Kura made
was played as it was made. What didn't play waits for the owner: nothing changes till they say.
"""

import logging
import sqlite3
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

from kura.convert import ConvertError, Programs, test_play
from kura.queue import NIGHT

log = logging.getLogger(__name__)

AGAIN = timedelta(days=30)  # how long a video's check holds before it's played again
SETTING = "health_check"  # in settings: whether the check runs, on unless turned off


def at_night(moment: datetime) -> bool:
    """The night the check plays videos in: the one the queue's nights-only schedule uses."""
    start, end = NIGHT
    return moment.time() >= start or moment.time() < end


@dataclass(frozen=True)
class Unplayed:
    """A video the check couldn't play, and where it stopped."""

    file_id: int
    path: str
    title_id: int | None
    title: str | None
    season: int | None
    episode: int | None
    episode_end: int | None
    problem: str
    at: str | None  # when it was checked; None: it's to be played again


@dataclass(frozen=True)
class Checkup:
    on: bool
    checked: int  # of the library's videos that play, checked within the month
    total: int
    unplayed: list[Unplayed]


def is_on(conn: sqlite3.Connection) -> bool:
    row = conn.execute("SELECT value FROM settings WHERE key = ?", (SETTING,)).fetchone()
    return row is None or row["value"] != "false"


def due(conn: sqlite3.Connection, now: datetime, limit: int) -> list[sqlite3.Row]:
    """The videos to play next: never checked first, then the longest since. A video that
    couldn't be read, or that Kura has marked broken, is broken already: it isn't played."""
    return conn.execute(
        """SELECT id, path, duration, health_problem FROM files
           WHERE gone_at IS NULL AND probe IS NOT NULL AND problem IS NULL
             AND (health_at IS NULL OR health_at < ?)
           ORDER BY health_at IS NOT NULL, health_at, id LIMIT ?""",
        ((now - AGAIN).isoformat(), limit),
    ).fetchall()


def check(conn: sqlite3.Connection, programs: Programs, row: sqlite3.Row, now: datetime) -> bool:
    """Test-plays one video and keeps what it found. False when it couldn't be played now: its
    drive isn't connected, or it's gone, which a scan tells. True when it was played, well or
    not."""
    path = Path(row["path"])
    if not path.is_file():
        return False
    try:
        problems = test_play(programs, path, row["duration"] or 0.0)
    except ConvertError as error:  # ffmpeg hung on it
        problems = [str(error)]
    except OSError as error:
        log.info("Kura couldn't test-play %s: %s", path, error)
        return False
    with conn:
        conn.execute(
            "UPDATE files SET health_at = ?, health_problem = ? WHERE id = ?",
            (now.isoformat(), _sentence(problems[0]) if problems else None, row["id"]),
        )
    return True


def night(
    conn: sqlite3.Connection,
    programs: Programs,
    now: Callable[[], datetime],
    *,
    until: datetime,
    stop: Callable[[], bool],
) -> list[int]:
    """Test-plays the videos that are due till `until`, or till `stop` says. Returns the ones
    that didn't play that played before (or were never checked)."""
    found: list[int] = []
    tried: set[int] = set()
    while now() < until and not stop():
        rows = [row for row in due(conn, now(), 20) if row["id"] not in tried]
        if not rows:
            break
        for row in rows:
            if now() >= until or stop():
                break
            tried.add(row["id"])
            if check(conn, programs, row, now()) and row["health_problem"] is None:
                after = conn.execute(
                    "SELECT health_problem FROM files WHERE id = ?", (row["id"],)
                ).fetchone()
                if after["health_problem"] is not None:
                    found.append(row["id"])
    return found


def checkup(conn: sqlite3.Connection, now: datetime) -> Checkup:
    """How the check stands: how many of the videos it plays were checked within the month, and
    the ones that didn't play."""
    counts = conn.execute(
        """SELECT COUNT(*) AS total, COUNT(CASE WHEN health_at >= ? THEN 1 END) AS checked
           FROM files WHERE gone_at IS NULL AND probe IS NOT NULL AND problem IS NULL""",
        ((now - AGAIN).isoformat(),),
    ).fetchone()
    rows = conn.execute(
        """SELECT f.id, f.path, f.title_id, t.name AS title, f.season, f.episode, f.episode_end,
                  f.health_problem, f.health_at
           FROM files AS f LEFT JOIN titles AS t ON t.id = f.title_id
           WHERE f.gone_at IS NULL AND f.problem IS NULL AND f.health_problem IS NOT NULL
           ORDER BY t.name, f.season, f.episode, f.path"""
    ).fetchall()
    return Checkup(
        on=is_on(conn),
        checked=counts["checked"],
        total=counts["total"],
        unplayed=[
            Unplayed(
                file_id=row["id"],
                path=row["path"],
                title_id=row["title_id"],
                title=row["title"],
                season=row["season"],
                episode=row["episode"],
                episode_end=row["episode_end"],
                problem=row["health_problem"],
                at=row["health_at"],
            )
            for row in rows
        ],
    )


def again(conn: sqlite3.Connection) -> None:
    """Every video is played again, from the next night."""
    with conn:
        conn.execute("UPDATE files SET health_at = NULL")


def plays_after_all(conn: sqlite3.Connection, file_id: int, now: datetime) -> None:
    """The owner played it and it's fine: it's taken off the list, till next month's check."""
    with conn:
        conn.execute(
            "UPDATE files SET health_problem = NULL, health_at = ? WHERE id = ?",
            (now.isoformat(), file_id),
        )


def mark_broken(conn: sqlite3.Connection, file_id: int, now: datetime) -> bool:
    """The owner says it's broken: it's a broken file from now on, as one that couldn't be read
    is, what the check found saying why. False when it isn't on the list."""
    with conn:
        done = conn.execute(
            """UPDATE files SET problem = health_problem, marked_at = ?, health_problem = NULL
               WHERE id = ? AND health_problem IS NOT NULL""",
            (now.isoformat(), file_id),
        )
    return done.rowcount > 0


def _sentence(problem: str) -> str:
    """ "It didn't play at 12:05 (…)": what the test play said, as a sentence of its own."""
    return problem[:1].upper() + problem[1:]
