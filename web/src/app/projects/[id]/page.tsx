import { notFound } from "next/navigation";
import { InfoCard } from "@/components/InfoCard";
import { StageRail } from "@/components/StageRail";
import { loadDashboardData } from "@/lib/config";
import { getProject } from "@/lib/projects";

export default async function ProjectDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const project = getProject(id);
  if (!project) {
    notFound();
  }
  const data = loadDashboardData();

  return (
    <div className="page-stack">
      <section className="hero hero--compact">
        <div className="eyebrow">{project.id}</div>
        <h1>{project.title}</h1>
        <p className="muted">{project.source_url}</p>
      </section>

      <div className="grid-two">
        <InfoCard title="Status" eyebrow="Run">
          <div className="chip-row">
            <span className="chip">{project.status}</span>
            <span className="chip">stage: {project.current_stage}</span>
          </div>
        </InfoCard>
        <InfoCard title="Localization" eyebrow="Targets">
          <p>
            Source: <strong>{project.source_language}</strong>
          </p>
          <p>Targets: {project.targets.join(", ").toUpperCase()}</p>
          <div className="chip-row">
            {project.preferred_path ? <span className="chip">preferred: {project.preferred_path}</span> : null}
            {project.fallback_path?.map((f) => (
              <span key={f} className="chip">fallback: {f}</span>
            ))}
          </div>
        </InfoCard>
      </div>

      <InfoCard title="Stage Flow" eyebrow="Harness">
        <StageRail stages={data.harness.stages} currentStage={project.current_stage} />
      </InfoCard>

      {project.artifacts && Object.keys(project.artifacts).length > 0 ? (
        <InfoCard title="Artifacts" eyebrow="Outputs">
          <ul>
            {Object.entries(project.artifacts).map(([k, v]) => (
              <li key={k}>
                <span className="muted">{k}: </span>
                <code>{String(v ?? "—")}</code>
              </li>
            ))}
          </ul>
        </InfoCard>
      ) : null}

      {project.notes?.length ? (
        <InfoCard title="Notes" eyebrow="Log">
          <ul>
            {project.notes.map((n, i) => (
              <li key={i}>{n}</li>
            ))}
          </ul>
        </InfoCard>
      ) : null}
    </div>
  );
}
