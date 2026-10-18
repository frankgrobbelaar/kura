from datetime import date

from kura.core.about import About, Said, about

TMDB = Said(
    overview="A school between the stars.",
    genres=("Sci-Fi & Fantasy",),
    studio="Comet Films",
    status="airing",
    started=date(2019, 4, 3),
    minutes=None,
)
ANILIST = Said(
    overview="Mira joins the academy.",
    genres=("Mecha", "School"),
    studio="Studio Kite",
    status="airing",
    started=date(2019, 4, 3),
    ended=date(2019, 6, 26),
    minutes=23,
)


def test_tmdbs_synopsis_and_anilists_genres_and_studio_come_first():
    found = about(TMDB, ANILIST, [24, 24, 25])

    assert found == About(
        overview="A school between the stars.",
        genres=("Mecha", "School"),
        studio="Studio Kite",
        status="airing",
        started=date(2019, 4, 3),
        ended=date(2019, 6, 26),
        minutes=24,  # what most of its episodes last
    )


def test_either_fills_in_what_the_other_doesnt_say():
    found = about(Said(started=date(2019, 4, 3)), ANILIST)

    assert (found.overview, found.genres, found.minutes) == (
        "Mira joins the academy.",
        ("Mecha", "School"),
        23,
    )
    assert about(TMDB, None).genres == ("Sci-Fi & Fantasy",)
