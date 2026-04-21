import { NextResponse } from "next/server";
import { spawn } from "node:child_process";
import fs from "node:fs";
import path from "node:path";

const repoRoot = path.resolve(process.cwd(), "..");

function thumbsDir(id: string): string {
  return path.join(repoRoot, "outputs", "jobs", id, "thumbnails");
}

function findVideo(id: string): string | null {
  const candidates = [
    path.join(repoRoot, "outputs", "packages", id, `${id}.ko-added.mp4`),
    path.join(repoRoot, "outputs", "packages", id, `${id}.ko-only.hardsub.mp4`),
    path.join(repoRoot, "outputs", "downloads", `${id}.hq.mp4`),
    path.join(repoRoot, "outputs", "downloads", `${id}.mp4`),
  ];
  for (const c of candidates) if (fs.existsSync(c)) return c;
  return null;
}

export async function GET(
  _req: Request,
  { params }: { params: Promise<{ id: string }> },
) {
  const { id } = await params;
  const safeId = id.replace(/[^a-zA-Z0-9_-]/g, "");
  const dir = thumbsDir(safeId);
  const manifestPath = path.join(dir, "manifest.json");
  if (!fs.existsSync(manifestPath)) {
    return NextResponse.json({ selected: null, candidates: [] });
  }
  try {
    const raw = fs.readFileSync(manifestPath, "utf8");
    const data = JSON.parse(raw);
    return NextResponse.json(data);
  } catch {
    return NextResponse.json({ selected: null, candidates: [] });
  }
}

export async function POST(
  _req: Request,
  { params }: { params: Promise<{ id: string }> },
) {
  const { id } = await params;
  const safeId = id.replace(/[^a-zA-Z0-9_-]/g, "");
  const video = findVideo(safeId);
  if (!video) {
    return NextResponse.json({ error: "video not found for this job" }, { status: 404 });
  }
  const scriptsDir = path.join(repoRoot, "scripts");
  const logPath = path.join(repoRoot, "outputs", "logs", `${safeId}.thumbs.log`);
  fs.mkdirSync(path.dirname(logPath), { recursive: true });
  const out = fs.openSync(logPath, "a");

  const proc = spawn(
    "python",
    [path.join(scriptsDir, "generate_thumbnails.py"), "--video", video, "--video-id", safeId, "--count", "3"],
    {
      cwd: repoRoot,
      detached: true,
      stdio: ["ignore", out, out],
    },
  );
  proc.unref();

  return NextResponse.json({ started: true, video, log: path.relative(repoRoot, logPath) });
}
