import { AgentRoster } from "@/components/AgentRoster";
import { InfoCard } from "@/components/InfoCard";
import { loadDashboardData } from "@/lib/config";

export default function OrchestraPage() {
  const data = loadDashboardData();

  return (
    <div className="page-stack">
      <section className="hero hero--compact">
        <div className="eyebrow">Roster</div>
        <h1>고정 에이전트는 박아두고, 동적 에이전트는 승격 규칙으로 붙입니다</h1>
        <p>
          오케스트라는 고정 코어를 전제로 운영하고, 반복 패턴이 생길 때만 동적 전문
          에이전트를 승격합니다.
        </p>
      </section>

      <div className="grid-two">
        <InfoCard title="Fixed Core" eyebrow="Always On">
          <p>{data.fixedAgents.length}개의 기본 에이전트가 하네스에 상주합니다.</p>
        </InfoCard>
        <InfoCard title="Dynamic Edge" eyebrow="Optional">
          <p>{data.dynamicAgents.length}개의 제안형 에이전트가 레지스트리에 대기합니다.</p>
        </InfoCard>
      </div>

      <AgentRoster fixedAgents={data.fixedAgents} dynamicAgents={data.dynamicAgents} />
    </div>
  );
}

