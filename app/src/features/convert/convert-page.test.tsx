import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router";
import { afterEach, describe, expect, it, vi } from "vitest";
import {
  type Ability,
  type ConvertOptions,
  EngineProvider,
  type FranchiseSummary,
  type QueueStatus,
  type System,
  type TitleSummary,
} from "@/lib/engine";
import { convertible } from "@/test/convert";
import { fakeEngine, READY, SETTINGS, SYSTEM, UNCHECKED } from "@/test/engine";
import { ConvertPage } from "./convert-page";

const shell = vi.hoisted(() => ({ invoke: vi.fn() }));

vi.mock("@tauri-apps/api/core", () => ({ invoke: shell.invoke }));
vi.mock("@tauri-apps/api/event", () => ({ listen: async () => () => {} }));

const OPTIONS: ConvertOptions = {
  standard: "Cinema 1080p",
  files: [
    convertible(1),
    convertible(2),
    convertible(3, { season: 2, episode: 1, label: "Dragon Ball Z · S02E01" }),
    convertible(4, { titleId: 2, title: "Dragon Ball GT", broken: true, ways: {} }),
    convertible(
      5,
      { titleId: 2, title: "Dragon Ball GT", height: 720, aspect: "16:9" },
      { best: 600, fast: 600, reencode: 120 },
    ),
  ],
  free: { "D:": 931_000_000_000 },
  setAside: {},
};
OPTIONS.files[4] = {
  ...(OPTIONS.files[4] as (typeof OPTIONS.files)[number]),
  ways: {
    best: { method: "fast", gpuSeconds: 600 },
    fast: { method: "fast", gpuSeconds: 600 },
    reencode: { method: "reencode", gpuSeconds: 120 },
  },
};

const FRANCHISES = [
  {
    id: 1,
    name: "Dragon Ball",
    titles: [
      { id: 1, name: "Dragon Ball Z" },
      { id: 2, name: "Dragon Ball GT" },
    ] as TitleSummary[],
  },
] as FranchiseSummary[];

const QUEUE: QueueStatus = {
  paused: false,
  schedule: "now",
  waitsForNight: false,
  problem: null,
  running: null,
  queued: [],
  gpuSeconds: 0,
  today: [],
  gpu: null,
  room: null,
  endsAt: null,
  early: false,
};

/** The owner's PC with some of its parts as another PC has them. */
function another(
  parts: Partial<Record<Ability["part"], Partial<Ability>>>,
  more: Partial<System> = {},
) {
  return {
    ...SYSTEM,
    abilities: SYSTEM.abilities.map((each) => ({ ...each, ...parts[each.part] })),
    ...more,
  };
}

const LAPTOP = another(
  {
    convert: { how: "HEVC 10-bit on Intel Quick Sync", seconds: [840] },
    ai: {
      state: "slow",
      how: "Real-ESRGAN on the processor's graphics, slowly",
      note: "SD episodes get the fast upscale unless you choose the AI model on Convert.",
      seconds: [32_400],
    },
  },
  {
    graphicsCard: "Intel(R) UHD Graphics 620",
    card: {
      name: "Intel(R) UHD Graphics 620",
      maker: "intel",
      memory: 128 * 1024 ** 2,
      integrated: true,
      driver: "31.0.101.2111",
    },
    encoder: "qsv",
  },
);

function renderConvert(address = "/convert") {
  shell.invoke.mockImplementation(async (command: string) =>
    command === "engine_status" ? READY : undefined,
  );
  const queries = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={queries}>
      <EngineProvider>
        <MemoryRouter initialEntries={[address]}>
          <Routes>
            <Route path="/convert" element={<ConvertPage />} />
            <Route path="/convert/queue" element={<p>The queue</p>} />
          </Routes>
        </MemoryRouter>
      </EngineProvider>
    </QueryClientProvider>,
  );
}

function sent(fetch: ReturnType<typeof fakeEngine>, method: string, path: string) {
  return fetch.mock.calls.filter(
    ([input, init]) =>
      (init?.method ?? "GET") === method && new URL(String(input)).pathname === path,
  );
}

describe("ConvertPage", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    shell.invoke.mockReset();
  });

  it("lists what isn't at the standard by franchise, title and season", async () => {
    fakeEngine({ "/convert": OPTIONS, "/franchises": FRANCHISES, "/queue": QUEUE });
    renderConvert();

    expect(
      await screen.findByRole("checkbox", { name: /Dragon Ball\s*franchise/ }),
    ).toBeInTheDocument();
    expect(screen.getByRole("checkbox", { name: /Dragon Ball Z\s*3 left/ })).toBeInTheDocument();
    expect(screen.getByRole("checkbox", { name: /Season 1\s*2 episodes/ })).toBeInTheDocument();
    expect(
      screen.getByRole("checkbox", { name: /Dragon Ball GT\s*1 left, 1 broken skipped/ }),
    ).toBeInTheDocument();
    expect(screen.getByText("Nothing chosen yet")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Choose what to convert" })).toBeDisabled();
  });

  it("finds a title to convert by its name, or its franchise's whole", async () => {
    fakeEngine({ "/convert": OPTIONS, "/franchises": FRANCHISES, "/queue": QUEUE });
    renderConvert();

    const search = await screen.findByRole("searchbox", { name: "Search what to convert" });
    expect(search).toHaveAttribute("placeholder", "Search 2 titles");
    fireEvent.change(search, { target: { value: "gt" } });

    // The title found stands on its own: ticking it ticks only its files.
    const gt = await screen.findByRole("checkbox", { name: /Dragon Ball GT\s*1 left/ });
    expect(screen.queryByRole("checkbox", { name: /franchise/ })).not.toBeInTheDocument();
    expect(screen.queryByRole("checkbox", { name: /Dragon Ball Z/ })).not.toBeInTheDocument();
    fireEvent.click(gt);
    expect(await screen.findByText("1 episode")).toBeInTheDocument();

    fireEvent.change(search, { target: { value: "dragon ball" } });
    expect(
      await screen.findByRole("checkbox", { name: /Dragon Ball\s*franchise/ }),
    ).toBeInTheDocument();
    expect(screen.getByRole("checkbox", { name: /Dragon Ball Z\s*3 left/ })).toBeInTheDocument();

    fireEvent.change(search, { target: { value: "Trigun" } });
    expect(await screen.findByRole("status")).toHaveTextContent("No title goes by “Trigun”.");
  });

  it("adds up what's chosen, and what each way takes", async () => {
    fakeEngine({ "/convert": OPTIONS, "/franchises": FRANCHISES, "/queue": QUEUE });
    renderConvert();

    (await screen.findByRole("checkbox", { name: /Season 1/ })).click();

    expect(await screen.findAllByText("2 episodes")).toHaveLength(2); // the season, and the chip
    expect(screen.getByText("48 min of video")).toBeInTheDocument();
    expect(screen.getByText("SD 480p · 4:3")).toBeInTheDocument();
    expect(screen.getByRole("radio", { name: /Best quality/ })).toHaveTextContent(
      "≈ 1 h per episode",
    );
    expect(screen.getByRole("radio", { name: /Fast/ })).toHaveTextContent("≈ 12 min per episode");
    expect(screen.getByText("≈ 2 h")).toBeInTheDocument();
    expect(screen.getByText("466 MB → 900 MB")).toBeInTheDocument();
    expect(screen.getByText("free, plenty for this")).toBeInTheDocument();
    expect(
      screen.getByText("4:3 shows stay 4:3 at 1440 × 1080. Nothing is stretched or cropped."),
    ).toBeInTheDocument();
    expect(screen.getByRole("checkbox", { name: /Dragon Ball Z\s*3 left/ })).toBePartiallyChecked();
  });

  it("starts with the videos ticked on a title's page chosen", async () => {
    fakeEngine({ "/convert": OPTIONS, "/franchises": FRANCHISES, "/queue": QUEUE });
    renderConvert("/convert?files=1,2,4,junk"); // 4 won't play: it can't be converted

    expect(await screen.findAllByText("2 episodes")).toHaveLength(2); // the season, and the chip
    expect(screen.getByRole("checkbox", { name: /Season 1/ })).toBeChecked();
  });

  it("says when a file gets less than the way chosen", async () => {
    fakeEngine({ "/convert": OPTIONS, "/franchises": FRANCHISES, "/queue": QUEUE });
    renderConvert();

    (await screen.findByRole("checkbox", { name: /Dragon Ball GT/ })).click();

    expect(
      await screen.findByText(/1 file gets Fast instead: the AI model is for SD/),
    ).toBeInTheDocument();
  });

  it("chooses the standard right here, and the estimates follow", async () => {
    let saved = SETTINGS;
    const compact: ConvertOptions = {
      ...OPTIONS,
      standard: "Compact 720p",
      files: OPTIONS.files.map((file) => ({ ...file, outputBytes: 250_000_000 })),
    };
    const fetch = fakeEngine({
      "/convert": () => (saved.standard === "compact-720" ? compact : OPTIONS),
      "/franchises": FRANCHISES,
      "/queue": QUEUE,
      "/settings": () => saved,
      "PUT /settings": (init?: RequestInit) => {
        saved = JSON.parse(String(init?.body));
        return saved;
      },
    });
    renderConvert();

    (await screen.findByRole("checkbox", { name: /Season 1/ })).click();
    expect(await screen.findByText("466 MB → 900 MB")).toBeInTheDocument();
    expect(screen.getByText("1080p · HEVC 10-bit · MKV")).toBeInTheDocument();
    (await screen.findByRole("radio", { name: "Compact 720p" })).click();

    expect(await screen.findByText("466 MB → 500 MB")).toBeInTheDocument();
    expect(saved.standard).toBe("compact-720");
    expect(sent(fetch, "PUT", "/settings")).toHaveLength(1);
    expect(screen.getByText("720p · HEVC 10-bit · MKV")).toBeInTheDocument();
  });

  it("says when every way does the same, for files that need no upscaling", async () => {
    const hd = convertible(
      6,
      { height: 1080, aspect: "16:9", label: "Dragon Ball Z · S01E06" },
      { best: 180, fast: 180, reencode: 180 },
    );
    hd.ways = {
      best: { method: "reencode", gpuSeconds: 180 },
      fast: { method: "reencode", gpuSeconds: 180 },
      reencode: { method: "reencode", gpuSeconds: 180 },
    };
    fakeEngine({
      "/convert": { ...OPTIONS, files: [hd] },
      "/franchises": FRANCHISES,
      "/queue": QUEUE,
    });
    renderConvert();

    (await screen.findByRole("checkbox", { name: /Dragon Ball Z/ })).click();

    expect(
      await screen.findByText(
        "This file needs no upscaling, so every way only re-encodes it to your standard and takes the same.",
      ),
    ).toBeInTheDocument();
    expect(screen.queryByText(/instead/)).not.toBeInTheDocument();
  });

  it("deletes originals once checked when asked, and reckons room that way", async () => {
    let saved = SETTINGS;
    const big = (id: number) => convertible(id, { size: 2_000_000_000 }); // results are smaller
    fakeEngine({
      "/convert": { ...OPTIONS, files: [big(1), big(2)], free: { "D:": 600_000_000 } },
      "/franchises": FRANCHISES,
      "/queue": QUEUE,
      "/settings": () => saved,
      "PUT /settings": (init?: RequestInit) => {
        saved = JSON.parse(String(init?.body));
        return saved;
      },
    });
    renderConvert();

    (await screen.findByRole("checkbox", { name: /Dragon Ball Z/ })).click();
    expect(await screen.findByText(/free: not enough, this needs 1\.1 GB/)).toBeInTheDocument();
    expect(screen.getByText("Kept 30 days")).toBeInTheDocument();
    screen.getByRole("radio", { name: "Delete" }).click();

    expect(await screen.findByText("Deleted")).toBeInTheDocument();
    expect(saved.originals).toBe("delete");
    expect(
      screen.getByText("for good, once each result is checked and in place: no putting back"),
    ).toBeInTheDocument();
    expect(await screen.findByText("free, plenty for this")).toBeInTheDocument();
  });

  it("offers another standard when everything is at this one", async () => {
    let saved = SETTINGS;
    fakeEngine({
      "/convert": () =>
        saved.standard === "compact-720" ? OPTIONS : { ...OPTIONS, files: [] as never[] },
      "/franchises": FRANCHISES,
      "/queue": QUEUE,
      "/settings": () => saved,
      "PUT /settings": (init?: RequestInit) => {
        saved = JSON.parse(String(init?.body));
        return saved;
      },
    });
    renderConvert();

    expect(
      await screen.findByRole("heading", { name: "Everything is at your standard" }),
    ).toBeInTheDocument();
    (await screen.findByRole("radio", { name: "Compact 720p" })).click();

    expect(await screen.findByRole("checkbox", { name: /Season 1/ })).toBeInTheDocument();
    expect(saved.standard).toBe("compact-720");
  });

  it("queues what's chosen to start now, then shows the queue", async () => {
    const fetch = fakeEngine({
      "/convert": OPTIONS,
      "/franchises": FRANCHISES,
      "/queue": QUEUE,
      "POST /queue": { added: 3 },
    });
    renderConvert();

    (await screen.findByRole("checkbox", { name: /Dragon Ball Z\s*3 left/ })).click();
    (await screen.findByRole("radio", { name: /Re-encode only/ })).click();
    (await screen.findByRole("button", { name: "Add 3 episodes to the queue" })).click();

    expect(await screen.findByText("The queue")).toBeInTheDocument();
    const [[, init]] = sent(fetch, "POST", "/queue") as [[unknown, RequestInit]];
    expect(JSON.parse(String(init.body))).toEqual({
      files: [1, 2, 3],
      method: "reencode",
      when: "now",
      fit: [],
    });
  });

  it("can queue for the night instead, in one step", async () => {
    const fetch = fakeEngine({
      "/convert": OPTIONS,
      "/franchises": FRANCHISES,
      "/queue": QUEUE,
      "POST /queue": { added: 2 },
    });
    renderConvert();

    (await screen.findByRole("checkbox", { name: /Season 1/ })).click();
    (await screen.findByRole("radio", { name: /Nights only/ })).click();
    (await screen.findByRole("button", { name: "Add 2 episodes to the queue" })).click();

    expect(await screen.findByText("The queue")).toBeInTheDocument();
    const [[, init]] = sent(fetch, "POST", "/queue") as [[unknown, RequestInit]];
    expect(JSON.parse(String(init.body))).toMatchObject({ when: "nights" });
    expect(sent(fetch, "PUT", "/queue/schedule")).toHaveLength(0);
  });

  it("warns of a drive without room, though another has plenty", async () => {
    fakeEngine({
      "/convert": {
        ...OPTIONS,
        files: [convertible(1), convertible(2, { drive: "F:" })],
        free: { "D:": 931_000_000_000, "F:": 200_000_000 },
      },
      "/franchises": FRANCHISES,
      "/queue": QUEUE,
    });
    renderConvert();

    (await screen.findByRole("checkbox", { name: /Dragon Ball Z\s*2 left/ })).click();

    expect(await screen.findByText("Space on F:")).toBeInTheDocument();
    expect(screen.getByText("free: not enough, this needs 563 MB")).toBeInTheDocument();
  });

  it("asks what to do when a drive hasn't room for the choice", async () => {
    const fetch = fakeEngine({
      "/convert": { ...OPTIONS, free: { "D:": 600_000_000 }, setAside: { "D:": 3_400_000_000 } },
      "/franchises": FRANCHISES,
      "/queue": QUEUE,
      "POST /queue": { added: 2 },
    });
    renderConvert();

    (await screen.findByRole("checkbox", { name: /Season 1/ })).click();
    (await screen.findByRole("button", { name: "Add 2 episodes to the queue" })).click();

    const dialog = await screen.findByRole("alertdialog", { name: "Not enough space" });
    expect(dialog).toHaveTextContent(
      "Dragon Ball Z · Season 1 needs about 1.1 GB. D: has 600 MB free.",
    );
    expect(sent(fetch, "POST", "/queue")).toHaveLength(0);
    fireEvent.click(screen.getByRole("button", { name: "Back" }));
    expect(screen.queryByRole("alertdialog")).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Add 2 episodes to the queue" }));
    fireEvent.click(await screen.findByRole("button", { name: /Convert the 1 that fit now/ }));

    expect(await screen.findByText("The queue")).toBeInTheDocument();
    const [[, init]] = sent(fetch, "POST", "/queue") as [[unknown, RequestInit]];
    expect(JSON.parse(String(init.body))).toMatchObject({ files: [1, 2], fit: ["D:"] });
  });

  it("empties the drive's quarantine first, once that's confirmed, then queues", async () => {
    const fetch = fakeEngine({
      "/convert": { ...OPTIONS, free: { "D:": 600_000_000 }, setAside: { "D:": 3_400_000_000 } },
      "/franchises": FRANCHISES,
      "/queue": QUEUE,
      "POST /queue": { added: 2 },
      "POST /quarantine/empty": { files: 4 },
    });
    renderConvert();

    (await screen.findByRole("checkbox", { name: /Season 1/ })).click();
    (await screen.findByRole("button", { name: "Add 2 episodes to the queue" })).click();
    fireEvent.click(await screen.findByRole("button", { name: /Empty quarantine first/ }));
    fireEvent.click(await screen.findByRole("button", { name: "Empty quarantine" }));

    expect(await screen.findByText("The queue")).toBeInTheDocument();
    const [[, emptied]] = sent(fetch, "POST", "/quarantine/empty") as [[unknown, RequestInit]];
    expect(JSON.parse(String(emptied.body))).toEqual({ drive: "D:" });
    const [[, init]] = sent(fetch, "POST", "/queue") as [[unknown, RequestInit]];
    expect(JSON.parse(String(init.body))).toMatchObject({ files: [1, 2], fit: [] });
  });

  it("shows a frame before and after, at three points of the file", async () => {
    const problem = "The graphics card couldn't run the AI model (DirectML needs DirectX 12).";
    const fetch = fakeEngine({
      "/convert": OPTIONS,
      "/franchises": FRANCHISES,
      "/queue": QUEUE,
      "/convert/1/preview/after": () => Response.json({ detail: problem }, { status: 422 }),
    });
    renderConvert();

    const panel = await screen.findByRole("region", { name: "See it first" });
    expect(panel).toHaveTextContent("Dragon Ball Z · S01E01 · drag the handle");
    expect(panel).toHaveTextContent("After · best quality 1080p");
    expect(screen.getByRole("button", { name: "12:00" })).toHaveAttribute("aria-pressed", "true");
    expect(await screen.findByText(problem)).toBeInTheDocument();

    screen.getByRole("button", { name: "3:36" }).click();

    await waitFor(() =>
      expect(
        fetch.mock.calls.some(([input]) =>
          String(input).endsWith("/convert/1/preview/after?way=best&point=0"),
        ),
      ).toBe(true),
    );
  });

  it("says when everything is at the standard", async () => {
    fakeEngine({
      "/convert": { ...OPTIONS, files: [] },
      "/franchises": FRANCHISES,
      "/queue": QUEUE,
    });
    renderConvert();

    expect(
      await screen.findByRole("heading", { name: "Everything is at your standard" }),
    ).toBeInTheDocument();
  });

  it("says its times are this PC's own once it's measured", async () => {
    fakeEngine({
      "/convert": OPTIONS,
      "/franchises": FRANCHISES,
      "/queue": QUEUE,
      "/system": SYSTEM,
    });
    renderConvert();

    expect(
      await screen.findByText("Measured on this PC · NVIDIA GeForce GTX 1660 SUPER"),
    ).toBeInTheDocument();
    expect(screen.queryByText(/These times are a guess/)).toBeNull();
  });

  it("says its times are a guess till this PC is measured, and tests it on asking", async () => {
    const fetch = fakeEngine({
      "/convert": OPTIONS,
      "/franchises": FRANCHISES,
      "/queue": QUEUE,
      "/system": UNCHECKED,
      "POST /system/test": {
        ...UNCHECKED,
        testing: { step: "encoder", done: [], fps: null, timing: true },
      },
    });
    renderConvert();

    expect(
      await screen.findByText(
        "These times are a guess, from a GTX 1660 Super, until Kura has measured this PC.",
      ),
    ).toBeInTheDocument();
    screen.getByRole("button", { name: "Test this PC" }).click();

    await waitFor(() => expect(sent(fetch, "POST", "/system/test")).toHaveLength(1));
  });

  it("chooses Fast where the AI model is slow on this PC, and says so", async () => {
    fakeEngine({
      "/convert": OPTIONS,
      "/franchises": FRANCHISES,
      "/queue": QUEUE,
      "/system": LAPTOP,
    });
    renderConvert();

    const best = await screen.findByRole("radio", { name: /Best quality/ });
    await waitFor(() => expect(screen.getByRole("radio", { name: /Fast/ })).toBeChecked());
    expect(best).toHaveTextContent("Slow here");
    expect(
      screen.getByText(
        "On this PC's graphics the AI model takes about 9 hours an episode, so Fast is chosen for SD. Choose Best quality any time: it's slow, not worse.",
      ),
    ).toBeInTheDocument();
    expect(screen.getByRole("radio", { name: /Re-encode only/ })).toHaveTextContent(
      "Intel Quick Sync encoder",
    );

    best.click();

    await waitFor(() => expect(best).toBeChecked()); // slow, not worse: still the owner's to choose
  });

  it("can't choose a way this PC can't run, and says why", async () => {
    const why =
      "Its graphics card can't run the AI model: it needs DirectX 12. SD episodes get the fast upscale instead.";
    fakeEngine({
      "/convert": OPTIONS,
      "/franchises": FRANCHISES,
      "/queue": QUEUE,
      "/system": another({ ai: { state: "no", how: "Not on this PC", note: why, seconds: [] } }),
    });
    renderConvert();

    const best = await screen.findByRole("radio", { name: /Best quality/ });
    await waitFor(() => expect(best).toBeDisabled());
    expect(best).toHaveTextContent("Not on this PC");
    expect(best).toHaveTextContent(why);
    expect(screen.getByRole("radio", { name: /Fast/ })).toBeChecked();
  });

  it("says when this PC can't convert, and what still works", async () => {
    const r7: System["card"] = {
      name: "AMD Radeon R7 250",
      maker: "amd",
      memory: 2 * 1024 ** 3,
      integrated: false,
      driver: "27.20.20913.2000",
    };
    fakeEngine({
      "/convert": OPTIONS,
      "/franchises": FRANCHISES,
      "/queue": QUEUE,
      "/system": { ...SYSTEM, card: r7, graphicsCard: r7?.name ?? null, encoder: null },
    });
    renderConvert();

    expect(await screen.findByText("This PC can't convert to your standard")).toBeInTheDocument();
    expect(
      screen.getByText(/Its graphics card, an AMD Radeon R7 250, has no encoder for HEVC 10-bit/),
    ).toHaveTextContent("English subtitles and the player");
    expect(screen.getByRole("button", { name: "Test this PC again" })).toBeInTheDocument();
    expect(screen.queryByRole("radio", { name: /Best quality/ })).toBeNull();
  });

  it("links the card maker's drivers when its encoder didn't start", async () => {
    fakeEngine({
      "/convert": OPTIONS,
      "/franchises": FRANCHISES,
      "/queue": QUEUE,
      "/system": {
        ...SYSTEM,
        encoder: null,
        driverLink: "https://www.nvidia.com/Download/index.aspx",
        encoderProblem: "Driver does not support the required nvenc API version.",
      },
    });
    renderConvert();

    expect(await screen.findByText("NVIDIA's encoder didn't start")).toBeInTheDocument();
    expect(
      screen.getByText("hevc_nvenc: Driver does not support the required nvenc API version"),
    ).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "NVIDIA's drivers" })).toHaveAttribute(
      "href",
      "https://www.nvidia.com/Download/index.aspx",
    );
  });
});
