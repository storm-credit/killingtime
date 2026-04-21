import fs from "node:fs";
import path from "node:path";
import yaml from "js-yaml";

export type Project = {
  id: string;
  title: string;
  source_url: string;
  source_language: string;
  targets: string[];
  current_stage: string;
  preferred_path: string;
  fallback_path: string[];
  status: string;
  notes: string[];
  artifacts?: Record<string, string | null | undefined>;
};

const repoRoot = path.resolve(process.cwd(), "..");
const manifestDir = path.join(repoRoot, "outputs", "manifests");

function readManifest(file: string): Project | null {
  try {
    const raw = fs.readFileSync(path.join(manifestDir, file), "utf8");
    const parsed = yaml.load(raw) as { project?: Project };
    return parsed?.project ?? null;
  } catch {
    return null;
  }
}

export function listProjects(): Project[] {
  if (!fs.existsSync(manifestDir)) return [];
  const files = fs.readdirSync(manifestDir).filter((f) => f.endsWith(".yml") || f.endsWith(".yaml"));
  return files
    .map((f) => readManifest(f))
    .filter((p): p is Project => Boolean(p))
    .sort((a, b) => a.id.localeCompare(b.id));
}

export function getProject(id: string): Project | null {
  const candidates = [`${id}.yml`, `${id}.yaml`];
  for (const f of candidates) {
    const p = readManifest(f);
    if (p) return p;
  }
  return null;
}
