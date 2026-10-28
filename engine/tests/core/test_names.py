"""Reading file names. Most examples come straight from the design boards."""

import subprocess
import sys
from pathlib import PureWindowsPath
from typing import Any

import pytest

from kura.core.names import Kind, ParsedName, film_part, parse_name


def parsed(path: str) -> ParsedName:
    return parse_name(PureWindowsPath(path))


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        (
            r"D:\Anime\Downloads\[Group] DBZ - 001 [480p].mkv",
            {"title": "DBZ", "episode": 1, "group": "Group", "height": 480, "folder_title": None},
        ),
        (
            r"D:\Anime\Downloads\[Hi10] Cowboy_Bebop_-_01_(BD_720p).mkv",
            {"title": "Cowboy Bebop", "episode": 1, "height": 720, "group": None},
        ),
        (r"D:\Anime\Downloads\Death Note 01.avi", {"title": "Death Note", "episode": 1}),
        (
            r"D:\Anime\Downloads\[DB] Death_Note_07 (720p).mkv",
            {"title": "Death Note", "episode": 7, "group": "DB", "height": 720},
        ),
        (r"D:\Anime\Downloads\trigun_03.mp4", {"title": "trigun", "episode": 3}),
        (
            r"D:\Anime\[SubsPlease] Frieren - 01 (1080p) [ABCD1234].mkv",
            {"title": "Frieren", "episode": 1, "group": "SubsPlease", "height": 1080},
        ),
        (
            r"D:\Anime\[Erai-raws] Dragon Ball Daima - 20 [1080p][Multiple Subtitle].mkv",
            {"title": "Dragon Ball Daima", "episode": 20, "group": "Erai-raws"},
        ),
        (
            r"D:\Anime\[Coalgirls]_Neon_Genesis_Evangelion_01_(640x480_DVD_h264)_[ABCD1234].mkv",
            {"title": "Neon Genesis Evangelion", "episode": 1, "height": 480},
        ),
        (
            r"D:\Anime\Fullmetal Alchemist Brotherhood - 01v2.mkv",
            {"title": "Fullmetal Alchemist Brotherhood", "episode": 1, "version": 2},
        ),
        (
            r"D:\Anime\Yu Yu Hakusho\Yu Yu Hakusho 112.avi",
            {"title": "Yu Yu Hakusho", "episode": 112},
        ),
        (
            r"D:\Anime\[Group] Dragon Ball GT - 64 (DVD 576p).mkv",
            {"title": "Dragon Ball GT", "episode": 64, "height": 576},
        ),
    ],
)
def test_fansub_names_with_absolute_episode_numbers(path: str, expected: dict[str, Any]):
    result = parsed(path)

    assert result.kind == Kind.EPISODE
    assert {key: getattr(result, key) for key in expected} == expected


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        (
            r"D:\Anime\TV\Dragon Ball Z (1989)\Season 01\Dragon Ball Z (1989) - S01E05.mkv",
            {"title": "Dragon Ball Z", "year": 1989, "season": 1, "episode": 5, "folder_season": 1},
        ),
        (
            r"D:\Anime\Sailor Moon\Season 01\Sailor Moon - S01E01 - A Moon Star is Born.mkv",
            {"season": 1, "episode": 1, "episode_title": "A Moon Star is Born"},
        ),
        (
            r"D:\Anime\[HorribleSubs] One Punch Man S2 - 01 [720p].mkv",
            {"title": "One Punch Man", "season": 2, "episode": 1},
        ),
        (
            r"D:\Anime\Dragon.Ball.Super.S01E131.1080p.BluRay.x264-GROUP.mkv",
            {"title": "Dragon Ball Super", "season": 1, "episode": 131, "episode_title": None},
        ),
    ],
)
def test_season_and_episode_names(path: str, expected: dict[str, Any]):
    result = parsed(path)

    assert result.kind == Kind.EPISODE
    assert {key: getattr(result, key) for key in expected} == expected


def test_a_hunter_x_hunter_year_is_a_year_not_a_season():
    result = parsed(r"D:\Anime\[Kametsu] Hunter x Hunter (2011) - 148 [BD 1080p Hi10 FLAC].mkv")

    assert (result.title, result.year, result.season, result.episode) == (
        "Hunter x Hunter",
        2011,
        None,
        148,
    )


def test_episode_titles_are_kept():
    result = parsed(r"D:\Anime\Dragon Ball\Dragon Ball - 001 - Secret of the Dragon Balls.mkv")

    assert (result.title, result.episode, result.episode_title) == (
        "Dragon Ball",
        1,
        "Secret of the Dragon Balls",
    )


def test_a_title_with_final_in_its_episode_title_keeps_both():
    result = parsed(r"D:\Anime\Dragon Ball Z Kai - 98 - The Final Battle.mkv")

    assert (result.title, result.episode, result.episode_title) == (
        "Dragon Ball Z Kai",
        98,
        "The Final Battle",
    )


def test_two_episodes_in_one_file():
    result = parsed(r"D:\Anime\Naruto Shippuden - 01-02 [720p].mkv")

    assert (result.episode, result.episode_end) == (1, 2)


def test_a_part_number_is_kept_though_anitopy_drops_it():
    # Season 3 Part 2 numbers its episodes from 1 again, so "Part 2" decides where they go.
    result = parsed(r"D:\Anime\[SubsPlease] Shingeki no Kyojin S3 Part 2 - 03 (1080p).mkv")

    assert (result.title, result.season, result.part, result.episode) == (
        "Shingeki no Kyojin",
        3,
        2,
        3,
    )
    assert parsed(r"D:\Anime\Shingeki no Kyojin S3 - 03.mkv").part is None
    assert parsed(r"D:\Anime\Cowboy Bebop\Cowboy Bebop - Session 05 - Part of It.mkv").part is None


def test_an_episode_titled_part_2_after_its_code_is_no_part():
    # The code says where it goes; "Part 2" after it is the episode's own title, so it and a copy
    # named "S01E05" alone are the same episode.
    result = parsed(r"D:\Anime\Dragon Ball Z\Dragon Ball Z - S01E05 - Part 2.mkv")

    assert (result.season, result.part, result.episode, result.episode_title) == (
        1,
        None,
        5,
        "Part 2",
    )


def test_words_like_session_are_not_part_of_the_title():
    result = parsed(
        r"D:\Anime\Cowboy Bebop\Cowboy Bebop - Session 05 - Ballad of Fallen Angels.mkv"
    )

    assert (result.title, result.episode, result.episode_title) == (
        "Cowboy Bebop",
        5,
        "Ballad of Fallen Angels",
    )


class TestFolders:
    def test_a_bare_episode_number_takes_show_year_and_season_from_its_folders(self):
        result = parsed(r"D:\Anime\TV\Dragon Ball Z (1989)\Season 03\05.mkv")

        assert result.title is None
        assert (result.folder_title, result.year, result.folder_season, result.episode) == (
            "Dragon Ball Z",
            1989,
            3,
            5,
        )
        assert result.best_title == "Dragon Ball Z"

    def test_absolute_numbers_keep_the_season_folder_apart(self):
        result = parsed(
            r"D:\Anime\Shonen\Naruto Shippuden\Season 07\Naruto Shippuden - 143 [720p].mkv"
        )

        assert (result.title, result.season, result.folder_season, result.episode) == (
            "Naruto Shippuden",
            None,
            7,
            143,
        )
        assert result.folder_title == "Naruto Shippuden"

    def test_a_specials_folder_is_season_zero(self):
        result = parsed(
            r"D:\Anime\TV\Dragon Ball Z (1989)\Specials\Dragon Ball Z (1989) - S00E01.mkv"
        )

        assert (result.season, result.folder_season, result.kind) == (0, 0, Kind.SPECIAL)

    @pytest.mark.parametrize("folder", ["Downloads", "Anime", "TV", "Extras", "New folder"])
    def test_general_folders_are_not_titles(self, folder: str):
        assert parsed(rf"D:\{folder}\01.mkv").folder_title is None

    def test_a_file_at_the_top_of_a_drive_has_no_folder_title(self):
        assert parsed(r"D:\Trigun 01.mkv").folder_title is None


class TestKinds:
    def test_a_name_without_an_episode_number_is_a_movie(self):
        result = parsed(r"D:\Anime\Movies\Broly the Legendary Super Saiyan.avi")

        assert (result.kind, result.title, result.episode) == (
            Kind.MOVIE,
            "Broly the Legendary Super Saiyan",
            None,
        )

    def test_movie_in_the_name_marks_a_movie(self):
        result = parsed(r"D:\Anime\Downloads\Cowboy Bebop Movie.mkv")

        assert (result.kind, result.title) == (Kind.MOVIE, "Cowboy Bebop")

    def test_the_movie_goes_as_a_whole(self):
        result = parsed(r"D:\Anime\Movies\Cowboy Bebop - The Movie (2001).mkv")

        assert (result.kind, result.title, result.year) == (Kind.MOVIE, "Cowboy Bebop", 2001)

    def test_a_year_and_no_episode_is_a_movie(self):
        result = parsed(r"D:\Anime\[Group] Dragon Ball Super - Broly (2018) [1080p].mkv")

        assert (result.kind, result.title, result.year) == (
            Kind.MOVIE,
            "Dragon Ball Super - Broly",
            2018,
        )

    def test_a_movie_title_with_brackets_survives(self):
        result = parsed(r"D:\Anime\Evangelion 1.11 You Are (Not) Alone (2007).mkv")

        assert (result.kind, result.title, result.year) == (
            Kind.MOVIE,
            "Evangelion 1.11 You Are (Not) Alone",
            2007,
        )

    def test_an_ova_is_a_special(self):
        result = parsed(r"D:\Anime\Hellsing Ultimate OVA 01.mkv")

        assert (result.kind, result.title, result.episode) == (
            Kind.SPECIAL,
            "Hellsing Ultimate",
            1,
        )

    def test_a_creditless_ending_is_an_extra(self):
        result = parsed(r"D:\Anime\[Group] Hunter x Hunter - NCED01 [1080p].mkv")

        assert (result.kind, result.title) == (Kind.EXTRA, "Hunter x Hunter")

    def test_a_creditless_opening_alone_has_no_title(self):
        result = parsed(r"D:\Anime\Shonen\Extras\NCOP01.mkv")

        assert (result.kind, result.title, result.folder_title) == (Kind.EXTRA, None, None)

    def test_dvd_files_are_recognised(self):
        result = parsed(r"D:\Anime\Old DVDs\VTS_02_1.VOB")

        assert (result.kind, result.title, result.episode) == (Kind.DVD, None, None)


class TestNumberedFilmsAndSpecials:
    """A whole series' release numbers its films and specials: "Dragon Ball Z - Movie 03 - The
    Tree of Might". The number counts the release's films, so a film goes by its own name."""

    FOLDER = r"D:\Anime\DRAGON BALL Z (1989-2019) - The COMPLETE Series\2a. Movies (1989-2018)"

    @pytest.mark.parametrize(
        ("name", "title", "year"),
        [
            (
                "Dragon Ball Z - Movie 03 - The Tree of Might (1990 BluRay - 1080p TRI AUDIO).mkv",
                "Dragon Ball Z: The Tree of Might",
                1990,
            ),
            (
                "Dragon Ball Z - Movie 08 - Broly, The Legendary Super Saiyan (1993 BluRay - 1080p"
                " TRI AUDIO).mkv",
                "Dragon Ball Z: Broly, The Legendary Super Saiyan",
                1993,
            ),
            (
                "Dragon Ball Z - Movie 14b - Battle of Gods, UNCut (2013 BluRay - 1080p DUAL"
                " AUDIO).mkv",
                "Dragon Ball Z: Battle of Gods",
                2013,
            ),
            (
                "Dragon Ball Z - Movie 15a (Theatrical Cut) - Resurrection 'F' aka Frieza (2015"
                " BluRay - 1080p DUAL AUDIO).mkv",
                "Dragon Ball Z: Resurrection 'F'",
                2015,
            ),
            (
                "Dragon Ball Z - Movie 15b (Future Trunks Special Edition) - Resurrection 'F' (2016"
                " WebRip - 1080p JAP Audio).mp4",
                "Dragon Ball Z: Resurrection 'F'",
                2016,
            ),
            (
                "Dragon Ball Z - Movie 16 - DB Super BROLY, MangaUK Version (2018 BluRay - 1080p"
                " DUAL Audio).mkv",
                "Dragon Ball Z: DB Super BROLY, MangaUK Version",
                2018,
            ),
        ],
    )
    def test_a_numbered_film_goes_by_its_own_name(self, name: str, title: str, year: int):
        result = parsed(rf"{self.FOLDER}\{name}")

        assert (result.kind, result.title, result.series, result.year) == (
            Kind.MOVIE,
            title,
            "Dragon Ball Z",
            year,
        )
        assert (result.episode, result.episode_title) == (None, None)

    def test_a_film_with_no_number_has_no_series_of_its_own(self):
        result = parsed(r"D:\Anime\Movies\Cowboy Bebop - The Movie (2001).mkv")

        assert (result.title, result.series) == ("Cowboy Bebop", None)

    def test_a_numbered_special_keeps_its_series_and_its_own_name(self):
        result = parsed(
            r"D:\Anime\DRAGON BALL Z\3. TV Specials (1990-2013)\Dragon Ball Z - Special 06 - The"
            r" History of Trunks (1995 BluRay - 1080p TRI Audio).mkv"
        )

        assert (result.kind, result.title, result.episode_title, result.year) == (
            Kind.SPECIAL,
            "Dragon Ball Z",
            "The History of Trunks",
            1995,
        )

    def test_a_public_service_announcement_is_a_special(self):
        result = parsed(
            r"D:\Anime\DRAGON BALL Z\5. PSAs (1988)\Dragon Ball - PSA 01 - Goku's Fire Brigade"
            r" (1988 - 480p JAP Audio).mp4"
        )

        assert (result.kind, result.title, result.episode, result.episode_title) == (
            Kind.SPECIAL,
            "Dragon Ball",
            1,
            "Goku's Fire Brigade",
        )

    def test_a_year_in_brackets_with_other_words_is_the_year(self):
        result = parsed(r"D:\Anime\Akira (1988 BluRay - 1080p).mkv")

        assert (result.title, result.year) == ("Akira", 1988)

    def test_a_span_of_years_is_no_year(self):
        assert parsed(r"D:\Anime\Akira (1988-2019 BluRay).mkv").year is None


class TestNamesThatNeedAMatch:
    def test_a_group_and_an_episode_but_no_title(self):
        result = parsed(r"D:\Anime\Downloads\[subs] ep03 final.mkv")

        assert (result.title, result.episode, result.group, result.best_title) == (
            None,
            3,
            "subs",
            None,
        )

    def test_a_movie_named_movie(self):
        result = parsed(r"D:\Anime\Misc\movie_final_v2.mp4")

        assert (result.kind, result.title, result.version) == (Kind.MOVIE, None, 2)

    @pytest.mark.parametrize("name", ["Ep.mkv", "Episode.mkv", "Vol.mkv"])
    def test_a_name_anitopy_trips_over_still_has_its_folders(self, name: str):
        result = parsed(rf"D:\Anime\Cowboy Bebop\{name}")

        assert (result.folder_title, result.episode) == ("Cowboy Bebop", None)


class TestCopies:
    @pytest.mark.parametrize(
        "name",
        [
            "Naruto 042 (copy).mkv",
            "Naruto 042 - Copy.mkv",
            "Naruto 042 - Copy (2).mkv",
            "Naruto 042 (2).mkv",
        ],
    )
    def test_copies_are_marked_and_still_read(self, name: str):
        result = parsed(rf"D:\Anime\Naruto\{name}")

        assert (result.title, result.episode, result.is_copy, result.group) == (
            "Naruto",
            42,
            True,
            None,
        )

    def test_kuras_own_keep_both_names_are_copies(self):
        result = parsed(
            r"D:\TV\Dragon Ball Z (1989)\Season 01\Dragon Ball Z (1989) - S01E05 (2).mkv"
        )

        assert (result.is_copy, result.season, result.episode) == (True, 1, 5)

    def test_an_ordinary_name_is_not_a_copy(self):
        assert parsed(r"D:\Anime\Death Note 01.avi").is_copy is False


def test_parsing_from_many_threads_at_once_gives_the_same_answers():
    from concurrent.futures import ThreadPoolExecutor

    paths = [
        r"D:\Anime\[Group] DBZ - 001 [480p].mkv",
        r"D:\Anime\[Kametsu] Hunter x Hunter (2011) - 148 [BD 1080p Hi10 FLAC].mkv",
    ] * 200
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(parsed, paths))

    assert {(r.title, r.episode) for r in results} == {("DBZ", 1), ("Hunter x Hunter", 148)}


def test_a_name_with_only_a_mark_after_its_episode_is_read_without_hanging():
    # anitopy's own search for an episode's title went round forever on these, holding the
    # lock every other name waits on. Read in a child, so a hang fails here and never holds up
    # the rest of the run.
    paths = [
        r"D:\Anime\Dragon Ball Z\Dragon Ball Z - 01 - .x.mkv",
        r"D:\Anime\Dragon Ball Z\Dragon Ball Z - S01E01 - .x.mkv",
        r"D:\Anime\Dragon Ball Z\Dragon Ball Z - 01 - .2.mkv",
        r"D:\Anime\Dragon Ball Z\Dragon Ball Z 01 - .x.x.mkv",
    ]
    code = (
        "import sys\n"
        "from pathlib import PureWindowsPath\n"
        "from kura.core.names import parse_name\n"
        "for path in sys.argv[1:]:\n"
        "    found = parse_name(PureWindowsPath(path))\n"
        "    print(found.title, found.episode)\n"
    )

    done = subprocess.run(
        [sys.executable, "-c", code, *paths],
        capture_output=True,
        text=True,
        timeout=60,
        check=True,
    )

    assert done.stdout.splitlines() == ["Dragon Ball Z 1"] * len(paths)


@pytest.mark.parametrize(
    ("name", "part"),
    [
        ("Akira (1988) CD1", 1),
        ("Akira.1988.cd2", 2),
        ("Akira (1988) - pt1", 1),
        ("Akira (1988) - Part 2", 2),
        ("Akira (1988) - disc 2", 2),
        ("Akira (1988) CD1 (copy)", 1),
        ("Akira (1988)", None),
        ("Mobile Suit Gundam 0083", None),
    ],
)
def test_a_films_part_is_read_from_the_end_of_its_name(name: str, part: int | None):
    assert film_part(name) == part


@pytest.mark.parametrize("name", ["Akira (1988).cd2.avi", "Akira (1988) - disc 2.mkv"])
def test_a_films_part_isnt_part_of_its_title(name: str):
    result = parsed(rf"D:\Anime\Movies\{name}")

    assert (result.kind, result.title, result.year, result.episode) == (
        Kind.MOVIE,
        "Akira",
        1988,
        None,
    )


PACK = (
    r"F:\Anime\[Anime Time] Boku No Hero Academia (My Hero Academia) (S01-S07+Movies+OVAs) [BD]"
    r" [Dual Audio][1080p][HEVC 10bit x265][AAC][Eng Sub]"
)


class TestReleasePacks:
    """A whole show in one release: its seasons in folders named after it, its films and OVAs
    numbered and named after the show, its creditless openings beside them (the owner's own pack,
    2026-10-18, which all waited for a match)."""

    def test_a_season_folder_named_after_its_show_gives_the_season_and_the_show(self):
        season = r"[Anime Time] My Hero Academia Season 02"
        result = parsed(rf"{PACK}\{season}\[Anime Time] My Hero Academia - 14.mkv")

        assert (result.title, result.folder_title, result.folder_season, result.episode) == (
            "My Hero Academia",
            "My Hero Academia",
            2,
            14,
        )

    @pytest.mark.parametrize(
        ("folder", "season"),
        [
            ("Shingeki no Kyojin Season 3", 3),
            ("Boku no Hero Academia 2nd Season", 2),
            ("Kimetsu no Yaiba S2", 2),
            ("Kimetsu no Yaiba - Season 02 [BD 1080p]", 2),
        ],
    )
    def test_season_folders_name_their_show_in_many_ways(self, folder: str, season: int):
        result = parsed(rf"D:\Anime\{folder}\01.mkv")

        assert (result.folder_season, result.episode) == (season, 1)
        assert result.folder_title is not None
        assert "season" not in result.folder_title.casefold()

    def test_a_release_packs_folder_is_read_for_the_shows_names(self):
        result = parsed(rf"{PACK}\01.mkv")

        assert result.folder_title == "Boku No Hero Academia (My Hero Academia)"

    @pytest.mark.parametrize(
        ("folder", "title"),
        [
            ("Fate stay night [Unlimited Blade Works]", "Fate stay night [Unlimited Blade Works]"),
            ("[Oshi no Ko]", "Oshi no Ko"),
            ("Cowboy Bebop (Complete Series) [BD 1080p] [Dual Audio]", "Cowboy Bebop"),
            ("[Group]_Cowboy_Bebop_[1080p]", "Cowboy Bebop"),
        ],
    )
    def test_a_folders_brackets_go_only_when_they_hold_a_releases_words(
        self, folder: str, title: str
    ):
        assert parsed(rf"D:\Anime\{folder}\01.mkv").folder_title == title

    def test_a_folders_own_marks_stay(self):
        # Kura's own name for a title AniList writes "Re:ZERO -Starting Life in Another World-".
        show = "Re ZERO -Starting Life in Another World- (2016)"
        result = parsed(rf"D:\Anime\TV\{show}\Season 02\{show} - S02E01.mkv")

        assert (result.folder_title, result.year) == (
            "Re ZERO -Starting Life in Another World-",
            2016,
        )

    @pytest.mark.parametrize(
        "folder",
        [
            "Attack on Titan (Season 2)",
            "Attack on Titan [S2]",
            "Attack on Titan (2nd Season)",
            r"Attack on Titan\(Season 2)",
            r"Attack on Titan\Season 2 [1080p]",
        ],
    )
    def test_a_season_in_a_folders_brackets_is_its_season(self, folder: str):
        result = parsed(rf"D:\Anime\{folder}\01.mkv")

        assert (result.folder_title, result.folder_season) == ("Attack on Titan", 2)

    def test_a_folder_of_a_shows_seasons_gives_no_season(self):
        result = parsed(r"D:\Anime\Attack on Titan S01-S04\Attack on Titan - 05.mkv")

        assert (result.folder_title, result.folder_season) == ("Attack on Titan", None)

    @pytest.mark.parametrize(
        ("name", "title"),
        [
            ("[Anime Time] My Hero Academia Movie 01 - Two Heroes.mkv", "Two Heroes"),
            (
                "[Anime Time] My Hero Academia Movie 03 - World Heroes Mission.mkv",
                "World Heroes Mission",
            ),
            ("[Anime Time] My Hero Academia Movie 04 - You're Next.mkv", "You're Next"),
        ],
    )
    def test_a_numbered_film_without_a_dash_before_movie(self, name: str, title: str):
        result = parsed(rf"{PACK}\[Anime Time] My Hero Academia Movies\{name}")

        assert (result.kind, result.title, result.series) == (
            Kind.MOVIE,
            f"My Hero Academia: {title}",
            "My Hero Academia",
        )
        # The release's folder names the show, above its films' own.
        assert result.folder_title == "Boku No Hero Academia (My Hero Academia)"

    @pytest.mark.parametrize(
        ("folder", "title", "kind"),
        [
            (r"D:\Anime\Cowboy Bebop\Cowboy Bebop Specials", "Cowboy Bebop", Kind.SPECIAL),
            (r"D:\Anime\Cowboy Bebop (1998)\OVA", "Cowboy Bebop", Kind.SPECIAL),
            (r"D:\Anime\Hellsing Ultimate OVA", "Hellsing Ultimate", Kind.SPECIAL),
            (r"D:\Anime\Show (2019) - Specials", "Show", Kind.SPECIAL),
            (r"D:\Anime\TV Specials", None, Kind.SPECIAL),
            (
                r"D:\Anime\Dragon Ball Z (1989)\3. TV Specials (1990-2013)",
                "Dragon Ball Z",
                Kind.SPECIAL,
            ),
            # Which of a show's films a bare number is, nothing says: it waits for the owner.
            (r"D:\Anime\Cowboy Bebop\Cowboy Bebop Movies", None, Kind.MOVIE),
            (r"D:\Anime\Anime Movies", None, Kind.MOVIE),
        ],
    )
    def test_a_folder_of_films_or_specials_says_what_a_bare_number_in_it_is(
        self, folder: str, title: str | None, kind: Kind
    ):
        # The show is the folder above's, or the folder's own first words when there's none
        # (but not "TV" of "TV Specials"). A release counts its films and OVAs its own way, so
        # the folder is no season 0.
        result = parsed(rf"{folder}\05.mkv")

        assert (result.kind, result.best_title, result.folder_season) == (kind, title, None)

    def test_a_folder_of_specials_leaves_a_named_file_as_it_is(self):
        result = parsed(r"D:\Anime\Cowboy Bebop\Cowboy Bebop Specials\Cowboy Bebop - 05.mkv")

        assert (result.kind, result.title, result.episode) == (Kind.EPISODE, "Cowboy Bebop", 5)

    @pytest.mark.parametrize(
        "folder",
        [
            "[Anime Time] Fullmetal Alchemist Brotherhood + OVA [BD][Dual Audio][1080p]",
            "Toradora! & OVA",
            "Clannad and Specials",
            "Naruto Shippuden with Movies",
        ],
    )
    def test_a_folder_of_a_show_and_its_ovas_holds_its_episodes(self, folder: str):
        result = parsed(rf"D:\Anime\{folder}\05.mkv")

        assert (result.kind, result.episode) == (Kind.EPISODE, 5)

    @pytest.mark.parametrize(
        ("folder", "title"),
        [
            ("K S2", "K"),  # a show's name can be one letter
            ("Ys OVA", "Ys"),
            ("The OVA", None),
            ("2a. Movies (1989-2018)", None),
        ],
    )
    def test_a_folders_first_words_name_a_show_unless_they_cant(self, folder: str, title: str):
        assert parsed(rf"D:\Anime\{folder}\05.mkv").folder_title == title

    def test_a_folder_of_specials_doesnt_change_a_name_that_says_what_it_is(self):
        result = parsed(r"D:\Anime\Cowboy Bebop\Cowboy Bebop Specials\Cowboy Bebop - The Movie.mkv")

        assert result.kind is Kind.MOVIE

    @pytest.mark.parametrize(
        ("name", "title", "series"),
        [
            (
                "Cowboy Bebop: The Movie - Knockin' on Heaven's Door.mkv",
                "Cowboy Bebop: Knockin' on Heaven's Door",
                "Cowboy Bebop",
            ),
            (
                "The Movie - Knockin' on Heaven's Door.mkv",
                "The Movie - Knockin' on Heaven's Door",
                None,
            ),
        ],
    )
    def test_a_films_series_is_a_name(self, name: str, title: str, series: str | None):
        result = parsed(rf"D:\Anime\Cowboy Bebop\{name}")

        assert (result.kind, result.title, result.series) == (Kind.MOVIE, title, series)

    def test_a_film_named_after_its_series_without_a_number(self):
        result = parsed(r"D:\Anime\Kimetsu no Yaiba Movie - Mugen Ressha-hen.mkv")

        assert (result.kind, result.title, result.series) == (
            Kind.MOVIE,
            "Kimetsu no Yaiba: Mugen Ressha-hen",
            "Kimetsu no Yaiba",
        )

    @pytest.mark.parametrize(
        ("name", "own"),
        [
            (
                "[Anime Time] My Hero Academia OVA - Training of the Dead!.mkv",
                "Training of the Dead!",
            ),
            (
                "[Anime Time] My Hero Academia OVA - Rescue! Rescue Training!.mkv",
                "Rescue! Rescue Training!",
            ),
            (
                "[Anime Time] My Hero Academia OVA - Make It! Do-or-Die Survival Training, Part 1"
                ".mkv",
                "Make It! Do-or-Die Survival Training, Part 1",
            ),
            (
                "[Anime Time] My Hero Academia OVA - HLB (Hero League Baseball).mkv",
                "HLB (Hero League Baseball)",
            ),
        ],
    )
    def test_a_named_ova_is_its_shows_special_by_its_own_name(self, name: str, own: str):
        result = parsed(rf"{PACK}\OVA\{name}")

        assert (result.kind, result.title, result.episode, result.episode_title) == (
            Kind.SPECIAL,
            "My Hero Academia",
            None,
            own,
        )
        # A release counts its OVAs its own way: its "OVA" folder is no season 0.
        assert result.folder_season is None

    @pytest.mark.parametrize(
        ("name", "title", "number", "own"),
        [
            (
                "Darker than Black OVA - Kuro no Keiyakusha Gaiden - 03.mkv",
                "Darker than Black",
                3,
                "Kuro no Keiyakusha Gaiden",
            ),
            ("[Group] Cowboy Bebop OVA: Session XX - 02.mkv", "Cowboy Bebop", 2, "Session XX"),
        ],
    )
    def test_a_named_ovas_episodes_keep_their_numbers(
        self, name: str, title: str, number: int, own: str
    ):
        result = parsed(rf"D:\Anime\{name}")

        assert (result.kind, result.title, result.episode, result.episode_title) == (
            Kind.SPECIAL,
            title,
            number,
            own,
        )

    @pytest.mark.parametrize(
        "name",
        [
            "Boku no Hero Academia [SP02] NCED - 01.mkv",
            "Boku no Hero Academia S2 [SP01] NCOP - 01.mkv",
            "Boku no Hero Academia S4 NCED 1.mkv",
            "Kimetsu no Yaiba - Creditless Opening.mkv",
            "[Group] Spy x Family - NC OP 2 [1080p].mkv",
            "Cowboy Bebop - Non-Credit Opening.mkv",
        ],
    )
    def test_creditless_openings_and_endings_are_extras_however_named(self, name: str):
        assert parsed(rf"{PACK}\Extras\{name}").kind is Kind.EXTRA

    def test_an_episode_whose_title_has_credit_in_it_is_an_episode(self):
        result = parsed(r"D:\Anime\Show\Show - 01 - A Noncreditable Story.mkv")

        assert (result.kind, result.episode) == (Kind.EPISODE, 1)


class TestJapaneseNames:
    """Names in Japanese, as they come from Japanese releases and recordings: 第01話 is episode
    1, 第2期 season 2, 劇場版 a film; full-width letters and digits read as plain ones. Chinese
    subtitle groups' 第01集 and 第01话 are episodes too."""

    @pytest.mark.parametrize(
        ("name", "expected"),
        [
            ("鬼滅の刃 第01話.mkv", {"title": "鬼滅の刃", "episode": 1}),
            ("鬼滅の刃 第１話.mkv", {"title": "鬼滅の刃", "episode": 1}),
            (
                "葬送のフリーレン 第01話 冒険の終わり.mkv",
                {"title": "葬送のフリーレン", "episode": 1, "episode_title": "冒険の終わり"},
            ),
            ("鬼滅の刃 第2期 第05話.mkv", {"title": "鬼滅の刃", "season": 2, "episode": 5}),
            ("進撃の巨人 第二期 第三話.mkv", {"title": "進撃の巨人", "season": 2, "episode": 3}),
            (
                "[Group] 僕のヒーローアカデミア #14 (1080p).mkv",
                {"title": "僕のヒーローアカデミア", "episode": 14},
            ),
            (
                f"Re{chr(0xFF1A)}ゼロから始める異世界生活 - 01.mkv",  # a full-width colon
                {"title": "Re:ゼロから始める異世界生活", "episode": 1},
            ),
            ("我推的孩子 第01集.mp4", {"title": "我推的孩子", "episode": 1}),
            ("鬼灭之刃 第01话.mkv", {"title": "鬼灭之刃", "episode": 1}),
        ],
    )
    def test_japanese_episode_and_season_markers(self, name: str, expected: dict[str, Any]):
        result = parsed(rf"D:\Anime\{name}")

        assert result.kind is Kind.EPISODE
        assert {key: getattr(result, key) for key in expected} == expected

    @pytest.mark.parametrize(
        ("name", "title", "year"),
        [
            ("劇場版 鬼滅の刃 無限列車編.mkv", "鬼滅の刃 無限列車編", None),
            (
                "Gekijouban Kimetsu no Yaiba Mugen Ressha-hen (2020) [BD 1080p].mkv",
                "Kimetsu no Yaiba Mugen Ressha-hen",
                2020,
            ),
            (
                "Gekijouban Kimetsu no Yaiba - Mugen Ressha-hen.mkv",
                "Kimetsu no Yaiba - Mugen Ressha-hen",
                None,
            ),
            # Its official name, the series' in corner brackets.
            ("劇場版「鬼滅の刃」無限列車編.mkv", "鬼滅の刃 無限列車編", None),
        ],
    )
    def test_a_theatrical_version_is_a_film(self, name: str, title: str, year: int | None):
        result = parsed(rf"D:\Anime\{name}")

        assert (result.kind, result.title, result.year) == (Kind.MOVIE, title, year)

    def test_a_series_theatrical_films_are_numbered_films(self):
        result = parsed(r"D:\Anime\Dragon Ball Z - Gekijouban 03 - The Tree of Might.mkv")

        assert (result.kind, result.title, result.series) == (
            Kind.MOVIE,
            "Dragon Ball Z: The Tree of Might",
            "Dragon Ball Z",
        )

    def test_a_name_that_starts_with_a_groups_brackets_and_its_marks_too(self):
        result = parsed(r"D:\Anime\葬送のフリーレン\【Group】 第01話 冒険の終わり.mkv")

        assert (result.kind, result.best_title, result.episode) == (
            Kind.EPISODE,
            "葬送のフリーレン",
            1,
        )

    @pytest.mark.parametrize(
        ("name", "season", "episode"),
        [("第01話 冒険の終わり.mkv", None, 1), ("第2期 第05話 冒険の終わり.mkv", 2, 5)],
    )
    def test_a_name_that_starts_with_its_marks_takes_its_show_from_the_folder(
        self, name: str, season: int | None, episode: int
    ):
        # What follows the episode's mark is its own title, not the show's.
        result = parsed(rf"D:\Anime\葬送のフリーレン\{name}")

        assert (result.kind, result.best_title, result.season, result.episode) == (
            Kind.EPISODE,
            "葬送のフリーレン",
            season,
            episode,
        )

    @pytest.mark.parametrize(
        "name", ["[Group] 【推しの子】 - 01 [1080p].mkv", "【推しの子】 第01話.mkv"]
    )
    def test_a_title_in_lenticular_brackets_is_the_title(self, name: str):
        # anitopy reads 【】 as a group's brackets; 【推しの子】 is the show's own name.
        result = parsed(rf"D:\Anime\{name}")

        assert (result.kind, result.title, result.episode) == (Kind.EPISODE, "推しの子", 1)

    def test_lenticular_brackets_beside_a_shows_folder_are_a_groups(self):
        result = parsed(r"D:\Anime\Oshi no Ko\【MMSUB】 - 01.mkv")

        assert (result.best_title, result.episode) == ("Oshi no Ko", 1)


class TestOddNames:
    def test_a_film_named_as_its_own_folder_keeps_its_number(self):
        result = parsed(r"D:\Anime\Movies\Jujutsu Kaisen 0 (2021)\Jujutsu Kaisen 0 (2021).mkv")

        assert (result.kind, result.title, result.year, result.episode) == (
            Kind.MOVIE,
            "Jujutsu Kaisen 0",
            2021,
            None,
        )

    def test_a_film_in_a_folder_of_its_own_keeps_what_its_name_says_of_the_release(self):
        film = "Paprika (2006) [1080p]"
        result = parsed(rf"D:\Anime\Movies\{film}\{film}.mkv")

        assert (result.kind, result.title, result.year, result.height) == (
            Kind.MOVIE,
            "Paprika",
            2006,
            1080,
        )

    def test_a_numbered_film_in_a_folder_of_its_own_is_found_by_its_own_name(self):
        film = "Dragon Ball Z - Movie 03 - The Tree of Might (1990)"
        result = parsed(rf"D:\Anime\Movies\{film}\{film}.mkv")

        assert (result.kind, result.title, result.series, result.year) == (
            Kind.MOVIE,
            "Dragon Ball Z: The Tree of Might",
            "Dragon Ball Z",
            1990,
        )

    def test_a_circled_number_is_no_number(self):
        # It's a digit to Python, but not one int() reads.
        assert parsed(r"D:\Anime\Show\Show - ①.mkv").episode is None

    def test_only_full_width_letters_and_digits_are_read_as_plain(self):
        # "½" stays as it is, as AniList writes it: Ranma ½.
        assert parsed(r"D:\Anime\Ranma ½\Ranma ½ - 01.mkv").title == "Ranma ½"

    def test_a_title_ending_in_end_keeps_it(self):
        # anitopy reads "End" as a release's word, as in "- 12 END".
        result = parsed(r"D:\Anime\Seraph of the End\Seraph of the End - 01.mkv")

        assert (result.title, result.episode) == ("Seraph of the End", 1)

    def test_scene_dots_dont_stay_in_the_title_nor_release_words_in_the_episodes(self):
        result = parsed(r"D:\Anime\Spy x Family\Spy.x.Family.S01E01.1080p.WEB.h264-SENPAI.mkv")

        assert (result.title, result.season, result.episode, result.episode_title) == (
            "Spy x Family",
            1,
            1,
            None,
        )
