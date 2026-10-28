"""Where a file sits in a TMDB show: numbered by season, counted straight through, or by date."""

import json
from dataclasses import replace
from datetime import date
from pathlib import Path, PureWindowsPath

import pytest

from kura.core.catalog import Anime, Show, anime_list, show
from kura.core.identify import FileFacts
from kura.core.names import parse_name
from kura.core.placing import (
    How,
    Placement,
    lists_special,
    named_special,
    numbered_through,
    place,
)
from tests.tmdb_data import DBZ_SEASONS, tv_details

ANILIST = Path(__file__).parent.parent / "data" / "anilist"


def tmdb_show(details: dict[str, object]) -> Show:
    found = show(details)
    assert found is not None
    return found


DBZ = tmdb_show(tv_details(12971, "Dragon Ball Z", DBZ_SEASONS, first_aired=date(1989, 4, 26)))

# Attack on Titan as TMDB has it: season 3 holds both of AniList's parts, the second starting
# with episode 13 on 29 April 2019.
TITAN = tmdb_show(
    tv_details(
        1429,
        "Attack on Titan",
        (25, 12, 22, 30),
        first_aired=date(2013, 4, 7),
        aired={
            (2, 1): date(2017, 4, 1),
            (3, 1): date(2018, 7, 23),
            (3, 13): date(2019, 4, 29),
            (4, 1): date(2020, 12, 7),
        },
    )
)

# Cowboy Bebop with its specials in season 0; the second first aired on 26 June 1998.
BEBOP = tmdb_show(
    tv_details(
        30991,
        "Cowboy Bebop",
        (26,),
        first_aired=date(1998, 4, 3),
        specials=3,
        special_dates=(date(1998, 4, 3), date(1998, 6, 26), date(2012, 12, 21)),
    )
)


def anilist(name: str, anime_id: int) -> Anime:
    found = anime_list(json.loads((ANILIST / f"{name}.json").read_text(encoding="utf-8")))
    return next(entry for entry in found if entry.id == anime_id)


def placed(path: str, where: Show, entry: Anime | None = None) -> Placement | None:
    return place(parse_name(PureWindowsPath(path)), where, entry)


def test_a_number_counted_straight_through_finds_its_season():
    # 39 + 35 + 33 + 32 = 139 episodes in seasons 1 to 4: episode 150 is season 5's eleventh.
    assert placed(r"D:\Anime\Dragon Ball Z\Dragon Ball Z - 150.mkv", DBZ) == Placement(
        5, 11, None, How.STRAIGHT
    )
    assert placed(r"D:\Anime\[Group] DBZ - 001 [480p].mkv", DBZ) == Placement(
        1, 1, None, How.STRAIGHT
    )
    assert placed(r"D:\Anime\Dragon Ball Z\Dragon Ball Z - 291.mkv", DBZ) == Placement(
        9, 38, None, How.STRAIGHT
    )


def test_a_number_past_the_last_episode_isnt_placed():
    assert placed(r"D:\Anime\Dragon Ball Z\Dragon Ball Z - 292.mkv", DBZ) is None


@pytest.mark.parametrize(
    "path",
    [
        # Nine seasons: a tenth's fifth episode, new or not yet on TMDB, isn't the show's fifth.
        r"D:\Anime\Dragon Ball Z - S10E05.mkv",
        r"D:\Anime\Dragon Ball Z\Season 10\05.mkv",
        # Season 4 has 32: a 33rd counted through the show would be season 1's.
        r"D:\Anime\Dragon Ball Z - S04E33.mkv",
    ],
)
def test_a_number_past_its_season_is_never_counted_back_into_an_earlier_one(path: str):
    # Placed there, the real episode of that number looks like a copy, and Tidy up would set
    # one of them aside. It waits for the owner instead.
    assert placed(path, DBZ) is None


def test_a_season_and_episode_are_taken_as_they_are():
    assert placed(r"D:\Anime\Dragon Ball Z - S04E05 - Title.mkv", DBZ) == Placement(
        4, 5, None, How.NUMBERED
    )
    assert placed(r"D:\Anime\Dragon Ball Z\Season 04\05.mkv", DBZ) == Placement(
        4, 5, None, How.NUMBERED
    )


def test_a_season_with_numbers_counted_through_the_show():
    # HorribleSubs numbered Attack on Titan's third season on from the second: 38 to 59.
    found = placed(r"D:\Anime\[HorribleSubs] Shingeki no Kyojin S3 - 49 [720p].mkv", TITAN)

    assert found == Placement(3, 12, None, How.STRAIGHT)


def test_a_later_part_numbered_from_one_again_is_placed_by_its_first_air_date():
    part_two = anilist("attack-on-titan-season-3-part-2", 104578)

    found = placed(
        r"D:\Anime\[SubsPlease] Shingeki no Kyojin S3 Part 2 - 03 (1080p).mkv", TITAN, part_two
    )

    assert found == Placement(3, 15, None, How.BY_DATE)


def test_the_first_entry_of_a_show_doesnt_shift_its_numbers():
    dbz = anilist("dragon-ball-z", 813)  # starts with the show's first episode

    found = placed(r"D:\Anime\Dragon Ball Z\Dragon Ball Z - S04E05.mkv", DBZ, dbz)

    assert found == Placement(4, 5, None, How.NUMBERED)


def test_two_episodes_in_one_file_stay_in_one_season():
    assert placed(r"D:\Anime\Dragon Ball Z - 001-002.mkv", DBZ) == Placement(1, 1, 2, How.STRAIGHT)
    # 39 and 40 straddle seasons 1 and 2: only the first is placed.
    assert placed(r"D:\Anime\Dragon Ball Z - 039-040.mkv", DBZ) == Placement(
        1, 39, None, How.STRAIGHT
    )


def test_a_special_goes_to_season_zero_by_the_date_it_first_aired():
    yoseatsume = anilist("cowboy-bebop", 4037)  # first aired 26 June 1998

    found = placed(r"D:\Anime\Cowboy Bebop\Cowboy Bebop - OVA.mkv", BEBOP, yoseatsume)

    assert found == Placement(0, 2, None, How.BY_DATE)


def test_a_special_already_numbered_keeps_its_number():
    found = placed(r"D:\Anime\Cowboy Bebop\Specials\Cowboy Bebop - 03.mkv", BEBOP)

    assert found == Placement(0, 3, None, How.NUMBERED)


def test_a_special_kura_cant_date_or_number_isnt_placed():
    assert placed(r"D:\Anime\Cowboy Bebop\Cowboy Bebop - OVA.mkv", BEBOP) is None
    assert placed(r"D:\Anime\Dragon Ball Z\Specials\Dragon Ball Z - 01.mkv", DBZ) is None


def test_films_and_extras_arent_episodes():
    assert placed(r"D:\Anime\Cowboy Bebop - The Movie (2001).mkv", BEBOP) is None
    assert placed(r"D:\Anime\Cowboy Bebop\Extras\NCOP01.mkv", BEBOP) is None


def test_a_special_named_the_plex_way_keeps_its_number_whatever_its_entry():
    yoseatsume = anilist("cowboy-bebop", 4037)  # first aired 26 June 1998, TMDB's S00E02

    found = placed(
        "D:/Anime/Cowboy Bebop (1998)/Specials/Cowboy Bebop (1998) - S00E03.mkv", BEBOP, yoseatsume
    )

    assert found == Placement(0, 3, None, How.NUMBERED)


def test_a_series_says_nothing_about_which_special_a_file_is():
    bebop = anilist("cowboy-bebop", 1)  # first aired 3 April 1998, the day TMDB's S00E01 did

    assert placed("D:/Anime/Cowboy Bebop/Cowboy Bebop - OVA.mkv", BEBOP, bebop) is None


# Dragon Ball Z with some of its specials, named as TMDB names them.
DBZ_SPECIALS = tmdb_show(
    tv_details(
        12971,
        "Dragon Ball Z",
        DBZ_SEASONS,
        first_aired=date(1989, 4, 26),
        specials=6,
        titles={
            (0, 1): "Bardock - The Father of Goku",
            (0, 2): "Summer Vacation Special",
            (0, 3): "The History of Trunks",
            (0, 4): "Plan to Eradicate the Saiyans (1)",
            (0, 5): "Plan to Eradicate the Saiyans (2)",
            (0, 6): "Episode of Bardock",
        },
    )
)
SPECIALS = r"D:\Anime\DRAGON BALL Z (1989-2019) - The COMPLETE Series\3. TV Specials (1990-2013)"


@pytest.mark.parametrize(
    ("name", "number"),
    [
        ("Dragon Ball Z - Special 01 - Bardock, The Father of Goku (1990 BluRay).mkv", 1),
        ("Dragon Ball Z - Special 02a - Summer Vacation aka Movie Overview (1992).mkv", 2),
        ("Dragon Ball Z - Special 06 - The History of Trunks (1995 BluRay).mkv", 3),
        ("Dragon Ball Z - OVA 01a - Plan to Eradicate The Saiyans, Part 1 of 2 (1993).mkv", 4),
        ("Dragon Ball Z - OVA 01b - Plan to Eradicate The Saiyans, Part 2 of 2 (1993).mkv", 5),
        ("Dragon Ball Z - OVA 04 - The Episode of Bardock (2011 - 1080p JAP Audio).mkv", 6),
    ],
)
def test_a_special_goes_by_its_own_name_among_the_shows_specials(name: str, number: int):
    series = anilist("dragon-ball-z", 813)

    found = placed(rf"{SPECIALS}\{name}", DBZ_SPECIALS, series)

    assert found == Placement(0, number, None, How.BY_NAME)


@pytest.mark.parametrize(
    "name",
    [
        "Dragon Ball Z - Special 02b - Summer Vacation COMMERCIALS (1992).mkv",
        "Dragon Ball Z - Special 05 (GT) - A Hero's Legacy (1997 DVDRip).mkv",
    ],
)
def test_a_special_whose_name_fits_none_of_the_shows_well_isnt_placed(name: str):
    assert placed(rf"{SPECIALS}\{name}", DBZ_SPECIALS, anilist("dragon-ball-z", 813)) is None


def test_an_entry_found_by_a_specials_own_name_goes_by_its_names_among_the_shows():
    names = ("Dragon Ball Z: Atsumare! Goku's World", "ドラゴンボールZ 集まれ!悟空ワールド")
    show_ = tmdb_show(
        tv_details(
            12971,
            "Dragon Ball Z",
            DBZ_SEASONS,
            first_aired=date(1989, 4, 26),
            specials=3,
            titles={
                (0, 1): "Bardock",
                (0, 2): "Summer Vacation Special",
                (0, 3): "Atsumare Goku World",
            },
        )
    )

    assert named_special(names, show_) == Placement(0, 3, None, How.BY_NAME)
    assert named_special(("Dragon Ball Z: Something Else",), show_) is None


def test_a_one_off_special_is_the_one_from_its_day_whatever_the_release_numbers_it():
    gt = tmdb_show(
        tv_details(
            888,
            "Dragon Ball GT",
            (64,),
            first_aired=date(1996, 2, 7),
            specials=2,
            special_dates=(date(1997, 3, 26), date(2023, 1, 1)),
        )
    )
    legacy = anilist("dragon-ball-gt", 987)  # one episode, first aired 26 March 1997

    found = placed(rf"{SPECIALS}\Dragon Ball Z - Special 05 (GT) - A Hero's Legacy.mkv", gt, legacy)

    assert found == Placement(0, 1, None, How.BY_DATE)


def test_episode_zero_of_a_later_part_isnt_the_episode_before_it():
    part_two = anilist("attack-on-titan-season-3-part-2", 104578)

    found = placed(
        "D:/Anime/[SubsPlease] Shingeki no Kyojin S3 Part 2 - 00 (1080p).mkv", TITAN, part_two
    )

    assert found is None


def test_a_show_lists_a_special_by_the_day_it_first_aired():
    assert lists_special(BEBOP, date(1998, 6, 27))  # a day out, as listings are
    assert not lists_special(BEBOP, date(1998, 7, 10))
    assert not lists_special(DBZ, date(1989, 4, 26))  # no specials at all


# My Hero Academia's first three seasons as TMDB has them, for the owner's own pack.
HEROES = tmdb_show(
    tv_details(65930, "My Hero Academia", (13, 25, 25), first_aired=date(2016, 4, 3))
)
HEROES_PACK = r"F:\Anime\[Anime Time] Boku No Hero Academia (My Hero Academia)"


def heroes(season: int, *numbers: int, named: str = "{n:02}") -> list[FileFacts]:
    """The pack's files in its "Season 0N" folder, each with its number as its id."""
    folder = rf"{HEROES_PACK}\[Anime Time] My Hero Academia Season 0{season}"
    files: list[FileFacts] = []
    for n in numbers:
        file = PureWindowsPath(rf"{folder}\[Anime Time] My Hero Academia - {named.format(n=n)}.mkv")
        files.append(FileFacts(n, file, parse_name(file), 24.0))
    return files


def test_a_season_folder_numbered_straight_through_the_show_goes_by_its_numbers():
    # Season 02 holds episodes 14 to 38: the show's 14th is its season 2's first.
    files = heroes(2, *range(14, 39))

    straight = numbered_through(files, HEROES)

    assert straight == set(range(14, 39))
    first, last = (place(replace(files[i].parsed, folder_season=None), HEROES) for i in (0, -1))
    assert (first, last) == (
        Placement(2, 1, None, How.STRAIGHT),
        Placement(2, 25, None, How.STRAIGHT),
    )


def test_a_season_folder_numbered_from_one_keeps_its_season():
    assert numbered_through(heroes(2, *range(1, 26)), HEROES) == set()
    assert numbered_through(heroes(1, *range(1, 14)), HEROES) == set()  # the same either way


def test_a_season_folder_missing_its_first_file_still_counts_straight_through():
    # 15 to 38: past season 1's 13, and on past season 2's own 25.
    assert numbered_through(heroes(2, *range(15, 39)), HEROES) == set(range(15, 39))


@pytest.mark.parametrize("first", [14, 15])
def test_a_season_folder_whose_numbers_could_be_either_keeps_its_season(first: int):
    # 14 to 25 are season 2's own numbers as well: nothing says they count straight through.
    assert numbered_through(heroes(2, *range(first, 26)), HEROES) == set()


def test_a_releases_other_seasons_tell_how_it_numbers_one_that_could_be_either():
    files = [*heroes(2, *range(14, 21)), *heroes(3, *range(39, 46))]

    assert numbered_through(files, HEROES) == {*range(14, 21), *range(39, 46)}


def test_each_folder_tells_its_own_numbering():
    files = [*heroes(2, *range(14, 39)), *heroes(3, *range(1, 26))]

    assert numbered_through(files, HEROES) == set(range(14, 39))


def test_a_name_that_says_its_season_goes_by_it():
    files = heroes(2, *range(14, 26), named="S02E{n:02}")

    assert numbered_through(files, HEROES) == set()
