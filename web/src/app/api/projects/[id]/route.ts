import { NextResponse } from "next/server";
import fs from "node:fs";
import path from "node:path";
import yaml from "js-yaml";

const repoRoot = path.resolve(process.cwd(), "..");
const manifestDir = path.join(repoRoot, "outputs", "manifests");

export async function GET(
  _req: Request,
  { params }: { params: Promise<{ id: string }> },
) {
  const { id } = await params;
  const safeId = id.replace(/[^a-zA-Z0-9_-]/g, "");
  if (!safeId) return NextResponse.json({ error: "invalid id" }, { status: 400 });

  const manifestPath = path.join(manifestDir, `${safeId}.yml`);
  if (!fs.existsSync(manifestPath)) {
    return NextResponse.json({ error: "not found" }, { status: 404 });
  }
  const raw = fs.readFileSync(manifestPath, "utf8");
  const parsed = yaml.load(raw) as { project?: unknown };

  const logPath = path.join(repoRoot, "outputs", "logs", `${safeId}.log`);
  let tail = "";
  if (fs.existsSync(logPath)) {
    const buf = fs.readFileSync(logPath, "utf8");
    tail = buf.slice(-4000);
  }

  return NextResponse.json({
    project: parsed?.project ?? null,
    log_tail: tail,
  });
}
