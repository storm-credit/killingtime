import { InfoCard } from "@/components/InfoCard";
import { loadDashboardData } from "@/lib/config";

export default function RegistryPage() {
  const data = loadDashboardData();

  return (
    <div className="page-stack">
      <section className="hero hero--compact">
        <div className="eyebrow">Registry</div>
        <h1>스킬, 훅, MCP는 고정값과 확장값을 분리해 둡니다</h1>
        <p>
          나중에 실제 번역 메모리, 자막 제공자, 플랫폼 내보내기 규칙이 붙어도 같은
          구조 안에서 확장되도록 설계했습니다.
        </p>
      </section>

      <div className="grid-two">
        <InfoCard title="Skills" eyebrow="Fixed + Dynamic">
          <div className="list-block">
            {data.fixedSkills.map((skill) => (
              <div key={skill.id} className="list-item">
                <strong>{skill.id}</strong>
                <p className="muted">{skill.owner}</p>
                <p>{skill.purpose}</p>
              </div>
            ))}
            {data.dynamicSkills.map((skill) => (
              <div key={skill.id} className="list-item">
                <strong>{skill.id}</strong>
                <p className="muted">{skill.status}</p>
                <p>{skill.activation_rule}</p>
              </div>
            ))}
          </div>
        </InfoCard>

        <InfoCard title="Hooks + MCP" eyebrow="Context">
          <p>MCP state: {data.mcp.state}</p>
          <p className="muted">Owner: {data.mcp.owner}</p>
          <div className="chip-row">
            {data.mcp.planned_connectors.map((connector) => (
              <span key={connector} className="chip">
                {connector}
              </span>
            ))}
          </div>
          <div className="list-block">
            {data.dynamicHooks.map((hook) => (
              <div key={hook.id} className="list-item">
                <strong>{hook.id}</strong>
                <p>{hook.activation_rule}</p>
              </div>
            ))}
          </div>
        </InfoCard>
      </div>
    </div>
  );
}

