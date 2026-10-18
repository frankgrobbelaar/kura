import { Link } from "react-router";
import { Poster } from "@/components/poster";
import { StatusShape } from "@/components/status";
import type { FranchiseSummary, TitleKind, TitleSummary } from "@/lib/engine";
import { files, kindCount, kindWord } from "@/lib/kinds";
import { share } from "@/lib/share";

/** How much of something is there: a title, or a franchise's titles together. */
type Amount = Pick<TitleSummary, "aired" | "present" | "missing" | "airing">;

/** One card on the shelf: a title on its own, or a franchise of several as one card. */
export function ShelfCard({ franchise }: { franchise: FranchiseSummary }) {
  const [only, ...others] = franchise.titles;
  if (only && others.length === 0) return <TitleCard title={only} />;
  return <FranchiseCard franchise={franchise} />;
}

/** A title as a poster card: what it is, when it came out, and how much of it is there. */
export function TitleCard({ title }: { title: TitleSummary }) {
  return (
    <Card to={`/titles/${title.id}`} poster={title} name={title.name} amount={title}>
      {titleFacts(title)}
    </Card>
  );
}

/** A franchise as one card, under its lead's poster: its series, films, OVAs and specials. */
export function FranchiseCard({ franchise }: { franchise: FranchiseSummary }) {
  const lead = franchise.titles.find((title) => title.id === franchise.id) ?? franchise.titles[0];
  if (!lead) return null;
  return (
    <Card
      to={`/franchises/${franchise.id}`}
      poster={{ ...lead, hasPoster: franchise.hasPoster }}
      name={franchise.name}
      amount={franchise}
    >
      {franchiseFacts(franchise)}
    </Card>
  );
}

function Card(props: {
  to: string;
  poster: TitleSummary;
  name: string;
  amount: Amount;
  children: string;
}) {
  const { amount } = props;
  const tag = tagOf(amount);
  const done = amount.aired > 0 ? share(amount.present, amount.aired) : null;
  return (
    <Link to={props.to} className="lift flex flex-col gap-2.5 rounded-16 focus-visible:outline-2">
      <div className="relative">
        <Poster title={props.poster} />
        {tag && (
          <span className="absolute top-2.5 left-2.5 inline-flex h-6 items-center gap-1.5 rounded-full bg-tag px-2.25 font-bold text-11">
            {tag.state && <StatusShape state={tag.state} className="size-2" />}
            {tag.text}
          </span>
        )}
        {done !== null && (
          <span
            aria-hidden="true"
            className="absolute inset-x-0 bottom-0 h-1 overflow-hidden rounded-b-14 bg-black/35"
          >
            <span className="block h-full bg-white/90" style={{ width: `${done}%` }} />
          </span>
        )}
      </div>
      <span className="flex flex-col gap-px px-0.5">
        <span title={props.name} className="line-clamp-2 font-extrabold text-14 leading-snug">
          {props.name}
        </span>
        <span className="truncate text-12 text-fg-muted">{props.children}</span>
        {done !== null && (
          <span className="text-12 text-fg-faint">
            {amount.present} of {amount.aired} · {amount.missing === 0 ? "complete" : `${done}%`}
          </span>
        )}
      </span>
    </Link>
  );
}

/** The card's tag: what most needs saying, by its status shape. */
function tagOf(amount: Amount): { text: string; state: "missing" | "ready" | null } | null {
  if (amount.missing > 0) return { text: `${amount.missing} missing`, state: "missing" };
  if (amount.airing) return { text: "Airing", state: null };
  if (amount.aired > 0) return { text: "Complete", state: "ready" };
  return null;
}

/** "TV series · 1989 · 291 episodes", "Movie · 2001", "OVA · 1992 · 2 files". */
function titleFacts(title: TitleSummary): string {
  const parts = [kindWord(title.kind)];
  if (title.year) parts.push(String(title.year));
  if (title.kind !== "movie") {
    parts.push(title.aired > 0 ? `${title.aired} episodes` : files(title.files));
  }
  return parts.join(" · ");
}

/** "Franchise · 6 series · 21 movies", or with one series, "TV series · 26 episodes · 1 movie". */
/** What a shelf card shows a franchise as: a title on its own, a series with its films and
 * specials, or a franchise (several series, or films alone). */
export function shelfKind(franchise: FranchiseSummary): TitleKind | "franchise" {
  const [only, ...more] = franchise.titles;
  if (only && more.length === 0) return only.kind;
  const series = franchise.titles.filter((title) => title.kind === "series");
  return series.length === 1 ? "series" : "franchise";
}

function franchiseFacts(franchise: FranchiseSummary): string {
  const series = franchise.titles.filter((title) => title.kind === "series");
  const [one] = series;
  const others = (["movie", "ova", "special"] as const)
    .filter((kind) => franchise.kinds[kind] > 0)
    .map((kind) => kindCount(kind, franchise.kinds[kind]));
  if (one && series.length === 1) {
    return [kindWord("series"), `${one.aired} episodes`, ...others].join(" · ");
  }
  const all = series.length > 0 ? [kindCount("series", series.length), ...others] : others;
  return ["Franchise", ...all].join(" · ");
}
