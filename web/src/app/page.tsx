import { InfoCard } from "@/components/InfoCard";
import { StageRail } from "@/components/StageRail";
import { loadDashboardData } from "@/lib/config";

export default function HomePage() {
  const data = loadDashboardData();
  const stats = [
    { label: "Fixed Agents", value: data.fixedAgents.length },
    { label: "Dynamic Agents", value: data.dynamicAgents.length },
    { label: "Stages", value: data.harness.stages.length },
    { label: "Hooks", value: data.fixedHooks.length + data.dynamicHooks.length },
  ];

  return (
    <div className="page-stack">
      <section className="hero">
        <div className="eyebrow">Subtitle Localization Harness</div>
        <h1>오케스트라가 총괄하고, 고정 코어는 유지하고, 확장은 파일로 더하는 구조</h1>
        <p>
          `oddengine`의 운영 철학을 가져오되, `killingtime`은 중국 드라마와 장편 영상의
          자막 추출·번역·QA·패키징 워크플로우에 맞춰 재편했습니다.
        </p>
      </section>

      <section className="stat-grid">
        {stats.map((stat) => (
          <div key={stat.label} className="stat-card">
            <div className="stat-value">{stat.value}</div>
            <div className="stat-label">{stat.label}</div>
          </div>
        ))}
      </section>

      <div className="grid-two">
        <InfoCard title="Active Project" eyebrow="Manifest">
          <p>
            <strong>{data.manifest.title}</strong>
          </p>
          <p className="muted">{data.manifest.id}</p>
          <p>
            Source: {data.manifest.source_language.toUpperCase()} to{" "}
            {data.manifest.targets.join(", ").toUpperCase()}
          </p>
          <div className="chip-row">
            <span className="chip">Preferred: {data.manifest.preferred_path}</span>
            {data.manifest.fallback_path.map((item) => (
              <span className="chip" key={item}>
                {item}
              </span>
            ))}
          </div>
        </InfoCard>

        <InfoCard title="Harness Principle" eyebrow="Pipeline">
          <p>{data.harness.principle}</p>
          <p className="muted">Mode: {data.harness.mode}</p>
          <div className="chip-row">
            {data.harness.hooks.map((hook) => (
              <span key={hook} className="chip">
                {hook}
              </span>
            ))}
          </div>
        </InfoCard>
      </div>

      <InfoCard title="Stage Flow" eyebrow="Current Stage">
        <StageRail stages={data.harness.stages} currentStage={data.manifest.current_stage} />
      </InfoCard>
    </div>
  );
}

