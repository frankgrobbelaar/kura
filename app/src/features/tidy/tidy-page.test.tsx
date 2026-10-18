import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router";
import { afterEach, describe, expect, it, vi } from "vitest";
import {
  type CopyFacts,
  EngineProvider,
  type ProposedChange,
  type TidyProposal,
} from "@/lib/engine";
import { fakeEngine, NO_SCAN, READY } from "@/test/engine";
import { TidyPage } from "./tidy-page";

const shell = vi.hoisted(() => ({ invoke: vi.fn() }));

vi.mock("@tauri-apps/api/core", () => ({ invoke: shell.invoke }));
vi.mock("@tauri-apps/api/event", () => ({ listen: async () => () => {} }));

const ROOT = "D:\\Anime";

function change(
  source: string,
  target: string,
  label: string,
  more: Partial<ProposedChange> = {},
): ProposedChange {
  return {
    kind: "move",
    source: `${ROOT}\\${source}`,
    target: `${ROOT}\\${target}`,
    root: ROOT,
    label,
    reason: "Named and filed",
    category: "mixed",
    titleId: 1,
    title: "Cowboy Bebop",
    taken: false,
    compared: null,
    video: `${ROOT}\\${source}`,
    ...more,
  };
}

const BEBOP_1 = change(
  "Downloads\\[Hi10] Cowboy_Bebop_-_01_(BD_720p).mkv",
  "TV\\Cowboy Bebop (1998)\\Season 01\\Cowboy Bebop (1998) - S01E01 - Asteroid Blues.mkv",
  "Cowboy Bebop · S01E01",
);
const DUPLICATE: ProposedChange = {
  ...change("Downloads\\Death Note 07.avi", "", "Death Note · S01E07 · duplicate", {
    kind: "quarantine",
    category: "duplicate",
    titleId: 2,
    title: "Death Note",
    reason: "Kept [DB] Death_Note_07 (720p).mkv instead: higher resolution",
  }),
  target: "D:\\Kura quarantine\\2026-10-11\\Death Note 07.avi",
};
const DEATH_NOTE_7 = change(
  "Downloads\\[DB] Death_Note_07 (720p).mkv",
  "TV\\Death Note (2006)\\Season 01\\Death Note (2006) - S01E07 - Overcast.mkv",
  "Death Note · S01E07",
  { titleId: 2, title: "Death Note" },
);
const TRIGUN_3 = change(
  "Trigun\\trigun_03.mp4",
  "TV\\Trigun (1998)\\Season 01\\Trigun (1998) - S01E03 - Peace Maker.mp4",
  "Trigun · S01E03",
  { titleId: 3, title: "Trigun", category: "rename" },
);

const PROPOSAL: TidyProposal = {
  changes: [DUPLICATE, BEBOP_1, DEATH_NOTE_7, TRIGUN_3],
  skipped: [],
  duplicates: [
    {
      label: "Death Note · S01E07",
      keep: {
        path: DEATH_NOTE_7.source,
        height: 720,
        codec: "h264",
        audio: ["jpn", "eng"],
        subtitles: 1,
        size: 352_000_000,
        plays: true,
        subtitleLanguages: ["eng"],
      },
      drop: [
        {
          path: DUPLICATE.source,
          height: 480,
          codec: "mpeg4",
          audio: ["jpn"],
          subtitles: 0,
          size: 175_000_000,
          plays: true,
          subtitleLanguages: [],
        },
      ],
      reason: "Kept [DB] Death_Note_07 (720p).mkv instead: higher resolution",
      english: null,
    },
  ],
  waiting: 4,
  broken: 9,
};

/** A change as the owner saw it, which is what applying sends. */
function reviewed({ source, kind, target }: ProposedChange) {
  return { source, kind, target };
}

function sent(fetch: ReturnType<typeof fakeEngine>, method: string, path: string) {
  return fetch.mock.calls.filter(
    ([input, init]) => (init?.method ?? "GET") === method && String(input).includes(path),
  );
}

/** Opens a "More" menu in a part of the page as a keyboard does, and picks one of its items. */
async function fromMenu(scope: HTMLElement, menu: string, item: string) {
  fireEvent.keyDown(within(scope).getByRole("button", { name: menu }), { key: "Enter" });
  (await screen.findByRole("menuitem", { name: item })).click();
}

function renderTidy() {
  shell.invoke.mockImplementation(async (command: string) =>
    command === "engine_status" ? READY : undefined,
  );
  const queries = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={queries}>
      <EngineProvider>
        <MemoryRouter initialEntries={["/tidy"]}>
          <Routes>
            <Route path="/tidy" element={<TidyPage />} />
            <Route path="/match" element={<p>Match</p>} />
            <Route path="/history" element={<p>History</p>} />
          </Routes>
        </MemoryRouter>
      </EngineProvider>
    </QueryClientProvider>,
  );
}

describe("TidyPage", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    shell.invoke.mockReset();
  });

  it("shows what Kura proposes, a title at a time, and counts it up", async () => {
    fakeEngine({ "/tidy": PROPOSAL });
    renderTidy();

    expect(await screen.findByRole("region", { name: "Cowboy Bebop" })).toBeInTheDocument();
    expect(screen.getByText("[Hi10] Cowboy_Bebop_-_01_(BD_720p).mkv")).toBeInTheDocument();
    expect(
      screen.getByText(
        "TV\\Cowboy Bebop (1998)\\Season 01\\Cowboy Bebop (1998) - S01E01 - Asteroid Blues.mkv",
      ),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /2 Mixed folders/ })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /1 Renames/ })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /4 Need a match/ })).toBeInTheDocument();
    expect(
      screen.getByText("4 changes selected. 4 files stay where they are until matched."),
    ).toBeInTheDocument();
    expect(screen.getAllByRole("button", { name: "Apply 4 changes" })).toHaveLength(2);
  });

  it("says when a name was another file's, compares the two, and skips this one", async () => {
    const wanted =
      "TV\\Cowboy Bebop (1998)\\Season 01\\Cowboy Bebop (1998) - S01E01 - Asteroid Blues";
    const there = {
      path: `${ROOT}\\${wanted}.mkv`,
      height: 1080,
      codec: "hevc",
      audio: ["jpn"],
      subtitles: 2,
      size: 1_200_000_000,
      plays: true,
      subtitleLanguages: ["eng", "ger"],
    };
    const coming = { ...there, path: BEBOP_1.source, height: 720, codec: "h264" };
    const taken = {
      ...BEBOP_1,
      target: `${ROOT}\\${wanted} (2).mkv`,
      taken: true,
      compared: { there, coming, thereGoes: "stays" as const },
    };
    const subtitles = change(
      "Downloads\\[Hi10] Cowboy_Bebop_-_01_(BD_720p).en.srt",
      `${wanted} (2).en.srt`,
      "Cowboy Bebop · S01E01",
      { reason: "Follows its video", video: BEBOP_1.source },
    );
    const fetch = fakeEngine({
      "/tidy": { ...PROPOSAL, changes: [taken, subtitles, DEATH_NOTE_7] },
      "POST /tidy": { planId: 4, moved: 1, quarantined: 0, problems: [] },
    });
    renderTidy();

    const named = await screen.findByRole("group", { name: "Name already taken" });
    expect(named).toHaveTextContent("A file with this name is already there");
    expect(named).toHaveTextContent(`${wanted}.mkv`);
    expect(named).toHaveTextContent(
      "Kura never overwrites a file. Keep both adds (2) to the new one.",
    );
    expect(screen.getByRole("region", { name: "Death Note" })).not.toHaveTextContent(
      "already there",
    );

    fireEvent.click(screen.getByRole("button", { name: "Compare the two" }));
    expect(named).toHaveTextContent("Already thereStays as it is");
    expect(named).toHaveTextContent("1080p · HEVC");
    expect(named).toHaveTextContent("720p · H.264");

    fireEvent.click(screen.getByRole("button", { name: "Skip" }));
    expect(named).toHaveTextContent("Skipped: it stays where it is this time");
    const [applying] = screen.getAllByRole("button", { name: "Apply 1 change" });
    fireEvent.click(applying as HTMLElement);

    await waitFor(() => expect(sent(fetch, "POST", "/tidy")).toHaveLength(1));
    const [[, init]] = sent(fetch, "POST", "/tidy") as [[unknown, RequestInit]];
    const applied = JSON.parse(String(init.body)).changes as { source: string }[];
    expect(applied.map((c) => c.source)).toEqual([DEATH_NOTE_7.source]); // with its subtitles
  });

  it("compares two copies, and keeps the other one when asked", async () => {
    const fetch = fakeEngine({ "/tidy": PROPOSAL });
    renderTidy();

    const copies = await screen.findByRole("region", { name: "Copies of Death Note · S01E07" });
    expect(copies).toHaveTextContent("720p · H.264");
    expect(copies).toHaveTextContent("Japanese, English");
    expect(copies).toHaveTextContent("480p · MPEG-4");
    screen.getByRole("button", { name: "Swap which one is kept" }).click();

    await waitFor(() =>
      expect(
        fetch.mock.calls.some(([input]) =>
          String(input).includes(`keep=${encodeURIComponent(DUPLICATE.source)}`),
        ),
      ).toBe(true),
    );
  });

  it("shows a change's file in its folder, and a copy's", async () => {
    fakeEngine({ "/tidy": PROPOSAL });
    renderTidy();

    const bebop = await screen.findByRole("region", { name: "Cowboy Bebop" });
    await fromMenu(bebop, "More for [Hi10] Cowboy_Bebop_-_01_(BD_720p).mkv", "Show in folder");
    await waitFor(() =>
      expect(shell.invoke).toHaveBeenCalledWith("show_in_folder", { path: BEBOP_1.source }),
    );
    const copies = screen.getByRole("region", { name: "Copies of Death Note · S01E07" });
    await fromMenu(copies, "More for Death Note 07.avi", "Show in folder");
    await waitFor(() =>
      expect(shell.invoke).toHaveBeenCalledWith("show_in_folder", { path: DUPLICATE.source }),
    );
  });

  it("applies the titles left in, then offers to undo", async () => {
    const fetch = fakeEngine({
      "/tidy": PROPOSAL,
      "POST /tidy": { planId: 13, moved: 2, quarantined: 1, problems: [], english: 0 },
      "POST /plans/13/undo": { planId: 13, moved: 2, quarantined: 1, problems: [], english: 0 },
    });
    renderTidy();

    (await screen.findByRole("checkbox", { name: /Trigun/ })).click();
    await waitFor(() =>
      expect(screen.getAllByRole("button", { name: "Apply 3 changes" })).toHaveLength(2),
    );
    screen.getAllByRole("button", { name: "Apply 3 changes" })[0]?.click();

    expect(await screen.findByText("Done: 2 files filed, 1 copy set aside.")).toBeInTheDocument();
    const [[, init]] = sent(fetch, "POST", "/tidy") as [[unknown, RequestInit]];
    expect(JSON.parse(String(init.body))).toEqual({
      changes: [DUPLICATE, BEBOP_1, DEATH_NOTE_7].map(reviewed),
      keep: [],
      english: [],
    });

    screen.getByRole("button", { name: "Undo" }).click();
    await waitFor(() => expect(sent(fetch, "POST", "/plans/13/undo")).toHaveLength(1));
  });

  it("applies only the changes a filter shows", async () => {
    const fetch = fakeEngine({
      "/tidy": PROPOSAL,
      "POST /tidy": { planId: 14, moved: 1, quarantined: 0, problems: [], english: 0 },
    });
    renderTidy();

    (await screen.findByRole("button", { name: /1 Renames/ })).click();
    (await screen.findAllByRole("button", { name: "Apply 1 change" }))[0]?.click();

    await waitFor(() => expect(sent(fetch, "POST", "/tidy")).toHaveLength(1));
    const [[, init]] = sent(fetch, "POST", "/tidy") as [[unknown, RequestInit]];
    expect(JSON.parse(String(init.body))).toEqual({
      changes: [reviewed(TRIGUN_3)],
      keep: [],
      english: [],
    });
  });

  it("finds changes by anime or file, and applies only those found", async () => {
    const fetch = fakeEngine({
      "/tidy": PROPOSAL,
      "POST /tidy": { planId: 14, moved: 2, quarantined: 1, problems: [], english: 0 },
    });
    renderTidy();

    const search = await screen.findByRole("searchbox", { name: "Search the changes" });
    fireEvent.change(search, { target: { value: "death note" } });

    // The copies of Death Note's episode, and its changes; no other title's.
    expect(await screen.findByRole("region", { name: "Duplicates" })).toBeVisible();
    const changes = screen.getByRole("region", { name: "Changes" });
    await waitFor(() => expect(changes).not.toHaveTextContent("Cowboy Bebop"));
    expect(changes).not.toHaveTextContent("Trigun");
    (await screen.findAllByRole("button", { name: "Apply 2 changes" }))[0]?.click();
    await waitFor(() => expect(sent(fetch, "POST", "/tidy")).toHaveLength(1));
    const [[, init]] = sent(fetch, "POST", "/tidy") as [[unknown, RequestInit]];
    expect(JSON.parse(String(init.body)).changes).toEqual([
      reviewed(DUPLICATE),
      reviewed(DEATH_NOTE_7),
    ]);

    fireEvent.change(search, { target: { value: "trigun_03" } });
    expect(await screen.findByText("Trigun · S01E03")).toBeVisible();
    expect(screen.queryByRole("region", { name: "Duplicates" })).not.toBeInTheDocument();
    fireEvent.change(search, { target: { value: "Naruto" } });
    expect(await screen.findByRole("status")).toHaveTextContent("No change goes by “Naruto”.");
  });

  it("waits for a scan to finish before applying", async () => {
    fakeEngine({ "/tidy": PROPOSAL, "/scan": { ...NO_SCAN, state: "running" } });
    renderTidy();

    expect(
      await screen.findByText("Kura is scanning. Apply once it's done, so it knows every file."),
    ).toBeInTheDocument();
    for (const button of screen.getAllByRole("button", { name: "Apply 4 changes" })) {
      expect(button).toBeDisabled();
    }
  });

  it("says so when the proposal changed since it was shown", async () => {
    const changed = "Kura's proposal changed since you looked at it. Look it over again.";
    fakeEngine({
      "/tidy": PROPOSAL,
      "POST /tidy": () => Response.json({ detail: changed }, { status: 409 }),
    });
    renderTidy();

    (await screen.findAllByRole("button", { name: "Apply 4 changes" }))[0]?.click();

    expect(await screen.findByRole("alert")).toHaveTextContent(changed);
  });

  it("offers the other copy's English, and leaves that copy where it is till it's added", async () => {
    const [copies] = PROPOSAL.duplicates as [TidyProposal["duplicates"][number]];
    const withEnglish: TidyProposal = {
      ...PROPOSAL,
      duplicates: [
        {
          ...copies,
          keep: { ...copies.keep, audio: ["jpn"], subtitleLanguages: ["ger"] },
          drop: [
            { ...(copies.drop[0] as CopyFacts), audio: ["jpn", "eng"], subtitleLanguages: ["eng"] },
          ],
          english: { other: DUPLICATE.source, sound: true, subtitles: true, tried: null },
        },
      ],
    };
    const fetch = fakeEngine({
      "/tidy": withEnglish,
      "POST /tidy": { planId: 13, moved: 3, quarantined: 0, problems: [], english: 1 },
    });
    renderTidy();

    const panel = await screen.findByRole("region", { name: "Copies of Death Note · S01E07" });
    expect(panel).toHaveTextContent("The other copy has English this one hasn't");
    expect(
      screen.getByRole("radio", { name: "Keep the better picture, with the other's English" }),
    ).toHaveAttribute("aria-checked", "true");
    expect(panel).toHaveTextContent("Kura adds its English sound and subtitles to the copy kept");
    expect(panel).toHaveTextContent("If the two aren't the same cut, the English won't line up");
    expect(screen.getAllByText("English", { selector: "strong" })).toHaveLength(2);
    // The copy whose English goes in isn't set aside now: its English counts instead.
    const [applying] = screen.getAllByRole("button", { name: "Apply 4 changes" });
    fireEvent.click(applying as HTMLElement);

    expect(
      await screen.findByText("Done: 3 files filed, English from 1 other copy joins the queue."),
    ).toBeInTheDocument();
    const [[, init]] = sent(fetch, "POST", "/tidy") as [[unknown, RequestInit]];
    expect(JSON.parse(String(init.body))).toEqual({
      changes: [BEBOP_1, DEATH_NOTE_7, TRIGUN_3].map(reviewed),
      keep: [],
      english: [DEATH_NOTE_7.source],
    });
  });

  it("sets the other copy aside with its English when asked to keep the better one as it is", async () => {
    const [copies] = PROPOSAL.duplicates as [TidyProposal["duplicates"][number]];
    const tried = "The two copies aren't the same cut, so the English wouldn't line up.";
    const fetch = fakeEngine({
      "/tidy": {
        ...PROPOSAL,
        duplicates: [
          { ...copies, english: { other: DUPLICATE.source, sound: true, subtitles: false, tried } },
        ],
      },
      "POST /tidy": { planId: 13, moved: 3, quarantined: 1, problems: [], english: 0 },
    });
    renderTidy();

    // Kura tried before and couldn't: it says why, and keeps the better one as it is.
    expect(await screen.findByText(`Kura tried before: ${tried}`)).toBeInTheDocument();
    expect(screen.getByRole("radio", { name: "Keep the better one as it is" })).toHaveAttribute(
      "aria-checked",
      "true",
    );
    const [applying] = screen.getAllByRole("button", { name: "Apply 4 changes" });
    fireEvent.click(applying as HTMLElement);

    await waitFor(() => expect(sent(fetch, "POST", "/tidy")).toHaveLength(1));
    const [[, init]] = sent(fetch, "POST", "/tidy") as [[unknown, RequestInit]];
    expect(JSON.parse(String(init.body))).toMatchObject({
      changes: [DUPLICATE, BEBOP_1, DEATH_NOTE_7, TRIGUN_3].map(reviewed),
      english: [],
    });
  });

  it("names the files an undo couldn't put back", async () => {
    fakeEngine({
      "/tidy": PROPOSAL,
      "POST /tidy": { planId: 13, moved: 2, quarantined: 1, problems: [] },
      "POST /plans/13/undo": {
        planId: 13,
        moved: 1,
        quarantined: 1,
        problems: [
          {
            label: "Cowboy Bebop · S01E01",
            source: BEBOP_1.source,
            problem: "Kura couldn't put it back. A file with its old name is there now.",
          },
        ],
      },
    });
    renderTidy();

    (await screen.findAllByRole("button", { name: "Apply 4 changes" }))[0]?.click();
    (await screen.findByRole("button", { name: "Undo" })).click();

    const stayed = await screen.findByRole("alert");
    expect(stayed).toHaveTextContent("Some files stayed where they were");
    expect(stayed).toHaveTextContent(
      "Cowboy Bebop · S01E01: Kura couldn't put it back. A file with its old name is there now.",
    );
  });

  it("says when everything is filed", async () => {
    fakeEngine({ "/tidy": { ...PROPOSAL, changes: [], duplicates: [], waiting: 0 } });
    renderTidy();

    expect(await screen.findByRole("heading", { name: "Everything is filed" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Apply/ })).not.toBeInTheDocument();
  });

  it("leads to the files set aside as not anime, even when none need a match", async () => {
    fakeEngine({
      "/tidy": { ...PROPOSAL, waiting: 0 },
      "/review/ignored": [{ id: 9, path: "D:\\Anime\\Special 07.mp4", size: 250_000_000 }],
    });
    renderTidy();

    (await screen.findByRole("button", { name: /1 Set aside as not anime/ })).click();

    expect(await screen.findByText("Match")).toBeInTheDocument();
  });

  it("leads to the files that need a match", async () => {
    fakeEngine({ "/tidy": PROPOSAL });
    renderTidy();

    (await screen.findByRole("button", { name: /4 Need a match/ })).click();

    expect(await screen.findByText("Match")).toBeInTheDocument();
  });
});
