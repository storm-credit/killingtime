import Link from "next/link";
import { loadDashboardData } from "@/lib/config";

export default function AdminHub() {
  const d = loadDashboardData();
  const sections = [
    {
      href: "/orchestra",
      title: "Orchestra",
      sub: "고정 · 동적 에이전트 로스터",
      value: `${d.fixedAgents.length + d.dynamicAgents.length} 명`,
    },
    {
      href: "/harness",
      title: "Harness",
      sub: "스테이지 / 훅 / 파이프라인",
      value: `${d.harness.stages.length} 스테이지`,
    },
    {
      href: "/registry",
      title: "Registry",
      sub: "스킬 / 훅 / MCP",
      value: `${d.fixedSkills.length + d.dynamicSkills.length} 스킬`,
    },
  ];

  return (
    <div className="page-stack">
      <section className="hero hero--compact">
        <div className="eyebrow">Admin</div>
        <h1>오케스트라 설정과 진단</h1>
        <p>파이프라인 설계를 손보거나 새 에이전트/스킬을 승격할 때 들어오세요. 일상 작업엔 필요 없습니다.</p>
      </section>

      <div className="grid-auto">
        {sections.map((s) => (
          <Link key={s.href} href={s.href} className="job-card" style={{ gridTemplateColumns: "1fr" }}>
            <div className="job-body">
              <div className="eyebrow">{s.title}</div>
              <h3 style={{ fontSize: "1.4rem" }}>{s.sub}</h3>
              <p className="job-meta" style={{ fontFamily: "inherit", fontSize: "1.02rem" }}>{s.value}</p>
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}
