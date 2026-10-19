// Turns the design canvases' boards (.dc.html) into plain HTML pages in docs/design/,
// so every screen opens in a browser without the canvas.
//
//   node scripts/design-snapshot.mjs --workflows <folder> --options <folder> --light <folder>
//                                    --player <folder> --english <folder> --anypc <folder>
//                                    --details <folder> --readme <page>
//
// Any of the seven canvases, each as Claude's Artifact tool saves it (a folder holding
// project/canvas.json), and the README options, a plain page (its HTML file, as a read of it
// saves it); only the pages of the ones given are written again. See docs/design/README.md.
import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import vm from "node:vm";

const CANVASES = {
  workflows: "https://claude.ai/artifact/XgGkfpW6doBUPcnrPqrbxb",
  options: "https://claude.ai/artifact/NWe6abnPRYCn6BGTVK25za",
  light: "https://claude.ai/artifact/7Bdz7CoKjBbV8JrSLXfu4y",
  player: "https://claude.ai/artifact/3MK2zSwv9fS1jzt2rP7Qw3",
  readme: "https://claude.ai/artifact/SJXeVqCrbCZPHk5Y17p7jk",
  english: "https://claude.ai/artifact/RmbcFdZiDMXYvz69cQ9CYA",
  anypc: "https://claude.ai/artifact/BRYamJpre3pLDT4ZZtPhaN",
  details: "https://claude.ai/artifact/6rp1m1fFNX5SmEKhDhgt7F",
};
const out = join(dirname(fileURLToPath(import.meta.url)), "..", "docs", "design");
const today = new Date().toISOString().slice(0, 10);

const folders = foldersIn(process.argv.slice(2));
if (!folders) {
  console.error(
    "Usage: node scripts/design-snapshot.mjs --workflows <folder> --options <folder> --light <folder> --player <folder> --english <folder> --anypc <folder> --details <folder> --readme <page>",
  );
  process.exit(1);
}
let written = 0;

// The workflows canvas: Main becomes index.html, every other board a page in screens/.
if (folders.workflows) {
  const workflows = readCanvas(folders.workflows);
  mkdirSync(join(out, "screens"), { recursive: true });
  for (const file of workflows.order) {
    const name = file.replace(".dc.html", "");
    const isIndex = name === "Main";
    const page = toPage(workflows, file, {
      canvas: CANVASES.workflows,
      link: (target) => (isIndex ? `screens/${target}.html` : `${target}.html`),
    });
    writeFileSync(join(out, isIndex ? "index.html" : `screens/${name}.html`), page);
    written += 1;
  }
}

// The options record: its Main board becomes options.html. It links to boards that
// were folded into the workflows canvas, so those links go to the overview.
if (folders.options) {
  const options = readCanvas(folders.options);
  writeFileSync(
    join(out, "options.html"),
    toPage(options, "Main.dc.html", { canvas: CANVASES.options, link: () => "index.html" }),
  );
  written += 1;
}

// Light mode: Paper, the owner's pick, becomes light.html (Home and the queue in it), the same
// two screens in Cinema's dark dark.html, and the three options side by side light-options.html.
if (folders.light) {
  const light = readCanvas(folders.light);
  const page = (file) => toPage(light, file, { canvas: CANVASES.light, link: () => "light.html" });
  writeFileSync(join(out, "light.html"), page("B-Paper.dc.html"));
  writeFileSync(join(out, "dark.html"), page("Cinema-Dark.dc.html"));
  writeFileSync(join(out, "light-options.html"), page("Main.dc.html"));
  written += 3;
}

// The player: the small one over a title's page, full screen with its menu open, in light, on
// "Which anime is this?", and its small things. A board's drag code doesn't come along: the
// snapshot's small player sits where it starts.
if (folders.player) {
  const player = readCanvas(folders.player);
  const pages = {
    "Main.dc.html": "player.html",
    "Full-screen.dc.html": "player-full.html",
    "Light.dc.html": "player-light.html",
    "Quick-check.dc.html": "player-check.html",
    "Small-things.dc.html": "player-states.html",
  };
  for (const [file, name] of Object.entries(pages)) {
    writeFileSync(
      join(out, name),
      toPage(player, file, { canvas: CANVASES.player, link: () => "player.html" }),
    );
    written += 1;
  }
}

// English for every episode: a title's languages and English made for it, the Make dialog, the
// queue and the player with them, English from another copy, Home by language, and the small
// things, each a page that links to the others.
if (folders.english) {
  const english = readCanvas(folders.english);
  const pages = {
    "Main.dc.html": "english.html",
    "Make.dc.html": "english-make.html",
    "Queue.dc.html": "english-queue.html",
    "Player.dc.html": "english-player.html",
    "Copy-sound.dc.html": "english-copy.html",
    "Home.dc.html": "english-home.html",
    "Small-things.dc.html": "english-states.html",
  };
  for (const [file, name] of Object.entries(pages)) {
    writeFileSync(
      join(out, name),
      toPage(english, file, {
        canvas: CANVASES.english,
        link: (target) => pages[`${target}.dc.html`] ?? "english.html",
      }),
    );
    written += 1;
  }
}

// Kura on any PC: what this PC can do, in Setup (on the owner's PC and on a laptop with Intel
// graphics) and in Settings › About, Convert's times measured on this PC, English subtitles on a
// smaller card, the small things, and what a PC needs, each a page that links to the others.
if (folders.anypc) {
  const anypc = readCanvas(folders.anypc);
  const pages = {
    "Main.dc.html": "anypc.html",
    "Laptop.dc.html": "anypc-laptop.html",
    "About.dc.html": "anypc-about.html",
    "Convert.dc.html": "anypc-convert.html",
    "Subtitles.dc.html": "anypc-subtitles.html",
    "Small-things.dc.html": "anypc-states.html",
    "Requirements.dc.html": "anypc-requirements.html",
  };
  for (const [file, name] of Object.entries(pages)) {
    writeFileSync(
      join(out, name),
      toPage(anypc, file, {
        canvas: CANVASES.anypc,
        link: (target) => pages[`${target}.dc.html`] ?? "anypc.html",
      }),
    );
    written += 1;
  }
}

// A video's or an episode's details: the side sheet as it was, and the three ways drawn instead
// of it, a peek beside what was clicked, a card with its picture (chosen) and the page opening up
// in place, each a page; the card's are details.html and details-video.html.
if (folders.details) {
  const details = readCanvas(folders.details);
  const pages = {
    "Main.dc.html": "details-before.html",
    "Today-Video.dc.html": "details-before-video.html",
    "A1-Peek-Episode.dc.html": "details-peek.html",
    "A2-Peek-Video.dc.html": "details-peek-video.html",
    "B1-Card-Episode.dc.html": "details.html",
    "B2-Card-Video.dc.html": "details-video.html",
    "C1-InPlace-Episode.dc.html": "details-in-place.html",
    "C2-InPlace-Video.dc.html": "details-in-place-video.html",
    "C3-InPlace-Map.dc.html": "details-in-place-map.html",
  };
  for (const [file, name] of Object.entries(pages)) {
    writeFileSync(
      join(out, name),
      toPage(details, file, { canvas: CANVASES.details, link: () => "details.html" }),
    );
    written += 1;
  }
}

// The README options: three drafts of the repo's README, the tour chosen. Not a canvas but a
// page, kept as it is; its pictures are the README's own, in docs/readme/.
if (folders.readme) {
  const page = readFileSync(folders.readme, "utf8").replace(
    /(["(])img\/([\w-]+\.png)/g,
    "$1../readme/$2",
  );
  writeFileSync(join(out, "readme.html"), toPlainPage(page, CANVASES.readme));
  written += 1;
}

console.log(`Wrote ${written} pages to ${out}`);

/** The canvases' folders by name (`--light <folder>`), or nothing when the arguments don't read. */
function foldersIn(args) {
  const found = {};
  for (let index = 0; index < args.length; index += 2) {
    const name = args[index].replace(/^--/, "");
    if (!(name in CANVASES) || !args[index + 1]) return null;
    found[name] = args[index + 1];
  }
  return Object.keys(found).length > 0 ? found : null;
}

function readCanvas(folder) {
  const index = JSON.parse(readFileSync(join(folder, "project", "canvas.json"), "utf8"));
  const source = (file) => readFileSync(join(folder, "project", file), "utf8");
  return { ...index, source };
}

function toPage(canvas, file, { canvas: url, link }) {
  const source = canvas.source(file);
  const title = canvas.boards[file]?.title ?? file;
  const helmet = source.match(/<helmet>([\s\S]*?)<\/helmet>/)?.[1] ?? "";
  // A board's own handlers (a drag, a ref) are the canvas's to run, not the page's.
  const board = source
    .match(/<x-dc>([\s\S]*?)<\/x-dc>/)[1]
    .replace(/<helmet>[\s\S]*?<\/helmet>/, "")
    .replace(/\s(?:ref|on[A-Z]\w*)="\{\{[^}]+\}\}"/g, "");
  const body = expand(board, renderValues(source)).replace(
    /href="([\w.-]+)\.dc\.html"/g,
    (_, target) => `href="${link(target)}"`,
  );
  return `<!doctype html>
<!-- Kura design snapshot of "${title}" (${url}), taken ${today}.
     Change the canvas, then re-run scripts/design-snapshot.mjs; don't edit this file. -->
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>${title} · Kura design</title>
${helmet.trim()}
</head>
<body>
${body.trim()}
</body>
</html>
`;
}

/** A plain page as a snapshot: its head and body, whether it came whole or as a fragment (what
 * goes in the head first, then the page). */
function toPlainPage(html, url) {
  const whole = {
    head: html.match(/<head[^>]*>([\s\S]*?)<\/head>/i)?.[1],
    body: html.match(/<body[^>]*>([\s\S]*)<\/body>/i)?.[1],
  };
  const lead =
    html.match(/^(?:\s*(?:<title>[\s\S]*?<\/title>|<link\b[^>]*>|<meta\b[^>]*>|<style>[\s\S]*?<\/style>))*/)?.[0] ??
    "";
  const head = (whole.head ?? lead).replace(/<meta\s+(?:charset|name="viewport")[^>]*>\s*/gi, "");
  const body = whole.body ?? html.slice(lead.length);
  const title = head.match(/<title>([\s\S]*?)<\/title>/)?.[1] ?? "Kura";
  return `<!doctype html>
<!-- Kura design snapshot of "${title}" (${url}), taken ${today}.
     Change the artifact, then re-run scripts/design-snapshot.mjs; don't edit this file. -->
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
${head.trim()}
</head>
<body>
${body.trim()}
</body>
</html>
`;
}

// A board's script builds the data its template repeats over. It only computes
// values, so it runs in an empty sandbox with nothing but the base class it needs.
function renderValues(source) {
  const script = source.match(/<script type="text\/x-dc"[^>]*>([\s\S]*?)<\/script>/)?.[1];
  if (!script) return {};
  const sandbox = vm.createContext({
    DCLogic: class {
      props = {};
    },
  });
  return vm.runInContext(`${script}\n;new Component().renderVals()`, sandbox, { timeout: 1000 });
}

// Expands <sc-for>, <sc-if> and {{holes}} the way the canvas renders them.
function expand(html, scope) {
  let result = "";
  let rest = html;
  for (;;) {
    const open = rest.match(/<sc-(for|if)\b([^>]*)>/);
    if (!open) return result + fillHoles(rest, scope);
    const [tag, kind, attributes] = open;
    const close = findClose(rest, kind, open.index + tag.length);
    const inner = rest.slice(open.index + tag.length, close);
    const binding = (name) =>
      attributes.match(new RegExp(`${name}="\\{\\{([^}]+)\\}\\}"`))?.[1].trim();

    result += fillHoles(rest.slice(0, open.index), scope);
    if (kind === "for") {
      const as = attributes.match(/as="([^"]+)"/)[1];
      for (const item of lookup(scope, binding("list")) ?? []) {
        result += expand(inner, { ...scope, [as]: item });
      }
    } else if (lookup(scope, binding("value"))) {
      result += expand(inner, scope);
    }
    rest = rest.slice(close + `</sc-${kind}>`.length);
  }
}

function findClose(html, kind, from) {
  const tags = new RegExp(`<sc-${kind}\\b|</sc-${kind}>`, "g");
  tags.lastIndex = from;
  let depth = 1;
  for (let tag = tags.exec(html); tag; tag = tags.exec(html)) {
    depth += tag[0].startsWith("</") ? -1 : 1;
    if (depth === 0) return tag.index;
  }
  throw new Error(`<sc-${kind}> is never closed`);
}

function fillHoles(html, scope) {
  return html.replace(/\{\{([^}]+)\}\}/g, (_, path) => escapeHtml(lookup(scope, path.trim()) ?? ""));
}

function lookup(scope, path) {
  return path.split(".").reduce((value, key) => value?.[key], scope);
}

function escapeHtml(value) {
  const entities = { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" };
  return String(value).replace(/[&<>"]/g, (character) => entities[character]);
}
