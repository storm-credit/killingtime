import { NextRequest, NextResponse } from "next/server";
import { spawn } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import yaml from "js-yaml";

const repoRoot = path.resolve(process.cwd(), "..");
const scriptsDir = path.join(repoRoot, "scripts");
const manifestDir = path.join(repoRoot, "outputs", "manifests");

function hasRunningJob(): string | null {
  if (!fs.existsSync(manifestDir)) return null;
  const files = fs.readdirSync(manifestDir).filter((f) => f.endsWith(".yml") || f.endsWith(".yaml"));
  for (const f of files) {
    try {
      const raw = fs.readFileSync(path.join(manifestDir, f), "utf8");
      const parsed = yaml.load(raw) as { project?: { id?: string; status?: string } };
      if (parsed?.project?.status === "in_progress") return parsed.project.id || f;
    } catch {
      /* skip */
    }
  }
  return null;
}

function extractVideoId(url: string): string | null {
  const patterns = [
    /[?&]v=([a-zA-Z0-9_-]{11})/,
    /youtu\.be\/([a-zA-Z0-9_-]{11})/,
    /\/shorts\/([a-zA-Z0-9_-]{11})/,
    /\/embed\/([a-zA-Z0-9_-]{11})/,
  ];
  for (const p of patterns) {
    const m = url.match(p);
    if (m) return m[1];
  }
  return null;
}

async function fetchYoutubeTitle(url: string): Promise<string | null> {
  try {
    const oe = `https://www.youtube.com/oembed?url=${encodeURIComponent(url)}&format=json`;
    const res = await fetch(oe, { signal: AbortSignal.timeout(8000) });
    if (!res.ok) return null;
    const data = (await res.json()) as { title?: string };
    return (data.title || "").trim() || null;
  } catch {
    return null;
  }
}

async function writeStubManifest(videoId: string, url: string, engine: string, targets: string[]) {
  fs.mkdirSync(manifestDir, { recursive: true });
  const manifestPath = path.join(manifestDir, `${videoId}.yml`);
  const title = (await fetchYoutubeTitle(url)) ?? videoId;
  const project = {
    id: videoId,
    title,
    source_url: url,
    source_language: "auto",
    targets,
    current_stage: "intake",
    preferred_path: "track_subtitles",
    fallback_path: ["asr_whisper"],
    status: "queued",
    notes: [`queued via web ${new Date().toISOString()}`, `engine=${engine}`],
    artifacts: {},
  };
  fs.writeFileSync(manifestPath, yaml.dump({ project }, { lineWidth: -1 }), "utf8");
  return manifestPath;
}

export async function POST(req: NextRequest) {
  const body = await req.json().catch(() => ({}));
  const { url, engine = "vertex", targets = ["ko"], cleanHardsub = false } = body as {
    url?: string;
    engine?: string;
    targets?: string[];
    cleanHardsub?: boolean;
  };

  if (!url || typeof url !== "string") {
    return NextResponse.json({ error: "url required" }, { status: 400 });
  }

  const videoId = extractVideoId(url);
  if (!videoId) {
    return NextResponse.json({ error: "could not parse YouTube video id from url" }, { status: 400 });
  }

  await writeStubManifest(videoId, url, engine, targets);

  const blocker = hasRunningJob();
  if (blocker && blocker !== videoId) {
    // Another job is already running; leave this one queued. The orchestra
    // worker (or browser tick) will pick it up when the current one finishes.
    return NextResponse.json({
      videoId,
      queued: true,
      blockedBy: blocker,
      redirect: `/projects/${videoId}`,
    });
  }

  spawnPipeline(videoId, url, engine, targets, cleanHardsub);

  return NextResponse.json({
    videoId,
    queued: false,
    manifest: path.relative(repoRoot, path.join(manifestDir, `${videoId}.yml`)),
    redirect: `/projects/${videoId}`,
  });
}

export function spawnPipeline(
  videoId: string,
  url: string,
  engine: string,
  targets: string[],
  cleanHardsub: boolean,
): void {
  const args = [
    path.join(scriptsDir, "orchestra_run.py"),
    url,
    "--targets",
    ...targets,
    "--engine",
    engine,
  ];
  if (cleanHardsub) args.push("--clean-hardsub");

  const env = { ...process.env };
  if (!env.GOOGLE_APPLICATION_CREDENTIALS && engine === "vertex") {
    const candidate = "C:\\Users\\Storm Credit\\Desktop\\Music\\oddengine\\vertex-sa-key.json";
    if (fs.existsSync(candidate)) env.GOOGLE_APPLICATION_CREDENTIALS = candidate;
  }

  const logDir = path.join(repoRoot, "outputs", "logs");
  fs.mkdirSync(logDir, { recursive: true });
  const logFile = path.join(logDir, `${videoId}.log`);
  const out = fs.openSync(logFile, "a");

  const proc = spawn("python", args, {
    cwd: repoRoot,
    env,
    detached: true,
    stdio: ["ignore", out, out],
  });
  proc.unref();
}
