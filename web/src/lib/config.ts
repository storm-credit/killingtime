import fs from "node:fs";
import path from "node:path";
import yaml from "js-yaml";
import type {
  DashboardData,
  DynamicAgentFile,
  FixedAgentFile,
  HarnessConfig,
  HookFile,
  McpConfig,
  ProjectManifest,
  SkillFile,
} from "@/lib/types";

const repoRoot = path.resolve(process.cwd(), "..");

function readYaml<T>(fullPath: string): T {
  const file = fs.readFileSync(fullPath, "utf8");
  return yaml.load(file) as T;
}

export function loadDashboardData(): DashboardData {
  const harness = readYaml<HarnessConfig>(
    path.join(repoRoot, "configs", "pipeline", "killingtime_harness.yml")
  );
  const fixedAgentFile = readYaml<FixedAgentFile>(
    path.join(repoRoot, "configs", "agents", "fixed-agents.yml")
  );
  const dynamicAgentFile = readYaml<DynamicAgentFile>(
    path.join(repoRoot, "configs", "agents", "dynamic-agents.yml")
  );
  const fixedSkillFile = readYaml<SkillFile>(
    path.join(repoRoot, "configs", "skills", "fixed-skills.yml")
  );
  const dynamicSkillFile = readYaml<SkillFile>(
    path.join(repoRoot, "configs", "skills", "dynamic-skills.yml")
  );
  const fixedHookFile = readYaml<HookFile>(
    path.join(repoRoot, "configs", "hooks", "fixed-hooks.yml")
  );
  const dynamicHookFile = readYaml<HookFile>(
    path.join(repoRoot, "configs", "hooks", "dynamic-hooks.yml")
  );
  const mcp = readYaml<McpConfig>(
    path.join(repoRoot, "configs", "mcp", "context-broker.yml")
  );

  const manifestsDir = path.join(repoRoot, "outputs", "manifests");
  let manifestProject: ProjectManifest["project"] = {
    id: "no-project",
    title: "아직 등록된 프로젝트가 없습니다",
    source_url: "",
    source_language: "—",
    targets: ["ko"],
    current_stage: "intake",
    preferred_path: "track_subtitles",
    fallback_path: ["asr_whisper"],
    status: "empty",
    notes: ["/projects/new 에서 URL을 넣어 시작하세요"],
  };

  if (fs.existsSync(manifestsDir)) {
    const files = fs
      .readdirSync(manifestsDir)
      .filter((f) => f.endsWith(".yml") || f.endsWith(".yaml"))
      .sort((a, b) => {
        const at = fs.statSync(path.join(manifestsDir, a)).mtimeMs;
        const bt = fs.statSync(path.join(manifestsDir, b)).mtimeMs;
        return bt - at;
      });
    if (files.length > 0) {
      try {
        const m = readYaml<ProjectManifest>(path.join(manifestsDir, files[0]));
        if (m?.project) manifestProject = m.project;
      } catch {
        /* keep placeholder */
      }
    }
  }

  return {
    harness,
    fixedAgents: fixedAgentFile.fixed_agents,
    dynamicAgents: dynamicAgentFile.dynamic_agents,
    fixedSkills: fixedSkillFile.fixed_skills ?? [],
    dynamicSkills: dynamicSkillFile.dynamic_skills ?? [],
    fixedHooks: fixedHookFile.fixed_hooks ?? [],
    dynamicHooks: dynamicHookFile.dynamic_hooks ?? [],
    mcp,
    manifest: manifestProject,
  };
}
