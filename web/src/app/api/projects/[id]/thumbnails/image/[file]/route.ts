import fs from "node:fs";
import path from "node:path";

const repoRoot = path.resolve(process.cwd(), "..");

export async function GET(
  _req: Request,
  { params }: { params: Promise<{ id: string; file: string }> },
) {
  const { id, file } = await params;
  const safeId = id.replace(/[^a-zA-Z0-9_-]/g, "");
  const safeFile = file.replace(/[^a-zA-Z0-9._-]/g, "");
  const fullPath = path.join(repoRoot, "outputs", "jobs", safeId, "thumbnails", safeFile);
  if (!fs.existsSync(fullPath)) {
    return new Response("not found", { status: 404 });
  }
  const buf = fs.readFileSync(fullPath);
  const contentType = safeFile.endsWith(".jpg") || safeFile.endsWith(".jpeg")
    ? "image/jpeg"
    : safeFile.endsWith(".png")
    ? "image/png"
    : "application/octet-stream";
  const arrayBuffer = buf.buffer.slice(buf.byteOffset, buf.byteOffset + buf.byteLength) as ArrayBuffer;
  return new Response(arrayBuffer, {
    headers: {
      "Content-Type": contentType,
      "Cache-Control": "no-cache, no-store, must-revalidate",
    },
  });
}
