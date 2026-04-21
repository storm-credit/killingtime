type FixedAgent = {
  id: string;
  label: string;
  tier: string;
  model: string;
  ownership: string[];
  stages: string[];
  tools: string[];
};

type DynamicAgent = {
  id: string;
  label: string;
  status: string;
  activation_rule: string;
  ownership: string[];
};

export function AgentRoster({
  fixedAgents,
  dynamicAgents,
}: {
  fixedAgents: FixedAgent[];
  dynamicAgents: DynamicAgent[];
}) {
  return (
    <div className="roster-grid">
      {fixedAgents.map((agent) => (
        <article key={agent.id} className="card agent-card">
          <div className="eyebrow">{agent.tier}</div>
          <h3>{agent.label}</h3>
          <p className="muted">{agent.model}</p>
          <p>{agent.ownership.join(" / ")}</p>
          <div className="chip-row">
            {agent.stages.map((stage) => (
              <span key={stage} className="chip">
                {stage}
              </span>
            ))}
          </div>
        </article>
      ))}
      {dynamicAgents.map((agent) => (
        <article key={agent.id} className="card agent-card agent-card--dynamic">
          <div className="eyebrow">dynamic</div>
          <h3>{agent.label}</h3>
          <p className="muted">{agent.status}</p>
          <p>{agent.activation_rule}</p>
          <div className="chip-row">
            {agent.ownership.map((item) => (
              <span key={item} className="chip">
                {item}
              </span>
            ))}
          </div>
        </article>
      ))}
    </div>
  );
}
