import { AudioLines, Captions, FileText, Play } from "lucide-react";
import { type ReactNode, type RefObject, useEffect, useRef, useState } from "react";
import { Link, useLocation, useNavigate, useParams } from "react-router";
import { Breadcrumb, LIBRARY } from "@/components/breadcrumb";
import { type Asking, ConfirmDelete, Deleted, DeleteIcon, useDeleting } from "@/components/delete";
import { EngineProblem } from "@/components/engine-problem";
import { Markdown } from "@/components/markdown";
import { Panel } from "@/components/panel";
import { Poster } from "@/components/poster";
import { NoMatches, SearchField, useAddressSearch } from "@/components/search-field";
import { HeaderSkeleton, Loading, PanelSkeleton } from "@/components/skeleton";
import { StatusLegend, StatusShape, statusWord } from "@/components/status";
import { Button } from "@/components/ui/button";
import { Segmented } from "@/components/ui/segmented";
import { type PlayItem, usePlayer, usePlayingFile } from "@/features/player/player-context";
import {
  type EpisodeState,
  type SeasonCount,
  type TidyResult,
  type TitleDetail,
  type TitleFile,
  useFranchiseMissing,
  useQueueGlance,
  useReport,
  useTitle,
} from "@/lib/engine";
import { openFolder, showInFolder, useExplorer } from "@/lib/explorer";
import { clockLength, codecName, isEnglish, languageName, listed, size, split } from "@/lib/format";
import { files, kindWord } from "@/lib/kinds";
import { matches } from "@/lib/search";
import { share } from "@/lib/share";
import { cn } from "@/lib/utils";
import { AboutPanel } from "./about-panel";

/** One anime or film: how much of it is there, its seasons and episode map, what's missing, its
 * specials and OVAs apart, its videos, and the gap analysis next to it. */
export function TitlePage() {
  const { id } = useParams();
  const titleId = Number(id);
  const title = useTitle(titleId);
  const location = useLocation();
  const came = location.state as { waiting?: number; videos?: boolean } | null;
  // Files that didn't fit the match the owner just gave it.
  const unfit = came?.waiting ?? 0;
  // Deleting asks first, beside what goes; right after, the page says so and offers it back.
  const [asking, setAsking] = useState<Asking | null>(null);
  const [deleted, setDeleted] = useState<TidyResult | null>(null);
  // The season whose videos show; a season's name in Seasons leads there too. A search looks
  // through every season's.
  const [shelf, setShelf] = useState<string | null>(null);
  const [query, setQuery] = useAddressSearch();
  const videosAt = useRef<HTMLElement>(null);
  const toVideos = () => {
    const still = window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
    videosAt.current?.scrollIntoView?.({ block: "start", behavior: still ? "auto" : "smooth" });
  };
  const showSeason = (season: number) => {
    setShelf(String(season));
    setQuery("");
    toVideos();
  };
  // Opened from the title bar's search, the page goes to its videos, searched for the one found.
  const loaded = title.data !== undefined;
  const fromSearch = came?.videos === true;
  // biome-ignore lint/correctness/useExhaustiveDependencies: each time the search leads here
  useEffect(() => {
    if (fromSearch && loaded) toVideos();
  }, [fromSearch, loaded, location.key]);
  const deleting = useDeleting((result) => {
    setAsking(null);
    setDeleted(result);
  });
  // As the queue moves from one file to the next, the videos it made say so.
  const running = useQueueGlance().data?.running ?? null;
  const runningId = running?.job.id ?? null;
  const { refetch } = title;
  const seen = useRef(runningId);
  useEffect(() => {
    if (seen.current === runningId) return;
    seen.current = runningId;
    void refetch();
  }, [runningId, refetch]);
  const ask = (next: Asking) => {
    deleting.reset();
    setDeleted(null);
    setAsking(next);
  };
  const confirm = (where: string) =>
    asking?.where === where ? (
      <ConfirmDelete
        asking={asking}
        busy={deleting.busy}
        problem={deleting.problem}
        onConfirm={() => deleting.delete(asking.files)}
        onCancel={() => setAsking(null)}
      />
    ) : null;

  if (!title.data) {
    return (
      <>
        <Breadcrumb trail={[LIBRARY]} current="…" />
        <EngineProblem queries={[title]} />
        <Loading label="Loading the title" queries={[title]}>
          <HeaderSkeleton />
          <div className="flex flex-wrap items-start gap-5">
            <div className="flex min-w-0 flex-[1.4_1_460px] flex-col gap-5">
              <PanelSkeleton rows={4} />
              <PanelSkeleton rows={3} />
            </div>
            <div className="flex min-w-0 flex-[1_1_340px] flex-col gap-5">
              <PanelSkeleton rows={3} />
            </div>
          </div>
        </Loading>
      </>
    );
  }
  const found = title.data;
  const numbered = found.episodes.filter((episode) => episode.season > 0);
  const specials = found.episodes.filter((episode) => episode.season === 0);

  return (
    <>
      <Breadcrumb
        trail={
          found.franchise
            ? [LIBRARY, { label: found.franchise.name, to: `/franchises/${found.franchise.id}` }]
            : [LIBRARY]
        }
        current={found.name}
      />
      <Header title={found} onAsk={ask} />
      {confirm("title")}
      {deleted && <Deleted result={deleted} onPutBack={() => setDeleted(null)} />}
      {unfit > 0 && <Unfit count={unfit} />}
      <EngineProblem queries={[title]} />
      {found.seasons.length === 0 && <AboutPanel title={found} />}
      {found.seasons.length > 0 && (
        <div className="flex flex-wrap items-start gap-5">
          <div className="flex min-w-0 flex-[1.4_1_460px] flex-col gap-5">
            <Seasons
              seasons={found.seasons}
              episodes={numbered}
              videos={found.videos}
              onShow={showSeason}
              onAsk={ask}
              confirm={asking?.where.startsWith("season-") ? confirm(asking.where) : null}
            />
            <EpisodeMap episodes={numbered} />
            <MissingAndBroken title={found} episodes={numbered} />
          </div>
          <div className="flex min-w-0 flex-[1_1_340px] flex-col gap-5">
            <AboutPanel title={found} />
            {specials.length > 0 && <Specials episodes={specials} />}
            <ReportPanel titleId={found.id} />
          </div>
        </div>
      )}
      <Videos
        title={found}
        shelf={shelf}
        onShelf={setShelf}
        query={query}
        onQuery={setQuery}
        at={videosAt}
        onAsk={ask}
        confirm={confirm}
        making={
          running?.job.kind === "subtitles" && running.total > 0
            ? {
                fileId: running.job.fileId,
                share: Math.floor((100 * running.frames) / running.total),
              }
            : null
        }
      />
    </>
  );
}

function Unfit({ count }: { count: number }) {
  const navigate = useNavigate();
  return (
    <section
      aria-label="Files that didn't fit"
      className="flex animate-fade-up flex-wrap items-center justify-between gap-3 rounded-20 border border-edge bg-glass px-5 py-4 shadow-panel"
    >
      <span className="text-13">
        {count === 1 ? "1 file didn't" : `${count} files didn't`} fit this match.{" "}
        {count === 1 ? "It waits" : "They wait"} for you in Need a match.
      </span>
      <Button size="sm" onClick={() => void navigate("/match")}>
        Match {count === 1 ? "it" : "them"}
      </Button>
    </section>
  );
}

function Header({ title, onAsk }: { title: TitleDetail; onAsk: (asking: Asking) => void }) {
  const navigate = useNavigate();
  const explorer = useExplorer();
  const { play } = usePlayer();
  const playing = usePlayingFile();
  // A film, or anything that's one video, plays from the top: its files in order.
  const playable = title.videos.filter((video) => !video.problem);
  const film = title.kind === "movie" || title.videos.length === 1;
  const first = film ? playable[0] : undefined;
  // What its franchise lacks, on the franchise's page: a title alone in the library has one too.
  // A title whose videos are all gone has no franchise left to show.
  const franchiseId = title.franchise?.id ?? title.id;
  const missing = useFranchiseMissing(franchiseId);
  const lacking = title.files > 0 && !missing.isError ? (missing.data?.titles.length ?? 0) : 0;
  const seasons = title.seasons.length;
  const facts = [
    title.year ? String(title.year) : null,
    seasons > 0 ? `${seasons} ${seasons === 1 ? "season" : "seasons"}` : null,
    title.aired > 0 ? `${title.aired} episodes` : null,
    title.kind === "movie" || title.aired === 0 ? files(title.files) : null,
    title.franchise ? `part of ${title.franchise.name}` : null,
  ].filter(Boolean);

  return (
    <section
      aria-label={title.name}
      className="flex animate-fade-up flex-wrap items-center gap-6 rounded-24 border border-edge bg-glass p-6 shadow-panel"
    >
      <Poster title={title} className="w-30 shrink-0" />
      <div className="flex min-w-0 flex-[1_1_320px] flex-col gap-2">
        <div className="flex flex-wrap items-center gap-2">
          <span className="inline-flex h-6.5 items-center rounded-full bg-accent px-2.5 font-extrabold text-12 text-on-accent">
            {kindWord(title.kind)}
          </span>
          <span className="text-12 text-fg-muted">
            {title.source === "tmdb" ? "Matched on TMDB and AniList" : "Matched on AniList"}
          </span>
          {title.airing && <span className="text-12 text-accent-fg">Still airing</span>}
        </div>
        <h1 className="type-title">{title.name}</h1>
        <span className="text-14 text-fg-muted">{facts.join(" · ")}</span>
        <TitleLanguages videos={title.videos} />
        {title.folder && (
          <span className="font-mono text-12 text-fg-soft [overflow-wrap:anywhere]">
            {title.folder}
          </span>
        )}
        <div className="flex flex-wrap gap-2.5 pt-1.5">
          {first && (
            <Button
              size="sm"
              variant="primary"
              onClick={() => {
                if (playing !== first.id) {
                  play(playable.map((video) => playItem(title, video)));
                }
              }}
            >
              {playing === first.id ? (
                <AudioLines size={16} strokeWidth={2.2} aria-hidden="true" />
              ) : (
                <Play size={14} fill="currentColor" aria-hidden="true" />
              )}
              {playing === first.id ? "Playing" : "Play"}
            </Button>
          )}
          {title.folder && (
            <Button size="sm" onClick={() => explorer.run(() => openFolder(title.folder ?? ""))}>
              Open folder
            </Button>
          )}
          <Button size="sm" onClick={() => void navigate(`/match?title=${title.id}`)}>
            Change match
          </Button>
          {lacking > 0 && (
            <Button size="sm" asChild>
              <Link to={`/franchises/${franchiseId}?missing`}>
                Missing titles <span className="font-mono text-12 text-fg-muted">{lacking}</span>
              </Link>
            </Button>
          )}
          {title.videos.length > 0 && (
            <Button
              size="sm"
              variant="ghost"
              onClick={() => onAsk({ what: title.name, where: "title", files: title.videos })}
            >
              Delete
            </Button>
          )}
        </div>
        {explorer.problem && (
          <p role="alert" className="text-13 text-broken-fg">
            {explorer.problem}
          </p>
        )}
      </div>
      {title.aired > 0 && (
        <div className="flex flex-col items-center gap-1">
          <span className="font-extrabold text-36 tracking-[-0.02em]">
            {share(title.present, title.aired)}%
          </span>
          <span className="text-12 text-fg-muted">
            {title.present} of {title.aired} episodes
          </span>
        </div>
      )}
    </section>
  );
}

function Seasons(props: {
  seasons: SeasonCount[];
  episodes: EpisodeState[];
  videos: TitleFile[];
  /** Shows the season's videos. */
  onShow: (season: number) => void;
  onAsk: (asking: Asking) => void;
  confirm: ReactNode;
}) {
  const { seasons, episodes } = props;
  return (
    <Panel id="seasons-title" title="Seasons" note="Season folders and order, as TMDB numbers them">
      <ul className="flex flex-col">
        {seasons.map((season) => {
          const mine = episodes.filter((episode) => episode.season === season.season);
          const files = props.videos.filter((video) => video.season === season.season);
          return (
            <li
              key={season.season}
              className="grid min-h-10 grid-cols-[5.5rem_1fr_3.5rem_7rem_2rem] items-center gap-3 border-rule border-b text-13 last:border-b-0"
            >
              {files.length > 0 ? (
                <button
                  type="button"
                  title={`Show season ${season.season}'s videos`}
                  onClick={() => props.onShow(season.season)}
                  className="cursor-pointer text-left font-bold underline-offset-3 hover:text-accent-fg hover:underline"
                >
                  Season {season.season}
                </button>
              ) : (
                <span className="font-bold">Season {season.season}</span>
              )}
              <span className="flex h-2 overflow-hidden rounded-3" aria-hidden="true">
                {mine.map((episode) => (
                  <StatusShape
                    key={episode.number}
                    state={episode.state}
                    className="status-joined h-full flex-1 rounded-none"
                  />
                ))}
              </span>
              <span className="text-right font-mono text-12">
                {season.present}/{season.aired}
              </span>
              <span className="text-12 text-fg-muted">{seasonWord(season, mine)}</span>
              {files.length > 0 ? (
                <DeleteIcon
                  label={`Delete season ${season.season}`}
                  onClick={() =>
                    props.onAsk({
                      what: `season ${season.season}`,
                      where: `season-${season.season}`,
                      files,
                    })
                  }
                />
              ) : (
                <span />
              )}
            </li>
          );
        })}
      </ul>
      {props.confirm}
    </Panel>
  );
}

/** Every numbered episode by its state, status by shape: a row of squares to each season, so a
 * long show reads season by season. */
function EpisodeMap({ episodes }: { episodes: EpisodeState[] }) {
  const counted = new Map(episodes.map((episode, index) => [key(episode), index + 1]));
  return (
    <Panel id="map-title" title="Episode map" note="Hover a square for the episode">
      <div className="flex flex-col gap-2.5">
        {seasonsOf(episodes).map(([season, mine]) => (
          <div key={season} className="grid grid-cols-[5rem_1fr] items-start gap-3">
            <span className="font-bold text-12 text-fg-muted leading-3">Season {season}</span>
            <div
              role="img"
              aria-label={`Season ${season}: ${statesIn(mine)}`}
              className="flex flex-wrap gap-1"
            >
              {mine.map((episode) => (
                <span
                  key={key(episode)}
                  className="flex"
                  title={`S${pad(episode.season)}E${pad(episode.number)} · episode ${counted.get(
                    key(episode),
                  )}${episode.name ? ` · ${episode.name}` : ""} · ${statusWord(
                    episode.state,
                  ).toLowerCase()}`}
                >
                  <StatusShape state={episode.state} className="size-3" />
                </span>
              ))}
            </div>
          </div>
        ))}
      </div>
      <StatusLegend states={[...new Set(episodes.map((episode) => episode.state))]} />
    </Panel>
  );
}

/** The episodes by season, in order: [season, its episodes]. */
function seasonsOf(episodes: EpisodeState[]): [number, EpisodeState[]][] {
  const seasons = new Map<number, EpisodeState[]>();
  for (const episode of episodes) {
    const mine = seasons.get(episode.season);
    if (mine) mine.push(episode);
    else seasons.set(episode.season, [episode]);
  }
  return [...seasons];
}

/** "29 ready, 1 broken, 2 missing": how many of each state, in the order they first come. */
function statesIn(episodes: EpisodeState[]): string {
  const counts = new Map<EpisodeState["state"], number>();
  for (const episode of episodes) counts.set(episode.state, (counts.get(episode.state) ?? 0) + 1);
  return [...counts]
    .map(([state, count]) => `${count} ${statusWord(state).toLowerCase()}`)
    .join(", ");
}

function MissingAndBroken({ title, episodes }: { title: TitleDetail; episodes: EpisodeState[] }) {
  const absolute = new Map(episodes.map((episode, index) => [key(episode), index + 1]));
  const rows = runs(
    episodes.filter((episode) => episode.state === "missing" || episode.state === "broken"),
  );
  return (
    <Panel id="gaps-title" title="Missing and broken">
      {rows.length === 0 ? (
        <p className="text-13 text-fg-muted">
          {title.upcoming > 0
            ? `Every aired episode is here. ${title.upcoming} still to air.`
            : "Every episode is here."}
        </p>
      ) : (
        <ul className="grid grid-cols-[1rem_auto_1fr] gap-x-3">
          {rows.map(({ first, last, count }) => (
            <li
              key={key(first)}
              className="col-span-3 grid min-h-10 grid-cols-subgrid items-center border-rule border-b text-13 last:border-b-0"
            >
              <StatusShape state={first.state} className="size-3" />
              <span className="font-mono">
                S{pad(first.season)}E{pad(first.number)}
                {count > 1 && `–E${pad(last.number)}`}
              </span>
              <span className="text-fg-muted">
                {count > 1 ? (
                  `Episodes ${absolute.get(key(first))} to ${absolute.get(key(last))} · ${count} missing`
                ) : (
                  <>
                    Episode {absolute.get(key(first))}
                    {first.name && !first.name.startsWith("Episode ") ? ` · ${first.name}` : ""}
                    {` · ${first.state === "broken" ? "won't play" : "missing"}`}
                    {first.aired ? ` · aired ${day(first.aired)}` : ""}
                  </>
                )}
              </span>
            </li>
          ))}
        </ul>
      )}
    </Panel>
  );
}

type Run = { first: EpisodeState; last: EpisodeState; count: number };

/** Missing episodes in a row within a season: three or more read as one range, as the gap
 * analysis lists them. A broken episode always stands alone: it needs replacing. */
function runs(episodes: EpisodeState[]): Run[] {
  const found: Run[] = [];
  for (const episode of episodes) {
    const run = found.at(-1);
    if (
      run &&
      run.last.state === "missing" &&
      episode.state === "missing" &&
      run.last.season === episode.season &&
      run.last.number + 1 === episode.number
    ) {
      run.last = episode;
      run.count += 1;
    } else {
      found.push({ first: episode, last: episode, count: 1 });
    }
  }
  return found.flatMap((run) =>
    run.count === 2
      ? [
          { first: run.first, last: run.first, count: 1 },
          { first: run.last, last: run.last, count: 1 },
        ]
      : [run],
  );
}

function Specials({ episodes }: { episodes: EpisodeState[] }) {
  const missing = episodes.filter((episode) => episode.state === "missing").length;
  return (
    <Panel
      id="specials-title"
      title="Specials and OVAs"
      note={missing > 0 ? `${missing} not in the library · never counted as missing` : "All here"}
    >
      <ul className="flex flex-col">
        {episodes.map((episode) => (
          <li
            key={key(episode)}
            className="grid min-h-9 grid-cols-[1rem_4.5rem_1fr] items-center gap-3 border-rule border-b text-13 last:border-b-0"
          >
            <StatusShape state={episode.state} className="size-3" />
            <span className="font-mono">S00E{pad(episode.number)}</span>
            <span className="truncate text-fg-muted">
              {episode.name ?? "Special"}
              {episode.aired ? ` · ${day(episode.aired)}` : ""}
            </span>
          </li>
        ))}
      </ul>
    </Panel>
  );
}

function ReportPanel({ titleId }: { titleId: number }) {
  const report = useReport(titleId);
  return (
    <Panel
      id="report-title"
      title="Gap Analysis"
      note="Rewritten after every scan"
      icon={<FileText size={16} />}
    >
      {report.data ? (
        <>
          <div className="max-h-[28rem] overflow-auto rounded-12 bg-inset px-4 py-3.5">
            <Markdown text={report.data.text} />
          </div>
          <span className="font-mono text-11 text-fg-muted [overflow-wrap:anywhere]">
            {report.data.path}
          </span>
          <ReportActions path={report.data.path} text={report.data.text} />
        </>
      ) : (
        <p className="text-13 text-fg-muted">
          {report.isPending
            ? "…"
            : "Kura writes it next to the show once its videos have a folder of their own: tidying up gives them one."}
        </p>
      )}
    </Panel>
  );
}

function ReportActions({ path, text }: { path: string; text: string }) {
  const [copied, setCopied] = useState(false);
  const explorer = useExplorer();
  return (
    <div className="flex flex-wrap items-center gap-2.5">
      <Button size="sm" onClick={() => explorer.run(() => showInFolder(path))}>
        Show in folder
      </Button>
      <Button
        size="sm"
        variant="ghost"
        onClick={() =>
          void navigator.clipboard.writeText(text).then(() => {
            setCopied(true);
          })
        }
      >
        {copied ? "Copied" : "Copy"}
      </Button>
      {explorer.problem && (
        <p role="alert" className="basis-full text-13 text-broken-fg">
          {explorer.problem}
        </p>
      )}
    </div>
  );
}

/** Its videos. A series' come a season at a time, the season picked above them, and a long season
 * keeps to a height and scrolls in its place; a film's file stands alone. */
function Videos(props: {
  title: TitleDetail;
  /** The shelf picked, or none yet: then the one playing, or the first. */
  shelf: string | null;
  onShelf: (shelf: string) => void;
  /** What's searched for, through every shelf: its episode's code or title, or its file's name. */
  query: string;
  onQuery: (query: string) => void;
  at: RefObject<HTMLElement | null>;
  onAsk: (asking: Asking) => void;
  confirm: (where: string) => ReactNode;
  /** The video having its subtitles made now, and how far it's got. */
  making: { fileId: number; share: number } | null;
}) {
  const { title, query } = props;
  const { play } = usePlayer();
  const playing = usePlayingFile();
  const all = shelves(title.videos);
  const shown =
    all.find((shelf) => shelf.key === props.shelf) ??
    all.find((shelf) => shelf.videos.some((video) => video.id === playing)) ??
    all[0];
  if (!shown) return null;
  const found = query
    ? all
        .flatMap((shelf) => shelf.videos)
        .filter((video) => matches(query, ...foundBy(title, video), split(video.path)[0]))
    : shown.videos;
  // What plays next: the rest of the season and the seasons after it; the specials, and files
  // without a season, among themselves.
  const season = (shelf: Shelf) => shelf.key !== "0" && shelf.key !== "other";
  const playFrom = (video: TitleFile) => {
    const own = all.find((shelf) => shelf.videos.includes(video)) ?? shown;
    const following = season(own)
      ? all.filter(season).flatMap((shelf) => shelf.videos)
      : own.videos;
    play(
      following.map((each) => playItem(title, each)),
      following.indexOf(video),
    );
  };
  const numbered = found.some((video) => video.episode !== null);
  const heading =
    title.kind === "movie" ? (title.videos.length === 1 ? "Its file" : "Its files") : "Videos";
  const without = title.videos.filter((video) => !video.problem && !english(video)).length;
  const note = [files(title.videos.length), without > 0 && `${without} without English`]
    .filter(Boolean)
    .join(" · ");
  const seasonal = !query && (season(shown) || shown.key === "0");
  const make = `/subtitles?title=${title.id}${seasonal ? `&season=${shown.key}` : ""}`;
  const count = title.videos.length;
  return (
    <Panel id="videos-title" at={props.at} title={heading} note={note}>
      <div className="flex flex-wrap items-center justify-between gap-3">
        {query ? (
          <span className="text-13 text-fg-muted">
            {found.length} of {count} videos
          </span>
        ) : all.length > 1 ? (
          <Segmented
            label="Season"
            value={shown.key}
            options={all.map((shelf) => ({ value: shelf.key, label: shelf.label }))}
            onChange={props.onShelf}
            className="flex-wrap self-start"
          />
        ) : (
          <span />
        )}
        <div className="flex flex-wrap items-center gap-3">
          {(count > 1 || query) && (
            <SearchField
              value={query}
              onChange={props.onQuery}
              label={`Search the videos of ${title.name}`}
              placeholder={`Search ${count} videos`}
              className="w-56"
            />
          )}
          <Link
            to={make}
            className="press inline-flex min-h-10 items-center gap-2 rounded-full border border-field-edge bg-field px-4 font-bold text-13 text-fg"
          >
            <Captions size={16} strokeWidth={1.9} aria-hidden="true" />
            Make English subtitles
          </Link>
        </div>
      </div>
      {found.length === 0 ? (
        <NoMatches>
          No video of {title.name} goes by “{query.trim()}”.
        </NoMatches>
      ) : (
        <ul
          aria-label={query ? "Videos found" : all.length > 1 ? shown.label : heading}
          className="-mr-2 flex max-h-120 flex-col overflow-y-auto pr-2"
        >
          {found.map((video) => (
            <VideoRow
              key={video.id}
              title={title}
              video={video}
              numbered={numbered}
              playing={playing === video.id}
              making={props.making?.fileId === video.id ? props.making.share : null}
              onPlay={() => playFrom(video)}
              onAsk={props.onAsk}
              confirm={props.confirm(`video-${video.id}`)}
            />
          ))}
        </ul>
      )}
    </Panel>
  );
}

function VideoRow(props: {
  title: TitleDetail;
  video: TitleFile;
  /** Its shelf numbers its episodes: the row starts with the episode's. */
  numbered: boolean;
  playing: boolean;
  /** Its subtitles being made, this far (percent); null otherwise. */
  making: number | null;
  onPlay: () => void;
  onAsk: (asking: Asking) => void;
  confirm: ReactNode;
}) {
  const { video, playing } = props;
  const name = videoName(video);
  return (
    <li
      className={cn(
        "grid min-h-11 items-center gap-x-3 border-rule border-b py-1 text-13 last:border-b-0",
        props.numbered
          ? "grid-cols-[4.5rem_minmax(0,1fr)_minmax(0,1.15fr)_auto_2.25rem_2rem]"
          : "grid-cols-[minmax(0,1fr)_minmax(0,1.15fr)_auto_2.25rem_2rem]",
      )}
    >
      {props.numbered && (
        <span className={cn("font-mono text-12", playing && "font-bold text-accent-fg")}>
          {video.episode !== null ? name : ""}
        </span>
      )}
      <span className={cn("truncate", playing && "font-bold text-accent-fg")} title={video.path}>
        {shownName(props.title, video)}
      </span>
      <Spoken video={video} making={props.making} />
      <span className={cn("text-12", playing ? "font-bold text-accent-fg" : "text-fg-muted")}>
        {playing ? "Playing" : video.problem ? "won't play" : facts(video)}
      </span>
      {/* The same button while it plays, so a keyboard keeps its place. */}
      {video.problem ? (
        <span />
      ) : (
        <button
          type="button"
          aria-label={`${playing ? "Playing" : "Play"} ${name}`}
          onClick={() => {
            if (!playing) props.onPlay();
          }}
          className={cn(
            "press inline-flex size-9 shrink-0 cursor-pointer items-center justify-center rounded-full border",
            playing ? "border-transparent text-accent-fg" : "border-field-edge bg-field text-fg",
          )}
        >
          {playing ? (
            <AudioLines size={16} strokeWidth={2.2} aria-hidden="true" />
          ) : (
            <Play size={14} fill="currentColor" aria-hidden="true" />
          )}
        </button>
      )}
      <DeleteIcon
        label={`Delete ${name}`}
        onClick={() => props.onAsk({ what: name, where: `video-${video.id}`, files: [video] })}
      />
      {props.confirm && <div className="col-span-full pb-2">{props.confirm}</div>}
    </li>
  );
}

/** What a video can be heard and read in: its sound, each of its subtitles (the English ones
 * Kura made marked so), English subtitles being made or waiting in the queue, and a hollow "No
 * English" when neither its sound nor its subtitles are in English. */
function Spoken({ video, making }: { video: TitleFile; making: number | null }) {
  if (video.problem) return <span />;
  const job = making !== null ? "running" : video.subtitlesJob;
  const subtitles = named(video.subtitles.filter((code) => !(video.made && isEnglish(code))));
  return (
    <span className="flex min-w-0 flex-wrap items-center gap-1.5 text-12 text-fg-muted">
      <span title={soundHint(video)}>{soundWords(video)}</span>
      {subtitles.map((name) => (
        <span key={name} className="rounded-full bg-tint/6 px-2 text-fg-soft">
          {name} subs
        </span>
      ))}
      {video.made && (
        <span className="rounded-full bg-accent/14 px-2 font-bold text-accent-fg">
          English subs · made by Kura
        </span>
      )}
      {job === "running" && (
        <span className="inline-flex items-center gap-1.5 font-bold text-accent-fg">
          <span aria-hidden="true" className="size-2 animate-pulse rounded-full bg-accent" />
          Making English subs{making !== null ? ` · ${making}%` : ""}
        </span>
      )}
      {job === "queued" && <span className="text-fg-soft">English subs next in the queue</span>}
      {!english(video) && !job && <NoEnglish />}
    </span>
  );
}

/** A video's sound in words: "Japanese, English", or "Language not labelled" when its file
 * doesn't say (Kura names the language it heard there, when it made English subtitles). */
function soundWords(video: TitleFile): string {
  if (video.sound.length === 0) return "No sound";
  const words = named(video.sound).join(", ");
  return words === languageName("") ? "Language not labelled" : words;
}

function soundHint(video: TitleFile): string | undefined {
  if (video.heard) {
    return `The file doesn't say which language its sound is in: Kura heard ${languageName(video.heard)} when it made English subtitles.`;
  }
  if (video.sound.includes("")) return "The file doesn't say which language its sound is in.";
  return undefined;
}

/** Each language's name once ("jpn" and "ja" are both "Japanese"), in the order first met. */
function named(codes: string[]): string[] {
  return [...new Set(codes.map(languageName))];
}

function NoEnglish({ count }: { count?: number }) {
  return (
    <span className="whitespace-nowrap rounded-full px-2 font-bold text-accent-fg ring-[1.5px] ring-accent-fg/55 ring-inset">
      {count === undefined ? "No English" : `${count} without English`}
    </span>
  );
}

/** What a title can be heard and read in over all its videos ("Japanese sound · German
 * subtitles, English on 64 of 303"), and how many of them have no English. */
function TitleLanguages({ videos }: { videos: TitleFile[] }) {
  const readable = videos.filter((video) => !video.problem);
  if (readable.length === 0) return null;
  const sound = byUse(readable.flatMap((video) => named(video.sound.filter(Boolean))));
  const others = byUse(
    readable.flatMap((video) => named(video.subtitles.filter((code) => code && !isEnglish(code)))),
  );
  const subtitled = readable.filter((video) => video.subtitles.some(isEnglish)).length;
  const without = readable.filter((video) => !english(video)).length;
  const words = [
    sound.length > 0 ? `${listed(sound.slice(0, 3))} sound` : null,
    subtitleWords(others.slice(0, 3), subtitled, readable.length),
  ].filter(Boolean);
  return (
    <span className="flex flex-wrap items-center gap-2 text-13 text-fg-soft">
      {words.join(" · ")}
      {without > 0 && <NoEnglish count={readable.length > 1 ? without : undefined} />}
    </span>
  );
}

/** "German and English subtitles", "German subtitles, English on 64 of 303", "No subtitles". */
function subtitleWords(others: string[], english: number, of: number): string {
  if (english === of) return `${listed([...others, "English"])} subtitles`;
  const rest = others.length > 0 ? `${listed(others)} subtitles` : null;
  if (english === 0) return rest ?? "No subtitles";
  return rest
    ? `${rest}, English on ${english} of ${of}`
    : `English subtitles on ${english} of ${of}`;
}

/** Each language once, the most used first. */
function byUse(codes: string[]): string[] {
  const counts = new Map<string, number>();
  for (const code of codes) counts.set(code, (counts.get(code) ?? 0) + 1);
  return [...counts].sort((a, b) => b[1] - a[1]).map(([code]) => code);
}

/** Whether a video can be watched in English: English sound, or English subtitles. */
function english(video: TitleFile): boolean {
  return [...video.sound, ...video.subtitles].some(isEnglish);
}

/** One season's videos, the specials', or those of files without a season. */
interface Shelf {
  /** The season's number, or "other". */
  key: string;
  label: string;
  videos: TitleFile[];
}

/** A title's videos by season, in episode order: "Season 1" onwards, then "Specials", then
 * "Other files" for any without a season. */
function shelves(videos: TitleFile[]): Shelf[] {
  const bySeason = new Map<number | null, TitleFile[]>();
  for (const video of videos) {
    bySeason.set(video.season, [...(bySeason.get(video.season) ?? []), video]);
  }
  // Seasons in order, the specials after them, files without a season last.
  const rank = (season: number | null) =>
    season === null ? Number.MAX_SAFE_INTEGER : season === 0 ? Number.MAX_SAFE_INTEGER - 1 : season;
  return [...bySeason]
    .sort(([a], [b]) => rank(a) - rank(b))
    .map(([season, mine]) => ({
      key: season === null ? "other" : String(season),
      label: season === null ? "Other files" : season === 0 ? "Specials" : `Season ${season}`,
      videos: mine.toSorted(
        (a, b) =>
          (a.episode ?? Number.MAX_SAFE_INTEGER) - (b.episode ?? Number.MAX_SAFE_INTEGER) ||
          a.path.localeCompare(b.path),
      ),
    }));
}

/** The episode's title when the episode list has it, else the file's name. */
function shownName(title: TitleDetail, video: TitleFile): string {
  const episode =
    video.episode === null
      ? undefined
      : title.episodes.find(
          (each) => each.season === video.season && each.number === video.episode,
        );
  return episode?.name ?? split(video.path)[0];
}

/** What a video is found by on its title's page, besides its file's name: the code and title of
 * each episode it holds ("S01E01", "S01E02" for a file of two), or its own name. */
function foundBy(title: TitleDetail, video: TitleFile): string[] {
  const { season, episode } = video;
  if (season === null || episode === null) return [videoName(video), shownName(title, video)];
  const numbers = Array.from(
    { length: (video.episodeEnd ?? episode) - episode + 1 },
    (_, step) => episode + step,
  );
  return [
    videoName(video),
    ...numbers.flatMap((number) => [
      code(season, number),
      title.episodes.find((each) => each.season === season && each.number === number)?.name ?? "",
    ]),
  ];
}

/** "1080p · HEVC · 24 min · 412 MB". */
function facts(video: TitleFile): string {
  return [
    video.height ? `${video.height}p` : null,
    video.codec ? codecName(video.codec) : null,
    video.duration ? clockLength(video.duration / 60) : null,
    size(video.size),
  ]
    .filter(Boolean)
    .join(" · ");
}

/** A video as the player names it: "Dragon Ball Z · S01E05" and its episode's title, or the
 * film's name, or its file's name. */
function playItem(title: TitleDetail, video: TitleFile): PlayItem {
  const numbered = video.season !== null && video.episode !== null;
  const episode = title.episodes.find(
    (each) => each.season === video.season && each.number === video.episode,
  );
  const name = video.path.split("\\").at(-1) ?? video.path;
  return {
    fileId: video.id,
    label: numbered ? `${title.name} · ${videoName(video)}` : title.name,
    name: numbered ? (episode?.name ?? null) : name,
    path: video.path,
  };
}

/** "S01E03", "S01E03-E04", or the file's name when it has no episode number. */
function videoName(video: TitleFile): string {
  if (video.season === null || video.episode === null) {
    return video.path.split("\\").at(-1) ?? video.path;
  }
  const last = video.episodeEnd ? `-E${pad(video.episodeEnd)}` : "";
  return `S${pad(video.season)}E${pad(video.episode)}${last}`;
}

function seasonWord(season: SeasonCount, episodes: EpisodeState[]): string {
  const missing = season.aired - season.present;
  const broken = episodes.filter((episode) => episode.state === "broken").length;
  const toAir = season.total - season.aired;
  if (missing > 0) return `${missing} missing`;
  if (broken > 0) return `${broken} broken`;
  if (toAir > 0) return `${toAir} still to air`;
  return "complete";
}

function key(episode: EpisodeState): string {
  return `${episode.season}-${episode.number}`;
}

function pad(value: number): string {
  return String(value).padStart(2, "0");
}

/** "S01E05". */
function code(season: number, number: number): string {
  return `S${pad(season)}E${pad(number)}`;
}

function day(iso: string): string {
  return new Date(`${iso}T12:00:00`).toLocaleDateString("en-GB", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}
