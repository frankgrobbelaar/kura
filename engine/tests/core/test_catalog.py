"""Reading AniList's and TMDB's answers into plain values."""

import json
from datetime import date
from pathlib import Path
from typing import cast

from kura.core.catalog import TitleKind, anime, anime_list, film, hits, plain_text, show
from kura.core.fields import Json
from tests.tmdb_data import DBZ_SEASONS, movie_details, tv_details, tv_search

ANILIST = Path(__file__).parent.parent / "data" / "anilist"


def answer(name: str) -> Json:
    """A real AniList answer to a search, saved in tests/data/anilist."""
    data: Json = json.loads((ANILIST / f"{name}.json").read_text(encoding="utf-8"))
    return data


def test_an_anilist_entry_has_every_name_its_kind_and_its_dates():
    dbz = anime_list(answer("dragon-ball-z"))[0]

    assert (dbz.id, dbz.title, dbz.episodes) == (813, "Dragon Ball Z", 291)
    assert dbz.kind is TitleKind.SERIES
    # The English title is also the romaji one, so it's listed once.
    assert dbz.titles[:3] == ("Dragon Ball Z", "ドラゴンボールZ", "DBZ")
    assert "Dragonball Z" in dbz.titles
    assert (dbz.start, dbz.end, dbz.minutes) == (date(1989, 4, 26), date(1996, 1, 31), 24)
    assert not dbz.airing
    assert (dbz.cover or "").startswith("https://")


def test_an_entry_knows_its_sequels_films_and_specials_but_not_the_manga():
    dbz = anime_list(answer("dragon-ball-z"))[0]

    sequel = next(r for r in dbz.related if r.relation == "SEQUEL")
    assert (sequel.id, sequel.title, sequel.kind) == (225, "Dragon Ball GT", TitleKind.SERIES)
    assert any(r.kind is TitleKind.MOVIE for r in dbz.related)
    assert all(r.relation != "ADAPTATION" for r in dbz.related)  # the manga


def test_films_ovas_and_specials_are_told_apart():
    found = {entry.id: entry.kind for entry in anime_list(answer("cowboy-bebop"))}

    assert found[1] is TitleKind.SERIES
    assert found[5] is TitleKind.MOVIE
    assert found[4037] is TitleKind.SPECIAL
    assert {e.kind for e in anime_list(answer("dragon-ball-z"))} >= {TitleKind.OVA}


def test_a_show_still_airing_has_no_end_yet():
    one_piece = anime_list(answer("one-piece"))[0]

    assert one_piece.airing
    assert one_piece.episodes is None
    assert one_piece.next_episode is not None


def test_an_entry_not_out_yet_has_no_kind_and_a_rough_date():
    upcoming = next(e for e in anime_list(answer("one-piece")) if e.id == 171630)

    assert upcoming.kind is None
    assert upcoming.start == date(2027, 2, 1)  # AniList knows the month, not the day


def test_odd_answers_are_skipped_rather_than_crash():
    assert anime({"id": 1}) is None  # no title at all
    assert anime_list({"data": None}) == []
    assert anime_list({"errors": [{"message": "Too Many Requests."}]}) == []


def test_tmdb_search_results_say_whether_they_are_japanese_animation():
    found = hits(tv_search((12971, "Dragon Ball Z", date(1989, 4, 26))), "tv")

    assert len(found) == 1
    assert (found[0].id, found[0].title, found[0].year) == (12971, "Dragon Ball Z", 1989)
    assert found[0].animation
    assert found[0].japanese


def test_a_tmdb_show_has_every_episode_in_season_order():
    details = tv_details(
        12971,
        "Dragon Ball Z",
        DBZ_SEASONS,
        first_aired=date(1989, 4, 26),
        specials=2,
        titles={(1, 1): "The New Threat"},
    )

    dbz = show(details)

    assert dbz is not None
    assert dbz.seasons == tuple(range(1, 10))
    assert len(dbz.season(1)) == 39
    assert len(dbz.season(0)) == 2  # the specials
    assert sum(len(dbz.season(n)) for n in dbz.seasons) == 291
    first = dbz.season(1)[0]
    assert (first.title, first.aired) == ("The New Threat", date(1989, 4, 26))
    assert not dbz.airing
    assert (dbz.poster, dbz.backdrop) == ("/poster-12971.jpg", "/backdrop-12971.jpg")


def test_a_tmdb_show_still_in_production_is_airing():
    details = tv_details(37854, "One Piece", (61,), first_aired=date(1999, 10, 20))
    details["status"] = "Returning Series"

    one_piece = show(details)

    assert one_piece is not None
    assert one_piece.airing


def test_a_tmdb_film():
    bebop = film(movie_details(11299, "Cowboy Bebop: The Movie", date(2001, 9, 1), 115))

    assert bebop is not None
    assert (bebop.title, bebop.year, bebop.minutes) == ("Cowboy Bebop: The Movie", 2001, 115)
    assert bebop.backdrop == "/backdrop-movie-11299.jpg"


def test_an_anilist_entry_has_its_banner_for_a_background():
    found = {
        "data": {
            "Page": {
                "media": [
                    {
                        "id": 1,
                        "title": {"english": "Cowboy Bebop"},
                        "format": "TV",
                        "bannerImage": "https://s4.anilist.co/file/anilistcdn/media/anime/banner/1.jpg",
                    }
                ]
            }
        }
    }

    [bebop] = anime_list(found)

    assert bebop.banner == "https://s4.anilist.co/file/anilistcdn/media/anime/banner/1.jpg"


def test_a_tmdb_show_says_what_its_about_panel_shows():
    details: dict[str, object] = {
        **tv_details(9, "Starfall Academy", (2,), first_aired=date(2019, 4, 3)),
        "overview": "A school between the stars.",
        "genres": [{"id": 16, "name": "Animation"}, {"id": 10765, "name": "Sci-Fi & Fantasy"}],
        "production_companies": [{"name": "Studio Kite"}, {"name": "Comet Films"}],
        "episode_run_time": [24],
        "last_air_date": "2019-04-10",
    }
    season = cast("dict[str, list[dict[str, object]]]", details["season/1"])
    season["episodes"][0]["overview"] = "Mira arrives at the academy."

    found = show(details)

    assert found is not None
    # Animation goes without saying.
    assert (found.overview, found.genres, found.studio) == (
        "A school between the stars.",
        ("Sci-Fi & Fantasy",),
        "Studio Kite",
    )
    assert (found.status, found.last_aired, found.minutes) == ("finished", date(2019, 4, 10), 24)
    assert [episode.overview for episode in found.episodes] == [
        "Mira arrives at the academy.",
        None,
    ]


def test_a_tmdb_status_is_said_in_kuras_words():
    def standing(status: str) -> str | None:
        details = tv_details(9, "Starfall", (1,), first_aired=date(2019, 4, 3), status=status)
        found = show(details)
        return found.status if found else None

    assert [standing(s) for s in ("Ended", "Canceled", "Planned", "Returning Series")] == [
        "finished",
        "cancelled",
        "coming",
        "airing",
    ]


def test_a_show_ends_with_its_seasons_latest_episode_not_a_special_years_on():
    details: dict[str, object] = {
        **tv_details(
            9,
            "Starfall",
            (2,),
            first_aired=date(2019, 4, 3),
            specials=1,
            special_dates=(date(2024, 12, 24),),
        ),
        "last_air_date": "2024-12-24",
    }

    found = show(details)

    assert found is not None
    assert found.last_aired == date(2019, 4, 10)


def test_a_film_being_made_is_still_to_come():
    def standing(status: str) -> str | None:
        found = film({**movie_details(5, "Starfall", date(2027, 8, 1), 0), "status": status})
        return found.status if found else None

    assert [standing(s) for s in ("In Production", "Post Production", "Released")] == [
        "coming",
        "coming",
        "finished",
    ]


def test_a_tmdb_film_says_what_its_about_panel_shows():
    details = {
        **movie_details(5, "Starfall: The First Comet", date(2022, 8, 1), 102),
        "overview": "The comet returns.",
        "genres": [{"id": 16, "name": "Animation"}, {"id": 18, "name": "Drama"}],
        "production_companies": [{"name": "Studio Kite"}],
        "status": "Released",
    }

    found = film(details)

    assert found is not None
    assert (found.overview, found.genres, found.studio, found.status, found.minutes) == (
        "The comet returns.",
        ("Drama",),
        "Studio Kite",
        "finished",
        102,
    )


def test_an_anilist_entry_says_its_synopsis_genres_and_studio():
    media: dict[str, object] = {
        "id": 9,
        "format": "TV",
        "status": "HIATUS",
        "title": {"english": "Starfall Academy", "romaji": "Hoshifuri Gakuen"},
        "description": "Mira joins the academy.<br><br>Her rival <i>Kai</i> waits. (Source: Comet)",
        "genres": ["Action", "Sci-Fi", "Action"],
        "studios": {"nodes": [{"name": "Studio Kite"}]},
        "coverImage": {
            "large": "https://s4.anilist.co/cover-l.jpg",
            "extraLarge": "https://s4.anilist.co/cover-xl.jpg",
        },
    }

    entry = anime(media)

    assert entry is not None
    assert entry.description == "Mira joins the academy.\n\nHer rival Kai waits."
    assert (entry.genres, entry.studio, entry.standing) == (
        ("Action", "Sci-Fi"),
        "Studio Kite",
        "paused",
    )
    assert entry.cover_big == "https://s4.anilist.co/cover-xl.jpg"


def test_a_synopsis_keeps_no_markup_spoilers_or_note_of_its_source():
    assert plain_text("A duel. ~!The rival is her brother.!~ Who wins?") == "A duel. Who wins?"
    assert plain_text("Tom &amp; Jerry&#039;s __big__ day") == "Tom & Jerry's big day"
    assert plain_text("One.<br>\nTwo.\n\n\n[Written by MAL Rewrite]") == "One.\n\nTwo."
    assert plain_text("<br>") is None
    assert plain_text(None) is None
