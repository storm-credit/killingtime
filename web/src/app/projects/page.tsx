import Link from "next/link";
import { listProjects, type Project } from "@/lib/projects";

function thumbUrl(sourceUrl: string, id: string): string | null {
  const m = sourceUrl.match(/[?&]v=([a-zA-Z0-9_-]{11})|youtu\.be\/([a-zA-Z0-9_-]{11})|\/shorts\/([a-zA-Z0-9_-]{11})/);
  const vid = m?.[1] || m?.[2] || m?.[3] || (/^[a-zA-Z0-9_-]{11}$/.test(id) ? id : null);
  return vid ? `https://i.ytimg.com/vi/${vid}/hqdefault.jpg` : null;
}

function statusChip(status: string): { label: string; className: string } {
  switch (status) {
    case "completed": return { label: "완료", className: "chip chip--success" };
    case "in_progress": return { label: "진행 중", className: "chip chip--active" };
    case "queued": return { label: "대기", className: "chip chip--muted" };
    case "needs_review": return { label: "검토 필요", className: "chip chip--gold" };
    case "empty": return { label: "시작 전", className: "chip chip--muted" };
    default: return { label: status, className: "chip chip--muted" };
  }
}

function JobCard({ p }: { p: Project }) {
  const thumb = thumbUrl(p.source_url || "", p.id);
  const s = statusChip(p.status);
  return (
    <Link href={`/projects/${p.id}`} className="job-card">
      <div
        className="job-thumb"
        style={thumb ? { backgroundImage: `url(${thumb})` } : undefined}
      />
      <div className="job-body">
        <h3>{p.title}</h3>
        <p className="job-meta">{p.id}</p>
        <div className="chip-row">
          <span className={s.className}>{s.label}</span>
          <span className="chip chip--muted">stage · {p.current_stage}</span>
          <span className="chip chip--muted">→ {p.targets.join(", ").toUpperCase()}</span>
        </div>
      </div>
    </Link>
  );
}

export default function LibraryPage() {
  const projects = listProjects();
  const completed = projects.filter((p) => p.status === "completed").length;
  const running = projects.filter((p) => p.status === "in_progress" || p.status === "queued").length;

  return (
    <div className="page-stack">
      <section className="hero hero--compact">
        <div className="eyebrow">Library</div>
        <h1>지금까지의 작업</h1>
        <p>
          완료된 영상은 `outputs/jobs/{`{id}`}/final.mp4` 로 모여 있습니다. 카드 클릭하면 진행
          상태와 산출물, 업로드용 메타데이터를 확인할 수 있어요.
        </p>
      </section>

      <div className="stat-grid">
        <div className="stat-card">
          <div className="stat-value">{projects.length}</div>
          <div className="stat-label">총 작업</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">{completed}</div>
          <div className="stat-label">완료</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">{running}</div>
          <div className="stat-label">진행/대기</div>
        </div>
        <Link href="/" className="stat-card" style={{ display: "block", color: "inherit" }}>
          <div className="stat-value" style={{ color: "var(--accent)" }}>+</div>
          <div className="stat-label">새 URL 넣기</div>
        </Link>
      </div>

      {projects.length === 0 ? (
        <div className="card">
          <h2 className="h2-section">아직 시작한 작업이 없어요</h2>
          <p className="muted">
            <Link href="/" style={{ color: "var(--accent)", fontWeight: 600 }}>홈으로 이동</Link>해서 YouTube URL을
            넣어 첫 번째 영상을 만들어보세요.
          </p>
        </div>
      ) : (
        <div className="grid-auto">
          {projects.map((p) => (
            <JobCard key={p.id} p={p} />
          ))}
        </div>
      )}
    </div>
  );
}
