import json
import sqlite3
from contextlib import closing
from pathlib import Path

import pytest

from kura import db
from kura.migrations import MIGRATIONS


def test_migrate_brings_a_new_database_to_the_latest_version(tmp_path: Path):
    with closing(db.connect(tmp_path / "kura.db")) as conn:
        assert db.migrate(conn) == len(MIGRATIONS)
        assert db.schema_version(conn) == len(MIGRATIONS)


def test_migrate_is_safe_to_run_again(tmp_path: Path):
    with closing(db.connect(tmp_path / "kura.db")) as conn:
        db.migrate(conn)
        assert db.migrate(conn) == len(MIGRATIONS)


def test_a_database_from_a_newer_kura_is_left_alone(tmp_path: Path):
    with closing(db.connect(tmp_path / "kura.db")) as conn:
        conn.execute(f"PRAGMA user_version = {len(MIGRATIONS) + 1}")

        with pytest.raises(db.NewerDatabaseError):
            db.migrate(conn)

        assert db.schema_version(conn) == len(MIGRATIONS) + 1


def test_a_failing_migration_changes_nothing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    broken = "CREATE TABLE half_done (id INTEGER); THIS IS NOT SQL;"
    monkeypatch.setattr(db, "MIGRATIONS", (*MIGRATIONS, broken))

    with closing(db.connect(tmp_path / "kura.db")) as conn:
        with pytest.raises(sqlite3.OperationalError):
            db.migrate(conn)

        assert db.schema_version(conn) == len(MIGRATIONS)
        tables = {row["name"] for row in conn.execute("SELECT name FROM sqlite_master")}
        assert "settings" in tables
        assert "half_done" not in tables


def test_identification_keeps_every_scan_and_file_from_before(tmp_path: Path):
    with closing(db.connect(tmp_path / "kura.db")) as conn:
        conn.executescript("".join(f"BEGIN;{sql}COMMIT;" for sql in MIGRATIONS[:3]))
        conn.execute("PRAGMA user_version = 3")
        conn.execute("INSERT INTO folders (path, added_at) VALUES ('D:/Anime', '2026-10-11')")
        conn.execute(
            "INSERT INTO files (folder_id, path, size, modified, found_at, seen_at)"
            " VALUES (1, 'D:/Anime/Trigun - 01.mkv', 1, 1, 'then', 'then')"
        )
        conn.execute(
            "INSERT INTO scans (started_at, finished_at, state, stage)"
            " VALUES ('2026-10-11T09:00', '2026-10-11T09:05', 'done', 'done')"
        )
        conn.commit()

        db.migrate(conn)

        scan = conn.execute("SELECT * FROM scans").fetchone()
        assert (scan["state"], scan["stage"], scan["note"]) == ("done", "done", None)
        file = conn.execute("SELECT * FROM files").fetchone()
        assert (file["path"], file["matched"], file["pinned"]) == (
            "D:/Anime/Trigun - 01.mkv",
            None,
            0,
        )
        conn.execute(  # the new stages are allowed
            "INSERT INTO scans (started_at, state, stage)"
            " VALUES ('later', 'running', 'identifying')"
        )


@pytest.mark.parametrize("since", [13, 14])  # Kura identifies better: 14, and again 15
def test_files_waiting_for_a_match_are_looked_up_again(tmp_path: Path, since: int):
    with closing(db.connect(tmp_path / "kura.db")) as conn:
        conn.executescript("".join(f"BEGIN;{sql}COMMIT;" for sql in MIGRATIONS[:since]))
        conn.execute(f"PRAGMA user_version = {since}")
        conn.execute("INSERT INTO folders (path, added_at) VALUES ('D:/Anime', 'then')")
        for name, matched, pinned in [
            ("no guess", "none", 0),
            ("a guess", "unsure", 0),
            ("matched", "sure", 0),
            ("chosen", "sure", 1),
            ("not anime", "ignored", 1),
            ("an extra", "extra", 0),
        ]:
            conn.execute(
                """INSERT INTO files (folder_id, path, size, modified, found_at, seen_at, matched,
                                      pinned, identified_at)
                   VALUES (1, ?, 1, 1, 'then', 'then', ?, ?, 'then')""",
                (name, matched, pinned),
            )
        conn.commit()

        db.migrate(conn)

        again = conn.execute("SELECT path FROM files WHERE identified_at IS NULL").fetchall()
        assert {row["path"] for row in again} == {"no guess", "a guess"}


def test_scans_from_before_kura_counted_changes_say_nothing_of_them(tmp_path: Path):
    with closing(db.connect(tmp_path / "kura.db")) as conn:
        conn.executescript("".join(f"BEGIN;{sql}COMMIT;" for sql in MIGRATIONS[:15]))
        conn.execute("PRAGMA user_version = 15")
        conn.execute("INSERT INTO scans (started_at, state, stage) VALUES ('then', 'done', 'done')")
        conn.commit()

        db.migrate(conn)

        row = conn.execute("SELECT added, gone FROM scans").fetchone()
        assert (row["added"], row["gone"]) == (None, None)


def test_conversions_the_test_play_failed_by_mistake_go_back_in_the_queue(tmp_path: Path):
    # The test play took two frames' times, rounded to one, for damage (2026-10-14): those
    # results played well, so their files are converted again, and none is counted as broken.
    rounded = (
        "The result didn't check out: it didn't play at 21:46 ([null @ 000001fc044723c0] "
        "Application provided invalid, non monotonically increasing dts to muxer in stream 0: "
        "6 >= 6). The original is as it was."
    )
    damaged = "The result didn't check out: it didn't play at 02:22 (Invalid data found)."
    with closing(db.connect(tmp_path / "kura.db")) as conn:
        conn.executescript("".join(f"BEGIN;{sql}COMMIT;" for sql in MIGRATIONS[:17]))
        conn.execute("PRAGMA user_version = 17")
        conn.execute("INSERT INTO folders (path, added_at) VALUES ('D:/Anime', 'then')")
        for file_id, (state, problem, marked) in enumerate(
            [
                ("failed", rounded, False),  # waiting for the owner
                ("skipped", rounded, True),  # the owner marked it broken
                ("failed", damaged, False),  # really damaged: stays as it is
                ("done", None, False),
            ],
            start=1,
        ):
            conn.execute(
                """INSERT INTO files (folder_id, path, size, modified, found_at, seen_at, problem,
                                      marked_at)
                   VALUES (1, ?, 1, 1, 'then', 'then', ?, ?)""",
                (f"S01E0{file_id}.mkv", problem if marked else None, "then" if marked else None),
            )
            conn.execute(
                """INSERT INTO jobs (file_id, method, position, state, added_at, started_at,
                                     finished_at, problem, log)
                   VALUES (?, 'reencode', ?, ?, 'then', 'then', 'then', ?, 'what ffmpeg said')""",
                (file_id, file_id, state, problem),
            )
        conn.commit()

        db.migrate(conn)

        jobs = conn.execute("SELECT state, problem, log, started_at FROM jobs ORDER BY id")
        assert [tuple(row) for row in jobs] == [
            ("queued", None, None, None),
            ("queued", None, None, None),
            ("failed", damaged, "what ffmpeg said", "then"),
            ("done", None, "what ffmpeg said", "then"),
        ]
        files = conn.execute("SELECT problem, marked_at FROM files ORDER BY id")
        assert [tuple(row) for row in files] == [(None, None)] * 4


def test_the_languages_of_videos_read_before_come_from_what_ffprobe_said(tmp_path: Path):
    said = {
        "streams": [
            {"codec_type": "video"},
            {"codec_type": "audio", "tags": {"language": "jpn"}},
            {"codec_type": "audio", "tags": {"language": "und"}},
            {"codec_type": "audio"},
            {"codec_type": "subtitle", "tags": {"language": "ENG"}},
        ]
    }
    with closing(db.connect(tmp_path / "kura.db")) as conn:
        conn.executescript("".join(f"BEGIN;{sql}COMMIT;" for sql in MIGRATIONS[:18]))
        conn.execute("PRAGMA user_version = 18")
        conn.execute("INSERT INTO folders (path, added_at) VALUES ('D:/Anime', 'then')")
        for name, probe in (("read.mkv", json.dumps(said)), ("unread.mkv", None)):
            conn.execute(
                """INSERT INTO files (folder_id, path, size, modified, found_at, seen_at, probe)
                   VALUES (1, ?, 1, 1, 'then', 'then', ?)""",
                (name, probe),
            )
        conn.commit()

        db.migrate(conn)

        rows = conn.execute("SELECT sound, subtitles FROM files ORDER BY id").fetchall()
        assert [json.loads(rows[0][0]), json.loads(rows[0][1])] == [["jpn", "", ""], ["eng"]]
        assert tuple(rows[1]) == (None, None)


def test_subtitles_made_before_know_the_sound_track_they_were_made_from(tmp_path: Path):
    with closing(db.connect(tmp_path / "kura.db")) as conn:
        conn.executescript("".join(f"BEGIN;{sql}COMMIT;" for sql in MIGRATIONS[:21]))
        conn.execute("PRAGMA user_version = 21")
        conn.execute("INSERT INTO folders (path, added_at) VALUES ('D:/Anime', 'then')")
        for file_id in (1, 2, 3):
            conn.execute(
                """INSERT INTO files (folder_id, path, size, modified, found_at, seen_at)
                   VALUES (1, ?, 1, 1, 'then', 'then')""",
                (f"S01E0{file_id}.mkv",),
            )
            conn.execute(
                """INSERT INTO made_subtitles (file_id, name, language, size, modified, made_at)
                   VALUES (?, '.en.srt', 'ja', 1, 1, 'then')""",
                (file_id,),
            )
        for file_id, sound, state, problem, finished in (
            (1, 1, "done", None, "2026-10-15T10:00"),  # made them from its second track
            (1, 0, "failed", "It stopped.", "2026-10-15T11:00"),  # asked again, and failed
            (2, None, "done", None, "2026-10-15T10:00"),  # from its first
        ):
            conn.execute(
                """INSERT INTO jobs (file_id, kind, method, sound, position, state, added_at,
                                     finished_at, problem)
                   VALUES (?, 'subtitles', 'best', ?, 1, ?, 'then', ?, ?)""",
                (file_id, sound, state, finished, problem),
            )
        conn.commit()

        db.migrate(conn)

        made = conn.execute("SELECT file_id, sound FROM made_subtitles ORDER BY file_id")
        assert [tuple(row) for row in made] == [(1, 1), (2, 0), (3, None)]


def test_earlier_tidy_ups_stop_naming_a_media_server(tmp_path: Path):
    with closing(db.connect(tmp_path / "kura.db")) as conn:
        conn.executescript("".join(f"BEGIN;{sql}COMMIT;" for sql in MIGRATIONS[:8]))
        conn.execute("PRAGMA user_version = 8")
        conn.execute(
            "INSERT INTO plans (title, created_at) VALUES (?, 'then')",
            ("Renamed 3 Trigun files for Plex",),
        )
        conn.execute(
            "INSERT INTO changes (plan_id, position, kind, source, target, label, reason, state)"
            " VALUES (1, 0, 'move', 'a.mkv', 'b.mkv', 'Trigun · S01E01', 'Named for Plex', 'done')"
        )
        conn.commit()

        db.migrate(conn)

        assert conn.execute("SELECT title FROM plans").fetchone()[0] == "Renamed 3 Trigun files"
        assert conn.execute("SELECT reason FROM changes").fetchone()[0] == "Named and filed"


def test_every_title_and_entry_is_asked_about_again_for_what_its_about_panel_shows(
    tmp_path: Path,
):
    with closing(db.connect(tmp_path / "kura.db")) as conn:
        conn.executescript("".join(f"BEGIN;{sql}COMMIT;" for sql in MIGRATIONS[:22]))
        conn.execute("PRAGMA user_version = 22")
        conn.execute(
            """INSERT INTO titles (id, kind, name, checked_at)
               VALUES (1, 'series', 'Starfall Academy', '2026-10-17T09:00:00+00:00'),
                      (2, 'series', 'Moonlit Harbour', NULL)"""
        )
        conn.execute(
            """INSERT INTO anilist_entries (id, name, checked_at)
               VALUES (9, 'Starfall Academy', '2026-10-17T09:00:00+00:00')"""
        )
        conn.commit()

        db.migrate(conn)

        titles = conn.execute("SELECT checked_at, overview FROM titles ORDER BY id").fetchall()
        assert [tuple(row) for row in titles] == [("2000-01-01T00:00:00+00:00", None), (None, None)]
        entry = conn.execute("SELECT checked_at, description FROM anilist_entries").fetchone()
        assert tuple(entry) == ("2000-01-01T00:00:00+00:00", None)


def test_every_tv_shows_list_is_asked_for_again_for_its_episodes_pictures(tmp_path: Path):
    with closing(db.connect(tmp_path / "kura.db")) as conn:
        conn.executescript("".join(f"BEGIN;{sql}COMMIT;" for sql in MIGRATIONS[:27]))
        conn.execute("PRAGMA user_version = 27")
        checked = "2026-10-18T09:00:00+00:00"
        conn.execute(
            """INSERT INTO titles (id, kind, name, tmdb_type, tmdb_id, checked_at)
               VALUES (1, 'series', 'Starfall Academy', 'tv', 9, ?),
                      (2, 'movie', 'Comet Night', 'movie', 11, ?),
                      (3, 'ova', 'Lantern Tales', NULL, NULL, ?),
                      (4, 'series', 'Moonlit Harbour', 'tv', 12, NULL)""",
            (checked, checked, checked),
        )
        conn.execute(
            "INSERT INTO episodes (title_id, season, number, name) VALUES (1, 1, 1, 'Arrival')"
        )
        conn.commit()

        db.migrate(conn)

        titles = conn.execute("SELECT checked_at FROM titles ORDER BY id").fetchall()
        assert [row[0] for row in titles] == ["2000-01-01T00:00:00+00:00", checked, checked, None]
        assert conn.execute("SELECT still FROM episodes").fetchone()[0] is None
