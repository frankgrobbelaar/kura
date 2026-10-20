"""Which anime a file is: grouping files, scoring AniList's entries, picking TMDB's show."""

import json
from dataclasses import replace
from datetime import date
from pathlib import Path, PureWindowsPath

from kura.core.catalog import Anime, Hit, TitleKind, anime_list, hits
from kura.core.identify import (
    SURE,
    WORTH_SHOWING,
    FileFacts,
    base_title,
    group_files,
    guesses,
    merged,
    normalize,
    pick_hit,
    respelled,
    searches,
    similarity,
    spelled_out,
    through_tmdb,
    tmdb_fit,
)
from kura.core.names import parse_name
from tests.tmdb_data import movie_search, tv_search

ANILIST = Path(__file__).parent.parent / "data" / "anilist"


def entries(name: str) -> list[Anime]:
    return anime_list(json.loads((ANILIST / f"{name}.json").read_text(encoding="utf-8")))


def facts(path: str, minutes: float | None = 24.0, number: int = 0) -> FileFacts:
    where = PureWindowsPath(path)
    return FileFacts(number, where, parse_name(where), minutes)


def test_files_named_alike_are_looked_up_together():
    found = group_files(
        [
            facts(r"D:\Anime\Dragon Ball Z\Dragon Ball Z - 001.mkv", number=1),
            facts(r"D:\Anime\Dragon Ball Z\Dragon Ball Z - 002.mkv", number=2),
            facts(r"D:\Anime\Downloads\[Group] Cowboy Bebop - 05 [480p].mkv", number=3),
        ]
    )

    assert [(g.query, [f.id for f in g.files]) for g in found] == [
        ("Cowboy Bebop", [3]),
        ("Dragon Ball Z", [1, 2]),
    ]


def test_a_bare_episode_takes_its_show_from_the_folder():
    [group] = group_files([facts(r"D:\Anime\Trigun (1998)\Season 01\05.mkv")])

    assert (group.query, group.year) == ("Trigun", 1998)


def test_films_are_looked_up_apart_from_episodes():
    found = group_files(
        [
            facts(r"D:\Anime\Cowboy Bebop\Cowboy Bebop - 01.mkv"),
            facts(r"D:\Anime\Cowboy Bebop\Cowboy Bebop - Movie.mkv", minutes=115),
        ]
    )

    assert [(g.query, g.movie) for g in found] == [
        ("Cowboy Bebop", False),
        ("Cowboy Bebop", True),
    ]


def test_extras_and_dvd_files_arent_looked_up():
    found = group_files(
        [
            facts(r"D:\Anime\Trigun\Extras\NCOP01.mkv"),
            facts(r"D:\Anime\Old DVDs\VTS_02_1.VOB"),
        ]
    )

    assert found == []


def test_dragon_ball_z_is_sure_and_kai_is_not():
    [group] = group_files(
        [facts(rf"D:\Anime\Dragon Ball Z (1989)\Dragon Ball Z - {n:03}.mkv") for n in (1, 150, 291)]
    )

    found = guesses(group, entries("dragon-ball-z"))

    assert found[0].anime.id == 813
    assert found[0].confidence >= SURE
    assert "Title matches" in found[0].reasons
    kai = next(guess for guess in found if guess.anime.id == 6033)
    assert kai.confidence < SURE
    assert "Only 97 episodes, files go up to 291" in kai.reasons


def test_a_nickname_finds_the_show():
    [group] = group_files([facts(r"D:\Anime\Downloads\[Group] DBZ - 001 [480p].MKV")])

    assert guesses(group, entries("dragon-ball-z"))[0].anime.id == 813


def test_a_film_file_matches_the_film_not_the_series():
    [group] = group_files(
        [facts(r"D:\Anime\Movies\Cowboy Bebop - The Movie (2001).mkv", minutes=115)]
    )

    best = guesses(group, entries("cowboy-bebop"))[0]

    assert best.anime.kind is TitleKind.MOVIE
    assert best.anime.id == 5


PACK = r"F:\Anime\[Anime Time] Boku No Hero Academia (My Hero Academia) (S01-S07+Movies+OVAs) [BD]"


def mha_pack(*numbers: int) -> list[FileFacts]:
    """The owner's own pack: My Hero Academia numbered 1 to 159 straight through its seasons."""
    return [
        facts(
            rf"{PACK}\[Anime Time] My Hero Academia Season 0{1 + (n - 1) // 25}"
            rf"\[Anime Time] My Hero Academia - {n:02}.mkv",
            number=n,
        )
        for n in numbers
    ]


def test_a_show_numbered_straight_through_its_seasons_is_its_first_season_and_those_after():
    # AniList keeps each season apart, but a release numbers the show through all of them.
    [group] = group_files(mha_pack(1, 14, 39, 64, 89, 114, 159))

    found = guesses(group, entries("my-hero-academia"))

    assert found[0].anime.id == 21459  # its first season, whose sequels go on past what's found
    assert found[0].confidence >= SURE
    assert "Its later seasons may hold the rest" in found[0].reasons
    final = next(guess for guess in found if guess.anime.id == 182896)  # the last season
    assert final.confidence < SURE
    assert "Only 11 episodes, files go up to 159" in final.reasons


def test_a_shows_seasons_found_as_far_as_its_files_go_fit_them_together():
    [group] = group_files(mha_pack(1, 30, 60, 88))

    best = guesses(group, entries("my-hero-academia"))[0]

    assert best.anime.id == 21459
    assert "88 episodes with its later seasons fit" in best.reasons
    assert best.confidence >= SURE


MOVIES = r"D:\Anime\DRAGON BALL Z (1989-2019) - The COMPLETE Series\2a. Movies (1989-2018)"
SPECIALS = r"D:\Anime\DRAGON BALL Z (1989-2019) - The COMPLETE Series\3. TV Specials (1990-2013)"


def test_a_remake_doesnt_win_on_its_later_seasons():
    # The 2019 Fruits Basket and its sequels hold 26 episodes too, but the 2001 series is 26 alone.
    found = entries("fruits-basket")
    remake_first = sorted(found, key=lambda entry: entry.id != 105334)
    [group] = group_files(
        [facts(rf"D:\Anime\Fruits Basket\Fruits Basket - {n:02}.mkv", number=n) for n in (1, 26)]
    )

    best = guesses(group, remake_first)[0]

    assert best.anime.id == 120


def test_a_film_named_only_by_its_series_is_none_of_its_films_surely():
    [group] = group_files([facts(r"D:\Anime\Dragon Ball Z\Dragon Ball Z - Movie.mkv", minutes=51)])

    assert group.movie
    assert guesses(group, entries("dragon-ball-z"))[0].confidence < SURE


def test_a_numbered_film_is_matched_by_its_own_name():
    [group] = group_files(
        [
            facts(
                rf"{MOVIES}\Dragon Ball Z - Movie 03 - The Tree of Might (1990 BluRay - 1080p TRI"
                " AUDIO).mkv",
                minutes=61,
            )
        ]
    )

    best = guesses(group, entries("dragon-ball-z-the-tree-of-might"))[0]

    assert (best.anime.id, best.confidence >= SURE) == (896, True)
    assert best.reasons == ("Title matches", "1990 fits", "A film, like the file", "61 min fits")


def test_a_film_is_looked_up_by_its_whole_name_then_by_shorter_ones():
    [group] = group_files(
        [
            facts(
                rf"{MOVIES}\Dragon Ball Z - Movie 16 - DB Super BROLY, MangaUK Version (2018"
                " BluRay - 1080p DUAL Audio).mkv",
                minutes=100,
            )
        ]
    )

    assert searches(group) == [
        "Dragon Ball Z: DB Super BROLY, MangaUK Version",
        "Dragon Ball Z DB Super BROLY",
        "DB Super BROLY, MangaUK Version",
        "DB Super BROLY",
        "Dragon Ball Super BROLY, MangaUK Version",  # "DB" is the series' initials
        "Dragon Ball Super BROLY",
        "Dragon Ball Z",
    ]


def test_a_film_named_with_its_series_initials_is_matched_by_them_written_out():
    [group] = group_files(
        [
            facts(
                rf"{MOVIES}\Dragon Ball Z - Movie 16 - DB Super BROLY, MangaUK Version (2018"
                " BluRay - 1080p DUAL Audio).mkv",
                minutes=100,
            )
        ]
    )

    # What AniList finds for "Dragon Ball Super BROLY": it found nothing for "DB Super BROLY".
    best = guesses(group, entries("dragon-ball-super-broly"))[0]

    assert (best.anime.id, best.confidence >= SURE) == (101302, True)
    assert best.reasons[:2] == ("Title matches", "2018 fits")


def test_only_a_series_initials_are_written_out():
    assert spelled_out("DB Super BROLY", "Dragon Ball Z") == "Dragon Ball Super BROLY"
    assert spelled_out("DBZ Kai", "Dragon Ball Z") == "Dragon Ball Z Kai"
    assert spelled_out("Db Super", "Dragon Ball Z") is None  # initials are capitals
    assert spelled_out("OVA Special", "Dragon Ball Z") is None  # not the series'
    assert spelled_out("DBZGT Final", "Dragon Ball Z") is None  # more than the series has


def test_the_same_search_isnt_asked_twice():
    [group] = group_files(
        [
            facts(
                rf"{MOVIES}\Dragon Ball Z - Movie 14b - Battle of Gods, UNCut (2013 BluRay - 1080p"
                " DUAL AUDIO).mkv",
                minutes=105,
            )
        ]
    )

    assert searches(group) == ["Dragon Ball Z: Battle of Gods", "Battle of Gods", "Dragon Ball Z"]


def test_a_series_is_looked_up_by_its_name_alone():
    [group] = group_files([facts(r"D:\Anime\Dragon Ball Z\Dragon Ball Z - 001.mkv")])

    assert searches(group) == ["Dragon Ball Z"]


def test_a_name_with_another_in_brackets_is_looked_up_by_either():
    [group] = group_files(
        [facts(r"D:\Anime\[Judas] Shingeki no Kyojin (Attack on Titan) - S04E01.mkv")]
    )

    assert searches(group) == [
        "Shingeki no Kyojin (Attack on Titan)",
        "Shingeki no Kyojin",
        "Attack on Titan",
    ]


def test_a_name_that_is_a_titles_main_part_fits_it_nearly_as_well():
    # AniList calls it "Seraph of the End: Vampire Reign"; the files go by its first words.
    [group] = group_files([facts(r"D:\Anime\Seraph of the End\Seraph of the End - 01.mkv")])

    best = guesses(group, entries("seraph-of-the-end"))[0]

    assert best.anime.id == 20829
    assert best.confidence >= SURE


def test_a_shows_main_name_beats_a_short_ones_other_name():
    # Onigiri, a series of four-minute episodes, is also known as "Demon Slayer".
    [group] = group_files(
        [facts(r"D:\Anime\Demon Slayer\Season 3\Demon Slayer - S03E01 - Someone's Dream.mkv")]
    )

    best = guesses(group, entries("demon-slayer"))[0]

    assert best.anime.title == "Demon Slayer: Kimetsu no Yaiba"
    assert best.confidence >= SURE


def test_accents_on_latin_letters_dont_count_and_japanese_is_kept():
    assert similarity("Pokémon", "Pokemon") == 1.0
    assert similarity("Atsumare! Gokū World", "Atsumare Goku World") == 1.0
    assert normalize("ガンダム") == "ガンダム"  # its marks are part of the letters


def shown(name: str, *, year: int | None = None, media: str = "movie", **more: object) -> Hit:
    found = {"tv": tv_search, "movie": movie_search}[media]((1, name, date(year or 2000, 1, 1)))
    [hit] = hits(found, "tv" if media == "tv" else "movie")
    return replace(hit, **more)


def test_a_tmdb_find_fits_by_its_names_year_kind_and_being_japanese_animation():
    [film] = group_files(
        [facts(rf"{MOVIES}\Dragon Ball Z - Movie 16 - DB Super BROLY (2018).mkv", minutes=100)]
    )

    right = tmdb_fit(film, shown("Dragon Ball Super: Broly", year=2018), 0)
    other_year = tmdb_fit(film, shown("Dragon Ball Super: Broly", year=2013), 0)
    live_action = tmdb_fit(
        film, shown("Dragon Ball Super: Broly", year=2018, animation=False, japanese=False), 0
    )
    a_show = tmdb_fit(film, shown("Dragon Ball Super: Broly", year=2018, media="tv"), 0)

    assert right >= SURE
    assert right > other_year
    assert right > live_action
    assert right > a_show


def test_a_name_tmdb_knows_among_its_other_names_fits_as_well_as_its_own():
    [episodes] = group_files([facts(r"D:\Anime\Bola de Dragon Z\Bola de Dragon Z - 001.mkv")])
    hit = shown("Dragon Ball Z", year=1989, media="tv")

    assert tmdb_fit(episodes, hit, 0) < SURE
    assert tmdb_fit(episodes, hit, 0, ["Bola de Dragón Z"]) == 100


def test_anilists_entries_for_a_tmdb_find_are_no_surer_than_it_fits():
    [episodes] = group_files([facts(r"D:\Anime\Bola de Dragon Z\Bola de Dragon Z - 001.mkv")])
    hit = shown("Dragon Ball Z", year=1989, media="tv")

    sure = through_tmdb(episodes, hit, 100, entries("dragon-ball-z"))
    doubtful = through_tmdb(episodes, hit, 60, entries("dragon-ball-z"))

    assert sure[0].anime.id == 813
    assert sure[0].confidence >= SURE
    assert sure[0].reasons[0] == "TMDB knows it as Dragon Ball Z"
    assert doubtful[0].confidence == 60
    assert all(guess.confidence >= WORTH_SHOWING for guess in doubtful)


def test_guesses_from_several_lookups_keep_each_entry_at_its_surest():
    [group] = group_files([facts(r"D:\Anime\Dragon Ball Z\Dragon Ball Z - 001.mkv")])
    found = guesses(group, entries("dragon-ball-z"))
    lower = [replace(guess, confidence=guess.confidence - 10) for guess in found]

    together = merged(lower, found)

    assert [guess.confidence for guess in together] == [guess.confidence for guess in found]


def test_a_name_anilist_writes_otherwise_is_put_its_way():
    found = entries("dragonball")  # what AniList finds for "Dragonball": "Dragon Ball", …

    assert respelled("Dragonball GT", found) == "dragon ball gt"
    assert respelled("Dragon Ball GT", found) is None  # nothing to put otherwise
    assert respelled("Mystery Show", found) is None


def test_specials_from_after_their_series_began_still_fit_it():
    group = group_files(
        [
            facts(
                rf"{SPECIALS}\Dragon Ball Z - Special 06 - The History of Trunks (1995 BluRay -"
                " 1080p TRI Audio).mkv",
                minutes=48,
                number=1,
            ),
            facts(
                rf"{SPECIALS}\Dragon Ball Z - Special 01 - Bardock, The Father of Goku (1990"
                " BluRay - 1080p TRI Audio).mkv",
                minutes=48,
                number=2,
            ),
        ]
    )[0]

    best = guesses(group, entries("dragon-ball-z"))[0]

    # A special's year and length are its own, not its series' episodes'.
    assert (best.anime.id, best.confidence >= SURE) == (813, True)
    assert not [reason for reason in best.reasons if reason.startswith(("From", "48 min"))]


def test_a_film_in_two_parts_is_as_long_as_both_together():
    [group] = group_files(
        [
            facts(rf"D:\Anime\Movies\Cowboy Bebop - The Movie (2001) CD{part}.avi", 58, part)
            for part in (1, 2)
        ]
    )

    best = guesses(group, entries("cowboy-bebop"))[0]

    assert (best.anime.id, best.confidence >= SURE) == (5, True)
    assert "116 min fits" in best.reasons


def test_the_wrong_year_counts_against_a_guess():
    right = group_files([facts(r"D:\Anime\Cowboy Bebop (1998)\Cowboy Bebop - 01.mkv")])[0]
    wrong = group_files([facts(r"D:\Anime\Cowboy Bebop (2021)\Cowboy Bebop - 01.mkv")])[0]
    bebop = entries("cowboy-bebop")

    assert guesses(right, bebop)[0].confidence > guesses(wrong, bebop)[0].confidence
    assert "From 1998, not 2021" in guesses(wrong, bebop)[0].reasons


def test_a_length_far_from_the_entrys_counts_against_it():
    short = group_files([facts(r"D:\Anime\Cowboy Bebop\Cowboy Bebop - 01.mkv", minutes=4)])[0]

    best = guesses(short, entries("cowboy-bebop"))[0]

    assert "4 min, not 24" in best.reasons


def test_one_episode_is_counted_as_one():
    files = [
        facts(f"D:/Anime/Cowboy Bebop - Yoseatsume Blues - 0{n}.mkv", number=n) for n in (1, 3)
    ]
    special = [entry for entry in entries("cowboy-bebop") if entry.id == 4037]

    one = guesses(group_files(files[:1])[0], special)[0]
    three = guesses(group_files(files)[0], special)[0]

    assert "1 episode fits" in one.reasons
    assert "Only 1 episode, files go up to 3" in three.reasons


def test_tmdb_has_attack_on_titans_later_parts_under_the_one_show():
    part_two = entries("attack-on-titan-season-3-part-2")[0]
    found = hits(
        tv_search(
            (1429, "Attack on Titan", date(2013, 4, 7)),
            (99999, "Attack on Titan: Junior High", date(2015, 10, 4)),
        ),
        "tv",
    )

    picked = pick_hit(part_two, found)

    assert picked is not None
    assert picked[0].id == 1429


def test_a_live_action_film_loses_to_the_anime_one():
    bebop_movie = next(e for e in entries("cowboy-bebop") if e.id == 5)
    found = hits(
        movie_search(
            (11299, "Cowboy Bebop: The Movie", date(2001, 9, 1)),
        ),
        "movie",
    )
    live_action = Hit(
        1, "movie", "Cowboy Bebop", "Cowboy Bebop", date(2021, 11, 19), False, False, 90
    )

    picked = pick_hit(bebop_movie, [live_action, *found])

    assert picked is not None
    assert picked[0].id == 11299


def test_nothing_alike_on_tmdb_is_no_pick():
    dbz = entries("dragon-ball-z")[0]
    found = hits(tv_search((1, "Sailor Moon", date(1992, 3, 7))), "tv")

    assert pick_hit(dbz, found) is None


def test_season_and_part_words_come_off_the_name():
    assert base_title("Attack on Titan Season 3 Part 2") == "Attack on Titan"
    assert base_title("Shingeki no Kyojin: The Final Season") == "Shingeki no Kyojin"
    assert base_title("Boku no Hero Academia 2nd Season") == "Boku no Hero Academia"
    assert base_title("Mob Psycho 100") == "Mob Psycho 100"
    assert base_title("Season 2") == "Season 2"  # nothing left: keep it as it was


def test_names_compare_without_case_punctuation_or_apostrophes():
    # A curly apostrophe, then a straight one.
    curly = f"Cowboy Bebop: Knockin{chr(0x2019)} on Heaven's Door"
    assert normalize(curly) == "cowboy bebop knockin on heavens door"
    assert similarity("Re:Zero", "Re Zero") == 1.0
    assert similarity("Bebop", "Cowboy Bebop") >= 0.45
    assert similarity("Dragon Ball Z", "Dragon Ball Z Kai") < 1.0
    assert similarity("", "Anything") == 0.0
