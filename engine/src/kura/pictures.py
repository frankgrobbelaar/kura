"""The picture across the top of a video's or an episode's details: TMDB's picture from the
episode, else a frame from the video itself, else its show's wide picture (TMDB's background, or
AniList's banner). Each is fetched or taken once, then kept."""

import sqlite3
from pathlib import Path

from kura import artwork, stills
from kura.config import DataPaths
from kura.web import Send


def of_episode(
    conn: sqlite3.Connection,
    paths: DataPaths,
    transport: Send,
    title_id: int,
    season: int,
    number: int,
) -> Path | None:
    """One of a title's episodes, the library's or not: TMDB's picture from it, or its show's.
    None when there's neither, or they can't be fetched now."""
    row = conn.execute(
        "SELECT still FROM episodes WHERE title_id = ? AND season = ? AND number = ?",
        (title_id, season, number),
    ).fetchone()
    if row is None:
        return None
    found = artwork.picture(paths, artwork.still_address(row["still"]), transport)
    return found or _show(conn, paths, transport, title_id)


def of_file(
    conn: sqlite3.Connection,
    paths: DataPaths,
    transport: Send,
    ffmpeg: Path | None,
    file_id: int,
) -> Path | None:
    """A video in the library: TMDB's picture from its episode, a frame from the file, or its
    show's. None when there's none of them."""
    row = conn.execute(
        """SELECT f.path, f.duration, f.problem, f.title_id, e.still FROM files AS f
           LEFT JOIN episodes AS e
             ON e.title_id = f.title_id AND e.season = f.season AND e.number = f.episode
           WHERE f.id = ? AND f.gone_at IS NULL""",
        (file_id,),
    ).fetchone()
    if row is None:
        return None
    found = artwork.picture(paths, artwork.still_address(row["still"]), transport)
    if found is None and row["problem"] is None:
        found = stills.picture(paths, ffmpeg, Path(row["path"]), row["duration"])
    if found is None and row["title_id"] is not None:
        found = _show(conn, paths, transport, row["title_id"])
    return found


def _show(
    conn: sqlite3.Connection, paths: DataPaths, transport: Send, title_id: int
) -> Path | None:
    """A title's wide picture: TMDB's background, or AniList's banner."""
    row = conn.execute("SELECT backdrop FROM titles WHERE id = ?", (title_id,)).fetchone()
    if row is None:
        return None
    return artwork.picture(paths, artwork.background_address(row["backdrop"]), transport)
