import fs from "node:fs";
import path from "node:path";
import yaml from "js-yaml";

const repoRoot = path.resolve(process.cwd(), "..");
const manifestDir = path.join(repoRoot, "outputs", "manifests");

function resolveVideo(id: string): string | null {
  const safeId = id.replace(/[^a-zA-Z0-9_.-]/g, "");
  const candidates = [
    path.join(repoRoot, "outputs", "packages", safeId, `${safeId}.ko-added.mp4`),
    path.join(repoRoot, "outputs", "packages", safeId, `${safeId}.ko-only.hardsub.mp4`),
    path.join(repoRoot, "outputs", "packages", safeId, `${safeId}.mp4`),
  ];
  for (const c of candidates) if (fs.existsSync(c)) return c;
  // Last resort: check manifest
  const manifestPath = path.join(manifestDir, `${safeId}.yml`);
  if (fs.existsSync(manifestPath)) {
    try {
      const raw = fs.readFileSync(manifestPath, "utf8");
      const parsed = yaml.load(raw) as { project?: { artifacts?: Record<string, string> } };
      const rel = parsed?.project?.artifacts?.final_mp4;
      if (rel) {
        const full = path.join(repoRoot, rel.replace(/\\/g, "/"));
        if (fs.existsSync(full)) return full;
      }
    } catch {
      /* fall through */
    }
  }
  return null;
}

function parseRange(range: string, size: number): [number, number] | null {
  const m = /^bytes=(\d*)-(\d*)$/.exec(range);
  if (!m) return null;
  const startStr = m[1];
  const endStr = m[2];
  let start: number;
  let end: number;
  if (startStr === "" && endStr === "") return null;
  if (startStr === "") {
    // suffix: last N bytes
    const suffix = parseInt(endStr, 10);
    start = Math.max(0, size - suffix);
    end = size - 1;
  } else {
    start = parseInt(startStr, 10);
    end = endStr === "" ? size - 1 : parseInt(endStr, 10);
  }
  if (!Number.isFinite(start) || !Number.isFinite(end) || start > end || end >= size) return null;
  return [start, end];
}

export async function GET(
  req: Request,
  { params }: { params: Promise<{ id: string }> },
) {
  const { id } = await params;
  const full = resolveVideo(id);
  if (!full) {
    return new Response("not found", { status: 404 });
  }

  const path0: string = full;
  const stat = fs.statSync(path0);
  const size = stat.size;
  const range = req.headers.get("range");
  const contentType = path0.endsWith(".mp4") ? "video/mp4" : "application/octet-stream";

  // Build a ReadableStream for a byte range (or the whole file).
  function streamRange(start: number, end: number) {
    const rs = fs.createReadStream(path0, { start, end });
    return new ReadableStream<Uint8Array>({
      start(controller) {
        rs.on("data", (chunk: Buffer | string) => {
          const buf = typeof chunk === "string" ? Buffer.from(chunk) : chunk;
          controller.enqueue(new Uint8Array(buf.buffer, buf.byteOffset, buf.byteLength));
        });
        rs.on("end", () => controller.close());
        rs.on("error", (err) => controller.error(err));
      },
      cancel() {
        rs.destroy();
      },
    });
  }

  if (range) {
    const parsed = parseRange(range, size);
    if (!parsed) {
      return new Response("invalid range", {
        status: 416,
        headers: { "Content-Range": `bytes */${size}` },
      });
    }
    const [start, end] = parsed;
    const stream = streamRange(start, end);
    return new Response(stream, {
      status: 206,
      headers: {
        "Content-Type": contentType,
        "Content-Length": String(end - start + 1),
        "Content-Range": `bytes ${start}-${end}/${size}`,
        "Accept-Ranges": "bytes",
        "Cache-Control": "no-cache",
      },
    });
  }

  const stream = streamRange(0, size - 1);
  return new Response(stream, {
    status: 200,
    headers: {
      "Content-Type": contentType,
      "Content-Length": String(size),
      "Accept-Ranges": "bytes",
      "Cache-Control": "no-cache",
    },
  });
}
