"""AniList and TMDB as the tests stand them in: real AniList answers saved in tests/data/anilist,
and TMDB answers built in TMDB's shape (tests/tmdb_data.py), for Dragon Ball Z, Cowboy Bebop and
My Hero Academia, and The Red Turtle, which only TMDB knows."""

import json
from collections.abc import Callable, Mapping
from datetime import date
from pathlib import Path
from typing import cast

from kura.anilist import API as ANILIST
from kura.tmdb import API as TMDB
from tests.fake_web import Answer, Asked, FakeWeb
from tests.tmdb_data import DBZ_SEASONS, movie_details, movie_search, tv_details, tv_search

SAVED = Path(__file__).parent / "data" / "anilist"

# What AniList answers, by what it's asked: real answers saved in tests/data/anilist. These are
# the answers to exactly these searches; as AniList does, a search with a word none of an entry's
# names has finds nothing ("Dragonball GT", "Dragon Ball Z - Movie 03 - The Tree of Might").
ANILIST_EXACT = {
    "dragon ball z: the tree of might": "dragon-ball-z-the-tree-of-might",
    "dragonball": "dragonball",
    "dragon ball gt": "dragon-ball-gt",
    "dragon ball super broly": "dragon-ball-super-broly",
    "dragon ball super: broly": "dragon-ball-super-broly",
}
# These answer any search that starts with them, more kindly than AniList.
ANILIST_ANSWERS = {
    "dragon ball z": "dragon-ball-z",
    "dbz": "dragon-ball-z",
    "cowboy bebop": "cowboy-bebop",
    "one piece": "one-piece",
    "my hero academia": "my-hero-academia",
}

DBZ_DETAILS = {
    **tv_details(12971, "Dragon Ball Z", DBZ_SEASONS, first_aired=date(1989, 4, 26)),
    "overview": "Five years after winning the World Martial Arts tournament, Goku is now living a"
    " peaceful life with his wife and son.",
    "genres": [
        {"id": 16, "name": "Animation"},
        {"id": 10759, "name": "Action & Adventure"},
        {"id": 10765, "name": "Sci-Fi & Fantasy"},
    ],
    "production_companies": [{"id": 5542, "name": "Toei Animation"}],
    "episode_run_time": [24],
    "last_air_date": "1996-01-31",
}
BEBOP_DETAILS = tv_details(
    30991,
    "Cowboy Bebop",
    (26,),
    first_aired=date(1998, 4, 3),
    specials=3,
    special_dates=(date(1998, 4, 3), date(1998, 6, 26), date(2012, 12, 21)),
    titles={(1, 1): "Asteroid Blues", (1, 2): "Stray Dog Strut"},
)


# My Hero Academia's first seven seasons, and two of its specials by the names TMDB gives them.
HEROES_DETAILS = tv_details(
    65930,
    "My Hero Academia",
    (13, 25, 25, 25, 25, 25, 21),
    first_aired=date(2016, 4, 3),
    specials=2,
    special_dates=(date(2020, 8, 16), date(2020, 8, 16)),
    titles={
        (0, 1): "Make It! Do-or-Die Survival Training (1)",
        (0, 2): "Make It! Do-or-Die Survival Training (2)",
    },
)


# The Red Turtle, a co-production of Studio Ghibli's that AniList doesn't list: TMDB knows it by
# its English and French names, and by its Japanese one among its others.
RED_TURTLE = 337703
RED_TURTLE_NAMES = ("the red turtle", "la tortue rouge", "レッドタートル ある島の物語")
RED_TURTLE_FOUND = {
    "page": 1,
    "results": [
        {
            "id": RED_TURTLE,
            "title": "The Red Turtle",
            "original_title": "La Tortue rouge",
            "release_date": "2016-06-29",
            "genre_ids": [16, 14],
            "original_language": "fr",
            "poster_path": f"/poster-movie-{RED_TURTLE}.jpg",
            "popularity": 20.0,
        }
    ],
}


def anilist(airing: Mapping[int, int]) -> Callable[[Asked], object]:
    """AniList's searches and entries. `airing` moves a show's next episode on in its answers
    about one entry: what AniList says now, while a search kept from days ago says less."""

    def answer(asked: Asked) -> object:
        variables = cast("dict[str, object]", asked.payload["variables"])
        if "id" in variables:
            anime_id = cast("int", variables["id"])
            media = saved_entry(anime_id)
            if media is not None and anime_id in airing:
                known = cast("dict[str, object]", media)
                media = {**known, "nextAiringEpisode": {"episode": airing[anime_id]}}
            return {"data": {"Media": media}}
        search = str(variables.get("search", "")).casefold()
        file = ANILIST_EXACT.get(search) or next(
            (f for name, f in ANILIST_ANSWERS.items() if search.startswith(name)), None
        )
        if file is None:
            return {"data": {"Page": {"media": []}}}
        return json.loads((SAVED / f"{file}.json").read_text(encoding="utf-8"))

    return answer


def saved_entry(anime_id: int) -> object:
    """One entry from the saved searches, as AniList answers a question about it."""
    for file in sorted(SAVED.glob("*.json")):
        answer = json.loads(file.read_text(encoding="utf-8"))
        for media in answer["data"]["Page"]["media"]:
            if media["id"] == anime_id:
                return media
    return None


def tmdb_show(details: dict[str, object]) -> Callable[[Asked], object]:
    """A /tv/{id} that answers the way TMDB does: the show, or the show with seasons appended."""

    def answer(asked: Asked) -> object:
        wanted = asked.query.get("append_to_response")
        if wanted is None:
            return {key: value for key, value in details.items() if not key.startswith("season/")}
        return {"id": details["id"], **{key: details[key] for key in wanted.split(",")}}

    return answer


def tmdb_search_tv(asked: Asked) -> object:
    query = asked.query["query"].casefold()
    # TMDB knows Dragon Ball Z by its Spanish name too, as AniList doesn't.
    if query in ("dragon ball z", "bola de dragon z"):
        return tv_search((12971, "Dragon Ball Z", date(1989, 4, 26)))
    if query == "cowboy bebop":
        return tv_search((30991, "Cowboy Bebop", date(1998, 4, 3)))
    if query == "my hero academia":
        return tv_search((65930, "My Hero Academia", date(2016, 4, 3)))
    return {"results": []}


def tmdb_search_movie(asked: Asked) -> object:
    query = asked.query["query"].casefold()
    if query.startswith("cowboy bebop"):
        return movie_search((11299, "Cowboy Bebop: The Movie", date(2001, 9, 1)))
    if query.startswith("my hero academia"):
        return movie_search((505262, "My Hero Academia: Two Heroes", date(2018, 8, 3)))
    if query in RED_TURTLE_NAMES:
        return RED_TURTLE_FOUND
    return {"results": []}


def internet(*, tmdb: bool = True, airing: Mapping[int, int] | None = None) -> FakeWeb:
    answers: dict[str, Answer] = {f"POST {ANILIST}": anilist(airing or {})}
    if tmdb:
        answers |= {
            f"GET {TMDB}/search/tv": tmdb_search_tv,
            f"GET {TMDB}/search/movie": tmdb_search_movie,
            f"GET {TMDB}/tv/12971": tmdb_show(DBZ_DETAILS),
            f"GET {TMDB}/tv/12971/alternative_titles": {
                "id": 12971,
                "results": [{"iso_3166_1": "ES", "title": "Bola de Dragón Z", "type": ""}],
            },
            f"GET {TMDB}/tv/30991": tmdb_show(BEBOP_DETAILS),
            f"GET {TMDB}/movie/11299": movie_details(
                11299, "Cowboy Bebop: The Movie", date(2001, 9, 1), 115
            ),
            f"GET {TMDB}/tv/65930": tmdb_show(HEROES_DETAILS),
            f"GET {TMDB}/movie/505262": movie_details(
                505262, "My Hero Academia: Two Heroes", date(2018, 8, 3), 96
            ),
            f"GET {TMDB}/movie/{RED_TURTLE}": {
                **movie_details(RED_TURTLE, "The Red Turtle", date(2016, 6, 29), 80),
                "original_title": "La Tortue rouge",
            },
            f"GET {TMDB}/movie/{RED_TURTLE}/alternative_titles": {
                "id": RED_TURTLE,
                "titles": [
                    {"iso_3166_1": "JP", "title": "レッドタートル ある島の物語", "type": ""}
                ],
            },
        }
    return FakeWeb(answers)
