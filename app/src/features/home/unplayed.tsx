import { Play } from "lucide-react";
import { FileMenuItems, FileNote, useFileActions } from "@/components/file-actions";
import { Button } from "@/components/ui/button";
import { MenuItem, MenuSeparator, RowMenu } from "@/components/ui/menu";
import { Sheet, SheetContent } from "@/components/ui/sheet";
import { type PlayItem, usePlayer } from "@/features/player/player-context";
import { type UnplayedVideo, useCheckOne, useCheckup, useCheckupAction } from "@/lib/engine";
import { split } from "@/lib/format";

/** The videos the overnight health check couldn't play, beside Home: each to play and see, try
 * again, say it plays after all, or mark broken. Nothing changes till the owner says. */
export function UnplayedSheet({ open, onClose }: { open: boolean; onClose: () => void }) {
  const checkup = useCheckup();
  const found = checkup.data?.unplayed ?? [];
  const { play } = usePlayer();
  return (
    <Sheet open={open} onOpenChange={(now) => !now && onClose()}>
      {open && (
        <SheetContent
          title="Videos that didn't play"
          description="The overnight health check stopped in them. Play one to see for yourself: it's only broken once you say so."
        >
          {found.length === 0 ? (
            <p className="text-13 text-fg-muted">Every video the check played, played.</p>
          ) : (
            <ul className="-mt-2 flex flex-col">
              {found.map((video) => (
                <Row
                  key={video.fileId}
                  video={video}
                  onPlay={() => {
                    onClose();
                    play([playItem(video)]);
                  }}
                />
              ))}
            </ul>
          )}
        </SheetContent>
      )}
    </Sheet>
  );
}

function Row({ video, onPlay }: { video: UnplayedVideo; onPlay: () => void }) {
  const action = useCheckupAction();
  const again = useCheckOne();
  const files = useFileActions();
  const label = labelOf(video);
  const tried = again.data;
  return (
    <li className="flex flex-col gap-2 border-rule border-b py-3.5 last:border-b-0">
      <span className="flex items-start gap-2">
        <span className="flex min-w-0 flex-1 flex-col gap-0.5">
          <span className="font-extrabold text-14">{label}</span>
          <span className="text-13 text-fg-soft">{video.problem}</span>
          <span className="font-mono text-11 text-fg-muted [overflow-wrap:anywhere]">
            {video.path}
          </span>
        </span>
        <RowMenu label={`More for ${label}`}>
          <MenuItem onSelect={() => action.mutate({ path: `/files/${video.fileId}/plays` })}>
            It plays fine
          </MenuItem>
          <FileMenuItems path={video.path} actions={files} />
          <MenuSeparator />
          <MenuItem
            danger
            onSelect={() => action.mutate({ path: `/files/${video.fileId}/broken` })}
          >
            Mark as broken
          </MenuItem>
        </RowMenu>
      </span>
      <span className="flex flex-wrap items-center gap-2">
        <Button size="sm" onClick={onPlay}>
          <Play size={13} fill="currentColor" aria-hidden="true" />
          Play
        </Button>
        <Button
          size="sm"
          variant="ghost"
          disabled={again.isPending}
          onClick={() => again.mutate({ path: `/files/${video.fileId}/check` })}
        >
          {again.isPending ? "Trying…" : "Try again"}
        </Button>
        {tried && (
          <span role="status" className="text-12 text-fg-muted">
            {tried.problem ? "It stopped again." : "It played this time."}
          </span>
        )}
      </span>
      {(action.error ?? again.error) && (
        <p role="alert" className="text-12 text-broken-fg">
          {(action.error ?? again.error)?.message}
        </p>
      )}
      <FileNote actions={files} />
    </li>
  );
}

/** "Starfall Academy · S01E05", or the file's name. */
function labelOf(video: UnplayedVideo): string {
  if (video.title && video.season !== null && video.episode !== null) {
    const pad = (value: number) => String(value).padStart(2, "0");
    const last = video.episodeEnd ? `-E${pad(video.episodeEnd)}` : "";
    return `${video.title} · S${pad(video.season)}E${pad(video.episode)}${last}`;
  }
  return video.title ?? split(video.path)[0];
}

function playItem(video: UnplayedVideo): PlayItem {
  const label = labelOf(video);
  return {
    fileId: video.fileId,
    label,
    name: label === split(video.path)[0] ? split(video.path)[1] : null,
    path: video.path,
    fileName: label === split(video.path)[0],
  };
}
