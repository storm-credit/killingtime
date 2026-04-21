import Link from "next/link";
import { InfoCard } from "@/components/InfoCard";
import { StageRail } from "@/components/StageRail";
import { loadDashboardData } from "@/lib/config";
import { listProjects } from "@/lib/projects";

export default function ProjectsPage() {
  const projects = listProjects();
  const data = loadDashboardData();

  return (
    <div className="page-stack">
      <section className="hero hero--compact">
        <div className="eyebrow">Projects</div>
        <h1>오케스트라가 돌아간 영상의 진행 상태를 한눈에</h1>
        <p>
          `outputs/manifests/` 의 매니페스트 파일을 읽어 스테이지 흐름을 표시합니다. 새
          작업은 `Intake` 에서 URL을 넣고 CLI 명령을 복사해 실행하세요.
        </p>
      </section>

      <div className="chip-row">
        <Link className="chip" href="/projects/new">+ New intake</Link>
      </div>

      {projects.length === 0 ? (
        <InfoCard title="아직 등록된 프로젝트가 없습니다" eyebrow="Empty">
          <p>`npm run orchestra -- &lt;YouTube URL&gt;` 또는 Intake 페이지에서 시작하세요.</p>
        </InfoCard>
      ) : (
        <div className="page-stack">
          {projects.map((p) => (
            <InfoCard key={p.id} title={p.title} eyebrow={p.id}>
              <p className="muted">{p.source_url}</p>
              <p>
                Source: <strong>{p.source_language}</strong> to {p.targets.join(", ").toUpperCase()}
              </p>
              <div className="chip-row">
                <span className="chip">{p.status}</span>
                <span className="chip">current: {p.current_stage}</span>
                {p.preferred_path ? <span className="chip">preferred: {p.preferred_path}</span> : null}
              </div>
              <StageRail stages={data.harness.stages} currentStage={p.current_stage} />
              <div className="chip-row">
                <Link href={`/projects/${p.id}`} className="chip">상세 보기</Link>
              </div>
            </InfoCard>
          ))}
        </div>
      )}
    </div>
  );
}
