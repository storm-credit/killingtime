import { InfoCard } from "@/components/InfoCard";
import { StageRail } from "@/components/StageRail";
import { loadDashboardData } from "@/lib/config";

export default function HarnessPage() {
  const data = loadDashboardData();

  return (
    <div className="page-stack">
      <section className="hero hero--compact">
        <div className="eyebrow">Harness</div>
        <h1>우선 자막을 찾고, 없으면 ASR/OCR로 들어가는 구조</h1>
        <p>
          이 하네스는 무조건 받아쓰기부터 하지 않습니다. 플랫폼 자막, 내장 자막, OCR,
          ASR의 우선순위를 명시하고, 그 판단 자체를 기록합니다.
        </p>
      </section>

      <InfoCard title="Pipeline Stages" eyebrow="Ordered Flow">
        <StageRail stages={data.harness.stages} currentStage={data.manifest.current_stage} />
      </InfoCard>

      <div className="grid-two">
        <InfoCard title="Fixed Hooks" eyebrow="Quality Control">
          <div className="list-block">
            {data.fixedHooks.map((hook) => (
              <div key={hook.id} className="list-item">
                <strong>{hook.id}</strong>
                <p className="muted">Owner: {hook.owner}</p>
                <p>{hook.check.join(" / ")}</p>
              </div>
            ))}
          </div>
        </InfoCard>

        <InfoCard title="Current Project Notes" eyebrow="Manifest">
          <div className="list-block">
            {data.manifest.notes.map((note) => (
              <div key={note} className="list-item">
                <p>{note}</p>
              </div>
            ))}
          </div>
        </InfoCard>
      </div>
    </div>
  );
}

