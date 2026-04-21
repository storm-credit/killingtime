import { NextRequest, NextResponse } from "next/server";
import { spawn } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import yaml from "js-yaml";

const repoRoot = path.resolve(process.cwd(), "..");
const scriptsDir = path.join(repoRoot, "scripts");
const manifestDir = path.join(repoRoot, "outputs", "manifests");

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

function writeStubManifest(videoId: string, url: string, engine: string, targets: string[]) {
  fs.mkdirSync(manifestDir, { recursive: true });
  const manifestPath = path.join(manifestDir, `${videoId}.yml`);
  const project = {
    id: videoId,
    title: videoId,
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

  writeStubManifest(videoId, url, engine, targets);

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

  return NextResponse.json({
    videoId,
    manifest: path.relative(repoRoot, path.join(manifestDir, `${videoId}.yml`)),
    log: path.relative(repoRoot, logFile),
    redirect: `/projects/${videoId}`,
  });
}
