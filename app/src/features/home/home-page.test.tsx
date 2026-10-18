import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router";
import { afterEach, describe, expect, it, vi } from "vitest";
import { PlayerLayer } from "@/features/player/player";
import { PlayerProvider } from "@/features/player/player-context";
import {
  type Continuing,
  EngineProvider,
  type EngineStatus,
  type Hearable,
  type TitleSummary,
} from "@/lib/engine";
import { fakeEngine, franchiseOf, NO_LIBRARY, NO_SCAN, READY, SETTINGS } from "@/test/engine";
import { HomePage } from "./home-page";

const shell = vi.hoisted(() => ({ invoke: vi.fn() }));

vi.mock("@tauri-apps/api/core", () => ({ invoke: shell.invoke }));
vi.mock("@tauri-apps/api/event", () => ({ listen: async () => () => {} }));
vi.mock("@tauri-apps/api/window", () => ({
  getCurrentWindow: () => ({ setFullscreen: async () => {} }),
}));

const FOLDER = {
  id: 1,
  path: "D:\\Anime",
  addedAt: "2026-10-11T09:30:00+00:00",
  available: true,
  files: 3,
  unread: 0,
  problems: 1,
};

const DBZ: TitleSummary = {
  id: 1,
  kind: "series",
  name: "Dragon Ball Z",
  year: 1989,
  released: "1989-04-26",
  airing: false,
  hasPoster: false,
  files: 287,
  added: "2026-10-11T09:44:00+00:00",
  aired: 291,
  present: 287,
  missing: 4,
  specialsMissing: 0,
  upcoming: 0,
};
const BEBOP: TitleSummary = {
  ...DBZ,
  id: 2,
  name: "Cowboy Bebop",
  year: 1998,
  released: "1998-04-03",
  files: 26,
  aired: 26,
  present: 26,
  missing: 0,
};
const MOVIE: TitleSummary = {
  ...DBZ,
  id: 3,
  kind: "movie",
  name: "Cowboy Bebop: The Movie",
  year: 2001,
  released: "2001-09-01",
  files: 1,
  aired: 0,
  present: 0,
  missing: 0,
};

/** The engine's answers for a library that's empty and already set up. */
function engineWith(answers: Record<string, unknown> = {}) {
  return fakeEngine({
    "/settings": SETTINGS,
    "/folders": [],
    "/library": NO_LIBRARY,
    "/scan": NO_SCAN,
    "/franchises": [],
    "/recovery": () => Response.json(null),
    ...answers,
  });
}

function sent(fetch: ReturnType<typeof fakeEngine>, method: string, path: string) {
  return fetch.mock.calls.filter(
    ([input, init]) =>
      (init?.method ?? "GET") === method && new URL(String(input)).pathname === path,
  );
}

function renderHome(engine: EngineStatus) {
  shell.invoke.mockImplementation(async (command: string) =>
    command === "engine_status" ? engine : undefined,
  );
  const queries = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={queries}>
      <EngineProvider>
        <PlayerProvider>
          <MemoryRouter>
            <Routes>
              <Route index element={<HomePage />} />
              <Route path="/setup" element={<p>Setup</p>} />
              <Route path="/scan" element={<p>Scan</p>} />
              <Route path="/match" element={<p>Match</p>} />
              <Route path="/titles/:id" element={<p>A title</p>} />
              <Route path="/franchises/:id" element={<p>A franchise</p>} />
              <Route path="/history" element={<p>History</p>} />
              <Route path="/subtitles" element={<p>Making subtitles</p>} />
            </Routes>
          </MemoryRouter>
          <PlayerLayer />
        </PlayerProvider>
      </EngineProvider>
    </QueryClientProvider>,
  );
}

describe("HomePage", () => {
  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
    shell.invoke.mockReset();
  });

  it("shows an empty shelf once the engine runs, and only the library", async () => {
    engineWith();
    renderHome(READY);

    expect(await screen.findByRole("heading", { name: "Your shelf is empty" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Add a folder" })).toBeEnabled();
    // What this copy of Kura is up to is in Settings › About.
    expect(screen.queryByRole("heading", { name: "This copy of Kura" })).not.toBeInTheDocument();
  });

  it("says what Kura settled after it closed unexpectedly, till it's seen", async () => {
    const at = new Date().toISOString();
    const fetch = engineWith({
      "/recovery": () => Response.json({ at, restarted: 1, finished: 0, putBack: 0, moves: 0 }),
      "POST /recovery/seen": null,
    });
    renderHome(READY);

    const said = await screen.findByText("Kura closed unexpectedly.");
    expect(said.closest("[role=status]")).toHaveTextContent(
      "Kura closed unexpectedly. One file was restarted from the beginning; the original was " +
        "never touched and nothing was lost.",
    );
    screen.getByRole("button", { name: "See what happened" }).click();
    await waitFor(() => expect(sent(fetch, "POST", "/recovery/seen")).toHaveLength(1));
    expect(await screen.findByText("History")).toBeInTheDocument();
  });

  it("words all that a crash left in one sentence", async () => {
    const at = new Date().toISOString();
    engineWith({
      "/recovery": () => Response.json({ at, restarted: 2, finished: 1, putBack: 0, moves: 3 }),
    });
    renderHome(READY);

    const said = await screen.findByText("Kura closed unexpectedly.");
    expect(said.closest("[role=status]")).toHaveTextContent(
      "Kura closed unexpectedly. 2 files were restarted from the beginning, one converted file " +
        "went into its original's place and 3 file moves were settled; nothing was lost.",
    );
  });

  it("opens setup on the very first run", async () => {
    engineWith({ "/settings": { ...SETTINGS, setUp: false } });
    renderHome(READY);

    expect(await screen.findByText("Setup")).toBeInTheDocument();
  });

  it("shows the library by picture size once a scan has read it", async () => {
    engineWith({
      "/folders": [FOLDER],
      "/library": { ...NO_LIBRARY, folders: 1, files: 3, size: 407_000_000, sd: 3, problems: 1 },
      "/scan": { ...NO_SCAN, state: "done", stage: "done", found: 3, toRead: 3, read: 3 },
    });
    renderHome(READY);

    const pictures = await screen.findByRole("heading", { name: "Your videos by picture" });
    expect(screen.getByText("3 videos · 0.4 GB · 1 folder")).toBeInTheDocument();
    expect(screen.getByText("1 file couldn't be read.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Scan again" })).toBeEnabled();
    expect(screen.getByText("100%")).toBeInTheDocument(); // every one of them SD
    // A summary at the top, before what needs the owner (and the shelf after that).
    const attention = await screen.findByRole("heading", { name: "Needs your attention" });
    expect(
      pictures.compareDocumentPosition(attention) & Node.DOCUMENT_POSITION_FOLLOWING,
    ).toBeTruthy();
  });

  it("goes on with what was being watched, and leaves a title out when asked", async () => {
    const stopped: Continuing = {
      titleId: 2,
      title: "Cowboy Bebop",
      kind: "series",
      hasPoster: false,
      playedAt: "2026-10-18T10:00:00+00:00",
      upNext: false,
      video: {
        fileId: 12,
        season: 1,
        episode: 2,
        episodeEnd: null,
        name: "Stray Dog Strut",
        path: "D:\\Anime\\Cowboy Bebop\\S01E02.mkv",
        duration: 1440,
        resume: 600,
      },
      following: [
        {
          fileId: 13,
          season: 1,
          episode: 3,
          episodeEnd: null,
          name: "Honky Tonk Women",
          path: "D:\\Anime\\Cowboy Bebop\\S01E03.mkv",
          duration: 1440,
          resume: null,
        },
      ],
    };
    const next: Continuing = {
      ...stopped,
      titleId: 3,
      title: "Cowboy Bebop: The Movie",
      kind: "movie",
      upNext: true,
      video: { ...stopped.video, fileId: 20, season: null, episode: null, resume: null },
      following: [],
    };
    let going = [stopped, next];
    const fetch = engineWith({
      "/folders": [FOLDER],
      "/library": { ...NO_LIBRARY, folders: 1, files: 3, size: 407_000_000, sd: 3 },
      "/continue": () => going,
      "DELETE /continue/3": () => {
        going = [stopped];
        return null;
      },
      "POST /player": {
        ticket: "T1",
        missing: null,
        drive: "D:",
        duration: 1440,
        sound: [],
        subtitles: [],
        chapters: [],
        chosenSound: null,
        chosenSubtitles: null,
        ready: [],
      },
    });
    renderHome(READY);

    const shelf = await screen.findByRole("region", { name: "Continue watching" });
    const [first, second] = within(shelf).getAllByRole("listitem") as [HTMLElement, HTMLElement];
    expect(first).toHaveTextContent("Cowboy Bebop");
    expect(first).toHaveTextContent("S01E02 · Stray Dog Strut");
    expect(first).toHaveTextContent("14 min left");
    expect(second).toHaveTextContent("The film");
    expect(second).toHaveTextContent("Up next");
    // Before the summary of the library.
    const pictures = await screen.findByRole("heading", { name: "Your videos by picture" });
    expect(shelf.compareDocumentPosition(pictures) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();

    within(first).getByRole("button", { name: "Play Cowboy Bebop · S01E02" }).click();
    const player = await screen.findByRole("region", { name: "Player" });
    expect(player).toHaveTextContent("Cowboy Bebop · S01E02");
    const video = player.querySelector("video") as HTMLVideoElement;
    await waitFor(() => expect(video.getAttribute("src")).toContain("at=600.000"));
    fireEvent(video, new Event("playing"));
    expect(await within(player).findByRole("button", { name: "Next episode" })).toBeInTheDocument();
    const [[, opened]] = sent(fetch, "POST", "/player") as [[unknown, RequestInit]];
    expect(JSON.parse(String(opened.body))).toEqual({ file: 12 });

    fireEvent.keyDown(
      within(second).getByRole("button", { name: "More for Cowboy Bebop: The Movie" }),
      {
        key: "Enter",
      },
    );
    (await screen.findByRole("menuitem", { name: "Remove from Continue watching" })).click();
    await waitFor(() => expect(within(shelf).getAllByRole("listitem")).toHaveLength(1));
    expect(sent(fetch, "DELETE", "/continue/3")).toHaveLength(1);
  });

  it("says what the videos can be heard and read in, and leads to making English subtitles", async () => {
    const heard = (id: number, more: Partial<Hearable> = {}): Hearable => ({
      fileId: id,
      label: `Starfall Academy · S01E0${id}`,
      titleId: 1,
      title: "Starfall Academy",
      season: 1,
      episode: id,
      seconds: 1440,
      sound: ["jpn"],
      subtitles: [],
      english: false,
      made: false,
      waiting: false,
      ...more,
    });
    engineWith({
      "/folders": [FOLDER],
      "/library": { ...NO_LIBRARY, folders: 1, files: 4, size: 4e9, hd1080: 4 },
      "/scan": { ...NO_SCAN, state: "done", stage: "done", found: 4, toRead: 4, read: 4 },
      "/subtitles": {
        files: [
          heard(1, { sound: ["jpn", "eng"], english: true }),
          heard(2, { subtitles: ["en"], english: true, made: true }),
          heard(3),
          heard(4, { titleId: 2, title: "Paper Lanterns" }),
        ],
        rates: { best: 0.4, fast: 0.15 },
      },
    });
    renderHome(READY);

    const languages = await screen.findByRole("region", { name: "Your videos by language" });
    const tiles = within(languages).getAllByRole("listitem");
    expect(tiles.map((tile) => tile.textContent)).toEqual([
      "English sound25%1dubbed, from the files",
      "English subtitles25%11 of them made by Kura",
      "No English50%2neither sound nor subtitles",
    ]);
    const card = await screen.findByRole("button", { name: /2 videos have no English/ });
    expect(card).toHaveTextContent(
      "Across 2 anime · Kura can make English subtitles from their sound",
    );
    card.click();
    expect(await screen.findByText("Making subtitles")).toBeInTheDocument();
  });

  it("says only when a scan ran, for a scan from before Kura counted what changed", async () => {
    engineWith({
      "/folders": [FOLDER],
      "/library": { ...NO_LIBRARY, folders: 1, files: 3, size: 407_000_000, sd: 1, hd720: 1 },
      "/scan": { ...NO_SCAN, state: "done", stage: "done", finishedAt: new Date().toISOString() },
    });
    renderHome(READY);

    expect(await screen.findByText(/^Scanned today \d\d:\d\d$/)).toBeInTheDocument();
    // Shares that add up: a third each of three would read 33% three times.
    expect(screen.getAllByText(/^\d+%$/).map((share) => share.textContent)).toEqual([
      "50%",
      "50%",
      "0%",
      "0%",
    ]);
  });

  it("catches up after a scan too quick to be seen running, and says what it found", async () => {
    let scans = 0;
    const finishedAt = new Date().toISOString();
    engineWith({
      "/folders": [FOLDER],
      "/franchises": [franchiseOf([DBZ])],
      "/library": () => ({
        ...NO_LIBRARY,
        folders: 1,
        files: scans > 1 ? 2 : 3,
        size: 407_000_000,
        sd: scans > 1 ? 2 : 3,
      }),
      "/scan": () => {
        scans += 1; // the second look finds another scan done: a video was removed meanwhile
        return {
          ...NO_SCAN,
          state: "done",
          stage: "done",
          startedAt: scans > 1 ? "2026-10-13T13:07:22Z" : "2026-10-13T13:06:16Z",
          finishedAt,
          found: scans > 1 ? 2 : 3,
          added: 0,
          gone: scans > 1 ? 1 : 0,
        };
      },
    });
    renderHome(READY);

    expect(await screen.findByText("1 anime · 3 videos · 0.4 GB · 1 folder")).toBeInTheDocument();
    expect(
      await screen.findByText("1 anime · 2 videos · 0.4 GB · 1 folder", undefined, {
        timeout: 6000,
      }),
    ).toBeInTheDocument();
    expect(screen.getByText(/^Scanned today \d\d:\d\d · 1 gone$/)).toBeInTheDocument();
  }, 10_000);

  it("leaves out adding a folder while a scan runs", async () => {
    engineWith({
      "/folders": [FOLDER],
      "/library": { ...NO_LIBRARY, folders: 1, files: 3, size: 407_000_000, sd: 3 },
      "/scan": { ...NO_SCAN, state: "running", stage: "reading", found: 3, toRead: 3, read: 1 },
    });
    renderHome(READY);

    expect(
      await screen.findByRole("button", { name: "Scanning… see progress" }),
    ).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Add a folder" })).not.toBeInTheDocument();
  });

  it("catches up with the library when the scan finishes", async () => {
    let asked = 0;
    let finished = false;
    engineWith({
      "/folders": [FOLDER],
      "/library": () => ({
        ...NO_LIBRARY,
        folders: 1,
        files: finished ? 3 : 1,
        size: 407_000_000,
        sd: finished ? 3 : 1,
      }),
      "/scan": () => {
        asked += 1;
        finished = asked > 1;
        return finished
          ? { ...NO_SCAN, state: "done", stage: "done", found: 3, toRead: 3, read: 3 }
          : { ...NO_SCAN, state: "running", stage: "reading", found: 3, toRead: 3, read: 1 };
      },
    });
    renderHome(READY);

    expect(await screen.findByText("1 video · 0.4 GB · 1 folder")).toBeInTheDocument();
    // The scan is asked again a second later, finds it done, and the library is asked again.
    expect(
      await screen.findByText("3 videos · 0.4 GB · 1 folder", undefined, { timeout: 3000 }),
    ).toBeInTheDocument();
  });

  it("notices a scan Kura started on its own", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    let started = false;
    engineWith({
      "/folders": [FOLDER],
      "/library": { ...NO_LIBRARY, folders: 1, files: 3, size: 407_000_000, sd: 3 },
      "/scan": () =>
        started
          ? { ...NO_SCAN, state: "running", stage: "finding", found: 3 }
          : { ...NO_SCAN, state: "done", stage: "done", found: 3, toRead: 3, read: 3 },
    });
    renderHome(READY);
    expect(await screen.findByRole("button", { name: "Scan again" })).toBeInTheDocument();

    started = true; // a new video arrived, and the watcher started a scan
    await act(() => vi.advanceTimersByTimeAsync(10_000));

    expect(
      await screen.findByRole("button", { name: "Scanning… see progress" }),
    ).toBeInTheDocument();
  });

  it("says when the engine couldn't answer, and asks again", async () => {
    let asked = 0;
    engineWith({
      "/folders": () => {
        asked += 1;
        return asked === 1
          ? Response.json({ detail: "The database is locked." }, { status: 503 })
          : [FOLDER];
      },
      "/library": { ...NO_LIBRARY, folders: 1, files: 3, size: 407_000_000, sd: 3 },
    });
    renderHome(READY);

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Kura couldn't load this screen. The database is locked. Nothing in your folders was touched.",
    );
    screen.getByRole("button", { name: "Try again" }).click();

    expect(
      await screen.findByRole("heading", { name: "Your videos by picture" }),
    ).toBeInTheDocument();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("says when the engine isn't running, and offers to try again", async () => {
    engineWith();
    renderHome({ state: "failed", message: "It stopped unexpectedly.", details: "Traceback…" });

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("Kura's engine isn't running. It stopped unexpectedly.");
    expect(alert).toHaveTextContent("Nothing in your folders was touched.");

    screen.getByRole("button", { name: "Try again" }).click();

    expect(shell.invoke).toHaveBeenCalledWith("restart_engine");
  });

  it("offers the engine's error lines only when there are some", async () => {
    engineWith();
    renderHome({ state: "failed", message: "It stopped unexpectedly.", details: "" });

    await screen.findByRole("alert");

    expect(screen.queryByRole("button", { name: "Copy details" })).not.toBeInTheDocument();
  });

  it("lists the franchises and series oldest release first, each saying what it is", async () => {
    const fetch = engineWith({
      "/folders": [FOLDER],
      "/library": { ...NO_LIBRARY, folders: 1, files: 314, size: 9e10 },
      "/scan": { ...NO_SCAN, state: "done", stage: "done" },
      "/franchises": [franchiseOf([DBZ]), franchiseOf([BEBOP, MOVIE])],
    });
    renderHome(READY);

    expect(
      await screen.findByRole("heading", { name: "Franchises and series" }),
    ).toBeInTheDocument();
    expect(screen.getByText("2 anime · by type, oldest release first")).toBeInTheDocument();
    expect(screen.getByText("TV series · 1989 · 291 episodes")).toBeInTheDocument();
    expect(screen.getByText("4 missing")).toBeInTheDocument();
    expect(screen.getByText("287 of 291 · 99%")).toBeInTheDocument();
    expect(screen.getByText("TV series · 26 episodes · 1 movie")).toBeInTheDocument();
    expect(screen.getByText("26 of 26 · complete")).toBeInTheDocument();
    expect(screen.getByText("2 anime · 314 videos · 90.0 GB · 1 folder")).toBeInTheDocument();
    expect(screen.getByRole("radio", { name: "Release date" })).toBeChecked();
    expect(
      fetch.mock.calls.some(([input]) => String(input).endsWith("/franchises?sort=released")),
    ).toBe(true);

    screen.getByRole("radio", { name: "Name" }).click();
    await waitFor(() =>
      expect(
        fetch.mock.calls.some(([input]) => String(input).endsWith("/franchises?sort=name")),
      ).toBe(true),
    );

    (await screen.findByRole("link", { name: /Cowboy Bebop/ })).click();
    expect(await screen.findByText("A franchise")).toBeInTheDocument();
  });

  it("lists franchises first, then what stands on its own, by type", async () => {
    const gt = { ...DBZ, id: 4, name: "Dragon Ball GT" };
    engineWith({
      "/folders": [FOLDER],
      "/library": { ...NO_LIBRARY, folders: 1, files: 314, size: 9e10 },
      "/scan": { ...NO_SCAN, state: "done", stage: "done" },
      "/franchises": [franchiseOf([MOVIE]), franchiseOf([DBZ, gt]), franchiseOf([BEBOP])],
    });
    renderHome(READY);

    const [franchises, series, movies] = await screen.findAllByRole("heading", { level: 3 });

    expect([franchises, series, movies].map((heading) => heading?.textContent)).toEqual([
      "Franchises 1",
      "Series 1",
      "Movies 1",
    ]);
  });

  it("finds a franchise by its name or any of its titles', and says when nothing is", async () => {
    const gt = { ...DBZ, id: 4, name: "Dragon Ball GT" };
    engineWith({
      "/folders": [FOLDER],
      "/library": { ...NO_LIBRARY, folders: 1, files: 314, size: 9e10 },
      "/scan": { ...NO_SCAN, state: "done", stage: "done" },
      "/franchises": [franchiseOf([DBZ, gt]), franchiseOf([BEBOP, MOVIE])],
    });
    renderHome(READY);

    const search = await screen.findByRole("searchbox", { name: "Search the shelf" });
    expect(search).toHaveAttribute("placeholder", "Search 2 anime");
    fireEvent.change(search, { target: { value: "gt" } });

    expect(
      await screen.findByText("1 of 2 anime · by type, oldest release first"),
    ).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Dragon Ball Z/ })).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: /Cowboy Bebop/ })).not.toBeInTheDocument();

    fireEvent.change(search, { target: { value: "Trigun " } });
    expect(await screen.findByRole("status")).toHaveTextContent(
      "No anime on the shelf goes by “Trigun”.",
    );

    fireEvent.keyDown(search, { key: "Escape" });
    expect(await screen.findByText("2 anime · by type, oldest release first")).toBeInTheDocument();
    expect(search).toHaveValue("");
  });

  it("leads a title on its own to its page", async () => {
    engineWith({
      "/folders": [FOLDER],
      "/library": { ...NO_LIBRARY, folders: 1, files: 287, size: 9e10 },
      "/scan": { ...NO_SCAN, state: "done", stage: "done" },
      "/franchises": [franchiseOf([DBZ])],
    });
    renderHome(READY);

    (await screen.findByRole("link", { name: /Dragon Ball Z/ })).click();

    expect(await screen.findByText("A title")).toBeInTheDocument();
  });

  it("says what needs attention, and leads to it", async () => {
    engineWith({
      "/folders": [FOLDER],
      "/library": { ...NO_LIBRARY, folders: 1, files: 314, problems: 9 },
      "/scan": { ...NO_SCAN, state: "done", stage: "done", waiting: 12, mixed: 1 },
      "/franchises": [franchiseOf([DBZ]), franchiseOf([BEBOP, MOVIE])],
    });
    renderHome(READY);

    expect(await screen.findByText("12 files need a match")).toBeInTheDocument();
    expect(screen.getByText("4 episodes missing")).toBeInTheDocument();
    expect(screen.getByText("Across 1 anime · gap reports updated")).toBeInTheDocument();
    expect(screen.getByText("9 files won't play")).toBeInTheDocument();
    expect(screen.getByText("1 folder holds mixed anime")).toBeInTheDocument();

    screen.getByRole("button", { name: /12 files need a match/ }).click();
    expect(await screen.findByText("Match")).toBeInTheDocument();
  });
});
