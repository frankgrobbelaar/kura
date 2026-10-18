import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router";
import { afterEach, describe, expect, it, vi } from "vitest";
import { ShelfCard } from "@/components/title-card";
import {
  EngineProvider,
  type FranchiseMissing,
  type FranchiseSummary,
  type MissingTitle,
  type TitleSummary,
} from "@/lib/engine";
import { fakeEngine, franchiseOf, READY } from "@/test/engine";
import { FranchisePage } from "./franchise-page";

const shell = vi.hoisted(() => ({ invoke: vi.fn() }));

vi.mock("@tauri-apps/api/core", () => ({ invoke: shell.invoke }));
vi.mock("@tauri-apps/api/event", () => ({ listen: async () => () => {} }));

const DRAGON_BALL: TitleSummary = {
  id: 7,
  kind: "series",
  name: "Dragon Ball",
  year: 1986,
  released: "1986-02-26",
  airing: false,
  hasPoster: false,
  files: 150,
  added: "2026-10-11T09:44:00+00:00",
  aired: 153,
  present: 150,
  missing: 3,
  specialsMissing: 0,
  upcoming: 0,
};
const DBZ: TitleSummary = {
  ...DRAGON_BALL,
  id: 8,
  name: "Dragon Ball Z",
  year: 1989,
  released: "1989-04-26",
  files: 291,
  aired: 291,
  present: 291,
  missing: 0,
};
const BATTLE_OF_GODS: TitleSummary = {
  ...DRAGON_BALL,
  id: 9,
  kind: "movie",
  name: "Dragon Ball Z: Battle of Gods",
  year: 2013,
  released: "2013-03-30",
  files: 1,
  aired: 0,
  present: 0,
  missing: 0,
};
const DRAGON_BALL_FRANCHISE = franchiseOf([DRAGON_BALL, DBZ, BATTLE_OF_GODS]);

// What AniList ties to Dragon Ball that the library has no part of.
const CURSE_OF_THE_BLOOD_RUBIES: MissingTitle = {
  anilistId: 502,
  kind: "movie",
  name: "Dragon Ball: Curse of the Blood Rubies",
  year: 1986,
  released: "1986-12-20",
  episodes: 1,
  coming: false,
  airing: false,
  cover: null,
  overview: null,
  genres: [],
  studio: null,
};
const KAI: MissingTitle = {
  ...CURSE_OF_THE_BLOOD_RUBIES,
  anilistId: 6033,
  kind: "series",
  name: "Dragon Ball Z Kai",
  year: 2009,
  released: "2009-04-05",
  episodes: 97,
};
const BEERUS: MissingTitle = {
  ...KAI,
  anilistId: 206814,
  name: "Dragon Ball Super: Beerus",
  year: 2026,
  released: "2026-10-11",
  episodes: null,
  airing: true,
};
const GINGA_PATROL: MissingTitle = {
  ...KAI,
  anilistId: 206812,
  name: "Dragon Ball Super: Ginga Patrol",
  year: null,
  released: null,
  episodes: null,
  coming: true,
};

function renderWithEngine(children: React.ReactNode, at: string) {
  shell.invoke.mockImplementation(async (command: string) =>
    command === "engine_status" ? READY : undefined,
  );
  const queries = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={queries}>
      <EngineProvider>
        <MemoryRouter initialEntries={[at]}>
          <Routes>
            <Route path="/franchises/:id" element={children} />
            <Route path="/titles/:id" element={<p>A title</p>} />
            <Route path="*" element={<p>Home</p>} />
          </Routes>
        </MemoryRouter>
      </EngineProvider>
    </QueryClientProvider>,
  );
  return queries;
}

afterEach(() => {
  vi.unstubAllGlobals();
  shell.invoke.mockReset();
});

describe("ShelfCard", () => {
  it.each<[string, FranchiseSummary, string]>([
    ["a title on its own", franchiseOf([DRAGON_BALL]), "TV series · 1986 · 153 episodes"],
    [
      "one series and its film",
      franchiseOf([DBZ, BATTLE_OF_GODS]),
      "TV series · 291 episodes · 1 movie",
    ],
    ["several series", DRAGON_BALL_FRANCHISE, "Franchise · 2 series · 1 movie"],
    [
      "films alone",
      franchiseOf([BATTLE_OF_GODS, { ...BATTLE_OF_GODS, id: 10 }]),
      "Franchise · 2 movies",
    ],
  ])("says what %s is", (_, franchise, facts) => {
    fakeEngine({});
    renderWithEngine(<ShelfCard franchise={franchise} />, "/franchises/1");

    expect(screen.getByText(facts)).toBeInTheDocument();
  });
});

describe("FranchisePage", () => {
  it("shows the franchise and its titles, oldest release first", async () => {
    const fetch = fakeEngine({ "/franchises/7": DRAGON_BALL_FRANCHISE });
    renderWithEngine(<FranchisePage />, "/franchises/7");

    expect(
      await screen.findByRole("heading", { name: "Dragon Ball", level: 1 }),
    ).toBeInTheDocument();
    expect(screen.getByText("Franchise")).toBeInTheDocument();
    expect(screen.getByText("1986 to 2013 · 2 series · 1 movie")).toBeInTheDocument();
    expect(screen.getByText("441 of 444 episodes")).toBeInTheDocument();
    expect(screen.getByText("3 titles · by type, oldest release first")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Series 2", level: 3 })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Movies 1", level: 3 })).toBeInTheDocument();
    const cards = screen.getAllByRole("link", { name: /Dragon Ball/ });
    expect(cards.map((card) => card.textContent)).toEqual([
      expect.stringContaining("TV series · 1986"),
      expect.stringContaining("TV series · 1989"),
      expect.stringContaining("Movie · 2013"),
    ]);
    expect(fetch.mock.calls.some(([input]) => String(input).endsWith("?sort=released"))).toBe(true);
  });

  it("lists the series first, then the films, each oldest release first", async () => {
    const rubies = { ...BATTLE_OF_GODS, id: 10, name: "Dragon Ball: Curse of the Blood Rubies" };
    const curse = { ...rubies, year: 1986, released: "1986-12-20" };
    fakeEngine({ "/franchises/7": franchiseOf([DRAGON_BALL, curse, DBZ, BATTLE_OF_GODS]) });
    renderWithEngine(<FranchisePage />, "/franchises/7");

    await screen.findByRole("heading", { name: "Movies 2", level: 3 });
    const cards = screen.getAllByRole("link", { name: /Dragon Ball/ });

    expect(cards.map((card) => card.getAttribute("href"))).toEqual([
      "/titles/7", // Dragon Ball, 1986
      "/titles/8", // Dragon Ball Z, 1989
      "/titles/10", // Curse of the Blood Rubies, 1986
      "/titles/9", // Battle of Gods, 2013
    ]);
  });

  it("lists every type together when what's missing or new comes first", async () => {
    fakeEngine({ "/franchises/7": DRAGON_BALL_FRANCHISE });
    renderWithEngine(<FranchisePage />, "/franchises/7");

    (await screen.findByRole("radio", { name: "Most missing" })).click();

    expect(await screen.findByText("3 titles · most missing first")).toBeInTheDocument();
    expect(screen.queryByRole("heading", { level: 3 })).not.toBeInTheDocument();
  });

  it("sorts by name too, and leads to each title", async () => {
    const fetch = fakeEngine({ "/franchises/7": DRAGON_BALL_FRANCHISE });
    renderWithEngine(<FranchisePage />, "/franchises/7");

    (await screen.findByRole("radio", { name: "Name" })).click();
    await waitFor(() =>
      expect(fetch.mock.calls.some(([input]) => String(input).endsWith("?sort=name"))).toBe(true),
    );
    screen.getByRole("link", { name: /Battle of Gods/ }).click();

    expect(await screen.findByText("A title")).toBeInTheDocument();
  });

  it("puts in the titles the library has no part of, in their places, when asked", async () => {
    fakeEngine({
      "/franchises/7": DRAGON_BALL_FRANCHISE,
      "/franchises/7/missing": {
        titles: [CURSE_OF_THE_BLOOD_RUBIES, KAI, BEERUS, GINGA_PATROL],
        looking: false,
      },
    });
    renderWithEngine(<FranchisePage />, "/franchises/7");

    const toggle = await screen.findByRole("button", { name: "Missing titles 4" });
    expect(toggle).toHaveAttribute("aria-pressed", "false");
    expect(screen.queryByText("Not in library")).not.toBeInTheDocument();
    toggle.click();

    expect(await screen.findByText("3 of 7 titles · by type, oldest release first")).toBeVisible();
    expect(toggle).toHaveAttribute("aria-pressed", "true");
    const series = screen.getByRole("region", { name: "Series 5" });
    expect(
      within(series)
        .getAllByRole("listitem")
        .map((card) => card.textContent),
    ).toEqual([
      expect.stringContaining("Dragon Ball"), // 1986, the library's
      expect.stringContaining("Dragon Ball Z"), // 1989, the library's
      expect.stringMatching(/Not in library.*Dragon Ball Z Kai.*TV series · 2009 · 97 episodes/),
      expect.stringMatching(/Not in library.*Dragon Ball Super: Beerus.*TV series · 2026 · airing/),
      expect.stringMatching(/Coming.*Dragon Ball Super: Ginga Patrol/), // undated, last
    ]);
    const movies = screen.getByRole("region", { name: "Movies 2" });
    expect(
      within(movies)
        .getAllByRole("listitem")
        .map((card) => card.textContent),
    ).toEqual([
      expect.stringMatching(/Not in library.*Curse of the Blood Rubies.*Movie · 1986$/),
      expect.stringContaining("Battle of Gods"),
    ]);
    // Kura has no page for a title it doesn't have.
    expect(screen.queryByRole("link", { name: /Kai|Beerus|Blood Rubies/ })).not.toBeInTheDocument();

    toggle.click();
    expect(await screen.findByText("3 titles · by type, oldest release first")).toBeVisible();
    expect(screen.queryByText("Not in library")).not.toBeInTheDocument();
  });

  it("finds titles by name, the ones it lacks too, and keeps the search with them", async () => {
    fakeEngine({
      "/franchises/7": DRAGON_BALL_FRANCHISE,
      "/franchises/7/missing": { titles: [CURSE_OF_THE_BLOOD_RUBIES, KAI], looking: false },
    });
    renderWithEngine(<FranchisePage />, "/franchises/7?missing");

    const search = await screen.findByRole("searchbox", { name: "Search Dragon Ball" });
    expect(search).toHaveAttribute("placeholder", "Search 5 titles");
    fireEvent.change(search, { target: { value: "z" } });

    expect(await screen.findByText("3 of 5 titles · by type, oldest release first")).toBeVisible();
    expect(
      within(screen.getByRole("region", { name: "Series 2" }))
        .getAllByRole("listitem")
        .map((card) => card.textContent),
    ).toEqual([
      expect.stringContaining("Dragon Ball Z"),
      expect.stringMatching(/Not in library.*Dragon Ball Z Kai/),
    ]);
    // Taking the titles it lacks away keeps the search.
    screen.getByRole("button", { name: "Missing titles 2" }).click();
    expect(await screen.findByText("2 of 3 titles · by type, oldest release first")).toBeVisible();
    expect(search).toHaveValue("z");

    fireEvent.change(search, { target: { value: "Cell" } });
    expect(await screen.findByRole("status")).toHaveTextContent(
      "No title in Dragon Ball goes by “Cell”.",
    );
  });

  it("says what the franchise is about and the years it spans", async () => {
    fakeEngine({
      "/franchises/7": DRAGON_BALL_FRANCHISE,
      "/titles/7/about": {
        overview: "Goku sets out to find the seven Dragon Balls.",
        genres: [],
        studio: null,
        status: "finished",
        started: "1986-02-26",
        ended: null,
        minutes: null,
        anilistId: 223,
        tmdbType: "tv",
        tmdbId: 12609,
      },
    });
    renderWithEngine(<FranchisePage />, "/franchises/7");

    const header = await screen.findByRole("region", { name: "Dragon Ball" });
    expect(header).toHaveTextContent("1986 to 2013 · 2 series · 1 movie");
    expect(await within(header).findByText(/Goku sets out to find/)).toBeVisible();
  });

  it("opens a title the library lacks to say what AniList knows of it", async () => {
    fakeEngine({
      "/franchises/7": DRAGON_BALL_FRANCHISE,
      "/franchises/7/missing": {
        titles: [
          {
            ...KAI,
            overview: "A remastered retelling, closer to the manga.",
            genres: ["Action", "Adventure"],
            studio: "Toei Animation",
          },
        ],
        looking: false,
      },
    });
    renderWithEngine(<FranchisePage />, "/franchises/7?missing");

    const card = await screen.findByRole("button", { name: "Dragon Ball Z Kai: not in library" });
    // A long name wraps rather than trails off, and says itself in full on hover.
    expect(within(card).getByText("Dragon Ball Z Kai")).toHaveClass("line-clamp-2");
    card.click();

    const sheet = await screen.findByRole("dialog", { name: "Dragon Ball Z Kai" });
    expect(sheet).toHaveTextContent("TV series · 2009 · 97 episodes");
    expect(sheet).toHaveTextContent("Not in your library");
    expect(sheet).toHaveTextContent("StudioToei Animation");
    expect(within(sheet).getByRole("list", { name: "Genres" })).toHaveTextContent(
      "ActionAdventure",
    );
    expect(sheet).toHaveTextContent("A remastered retelling, closer to the manga.");
    within(sheet).getByRole("button", { name: "On AniList" }).click();
    await waitFor(() =>
      expect(shell.invoke).toHaveBeenCalledWith("open_anilist_page", { id: 6033 }),
    );

    within(sheet).getByRole("button", { name: "Close" }).click();
    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
  });

  it("opens with the titles it lacks put in, when a title's page leads here", async () => {
    fakeEngine({
      "/franchises/7": DRAGON_BALL_FRANCHISE,
      "/franchises/7/missing": { titles: [KAI], looking: false },
    });
    renderWithEngine(<FranchisePage />, "/franchises/7?missing");

    expect(await screen.findByText("3 of 4 titles · by type, oldest release first")).toBeVisible();
    expect(screen.getByRole("button", { name: "Missing titles 1" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
    expect(screen.getByText("Not in library")).toBeVisible();
  });

  it("is a title alone in the library's own page for what its franchise lacks", async () => {
    fakeEngine({
      "/franchises/7": franchiseOf([DRAGON_BALL]),
      "/franchises/7/missing": { titles: [KAI], looking: false },
    });
    renderWithEngine(<FranchisePage />, "/franchises/7");

    expect(await screen.findByText("1 title · by type, oldest release first")).toBeVisible();
    expect(screen.getByText("TV series")).toBeVisible(); // what it is, not "Franchise"
    screen.getByRole("button", { name: "Missing titles 1" }).click();
    expect(await screen.findByText("1 of 2 titles · by type, oldest release first")).toBeVisible();
  });

  it("lists the titles it lacks after its own when what's in the library comes first", async () => {
    fakeEngine({
      "/franchises/7": DRAGON_BALL_FRANCHISE,
      "/franchises/7/missing": { titles: [CURSE_OF_THE_BLOOD_RUBIES], looking: false },
    });
    renderWithEngine(<FranchisePage />, "/franchises/7");

    (await screen.findByRole("radio", { name: "Recently added" })).click();
    (await screen.findByRole("button", { name: "Missing titles 1" })).click();

    expect(await screen.findByText("3 of 4 titles · newest added first")).toBeVisible();
    expect(screen.getAllByRole("listitem").at(-1)).toHaveTextContent("Curse of the Blood Rubies");
  });

  it("says it's still looking the rest of the franchise up", async () => {
    fakeEngine({
      "/franchises/7": DRAGON_BALL_FRANCHISE,
      "/franchises/7/missing": { titles: [], looking: true },
    });
    renderWithEngine(<FranchisePage />, "/franchises/7");

    (await screen.findByRole("button", { name: "Missing titles …" })).click();

    expect(
      await screen.findByText(
        "3 of 3 titles · still looking up the rest · by type, oldest release first",
      ),
    ).toBeVisible();
  });

  it("offers no missing titles once the library has the whole franchise", async () => {
    let rest: FranchiseMissing = { titles: [KAI], looking: false };
    fakeEngine({ "/franchises/7": DRAGON_BALL_FRANCHISE, "/franchises/7/missing": () => rest });
    const queries = renderWithEngine(<FranchisePage />, "/franchises/7");
    (await screen.findByRole("button", { name: "Missing titles 1" })).click();
    expect(await screen.findByText("3 of 4 titles · by type, oldest release first")).toBeVisible();

    // A scan finds the last one, and every screen asks again.
    rest = { titles: [], looking: false };
    await act(async () => {
      await queries.invalidateQueries();
    });

    expect(await screen.findByText("3 titles · by type, oldest release first")).toBeVisible();
    expect(screen.queryByRole("button", { name: /Missing titles/ })).not.toBeInTheDocument();
  });

  it("shows the page's shape while it loads", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() => new Promise<Response>(() => {})),
    );
    renderWithEngine(<FranchisePage />, "/franchises/7");

    expect(
      await screen.findByRole("status", { name: "Loading the franchise" }),
    ).toBeInTheDocument();
  });

  it("says when the engine couldn't find it", async () => {
    fakeEngine({});
    renderWithEngine(<FranchisePage />, "/franchises/99");

    expect(await screen.findByRole("alert")).toBeInTheDocument();
    expect(screen.queryByRole("status")).not.toBeInTheDocument(); // no shapes once it failed
    screen.getByRole("link", { name: "Library" }).click();
    expect(await screen.findByText("Home")).toBeInTheDocument();
  });
});
