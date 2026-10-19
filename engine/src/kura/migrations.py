"""The database schema, as an append-only list of migrations.

Migration N upgrades the database from version N-1 to N; the version lives in
SQLite's `PRAGMA user_version`. Never edit a migration once it has shipped in a
release: add a new one at the end instead.
"""

from typing import Final

MIGRATIONS: Final[tuple[str, ...]] = (
    # 1. Settings: Kura's preferences, one JSON value per key.
    """
    CREATE TABLE settings (
        key   TEXT PRIMARY KEY,
        value TEXT NOT NULL  -- JSON
    ) STRICT;
    """,
    # 2. Plans and their changes: the undo journal for every rename, move and quarantine.
    """
    CREATE TABLE plans (
        id         INTEGER PRIMARY KEY,
        title      TEXT NOT NULL,
        created_at TEXT NOT NULL,
        applied_at TEXT,
        undone_at  TEXT
    ) STRICT;

    CREATE TABLE changes (
        id           INTEGER PRIMARY KEY,
        plan_id      INTEGER NOT NULL REFERENCES plans (id),
        position     INTEGER NOT NULL,
        kind         TEXT NOT NULL CHECK (kind IN ('move', 'quarantine')),
        source       TEXT NOT NULL,
        target       TEXT NOT NULL,
        label        TEXT NOT NULL,
        reason       TEXT NOT NULL,
        state        TEXT NOT NULL DEFAULT 'planned'
                     CHECK (state IN ('planned', 'moving', 'done', 'failed', 'undoing', 'undone')),
        problem      TEXT,
        created_dirs TEXT NOT NULL DEFAULT '[]',  -- JSON: folders this change created
        UNIQUE (plan_id, position)
    ) STRICT;
    """,
    # 3. The library: the folders Kura looks after, every video found in them, and the scans.
    """
    CREATE TABLE folders (
        id       INTEGER PRIMARY KEY,
        path     TEXT NOT NULL UNIQUE COLLATE NOCASE,
        added_at TEXT NOT NULL
    ) STRICT;

    CREATE TABLE files (
        id        INTEGER PRIMARY KEY,
        folder_id INTEGER NOT NULL REFERENCES folders (id) ON DELETE CASCADE,
        path      TEXT NOT NULL UNIQUE COLLATE NOCASE,
        size      INTEGER NOT NULL,
        modified  INTEGER NOT NULL,  -- nanoseconds since 1970, as Windows reports it
        found_at  TEXT NOT NULL,
        seen_at   TEXT NOT NULL,     -- the last scan that found it
        gone_at   TEXT,              -- a later scan didn't find it
        probed_at TEXT,              -- when ffprobe read it; NULL while it's still to read
        probe     TEXT,              -- ffprobe's JSON report
        problem   TEXT,              -- why it couldn't be read, in words
        duration  REAL,              -- seconds
        width     INTEGER,
        height    INTEGER,
        codec     TEXT               -- the picture's codec, such as hevc
    ) STRICT;
    CREATE INDEX files_by_folder ON files (folder_id);

    CREATE TABLE scans (
        id          INTEGER PRIMARY KEY,
        started_at  TEXT NOT NULL,
        finished_at TEXT,
        state       TEXT NOT NULL CHECK (state IN ('running', 'paused', 'done', 'failed')),
        stage       TEXT NOT NULL CHECK (stage IN ('finding', 'reading', 'done')),
        problem     TEXT
    ) STRICT;
    """,
    # 4. Identification: the titles in the library (TMDB's shows and films, or AniList's entries
    #    without a TMDB key), their episode lists, and what each video is. Scans gain the stages
    #    after reading; SQLite can't change a CHECK, so that table is made again.
    """
    CREATE TABLE titles (
        id         INTEGER PRIMARY KEY,
        kind       TEXT NOT NULL CHECK (kind IN ('series', 'movie', 'ova', 'special')),
        name       TEXT NOT NULL,
        year       INTEGER,
        released   TEXT,     -- first aired, or the film's release: lists sort by it
        tmdb_type  TEXT CHECK (tmdb_type IN ('tv', 'movie')),
        tmdb_id    INTEGER,
        anilist_id INTEGER,  -- the AniList entry it was found by
        airing     INTEGER NOT NULL DEFAULT 0 CHECK (airing IN (0, 1)),
        poster     TEXT,     -- TMDB's image path, or AniList's cover address
        checked_at TEXT,     -- when its episode list was last asked for
        UNIQUE (tmdb_type, tmdb_id)
    ) STRICT;
    CREATE UNIQUE INDEX titles_by_anilist ON titles (anilist_id) WHERE tmdb_id IS NULL;

    CREATE TABLE episodes (
        title_id INTEGER NOT NULL REFERENCES titles (id) ON DELETE CASCADE,
        season   INTEGER NOT NULL,  -- 0 holds the specials
        number   INTEGER NOT NULL,
        name     TEXT,
        aired    TEXT,
        minutes  INTEGER,
        PRIMARY KEY (title_id, season, number)
    ) STRICT, WITHOUT ROWID;

    ALTER TABLE files ADD COLUMN title_id INTEGER REFERENCES titles (id) ON DELETE SET NULL;
    ALTER TABLE files ADD COLUMN anilist_id INTEGER;   -- the AniList entry it matched
    ALTER TABLE files ADD COLUMN season INTEGER;       -- where it sits in its title, numbered
    ALTER TABLE files ADD COLUMN episode INTEGER;      -- as TMDB numbers it; NULL for a film
    ALTER TABLE files ADD COLUMN episode_end INTEGER;  -- the last episode, when it holds several
    ALTER TABLE files ADD COLUMN matched TEXT
        CHECK (matched IN ('sure', 'unsure', 'none', 'extra', 'ignored'));
    ALTER TABLE files ADD COLUMN confidence INTEGER;
    ALTER TABLE files ADD COLUMN guesses TEXT;         -- JSON: the best guesses, for review
    ALTER TABLE files ADD COLUMN pinned INTEGER NOT NULL DEFAULT 0 CHECK (pinned IN (0, 1));
    ALTER TABLE files ADD COLUMN identified_at TEXT;   -- NULL while it's still to identify
    CREATE INDEX files_by_title ON files (title_id);

    CREATE TABLE scans_next (
        id          INTEGER PRIMARY KEY,
        started_at  TEXT NOT NULL,
        finished_at TEXT,
        state       TEXT NOT NULL CHECK (state IN ('running', 'paused', 'done', 'failed')),
        stage       TEXT NOT NULL CHECK (
                        stage IN ('finding', 'reading', 'identifying', 'checking', 'done')),
        problem     TEXT,
        note        TEXT     -- what the scan couldn't do, though it finished
    ) STRICT;
    INSERT INTO scans_next (id, started_at, finished_at, state, stage, problem)
        SELECT id, started_at, finished_at, state, stage, problem FROM scans;
    DROP TABLE scans;
    ALTER TABLE scans_next RENAME TO scans;
    """,
    # 5. How AniList relates the entries the library has to others (sequel, prequel, film,
    #    side story...): what ties a franchise together.
    """
    CREATE TABLE anilist_links (
        anilist_id INTEGER NOT NULL,  -- an entry Kura matched files to
        related_id INTEGER NOT NULL,  -- an entry AniList relates it to
        relation   TEXT NOT NULL,     -- SEQUEL, PREQUEL, PARENT, SIDE_STORY, ALTERNATIVE, ...
        PRIMARY KEY (anilist_id, related_id)
    ) STRICT, WITHOUT ROWID;
    """,
    # 6. The conversion queue: each file waiting, converting or converted, in the owner's order,
    #    with what it takes to put the original back. A plan says whether it tidied or converted.
    """
    CREATE TABLE jobs (
        id              INTEGER PRIMARY KEY,
        file_id         INTEGER NOT NULL REFERENCES files (id) ON DELETE CASCADE,
        method          TEXT NOT NULL CHECK (method IN ('remux', 'reencode', 'fast', 'best')),
        position        INTEGER NOT NULL,  -- the order the queue takes them in
        state           TEXT NOT NULL DEFAULT 'queued' CHECK (
                            state IN ('queued', 'running', 'replacing', 'done', 'failed',
                                      'skipped', 'restored')),
        added_at        TEXT NOT NULL,
        started_at      TEXT,
        finished_at     TEXT,
        problem         TEXT,              -- why it failed, in words
        plan_id         INTEGER REFERENCES plans (id),  -- the original set aside, the result put
                                                        -- in its place
        source_size     INTEGER,           -- the original as it was, to put it back
        source_modified INTEGER,
        source_probe    TEXT,
        output_size     INTEGER
    ) STRICT;
    CREATE INDEX jobs_by_state ON jobs (state, position);

    ALTER TABLE plans ADD COLUMN kind TEXT NOT NULL DEFAULT 'tidy'
        CHECK (kind IN ('tidy', 'convert'));
    """,
    # 7. The result a conversion made, as ffprobe read it: History says what each file became,
    #    even once its original is back.
    """
    ALTER TABLE jobs ADD COLUMN output_probe TEXT;
    """,
    # 8. When what a change set aside was cleared out of quarantine: after that it can't come back.
    """
    ALTER TABLE changes ADD COLUMN cleared_at TEXT;
    """,
    # 9. Kura's words never name a media server (the owner, 2026-10-11): what earlier tidy-ups
    #    said is put the way it says it now.
    """
    UPDATE plans SET title = REPLACE(title, ' for Plex', '') WHERE title LIKE '% for Plex';
    UPDATE changes SET reason = REPLACE(reason, 'Named for Plex', 'Named and filed')
        WHERE reason LIKE 'Named for Plex%';
    """,
    # 10. A title's wide background picture, and the poster and background files Kura wrote next
    #     to a show for media servers: only those, and only unchanged, are Kura's to take away.
    """
    ALTER TABLE titles ADD COLUMN backdrop TEXT;  -- TMDB's image path, or AniList's banner address

    CREATE TABLE artwork_files (
        path       TEXT PRIMARY KEY,  -- poster.jpg or fanart.jpg next to a title's videos
        title_id   INTEGER NOT NULL REFERENCES titles (id) ON DELETE CASCADE,
        size       INTEGER NOT NULL,  -- as Kura wrote it
        written_at TEXT NOT NULL
    ) STRICT;
    """,
    # 11. A converted file whose original another app had open (a player playing it): the result
    #     waits beside the original, checked (`output_probe` describes it), and Kura tries again
    #     to put it in place from this time.
    """
    ALTER TABLE jobs ADD COLUMN retry_at TEXT;
    """,
    # 12. What ffmpeg said when a conversion failed, for "Copy full log".
    """
    ALTER TABLE jobs ADD COLUMN log TEXT;
    """,
    # 13. When the owner marked a file broken: a scan leaves it so till the file changes.
    """
    ALTER TABLE files ADD COLUMN marked_at TEXT;
    """,
    # 14. Kura finds numbered films and specials by their own names now, and a series AniList
    #     writes otherwise ("Dragonball GT"): the files waiting for a match are looked up again
    #     by the next scan. The owner's own choices stay as they are.
    """
    UPDATE files SET identified_at = NULL
        WHERE matched IN ('none', 'unsure') AND pinned = 0;
    """,
    # 15. Names AniList can't find are searched on TMDB too, a film named with its series'
    #     initials is found, and a series' special its show's list doesn't name is looked up by
    #     its own name: the files waiting for a match are looked up again by the next scan.
    """
    UPDATE files SET identified_at = NULL
        WHERE matched IN ('none', 'unsure') AND pinned = 0;
    """,
    # 16. What each scan changed: videos it found new, and videos gone since the scan before.
    #     Earlier scans don't say (NULL).
    """
    ALTER TABLE scans ADD COLUMN added INTEGER;
    ALTER TABLE scans ADD COLUMN gone INTEGER;
    """,
    # 17. The rest of each franchise (kura/franchises.py): what AniList says of every entry tied
    #     to the library's titles by story, the library's or not. Their links join
    #     anilist_links, which then holds those of entries the library lacks too.
    """
    CREATE TABLE anilist_entries (
        id         INTEGER PRIMARY KEY,  -- AniList's number for it
        name       TEXT,     -- NULL once AniList no longer has it
        names      TEXT,     -- JSON: every name it goes by
        format     TEXT,     -- TV, MOVIE, OVA, SPECIAL, ONA, MUSIC, ...
        status     TEXT,     -- FINISHED, RELEASING, NOT_YET_RELEASED, CANCELLED or HIATUS
        started    TEXT,
        episodes   INTEGER,
        cover      TEXT,     -- the cover's web address
        checked_at TEXT NOT NULL  -- when AniList was last asked about it
    ) STRICT;
    """,
    # 18. The test play took two frames' times, rounded to one, for damage (2026-10-14), though
    #     those results played well: their files go back in the queue where they were, and one
    #     the owner marked broken for it isn't counted as broken.
    """
    UPDATE files SET problem = NULL, marked_at = NULL
        WHERE problem LIKE '%non monotonically increasing dts%';
    UPDATE jobs SET state = 'queued', problem = NULL, log = NULL, started_at = NULL,
                    finished_at = NULL
        WHERE state IN ('failed', 'skipped')
          AND problem LIKE '%non monotonically increasing dts%';
    """,
    # 19. The languages each video can be heard and read in: its sound tracks' and its subtitle
    #     tracks', as ffprobe's report on it names them ("jpn"; "" when one doesn't say), read
    #     from that report for the videos read already.
    """
    ALTER TABLE files ADD COLUMN sound TEXT;      -- JSON: each sound track's language, in order
    ALTER TABLE files ADD COLUMN subtitles TEXT;  -- JSON: each subtitle track's, the same way
    UPDATE files SET
        sound = (
            SELECT json_group_array(
                COALESCE(NULLIF(lower(json_extract(s.value, '$.tags.language')), 'und'), ''))
            FROM json_each(files.probe, '$.streams') AS s
            WHERE json_extract(s.value, '$.codec_type') = 'audio'),
        subtitles = (
            SELECT json_group_array(
                COALESCE(NULLIF(lower(json_extract(s.value, '$.tags.language')), 'und'), ''))
            FROM json_each(files.probe, '$.streams') AS s
            WHERE json_extract(s.value, '$.codec_type') = 'subtitle')
        WHERE probe IS NOT NULL;
    """,
    # 20. English subtitles Kura makes from a video's sound (kura/subtitles.py). They wait in the
    #     queue with the conversions, as jobs of their own kind: `method` is the quality ('best'
    #     or 'fast'), `sound` the track they're made from (from 0). The owner asks for them a
    #     batch at a time, which History shows and can take away again. The files Kura wrote are
    #     its own while they're there as it wrote them, their size and time unchanged: `name`
    #     follows the video's ("Episode 1" + ".en.srt").
    """
    CREATE TABLE subtitle_batches (
        id       INTEGER PRIMARY KEY,
        title    TEXT NOT NULL,  -- what they're for: "Starfall Academy · Season 1"
        quality  TEXT NOT NULL CHECK (quality IN ('best', 'fast')),
        language TEXT NOT NULL,  -- the sound they're made from: "jpn"
        added_at TEXT NOT NULL
    ) STRICT;

    -- 'merge' is taken now for English from another copy, which comes next: a check can't
    -- change without the table being made anew.
    ALTER TABLE jobs ADD COLUMN kind TEXT NOT NULL DEFAULT 'convert'
        CHECK (kind IN ('convert', 'subtitles', 'merge'));
    ALTER TABLE jobs ADD COLUMN sound INTEGER;
    ALTER TABLE jobs ADD COLUMN batch_id INTEGER
        REFERENCES subtitle_batches (id) ON DELETE SET NULL;

    CREATE TABLE made_subtitles (
        file_id  INTEGER PRIMARY KEY REFERENCES files (id) ON DELETE CASCADE,
        name     TEXT NOT NULL,     -- after the video's own name: ".en.srt"
        batch_id INTEGER REFERENCES subtitle_batches (id) ON DELETE SET NULL,
        language TEXT NOT NULL,     -- what Whisper heard: "ja"
        size     INTEGER NOT NULL,  -- as Kura wrote them, in bytes
        modified INTEGER NOT NULL,  -- and when, in nanoseconds: an edit changes it
        made_at  TEXT NOT NULL
    ) STRICT;
    """,
    # 21. English from another copy (kura/merge.py): a job of kind 'merge' adds the English sound
    #     and subtitles another copy of the same episode has (`other_id`) to the file kept, and
    #     sets that copy aside with the kept file's original once the result is in place.
    """
    ALTER TABLE jobs ADD COLUMN other_id INTEGER REFERENCES files (id) ON DELETE SET NULL;
    """,
    # 22. The sound track Kura made a video's English subtitles from (from 0), so a track that
    #     doesn't say its language shows the one Whisper heard in it. Filled from the job that
    #     made them, which the queue keeps.
    """
    ALTER TABLE made_subtitles ADD COLUMN sound INTEGER;
    UPDATE made_subtitles SET sound = (
        SELECT COALESCE(j.sound, 0) FROM jobs AS j
        WHERE j.file_id = made_subtitles.file_id AND j.kind = 'subtitles'
          AND j.state = 'done' AND j.problem IS NULL
        ORDER BY j.finished_at DESC, j.id DESC LIMIT 1);
    """,
    # 23. What TMDB and AniList say of each title and episode, for a title's About panel and an
    #     episode's details: its synopsis, genres, studio, where it stands, when it last aired
    #     and how long an episode lasts. Every title's list, and every AniList entry, is asked
    #     for again soon, so what's known fills in.
    """
    ALTER TABLE titles ADD COLUMN overview TEXT;   -- its synopsis
    ALTER TABLE titles ADD COLUMN genres TEXT;     -- JSON: its genres, as TMDB names them
    ALTER TABLE titles ADD COLUMN studio TEXT;     -- the first company TMDB names for it
    ALTER TABLE titles ADD COLUMN status TEXT
        CHECK (status IN ('finished', 'airing', 'coming', 'cancelled', 'paused'));
    ALTER TABLE titles ADD COLUMN ended TEXT;      -- its latest episode so far
    ALTER TABLE titles ADD COLUMN minutes INTEGER; -- an episode's usual length, or the film's
    ALTER TABLE episodes ADD COLUMN overview TEXT; -- what happens in it
    ALTER TABLE anilist_entries ADD COLUMN description TEXT;  -- its synopsis, as plain text
    ALTER TABLE anilist_entries ADD COLUMN genres TEXT;       -- JSON
    ALTER TABLE anilist_entries ADD COLUMN studio TEXT;       -- its main animation studio
    ALTER TABLE anilist_entries ADD COLUMN ended TEXT;
    ALTER TABLE anilist_entries ADD COLUMN minutes INTEGER;
    UPDATE titles SET checked_at = '2000-01-01T00:00:00+00:00' WHERE checked_at IS NOT NULL;
    UPDATE anilist_entries SET checked_at = '2000-01-01T00:00:00+00:00';
    """,
    # 24. What the owner has watched, and where each video stopped (kura/watched.py): Play picks
    #     a video up there, and Home's "Continue watching" goes on from the latest played.
    """
    CREATE TABLE watched (
        file_id    INTEGER PRIMARY KEY REFERENCES files (id) ON DELETE CASCADE,
        position   REAL NOT NULL,  -- seconds in, where it last stopped
        duration   REAL,           -- how long it plays, as the player had it
        played_at  TEXT,           -- when it last played (UTC); None: out of Continue watching
        watched_at TEXT            -- seen to its last tenth, or marked watched
    ) STRICT;
    """,
    # 25. The episodes the owner was told are out today (kura/coming.py), so each is told once.
    """
    CREATE TABLE aired_told (
        title_id INTEGER NOT NULL REFERENCES titles (id) ON DELETE CASCADE,
        season   INTEGER NOT NULL,
        number   INTEGER NOT NULL,
        told_at  TEXT NOT NULL,
        PRIMARY KEY (title_id, season, number)
    ) STRICT;
    """,
    # 26. The health check (kura/checkup.py): when each video was last test-played overnight,
    #     and what went wrong if it didn't play, for the owner to look at.
    """
    ALTER TABLE files ADD COLUMN health_at TEXT;
    ALTER TABLE files ADD COLUMN health_problem TEXT;
    """,
    # 27. The poster the owner chose for a title (kura/posters.py), over the one TMDB or AniList
    #     gives it: a TMDB image path, or an AniList cover's address.
    """
    ALTER TABLE titles ADD COLUMN poster_choice TEXT;
    """,
    # 28. A picture from each episode, when TMDB has one, across the top of its details (a path on
    #     TMDB's image server). Every TV show's list is asked for again soon, so they fill in.
    """
    ALTER TABLE episodes ADD COLUMN still TEXT;
    UPDATE titles SET checked_at = '2000-01-01T00:00:00+00:00'
        WHERE checked_at IS NOT NULL AND tmdb_type = 'tv';
    """,
)
