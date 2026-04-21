export type HarnessConfig = {
  name: string;
  domain: string;
  principle: string;
  mode: string;
  hooks: string[];
  stage_order: string[];
  stages: Array<{
    id: string;
    owner: string;
    output: string;
    success_definition: string;
  }>;
};

export type FixedAgentFile = {
  fixed_agents: Array<{
    id: string;
    label: string;
    tier: string;
    model: string;
    ownership: string[];
    stages: string[];
    tools: string[];
    extension_policy: string;
  }>;
};

export type DynamicAgentFile = {
  dynamic_agents: Array<{
    id: string;
    label: string;
    status: string;
    activation_rule: string;
    ownership: string[];
  }>;
};

export type SkillFile = {
  fixed_skills?: Array<{
    id: string;
    owner: string;
    purpose: string;
  }>;
  dynamic_skills?: Array<{
    id: string;
    status: string;
    activation_rule: string;
  }>;
};

export type HookFile = {
  fixed_hooks?: Array<{
    id: string;
    owner: string;
    check: string[];
  }>;
  dynamic_hooks?: Array<{
    id: string;
    status: string;
    activation_rule: string;
  }>;
};

export type McpConfig = {
  state: string;
  owner: string;
  purpose: string[];
  knowledge_sources: Array<{
    id: string;
    path: string;
    type: string;
    priority: string;
  }>;
  planned_connectors: string[];
};

export type ProjectManifest = {
  project: {
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
  };
};

export type DashboardData = {
  harness: HarnessConfig;
  fixedAgents: FixedAgentFile["fixed_agents"];
  dynamicAgents: DynamicAgentFile["dynamic_agents"];
  fixedSkills: NonNullable<SkillFile["fixed_skills"]>;
  dynamicSkills: NonNullable<SkillFile["dynamic_skills"]>;
  fixedHooks: NonNullable<HookFile["fixed_hooks"]>;
  dynamicHooks: NonNullable<HookFile["dynamic_hooks"]>;
  mcp: McpConfig;
  manifest: ProjectManifest["project"];
};

