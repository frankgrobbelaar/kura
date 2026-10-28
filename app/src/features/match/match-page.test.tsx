import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter, Route, Routes, useLocation, useParams } from "react-router";
import { afterEach, describe, expect, it, vi } from "vitest";
import { PlayerLayer } from "@/features/player/player";
import { PlayerProvider } from "@/features/player/player-context";
import { EngineProvider, type Guess, type WaitingFile } from "@/lib/engine";
import { fakeEngine, READY } from "@/test/engine";
import { MatchPage } from "./match-page";

const shell = vi.hoisted(() => ({ invoke: vi.fn() }));

vi.mock("@tauri-apps/api/core", () => ({ invoke: shell.invoke }));
vi.mock("@tauri-apps/api/event", () => ({ listen: async () => () => {} }));
vi.mock("@tauri-apps/api/window", () => ({
  getCurrentWindow: () => ({ setFullscreen: async () => {} }),
}));

const TRIGUN: Guess = {
  anilistId: 6,
  tmdbType: null,
  tmdbId: null,
  title: "Trigun",
  kind: "series",
  year: 1998,
  episodes: 26,
  minutes: 24,
  cover: null,
  confidence: 41,
  reasons: ["The 6 Trigun files in this folder share the [subs] tag"],
};
const BEBOP: Guess = {
  ...TRIGUN,
  anilistId: 1,
  title: "Cowboy Bebop",
  confidence: 38,
  reasons: [],
};

function waiting(id: number, episode: number, alike: number[] = []): WaitingFile {
  return {
    id,
    path: `D:\\Anime\\Downloads\\[subs] ep0${episode} final.mkv`,
    size: 233_000_000,
    minutes: 24.17,
    height: 480,
    codec: "h264",
    audio: ["jpn", "eng"],
    subtitles: ["eng"],
    group: "subs",
    title: null,
    season: null,
    episode,
    kind: "episode",
    guesses: [TRIGUN, BEBOP],
    alike,
  };
}

const QUEUE = [waiting(3, 3, [4, 5]), waiting(4, 4, [3, 5]), waiting(5, 5, [3, 4])];
const DELETED = { planId: 12, moved: 0, quarantined: 1, problems: [] };

function sent(fetch: ReturnType<typeof fakeEngine>, method: string, path: string) {
  return fetch.mock.calls.filter(
    ([input, init]) => (init?.method ?? "GET") === method && String(input).includes(path),
  );
}

/** Opens a row's "More" menu as a keyboard does, and picks one of its items. */
async function fromMenu(menu: string, item: string) {
  fireEvent.keyDown(await screen.findByRole("button", { name: menu }), { key: "Enter" });
  (await screen.findByRole("menuitem", { name: item })).click();
}

function renderMatch(at = "/match") {
  shell.invoke.mockImplementation(async (command: string) =>
    command === "engine_status" ? READY : undefined,
  );
  const queries = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={queries}>
      <EngineProvider>
        <PlayerProvider>
          <MemoryRouter initialEntries={[at]}>
            <Routes>
              <Route path="/match" element={<MatchPage />} />
              <Route path="/titles/:id" element={<ShownTitle />} />
              <Route path="*" element={<p>Home</p>} />
            </Routes>
          </MemoryRouter>
          <PlayerLayer />
        </PlayerProvider>
      </EngineProvider>
    </QueryClientProvider>,
  );
}

function ShownTitle() {
  const waiting = (useLocation().state as { waiting?: number } | null)?.waiting;
  return (
    <p>
      Title {useParams().id}
      {waiting !== undefined && `, ${waiting} waiting`}
    </p>
  );
}

describe("MatchPage", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    shell.invoke.mockReset();
  });

  it("shows the file, what reading it showed, and Kura's best guesses", async () => {
    fakeEngine({ "/review": QUEUE });
    renderMatch();

    expect(
      await screen.findByRole("heading", { name: "[subs] ep03 final.mkv" }),
    ).toBeInTheDocument();
    expect(screen.getByText("File 1 of 3")).toBeInTheDocument();
    expect(screen.getByText("24:10")).toBeInTheDocument();
    expect(screen.getByText("480p · H.264")).toBeInTheDocument();
    expect(screen.getByText("Japanese, English")).toBeInTheDocument();
    expect(screen.getByText("[subs]")).toBeInTheDocument();
    expect(screen.getByRole("radio", { name: /Trigun \(1998\)/ })).toBeChecked();
    expect(screen.getByText("41%")).toBeInTheDocument();
    expect(screen.getByText("Use this for the 2 other [subs] files here")).toBeInTheDocument();
    expect(screen.getByText("Episodes 04 and 05, numbered from their names")).toBeInTheDocument();
  });

  it("plays the file to tell what it is, from the start or from a still", async () => {
    const opened = {
      ticket: "T1",
      missing: null,
      drive: "D:",
      duration: 1450,
      sound: [],
      subtitles: [],
      chapters: [],
      chosenSound: null,
      chosenSubtitles: null,
      ready: [],
    };
    const fetch = fakeEngine({ "/review": QUEUE, "POST /player": opened });
    renderMatch();

    (await screen.findByRole("button", { name: "Play from 12:05" })).click();

    const player = await screen.findByRole("region", { name: "Player" });
    expect(player).toHaveTextContent("[subs] ep03 final.mkv");
    expect(player).toHaveTextContent("From the still at 12:05");
    await waitFor(() => {
      const src = player.querySelector("video")?.getAttribute("src") ?? "";
      expect(src).toContain("/stream/T1?at=725.100");
    });
    screen.getByRole("button", { name: "Play it" }).click();
    await waitFor(() =>
      expect(screen.getByRole("region", { name: "Player" })).toHaveTextContent(
        "D:\\Anime\\Downloads",
      ),
    );
    expect(sent(fetch, "POST", "/player").length).toBeGreaterThanOrEqual(2);
  });

  it("confirms the choice for the file and the ones like it", async () => {
    const fetch = fakeEngine({ "/review": QUEUE, "POST /review/3": { placed: 3 } });
    renderMatch();

    (await screen.findByRole("button", { name: "Confirm Trigun, episode 3" })).click();

    await waitFor(() => expect(sent(fetch, "POST", "/review/3")).toHaveLength(1));
    const [[, init]] = sent(fetch, "POST", "/review/3") as [[unknown, RequestInit]];
    expect(JSON.parse(String(init.body))).toEqual({ anilistId: 6, kind: "episode", also: [4, 5] });
  });

  it("picks another guess with its number key, and the kind with the switch", async () => {
    const fetch = fakeEngine({ "/review": QUEUE, "POST /review/3": { placed: 1 } });
    renderMatch();
    await screen.findByRole("radio", { name: /Trigun/ });

    fireEvent.keyDown(window, { key: "2" });
    await waitFor(() => expect(screen.getByRole("radio", { name: /Cowboy Bebop/ })).toBeChecked());
    screen.getByRole("radio", { name: "Special or extra" }).click();
    screen.getByRole("checkbox").click();
    (await screen.findByRole("button", { name: "Confirm Cowboy Bebop" })).click();

    await waitFor(() => expect(sent(fetch, "POST", "/review/3")).toHaveLength(1));
    const [[, init]] = sent(fetch, "POST", "/review/3") as [[unknown, RequestInit]];
    expect(JSON.parse(String(init.body))).toEqual({ anilistId: 1, kind: "special", also: [] });
  });

  it("confirms a film AniList doesn't list by TMDB's number for it", async () => {
    const turtle: Guess = {
      ...TRIGUN,
      anilistId: null,
      tmdbType: "movie",
      tmdbId: 337703,
      title: "The Red Turtle",
      kind: "movie",
      year: 2016,
      confidence: 95,
      reasons: ["Only TMDB knows it", "Title matches", "2016 fits"],
    };
    const film: WaitingFile = {
      ...waiting(9, 1),
      path: "F:\\Anime\\Movies\\The Red Turtle (2016)\\The Red Turtle (2016).mp4",
      minutes: 80.8,
      episode: null,
      kind: "movie",
      guesses: [turtle, TRIGUN],
    };
    const fetch = fakeEngine({ "/review": [film], "POST /review/9": { placed: 1 } });
    renderMatch();

    expect(await screen.findByRole("radio", { name: /The Red Turtle \(2016\)/ })).toBeChecked();
    expect(screen.getByText(/Only TMDB knows it/)).toBeInTheDocument();
    (await screen.findByRole("button", { name: "Confirm The Red Turtle" })).click();

    await waitFor(() => expect(sent(fetch, "POST", "/review/9")).toHaveLength(1));
    const [[, init]] = sent(fetch, "POST", "/review/9") as [[unknown, RequestInit]];
    expect(JSON.parse(String(init.body))).toEqual({
      tmdbType: "movie",
      tmdbId: 337703,
      kind: "movie",
      also: [],
    });
  });

  it("asks which episode a file is when its name doesn't say", async () => {
    const dvd: WaitingFile = {
      ...waiting(7, 1),
      path: "D:\\Anime\\Old DVDs\\VTS_01_1.VOB",
      episode: null,
      kind: "dvd",
    };
    const fetch = fakeEngine({ "/review": [dvd], "POST /review/7": { placed: 1 } });
    renderMatch();

    const number = await screen.findByRole("textbox", { name: "Which episode" });
    expect(screen.getByRole("button", { name: "Confirm Trigun" })).toBeInTheDocument();
    fireEvent.change(number, { target: { value: "15x0" } });
    (await screen.findByRole("button", { name: "Confirm Trigun, episode 150" })).click();

    await waitFor(() => expect(sent(fetch, "POST", "/review/7")).toHaveLength(1));
    const [[, init]] = sent(fetch, "POST", "/review/7") as [[unknown, RequestInit]];
    expect(JSON.parse(String(init.body))).toEqual({
      anilistId: 6,
      kind: "episode",
      also: [],
      episode: 150,
    });
  });

  it("searches when none of the guesses is right", async () => {
    fakeEngine({
      "/review": QUEUE,
      "/review/3/search": [{ ...TRIGUN, anilistId: 99, title: "Trigun Stampede", confidence: 70 }],
    });
    renderMatch();

    fireEvent.change(await screen.findByRole("searchbox", { name: "Search for the right anime" }), {
      target: { value: "Trigun Stampede" },
    });

    expect(await screen.findByRole("radio", { name: /Trigun Stampede/ })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Found" })).toBeInTheDocument();
  });

  it("skips to the next file, and leaves out what isn't anime", async () => {
    const fetch = fakeEngine({ "/review": QUEUE, "POST /review/4/ignore": null });
    renderMatch();

    (await screen.findByRole("button", { name: "Skip for now" })).click();
    expect(
      await screen.findByRole("heading", { name: "[subs] ep04 final.mkv" }),
    ).toBeInTheDocument();
    screen.getByRole("button", { name: "Not anime, ignore it" }).click();

    await waitFor(() => expect(sent(fetch, "POST", "/review/4/ignore")).toHaveLength(1));
  });

  it("keeps going round the files that were skipped", async () => {
    fakeEngine({ "/review": QUEUE });
    renderMatch();

    for (const shown of ["ep03", "ep04", "ep05", "ep03", "ep04"]) {
      expect(
        await screen.findByRole("heading", { name: `[subs] ${shown} final.mkv` }),
      ).toBeInTheDocument();
      screen.getByRole("button", { name: "Skip for now" }).click();
    }
  });

  it("searches once the owner stops typing", async () => {
    const fetch = fakeEngine({
      "/review": QUEUE,
      "/review/3/search": [{ ...TRIGUN, anilistId: 99, title: "Trigun Stampede", confidence: 70 }],
    });
    renderMatch();
    const box = await screen.findByRole("searchbox", { name: "Search for the right anime" });

    for (const typed of ["Tr", "Tri", "Trig", "Trigu", "Trigun"]) {
      fireEvent.change(box, { target: { value: typed } });
    }

    expect(await screen.findByRole("radio", { name: /Trigun Stampede/ })).toBeInTheDocument();
    expect(sent(fetch, "GET", "/review/3/search")).toHaveLength(1);
  });

  it("changes a title's match for all its files, then shows where they went", async () => {
    const fetch = fakeEngine({
      "/review": [{ ...waiting(3, 1, [4, 5]), guesses: [BEBOP, TRIGUN] }],
      "/titles/1": { name: "Cowboy Bebop" },
      "POST /review/3": { placed: 2, waiting: 1, titleId: 8 },
    });
    renderMatch("/match?title=1");

    expect(await screen.findByText("All 3 files of Cowboy Bebop")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Cowboy Bebop" })).toHaveAttribute("href", "/titles/1");
    expect(screen.getByText("Use this for its other 2 files")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Skip for now" })).not.toBeInTheDocument();
    fireEvent.keyDown(screen.getByRole("button", { name: "More for this file" }), { key: "Enter" });
    expect(await screen.findByRole("menuitem", { name: "Show in folder" })).toBeInTheDocument();
    expect(screen.queryByRole("menuitem", { name: "Delete…" })).not.toBeInTheDocument();
    fireEvent.keyDown(screen.getByRole("menu"), { key: "Escape" });
    await waitFor(() => expect(screen.queryByRole("menu")).not.toBeInTheDocument());
    expect(fetch.mock.calls.some(([input]) => String(input).endsWith("/review?title=1"))).toBe(
      true,
    );
    fireEvent.keyDown(window, { key: "2" });
    (await screen.findByRole("button", { name: "Confirm Trigun, episode 1" })).click();

    expect(await screen.findByText("Title 8, 1 waiting")).toBeInTheDocument();
    const [[, init]] = sent(fetch, "POST", "/review/3") as [[unknown, RequestInit]];
    expect(JSON.parse(String(init.body))).toEqual({
      anilistId: TRIGUN.anilistId,
      kind: "episode",
      title: 1,
    });
  });

  it("deletes the file on screen once asked, says so, and puts it back", async () => {
    let gone: number[] = []; // once deleted, the files waiting come back without them
    const fetch = fakeEngine({
      "/review": () => QUEUE.filter((file) => !gone.includes(file.id)),
      "POST /files/delete": (init?: RequestInit) => {
        gone = (JSON.parse(String(init?.body)) as { files: number[] }).files;
        return DELETED;
      },
      "POST /plans/12/undo": () => {
        gone = [];
        return { ...DELETED, moved: 1, quarantined: 0 };
      },
    });
    renderMatch();

    await fromMenu("More for this file", "Delete…");
    const asking = await screen.findByRole("group", { name: "Delete this file?" });
    await waitFor(() =>
      expect(asking).toHaveTextContent(
        "1 video (233 MB) goes to the quarantine on D:, with any subtitles named after it. " +
          "They're deleted for good after 30 days; till then History puts them back.",
      ),
    );
    within(asking).getByRole("button", { name: "Delete 1 video" }).click();

    expect(await screen.findByText("Deleted 1 video.")).toBeInTheDocument();
    expect(
      await screen.findByRole("heading", { name: "[subs] ep04 final.mkv" }),
    ).toBeInTheDocument();
    const [[, init]] = sent(fetch, "POST", "/files/delete") as [[unknown, RequestInit]];
    expect(JSON.parse(String(init.body))).toEqual({ files: [3] });
    screen.getByRole("button", { name: "Put back" }).click();

    expect(
      await screen.findByRole("heading", { name: "[subs] ep03 final.mkv" }),
    ).toBeInTheDocument();
    expect(sent(fetch, "POST", "/plans/12/undo")).toHaveLength(1);
  });

  it("deletes a file further on from what's up next, and can be talked out of it", async () => {
    const fetch = fakeEngine({ "/review": QUEUE, "POST /files/delete": DELETED });
    renderMatch();

    await fromMenu("More for [subs] ep04 final.mkv", "Delete…");
    (await screen.findByRole("button", { name: "Cancel" })).click();
    await waitFor(() =>
      expect(screen.queryByRole("group", { name: "Delete this file?" })).not.toBeInTheDocument(),
    );
    await fromMenu("More for [subs] ep05 final.mkv", "Delete…");
    const asking = await screen.findByRole("group", { name: "Delete this file?" });
    within(asking).getByRole("button", { name: "Delete 1 video" }).click();

    await waitFor(() => expect(sent(fetch, "POST", "/files/delete")).toHaveLength(1));
    const [[, init]] = sent(fetch, "POST", "/files/delete") as [[unknown, RequestInit]];
    expect(JSON.parse(String(init.body))).toEqual({ files: [5] });
    expect(screen.getByRole("heading", { name: "[subs] ep03 final.mkv" })).toBeInTheDocument();
  });

  it("offers the last file back once it's deleted", async () => {
    let gone = false;
    fakeEngine({
      "/review": () => (gone ? [] : [waiting(3, 3)]),
      "POST /files/delete": () => {
        gone = true;
        return DELETED;
      },
    });
    renderMatch();

    await fromMenu("More for this file", "Delete…");
    (await screen.findByRole("button", { name: "Delete 1 video" })).click();

    expect(
      await screen.findByRole("heading", { name: "Every file is matched" }),
    ).toBeInTheDocument();
    expect(screen.getByText("Deleted 1 video.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Put back" })).toBeInTheDocument();
  });

  it("lists the files set aside as not anime, to match after all or delete", async () => {
    let ignored = [
      { id: 9, path: "D:\\Anime\\Specials\\Special 07.mp4", size: 250_000_000 },
      { id: 10, path: "D:\\Anime\\Specials\\Special 08.mp4", size: 27_000_000 },
    ];
    const fetch = fakeEngine({
      "/review": [],
      "/review/ignored": () => ignored,
      "DELETE /review/10/ignore": () => {
        ignored = ignored.filter((file) => file.id !== 10);
        return null;
      },
      "POST /files/delete": () => {
        ignored = ignored.filter((file) => file.id !== 9);
        return DELETED;
      },
    });
    renderMatch();

    expect(
      await screen.findByRole("heading", { name: "Set aside as not anime" }),
    ).toBeInTheDocument();
    expect(screen.getByText("D:\\Anime\\Specials · 250 MB")).toBeInTheDocument();
    screen.getByRole("button", { name: "Match it: Special 08.mp4" }).click();
    await waitFor(() => expect(screen.queryByText("Special 08.mp4")).not.toBeInTheDocument());
    expect(sent(fetch, "DELETE", "/review/10/ignore")).toHaveLength(1);

    await fromMenu("More for Special 07.mp4", "Delete…");
    const asking = await screen.findByRole("group", { name: "Delete this file?" });
    within(asking).getByRole("button", { name: "Delete 1 video" }).click();

    expect(await screen.findByText("Deleted 1 video.")).toBeInTheDocument();
    const [[, init]] = sent(fetch, "POST", "/files/delete") as [[unknown, RequestInit]];
    expect(JSON.parse(String(init.body))).toEqual({ files: [9] });
    await waitFor(() =>
      expect(
        screen.queryByRole("heading", { name: "Set aside as not anime" }),
      ).not.toBeInTheDocument(),
    );
  });

  it("shows a file in its folder, copies its path, and says when Explorer can't", async () => {
    fakeEngine({ "/review": QUEUE });
    renderMatch();
    const writeText = vi.fn(async () => {});
    Object.defineProperty(navigator, "clipboard", { value: { writeText }, configurable: true });

    await fromMenu("More for this file", "Show in folder");
    await waitFor(() =>
      expect(shell.invoke).toHaveBeenCalledWith("show_in_folder", { path: QUEUE[0]?.path }),
    );
    await fromMenu("More for [subs] ep04 final.mkv", "Copy path");
    await waitFor(() => expect(writeText).toHaveBeenCalledWith(QUEUE[1]?.path));
    expect(await screen.findByText("Its path is copied.")).toBeInTheDocument();

    shell.invoke.mockImplementation(async (command: string) => {
      if (command === "engine_status") return READY;
      if (command === "show_in_folder") throw "Windows can't find D:\\Anime\\Downloads.";
      return undefined;
    });
    await fromMenu("More for this file", "Show in folder");
    expect(await screen.findByText(/Windows can't find/)).toBeInTheDocument();
  });

  it("says when every file is matched", async () => {
    fakeEngine({ "/review": [] });
    renderMatch();

    expect(
      await screen.findByRole("heading", { name: "Every file is matched" }),
    ).toBeInTheDocument();
    screen.getByRole("button", { name: "Go to Home" }).click();
    expect(await screen.findByText("Home")).toBeInTheDocument();
  });
});
