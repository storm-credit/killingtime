import { NextResponse } from "next/server";
import fs from "node:fs";
import path from "node:path";

const repoRoot = path.resolve(process.cwd(), "..");

export async function POST(
  _req: Request,
  { params }: { params: Promise<{ id: string; n: string }> },
) {
  const { id, n } = await params;
  const safeId = id.replace(/[^a-zA-Z0-9_-]/g, "");
  const idx = Number.parseInt(n, 10);
  if (!Number.isFinite(idx) || idx < 0 || idx > 9) {
    return NextResponse.json({ error: "invalid index" }, { status: 400 });
  }
  const manifestPath = path.join(repoRoot, "outputs", "jobs", safeId, "thumbnails", "manifest.json");
  if (!fs.existsSync(manifestPath)) {
    return NextResponse.json({ error: "manifest not found" }, { status: 404 });
  }
  try {
    const raw = fs.readFileSync(manifestPath, "utf8");
    const data = JSON.parse(raw) as { candidates?: unknown[]; selected?: number | null };
    if (!data.candidates || !Array.isArray(data.candidates) || idx >= data.candidates.length) {
      return NextResponse.json({ error: "index out of range" }, { status: 400 });
    }
    data.selected = idx;
    fs.writeFileSync(manifestPath, JSON.stringify(data, null, 2), "utf8");
    return NextResponse.json({ selected: idx });
  } catch (e) {
    return NextResponse.json({ error: (e as Error).message }, { status: 500 });
  }
}
