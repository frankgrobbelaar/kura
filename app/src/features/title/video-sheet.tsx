import { Play } from "lucide-react";
import { type ReactNode, useState } from "react";
import { Facts, Synopsis } from "@/components/about";
import { FileNote, useFileActions } from "@/components/file-actions";
import { StatusShape } from "@/components/status";
import { Button } from "@/components/ui/button";
import { Sheet, SheetContent } from "@/components/ui/sheet";
import {
  type FileDetails,
  type TitleDetail,
  useEpisodeDetails,
  useFileDetails,
} from "@/lib/engine";
import { clockTime, codecName, languageName, size, split } from "@/lib/format";

/** What the sheet tells of: one of the title's videos, or one of its episodes, which the
 * library may not have. */
export type Opened = { video: number } | { episode: { season: number; number: number } };

/** One video or episode in full, beside the title's page: what happens in it (hidden till asked,
 * as it gives the story away), what the file holds and where it is, and what converting it does. */
export function VideoSheet(props: {
  title: TitleDetail;
  opened: Opened | null;
  onClose: () => void;
  onPlay: (fileId: number) => void;
}) {
  const { title, opened } = props;
  const asked = opened && "episode" in opened ? opened.episode : null;
  const episode = useEpisodeDetails(
    title.id,
    asked?.season ?? 0,
    asked?.number ?? 0,
    asked !== null,
  );
  const fileId = opened && "video" in opened ? opened.video : (episode.data?.fileId ?? null);
  const file = useFileDetails(fileId);
  const found = fileId === null ? null : file.data;
  const season = found?.season ?? asked?.season ?? null;
  const number = found?.episode ?? asked?.number ?? null;
  const name = found?.episodeName ?? episode.data?.name ?? null;
  const aired = found?.aired ?? episode.data?.aired ?? null;
  const overview = found ? found.overview : (episode.data?.overview ?? null);
  const heading =
    season !== null && number !== null
      ? `${code(season, number, found?.episodeEnd ?? null)}${name ? ` · ${name}` : ""}`
      : found
        ? split(found.path)[0]
        : "…";
  const line = [title.name, aired ? `aired ${day(aired)}` : null].filter(Boolean).join(" · ");
  return (
    <Sheet open={opened !== null} onOpenChange={(open) => !open && props.onClose()}>
      {opened && (
        <SheetContent title={heading} description={line}>
          {found ? (
            <Video file={found} onPlay={() => props.onPlay(found.id)} />
          ) : fileId === null && episode.data ? (
            <span className="inline-flex h-6 items-center gap-1.5 self-start rounded-full bg-tint/6 px-2.25 font-bold text-11">
              <StatusShape state="missing" className="size-2" />
              Not in your library
            </span>
          ) : (
            (file.isError || episode.isError) && (
              <p role="alert" className="text-13 text-broken-fg">
                {(file.error ?? episode.error)?.message}
              </p>
            )
          )}
          {overview && <WhatHappens text={overview} />}
          {found && <TheFile file={found} />}
        </SheetContent>
      )}
    </Sheet>
  );
}

/** Play, and the file's place: shown in its folder, or its path copied. */
function Video({ file, onPlay }: { file: FileDetails; onPlay: () => void }) {
  const actions = useFileActions();
  return (
    <div className="flex flex-col gap-2">
      <div className="flex flex-wrap gap-2">
        {!file.problem && (
          <Button size="sm" variant="primary" onClick={onPlay}>
            <Play size={14} fill="currentColor" aria-hidden="true" />
            Play
          </Button>
        )}
        <Button size="sm" onClick={() => actions.show(file.path)}>
          Show in folder
        </Button>
        <Button size="sm" variant="ghost" onClick={() => actions.copy(file.path)}>
          Copy path
        </Button>
      </div>
      <FileNote actions={actions} />
    </div>
  );
}

/** What happens in an episode: hidden till asked, as it gives the story away. */
function WhatHappens({ text }: { text: string }) {
  const [shown, setShown] = useState(false);
  return (
    <section aria-label="What happens" className="flex flex-col items-start gap-2">
      {shown ? (
        <Synopsis text={text} lines={6} />
      ) : (
        <p className="text-13 text-fg-muted">
          What happens in it stays hidden: it gives the story away.
        </p>
      )}
      <Button size="sm" variant="ghost" className="-ml-3.5" onClick={() => setShown(!shown)}>
        {shown ? "Hide what happens" : "Show what happens"}
      </Button>
    </section>
  );
}

/** The file: what it holds, where it is, and what converting it does. */
function TheFile({ file }: { file: FileDetails }) {
  const facts: [string, ReactNode][] = [
    ["Picture", picture(file)],
    ["Sound", lines(file.sound.map((track) => sound(track)))],
    ["Subtitles", lines(file.subtitles.map((track) => subtitles(track)))],
    ["Length", file.duration ? clockTime(file.duration) : null],
    ["Size", size(file.size)],
    ["Chapters", file.chapters > 0 ? String(file.chapters) : null],
    ["Found", day(file.foundAt)],
    ["Converting", converting(file)],
  ];
  return (
    <section aria-label="The file" className="flex flex-col gap-3">
      <h3 className="font-extrabold text-15">The file</h3>
      {file.problem && (
        <p className="rounded-14 border border-broken/40 bg-broken/8 px-3.5 py-2.5 text-13">
          It won't play: {file.problem}
        </p>
      )}
      <Facts facts={facts} />
      <p className="font-mono text-12 text-fg-soft [overflow-wrap:anywhere]">{file.path}</p>
    </section>
  );
}

function picture(file: FileDetails): string | null {
  const { picture } = file;
  if (!picture) return null;
  return [
    `${picture.width} × ${picture.height}`,
    `${codecName(picture.codec)} ${picture.bitDepth}-bit`,
    picture.frameRate ? `${Math.round(picture.frameRate * 100) / 100} fps` : null,
    file.converted ? "made by Kura" : null,
  ]
    .filter(Boolean)
    .join(" · ");
}

function sound(track: FileDetails["sound"][number]): string {
  const layout =
    track.channels === 1
      ? "mono"
      : track.channels === 2
        ? "stereo"
        : track.channels === 6
          ? "5.1"
          : track.channels === 8
            ? "7.1"
            : `${track.channels} channels`;
  return [
    track.language ? languageName(track.language) : "Language not labelled",
    `${track.codec.toUpperCase()} ${layout}`,
    track.lossless ? "lossless" : null,
  ]
    .filter(Boolean)
    .join(" · ");
}

function subtitles(track: FileDetails["subtitles"][number]): string {
  return [
    track.language ? languageName(track.language) : "Language not labelled",
    track.beside ? "beside it" : track.text ? "in it" : "in it, as pictures",
    track.forced ? "signs and songs" : null,
    track.made ? "made by Kura" : null,
  ]
    .filter(Boolean)
    .join(" · ");
}

function converting(file: FileDetails): string | null {
  const { state, reasons } = file.converting;
  if (state === "broken") return null;
  if (state === "ready") return "At your standard: nothing to do";
  return reasons[0] ?? "To convert";
}

/** Several lines in one fact, or nothing for none. */
function lines(items: string[]): ReactNode {
  if (items.length === 0) return null;
  return (
    <span className="flex flex-col">
      {items.map((item, index) => (
        // biome-ignore lint/suspicious/noArrayIndexKey: two tracks can read the same
        <span key={index}>{item}</span>
      ))}
    </span>
  );
}

function code(season: number, number: number, last: number | null): string {
  const pad = (value: number) => String(value).padStart(2, "0");
  return `S${pad(season)}E${pad(number)}${last ? `-E${pad(last)}` : ""}`;
}

function day(iso: string): string {
  return new Date(`${iso.slice(0, 10)}T12:00:00`).toLocaleDateString("en-GB", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}
