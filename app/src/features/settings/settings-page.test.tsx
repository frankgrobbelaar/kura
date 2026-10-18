import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router";
import { afterEach, describe, expect, it, vi } from "vitest";
import {
  type Backup,
  type DataSizes,
  EngineProvider,
  type Health,
  type LibraryFolder,
} from "@/lib/engine";
import type { ReadyUpdate } from "@/lib/updates";
import { fakeEngine, READY, SETTINGS, SYSTEM } from "@/test/engine";
import { SettingsPage } from "./settings-page";

const shell = vi.hoisted(() => ({ invoke: vi.fn() }));

vi.mock("@tauri-apps/api/core", () => ({ invoke: shell.invoke }));
vi.mock("@tauri-apps/api/event", () => ({ listen: async () => () => {} }));

const FOLDERS: LibraryFolder[] = [
  {
    id: 1,
    path: "D:\\Anime",
    addedAt: "2026-10-10T10:00:00+02:00",
    available: true,
    files: 2941,
    unread: 0,
    problems: 9,
  },
  {
    id: 2,
    path: "F:\\More anime",
    addedAt: "2026-10-10T10:00:00+02:00",
    available: false,
    files: 12,
    unread: 0,
    problems: 0,
  },
];

const HEALTH: Health = {
  status: "ok",
  version: "0.1.0",
  dataDir: "C:\\Users\\Someone\\AppData\\Local\\Kura",
  schemaVersion: 3,
};

const DATA: DataSizes = {
  folder: "C:\\Users\\Someone\\AppData\\Local\\Kura",
  database: 48_000_000,
  artwork: 610_000_000,
  cache: 20_000_000,
  logs: 12_000_000,
  backups: 0,
  tools: 180_000_000,
  quarantine: [{ folder: "D:\\Kura quarantine", bytes: 3_400_000_000, files: 14 }],
  moved: null,
};

/** A local time `daysAgo` days back, as the engine writes a backup's: "2026-10-11T03:00". */
function stamp(daysAgo: number, time: string): string {
  const day = new Date();
  day.setDate(day.getDate() - daysAgo);
  const date = [day.getFullYear(), day.getMonth() + 1, day.getDate()]
    .map((part) => String(part).padStart(2, "0"))
    .join("-");
  return `${date}T${time}`;
}

function backup(made: string): Backup {
  const [date, time] = made.split("T");
  const name = `kura ${date} ${time?.replace(":", "")}.db`;
  return { name, made, size: 47_000_000, beforeRestoring: false, fromExport: false, byHand: false };
}

const TONIGHT = backup(stamp(0, "03:00"));
const LAST_NIGHT = backup(stamp(1, "03:00"));

function renderSettings(section = "libraries", shellAnswers = true) {
  if (shellAnswers) {
    shell.invoke.mockImplementation(
      async (command: string, args?: { on?: boolean; look?: string }) => {
        if (command === "engine_status") return READY;
        if (command === "pick_folder") return "D:\\Backups";
        if (command === "start_with_windows") return false;
        if (command === "set_start_with_windows") return args?.on;
        if (command === "keep_in_tray") return false;
        if (command === "set_keep_in_tray") return args?.on;
        if (command === "look") return "windows";
        if (command === "set_look") return args?.look;
        return undefined;
      },
    );
  }
  const queries = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={queries}>
      <EngineProvider>
        <MemoryRouter initialEntries={[`/settings/${section}`]}>
          <Routes>
            <Route path="/settings/:section" element={<SettingsPage />} />
          </Routes>
        </MemoryRouter>
      </EngineProvider>
    </QueryClientProvider>,
  );
}

/** The shell's answers when Kura checks for updates, in turn (the last one repeats): an update,
 * none (null), or why it couldn't check (a string, as the shell's errors are). */
function answerUpdates(answers: (ReadyUpdate | null | string)[]) {
  shell.invoke.mockImplementation((command: string) => {
    if (command === "engine_status") return Promise.resolve(READY);
    if (command !== "prepare_update") return Promise.resolve(undefined);
    const answer = answers.length > 1 ? answers.shift() : answers[0];
    return typeof answer === "string" ? Promise.reject(answer) : Promise.resolve(answer);
  });
}

function checks() {
  return shell.invoke.mock.calls.filter(([command]) => command === "prepare_update").length;
}

function sent(fetch: ReturnType<typeof fakeEngine>, method: string, path: string) {
  return fetch.mock.calls.filter(
    ([input, init]) =>
      (init?.method ?? "GET") === method && new URL(String(input)).pathname === path,
  );
}

function body(fetch: ReturnType<typeof fakeEngine>, method: string, path: string): unknown {
  const [[, init]] = sent(fetch, method, path) as [[unknown, RequestInit]];
  return JSON.parse(String(init.body));
}

describe("SettingsPage", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    vi.unstubAllEnvs();
    shell.invoke.mockReset();
  });

  it("lists the library's folders, and forgets one", async () => {
    const fetch = fakeEngine({ "/folders": FOLDERS, "DELETE /folders/2": null });
    renderSettings();

    expect(await screen.findByText("2941 videos")).toBeInTheDocument();
    expect(
      screen.getByText("Not connected: its files wait till the drive is back"),
    ).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Libraries\s*2/ })).toBeInTheDocument();
    screen.getAllByRole("button", { name: "Forget" })[1]?.click();

    await waitFor(() => expect(sent(fetch, "DELETE", "/folders/2")).toHaveLength(1));
  });

  it("test-plays every video overnight unless turned off, and plays them all again", async () => {
    const fetch = fakeEngine({
      "/folders": FOLDERS,
      "/settings": SETTINGS,
      "PUT /settings": SETTINGS,
      "/checkup": {
        on: true,
        checked: 1204,
        total: 1530,
        unplayed: [
          {
            fileId: 4,
            path: "D:AnimeS01E04.mkv",
            titleId: 1,
            title: "Starfall",
            season: 1,
            episode: 4,
            episodeEnd: null,
            problem: "It didn't play at 12:05 (Invalid data)",
            at: "2026-10-18T01:30:00+02:00",
          },
        ],
      },
      "POST /checkup/again": null,
    });
    renderSettings();

    const check = await screen.findByRole("switch", { name: "Test-play every video overnight" });
    expect(check).toBeChecked();
    expect(
      await screen.findByText("1,204 of 1,530 videos checked this month · 1 didn't play"),
    ).toBeInTheDocument();
    screen.getByRole("button", { name: "Check them all again" }).click();
    await waitFor(() => expect(sent(fetch, "POST", "/checkup/again")).toHaveLength(1));
    check.click();
    await waitFor(() => expect(sent(fetch, "PUT", "/settings")).toHaveLength(1));
    expect(body(fetch, "PUT", "/settings")).toMatchObject({ healthCheck: false });
  });

  it("changes the standard at once", async () => {
    const fetch = fakeEngine({
      "/folders": FOLDERS,
      "/settings": SETTINGS,
      "PUT /settings": SETTINGS,
    });
    renderSettings("standard");

    (await screen.findByRole("radio", { name: /Compact 720p/ })).click();

    await waitFor(() => expect(sent(fetch, "PUT", "/settings")).toHaveLength(1));
    expect(body(fetch, "PUT", "/settings")).toMatchObject({ standard: "compact-720" });
  });

  it("shows where the data lives and how big each part is", async () => {
    fakeEngine({ "/folders": FOLDERS, "/settings": SETTINGS, "/data": DATA });
    renderSettings("data");

    expect(await screen.findByText(DATA.folder)).toBeInTheDocument();
    expect(screen.getByText("610 MB")).toBeInTheDocument();
    expect(
      screen.getByText(
        "3.4 GB in 14 files: copies set aside and converted files' originals, each on its own drive.",
      ),
    ).toBeInTheDocument();
    const quarantine = screen.getByRole("radiogroup", { name: "Keep what's set aside" });
    expect(within(quarantine).getByRole("radio", { name: "30 days" })).toHaveAttribute(
      "aria-checked",
      "true",
    );
  });

  it("turns the reports off, and keeps what's set aside longer", async () => {
    const fetch = fakeEngine({
      "/folders": FOLDERS,
      "/settings": SETTINGS,
      "/data": DATA,
      "PUT /settings": SETTINGS,
    });
    renderSettings("data");

    (await screen.findByRole("switch", { name: "A gap report in each anime's folder" })).click();
    await waitFor(() => expect(sent(fetch, "PUT", "/settings")).toHaveLength(1));
    expect(body(fetch, "PUT", "/settings")).toMatchObject({ reports: false });
  });

  it("deletes converted files' originals once checked, when asked", async () => {
    let saved = SETTINGS;
    const fetch = fakeEngine({
      "/folders": FOLDERS,
      "/settings": () => saved,
      "/data": DATA,
      "PUT /settings": (init?: RequestInit) => {
        saved = JSON.parse(String(init?.body));
        return saved;
      },
    });
    renderSettings("data");

    expect(
      await screen.findByText(
        "Kept here like any copy, so History can put one back till it's cleared out.",
      ),
    ).toBeInTheDocument();
    screen.getByRole("radio", { name: "Delete" }).click();

    await waitFor(() => expect(sent(fetch, "PUT", "/settings")).toHaveLength(1));
    expect(body(fetch, "PUT", "/settings")).toMatchObject({ originals: "delete" });
    expect(
      await screen.findByText(
        "Deleted for good once each converted copy is checked and in place: no putting back.",
      ),
    ).toBeInTheDocument();
  });

  it("keeps History as long as the owner says, clearing what's older each day", async () => {
    let saved = SETTINGS;
    const fetch = fakeEngine({
      "/folders": FOLDERS,
      "/settings": () => saved,
      "/data": DATA,
      "PUT /settings": (init?: RequestInit) => {
        saved = JSON.parse(String(init?.body));
        return saved;
      },
    });
    renderSettings("data");

    const keep = await screen.findByRole("radiogroup", { name: "Keep History" });
    expect(screen.getByText("Kept till you clear it on History.")).toBeInTheDocument();
    within(keep).getByRole("radio", { name: "30 days" }).click();

    await waitFor(() => expect(sent(fetch, "PUT", "/settings")).toHaveLength(1));
    expect(body(fetch, "PUT", "/settings")).toMatchObject({ historyDays: 30 });
    expect(await screen.findByText(/^Cleared each day of what's older/)).toBeInTheDocument();
  });

  it("says what changing the standard does to what's converted already", async () => {
    fakeEngine({ "/folders": FOLDERS, "/settings": SETTINGS });
    renderSettings("standard");

    expect(
      await screen.findByText(/Change it, and what's at the old one can be converted again/),
    ).toBeInTheDocument();
  });

  it("puts poster and background pictures next to each show, when asked", async () => {
    const fetch = fakeEngine({
      "/folders": FOLDERS,
      "/settings": SETTINGS,
      "/data": DATA,
      "PUT /settings": SETTINGS,
    });
    renderSettings("data");

    (
      await screen.findByRole("switch", {
        name: "Poster and background pictures next to each show",
      })
    ).click();

    await waitFor(() => expect(sent(fetch, "PUT", "/settings")).toHaveLength(1));
    expect(body(fetch, "PUT", "/settings")).toMatchObject({ artwork: true });
  });

  it("exports everything to a folder the owner picks", async () => {
    const fetch = fakeEngine({
      "/folders": FOLDERS,
      "/settings": SETTINGS,
      "/data": DATA,
      "POST /export": { path: "D:\\Backups\\Kura export 2026-10-11.zip", size: 912_000_000 },
    });
    renderSettings("data");

    (await screen.findByRole("button", { name: "Export everything" })).click();

    expect(
      await screen.findByText("D:\\Backups\\Kura export 2026-10-11.zip · 912 MB"),
    ).toBeInTheDocument();
    expect(body(fetch, "POST", "/export")).toEqual({ folder: "D:\\Backups" });
  });

  it("shows last night's backup, and makes one now", async () => {
    const fetch = fakeEngine({
      "/folders": FOLDERS,
      "/settings": SETTINGS,
      "/data": DATA,
      "/backups": { backups: [TONIGHT, LAST_NIGHT], restored: null },
      "POST /backups": backup(stamp(0, "14:12")),
    });
    renderSettings("data");

    expect(await screen.findByText("Last backup today 03:00")).toBeInTheDocument();
    expect(screen.getByText("47 MB · checked")).toBeInTheDocument();
    screen.getByRole("button", { name: "Back up now" }).click();

    await waitFor(() => expect(sent(fetch, "POST", "/backups")).toHaveLength(1));
  });

  it("restores the backup the owner picks, as the engine starts again", async () => {
    const restore = `/backups/${encodeURIComponent(LAST_NIGHT.name)}/restore`;
    const fetch = fakeEngine({
      "/folders": FOLDERS,
      "/settings": SETTINGS,
      "/data": DATA,
      "/backups": { backups: [TONIGHT, LAST_NIGHT], restored: null },
      [`POST ${restore}`]: null,
    });
    renderSettings("data");

    await screen.findByText("Last backup today 03:00");
    screen.getByRole("button", { name: "Restore a backup" }).click();
    (await screen.findByRole("radio", { name: /Yesterday 03:00/ })).click();
    const go = screen.getByRole("button", { name: "Restore it" });
    await waitFor(() => expect(go).toBeEnabled());
    go.click();

    await waitFor(() => expect(sent(fetch, "POST", restore)).toHaveLength(1));
    await waitFor(() => expect(shell.invoke).toHaveBeenCalledWith("restart_engine"));
  });

  it("says what kind each backup is", async () => {
    const byHand = { ...backup(stamp(0, "14:12")), byHand: true };
    const imported = `kura ${stamp(0, "14:20").replace("T", " ").replace(":", "")} from an export (2).db`;
    fakeEngine({
      "/folders": FOLDERS,
      "/settings": SETTINGS,
      "/data": DATA,
      "/backups": {
        backups: [byHand, TONIGHT],
        restored: { name: imported, at: new Date().toISOString(), problem: null },
      },
    });
    renderSettings("data");

    expect(await screen.findByText("Imported the export.")).toBeInTheDocument();
    screen.getByRole("button", { name: "Restore a backup" }).click();
    expect(
      await screen.findByRole("radio", { name: "Today 14:12 · by hand, 47 MB" }),
    ).toBeInTheDocument();
    expect(screen.getByRole("radio", { name: "Today 03:00, 47 MB" })).toBeInTheDocument();
  });

  it("says how today's restore went", async () => {
    fakeEngine({
      "/folders": FOLDERS,
      "/settings": SETTINGS,
      "/data": DATA,
      "/backups": {
        backups: [TONIGHT, LAST_NIGHT],
        restored: { name: LAST_NIGHT.name, at: new Date().toISOString(), problem: null },
      },
    });
    renderSettings("data");

    expect(
      await screen.findByText("Restored the backup from yesterday 03:00."),
    ).toBeInTheDocument();
  });

  it("starts Kura with Windows, waiting in the tray, when asked", async () => {
    fakeEngine({ "/folders": FOLDERS });
    renderSettings("general");

    const start = await screen.findByRole("switch", { name: "Start Kura when Windows starts" });
    await waitFor(() => expect(start).toHaveAttribute("aria-checked", "false"));
    start.click();

    await waitFor(() =>
      expect(shell.invoke).toHaveBeenCalledWith("set_start_with_windows", { on: true }),
    );
    await waitFor(() => expect(start).toHaveAttribute("aria-checked", "true"));
  });

  it("keeps Kura running in the tray when its window closes, when asked", async () => {
    fakeEngine({ "/folders": FOLDERS });
    renderSettings("general");

    const keep = await screen.findByRole("switch", {
      name: "Keep Kura running when you close the window",
    });
    await waitFor(() => expect(keep).toHaveAttribute("aria-checked", "false"));
    keep.click();

    await waitFor(() =>
      expect(shell.invoke).toHaveBeenCalledWith("set_keep_in_tray", { on: true }),
    );
    await waitFor(() => expect(keep).toHaveAttribute("aria-checked", "true"));
    expect(shell.invoke).not.toHaveBeenCalledWith("set_start_with_windows", expect.anything());
  });

  it("is light or dark as Windows is, or as the owner picks", async () => {
    fakeEngine({ "/folders": FOLDERS });
    renderSettings("general");

    const looks = await screen.findByRole("radiogroup", { name: "Light or dark" });
    const radio = (name: string) => within(looks).getByRole("radio", { name });
    await waitFor(() => expect(radio("Same as Windows")).toHaveAttribute("aria-checked", "true"));
    radio("Light").click();

    await waitFor(() => expect(shell.invoke).toHaveBeenCalledWith("set_look", { look: "light" }));
    await waitFor(() => expect(radio("Light")).toHaveAttribute("aria-checked", "true"));
    expect(radio("Same as Windows")).toHaveAttribute("aria-checked", "false");
  });

  it("moves the data to another drive, as the engine starts again", async () => {
    const fetch = fakeEngine({
      "/folders": FOLDERS,
      "/settings": SETTINGS,
      "/data": DATA,
      "/backups": { backups: [], restored: null },
      "POST /data/move": null,
    });
    renderSettings("data");

    (await screen.findByRole("button", { name: "Move to another drive" })).click();
    const asking = await screen.findByRole("group", {
      name: "Move Kura's data to D:\\Backups\\Kura?",
    });
    within(asking).getByRole("button", { name: "Move it" }).click();

    await waitFor(() => expect(shell.invoke).toHaveBeenCalledWith("restart_engine"));
    expect(body(fetch, "POST", "/data/move")).toEqual({ folder: "D:\\Backups\\Kura" });
  });

  it("imports an export once asked, as the engine starts again", async () => {
    shell.invoke.mockImplementation(async (command: string) => {
      if (command === "engine_status") return READY;
      if (command === "pick_export") return "D:\\Backups\\Kura export 2026-10-10.zip";
      return undefined;
    });
    const fetch = fakeEngine({
      "/folders": FOLDERS,
      "/settings": SETTINGS,
      "/data": DATA,
      "/backups": { backups: [], restored: null },
      "POST /backups/import": null,
    });
    renderSettings("data", false);

    (await screen.findByRole("button", { name: "Import an export" })).click();
    const asking = await screen.findByRole("group", { name: "Import Kura export 2026-10-10.zip?" });
    within(asking).getByRole("button", { name: "Import it" }).click();

    await waitFor(() => expect(shell.invoke).toHaveBeenCalledWith("restart_engine"));
    expect(body(fetch, "POST", "/backups/import")).toEqual({
      path: "D:\\Backups\\Kura export 2026-10-10.zip",
    });
  });

  it("says what this copy of Kura is up to, and where to add the TMDB key", async () => {
    fakeEngine({
      "/folders": FOLDERS,
      "/health": HEALTH,
      "/tmdb": { connected: false, keyEnd: null },
    });
    renderSettings("about");

    expect(await screen.findByText("0.1.0")).toBeInTheDocument();
    expect(screen.getByText("Running")).toBeInTheDocument();
    expect(screen.getByText(HEALTH.dataDir)).toBeInTheDocument();
    expect(screen.getByText("Ready · schema version 3")).toBeInTheDocument();
    expect(screen.getByText("Checked in installed copies of Kura")).toBeInTheDocument();
    expect(await screen.findByText(/AniList only: no episode titles yet/)).toBeInTheDocument();
    screen.getByRole("link", { name: "Add your TMDB key" }).click();

    expect(await screen.findByLabelText("TMDB API Read Access Token")).toBeInTheDocument();
  });

  it("names the TMDB key in use, beside TMDB's credit", async () => {
    fakeEngine({
      "/folders": FOLDERS,
      "/health": HEALTH,
      "/tmdb": { connected: true, keyEnd: "ab12" },
    });
    renderSettings("about");

    expect(await screen.findByText("TMDB connected · key ending ab12")).toBeInTheDocument();
    expect(screen.getByText(/not endorsed or certified by TMDB/)).toBeInTheDocument();
    expect(screen.getByRole("img", { name: "TMDB" })).toBeInTheDocument(); // its logo, as it asks
  });

  it("says Kura is for your own videos, and never fetches or shares any", async () => {
    fakeEngine({
      "/folders": FOLDERS,
      "/health": HEALTH,
      "/tmdb": { connected: true, keyEnd: "ab12" },
    });
    renderSettings("about");

    expect(
      await screen.findByText(/for videos you have the right to keep and watch/),
    ).toHaveTextContent("it never searches for, downloads or shares video");
  });

  it("says what this PC can do, how long it takes, and how that was measured", async () => {
    const fetch = fakeEngine({
      "/folders": FOLDERS,
      "/health": HEALTH,
      "/system": SYSTEM,
      "POST /system/test": {
        ...SYSTEM,
        testing: { step: "encoder", done: [], fps: null, timing: true },
      },
    });
    renderSettings("about");

    const panel = await screen.findByRole("region", { name: "This PC" });
    expect(
      within(panel).getByText("NVIDIA GeForce GTX 1660 SUPER · 6 GB · driver 617.42"),
    ).toBeInTheDocument();
    expect(within(panel).getByText("Intel Core i5-9600K · 6 cores")).toBeInTheDocument();
    expect(within(panel).getByText("24 GB")).toBeInTheDocument();
    expect(within(panel).getByText("NVIDIA's encoder (NVENC)")).toBeInTheDocument();
    expect(within(panel).getByText("≈ 3 min an episode")).toBeInTheDocument();
    expect(
      within(panel).getByText(
        "Measured on 15 Oct, and since then by 12 conversions and 37 episodes' subtitles. Test again after changing the graphics card or its driver.",
      ),
    ).toBeInTheDocument();

    within(panel).getByRole("button", { name: "Test again" }).click();

    await waitFor(() =>
      expect(
        fetch.mock.calls.filter(
          ([input, init]) => init?.method === "POST" && String(input).endsWith("/system/test"),
        ),
      ).toHaveLength(1),
    );
  });

  it("says when the engine isn't running", async () => {
    shell.invoke.mockImplementation(async (command: string) =>
      command === "engine_status"
        ? { state: "failed", message: "It stopped unexpectedly.", details: "" }
        : undefined,
    );
    fakeEngine({});
    renderSettings("about", false);

    expect(await screen.findByText("Not running")).toBeInTheDocument();
  });

  it("opens the downloads page to show every version and what changed", async () => {
    fakeEngine({ "/folders": FOLDERS, "/health": HEALTH });
    renderSettings("about");

    (await screen.findByRole("button", { name: "Every version and what changed" })).click();

    expect(shell.invoke).toHaveBeenCalledWith("open_downloads_page");
  });

  it("checks for a new version when asked, and installs the one it finds", async () => {
    vi.stubEnv("PROD", true); // only installed copies check for updates
    answerUpdates([null, { version: "0.3.0", notes: "- Check for a new version." }]);
    fakeEngine({ "/folders": FOLDERS, "/health": HEALTH });
    renderSettings("updates", false);

    expect(
      await screen.findByText(/^Up to date · last checked today \d\d:\d\d$/),
    ).toBeInTheDocument();
    expect(await screen.findByText("0.1.0")).toBeInTheDocument();
    screen.getByRole("button", { name: "Check for a new version" }).click();

    expect(await screen.findByText("Kura 0.3.0 is ready to install")).toBeInTheDocument();
    expect(checks()).toBe(2);
    expect(screen.queryByRole("button", { name: "Check for a new version" })).toBeNull();
    screen.getByRole("button", { name: "Restart and update" }).click();

    await waitFor(() => expect(shell.invoke).toHaveBeenCalledWith("install_update"));
  });

  it("says why it couldn't check, and checks again when asked", async () => {
    vi.stubEnv("PROD", true);
    answerUpdates(["error sending request", null]);
    fakeEngine({ "/folders": FOLDERS, "/health": HEALTH });
    renderSettings("updates", false);

    expect(
      await screen.findByText("Can't check right now: error sending request"),
    ).toBeInTheDocument();
    screen.getByRole("button", { name: "Check for a new version" }).click();

    expect(await screen.findByText(/^Up to date · last checked today/)).toBeInTheDocument();
  });

  it("leaves checking for updates to installed copies", async () => {
    fakeEngine({ "/folders": FOLDERS, "/health": HEALTH });
    renderSettings("updates");

    expect(await screen.findByText("Checked in installed copies of Kura")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Check for a new version" })).toBeNull();
    expect(checks()).toBe(0);
  });

  it("takes an unknown section to the first", async () => {
    fakeEngine({ "/folders": FOLDERS });
    renderSettings("nowhere");

    expect(
      await screen.findByRole("switch", { name: "Start Kura when Windows starts" }),
    ).toBeInTheDocument();
  });
});
