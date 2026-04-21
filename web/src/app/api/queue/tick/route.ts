import { NextResponse } from "next/server";
import fs from "node:fs";
import path from "node:path";
import yaml from "js-yaml";
import { spawnPipeline } from "../../projects/route";

const repoRoot = path.resolve(process.cwd(), "..");
const manifestDir = path.join(repoRoot, "outputs", "manifests");

type Project = {
  id: string;
  source_url?: string;
  status?: string;
  targets?: string[];
  notes?: string[];
};

function parseEngine(notes: string[] = []): string {
  for (const n of notes) {
    const m = n.match(/engine=([a-z]+)/);
    if (m) return m[1];
  }
  return "vertex";
}

export async function POST() {
  if (!fs.existsSync(manifestDir)) {
    return NextResponse.json({ started: null });
  }

  const files = fs.readdirSync(manifestDir).filter((f) => f.endsWith(".yml") || f.endsWith(".yaml"));
  const entries: { file: string; project: Project; mtime: number }[] = [];
  for (const f of files) {
    try {
      const full = path.join(manifestDir, f);
      const raw = fs.readFileSync(full, "utf8");
      const parsed = yaml.load(raw) as { project?: Project };
      const proj = parsed?.project;
      if (proj && proj.id) {
        entries.push({ file: full, project: proj, mtime: fs.statSync(full).mtimeMs });
      }
    } catch {
      /* skip bad yaml */
    }
  }

  const running = entries.find((e) => e.project.status === "in_progress");
  if (running) {
    return NextResponse.json({ started: null, reason: "running", runningId: running.project.id });
  }

  const queued = entries
    .filter((e) => e.project.status === "queued")
    .sort((a, b) => a.mtime - b.mtime);

  if (queued.length === 0) {
    return NextResponse.json({ started: null, reason: "empty" });
  }

  const next = queued[0];
  const p = next.project;
  if (!p.source_url) {
    return NextResponse.json({ started: null, reason: "no url" });
  }

  spawnPipeline(
    p.id,
    p.source_url,
    parseEngine(p.notes),
    p.targets && p.targets.length > 0 ? p.targets : ["ko"],
    false,
  );

  return NextResponse.json({ started: p.id, queueSize: queued.length - 1 });
}
