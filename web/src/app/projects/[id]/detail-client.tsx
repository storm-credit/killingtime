'use client';

import Link from "next/link";
import { useEffect, useState } from "react";
import { ThumbnailPicker } from "@/components/ThumbnailPicker";

type Project = {
  id: string;
  title: string;
  source_url: string;
  source_language: string;
  targets: string[];
  current_stage: string;
  status: string;
  notes?: string[];
  artifacts?: Record<string, string | null | undefined>;
};

type Stage = { id: string; owner: string; output: string; success_definition: string };

type ApiResponse = {
  project: Project | null;
  log_tail: string;
};

function StageTimeline({
  stages,
  current,
  status,
}: {
  stages: Stage[];
  current: string;
  status: string;
}) {
  const idx = stages.findIndex((s) => s.id === current);
  const done = status === "completed";
  const labels: Record<string, string> = {
    intake: "인테이크",
    source_probe: "소스 감지",
    subtitle_discovery: "자막 탐색",
    source_extraction: "자막 추출",
    translation: "번역",
    qa: "검수",
    export: "패키징",
  };

  return (
    <div className="timeline">
      {stages.map((s, i) => {
        const active = s.id === current && !done;
        const complete = done || i < idx;
        const cls = [
          "timeline-step",
          active ? "timeline-step--active" : "",
          complete ? "timeline-step--done" : "",
        ]
          .filter(Boolean)
          .join(" ");
        return (
          <div key={s.id} className={cls}>
            <div className="timeline-dot">{complete ? "✓" : i + 1}</div>
            <div className="timeline-label">
              <h4>{labels[s.id] || s.id}</h4>
              <p>{s.success_definition}</p>
            </div>
          </div>
        );
      })}
    </div>
  );
}

function statusChip(status: string, current: string): { label: string; className: string } {
  if (status === "completed") return { label: "✓ 완료", className: "chip chip--success" };
  if (status === "needs_review") return { label: "⚠ 검토 필요", className: "chip chip--gold" };
  if (status === "queued") return { label: "⏳ 대기", className: "chip chip--muted" };
  return { label: `▶ ${current} 진행 중`, className: "chip chip--active" };
}

function parseEngineFromNotes(notes: string[] = []): string | null {
  for (const n of notes) {
    const m = n.match(/engine=([a-z]+)/);
    if (m) return m[1];
  }
  return null;
}

function EngineBadge({ id }: { id: string }) {
  const cls = `engine-badge engine-badge--${id}`;
  return (
    <span className={cls}>
      <span className="engine-badge-dot" />
      {id.toUpperCase()}
    </span>
  );
}

function thumbUrl(id: string): string | null {
  return /^[a-zA-Z0-9_-]{11}$/.test(id) ? `https://i.ytimg.com/vi/${id}/hqdefault.jpg` : null;
}

export function ProjectDetail({ id, stages }: { id: string; stages: Stage[] }) {
  const [data, setData] = useState<ApiResponse | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    async function tick() {
      try {
        const res = await fetch(`/api/projects/${id}`, { cache: "no-store" });
        if (res.status === 404) {
          if (alive) setErr("프로젝트를 찾을 수 없습니다.");
          return;
        }
        const j = (await res.json()) as ApiResponse;
        if (alive) {
          setData(j);
          setErr(null);
        }
      } catch {
        if (alive) setErr("서버 응답 없음");
      }
    }
    tick();
    const interval = setInterval(() => {
      if (data?.project?.status === "completed") return;
      tick();
    }, 3000);
    return () => {
      alive = false;
      clearInterval(interval);
    };
  }, [id, data?.project?.status]);

  if (err) {
    return (
      <div className="page-stack">
        <section className="hero hero--compact">
          <div className="eyebrow">Not Found</div>
          <h1>{err}</h1>
          <p>
            <Link href="/" style={{ color: "var(--accent)", fontWeight: 600 }}>홈으로 돌아가기</Link>
          </p>
        </section>
      </div>
    );
  }
  if (!data || !data.project) {
    return (
      <div className="page-stack">
        <section className="hero hero--compact">
          <div className="eyebrow">{id}</div>
          <h1>매니페스트 대기 중...</h1>
          <p className="muted">파이프라인을 시작하는 중입니다.</p>
        </section>
      </div>
    );
  }

  const p = data.project;
  const s = statusChip(p.status, p.current_stage);
  const engine = parseEngineFromNotes(p.notes);
  const thumb = thumbUrl(p.id);
  const done = p.status === "completed";

  return (
    <div className="page-stack">
      <section className="hero">
        <div className="eyebrow">Job · {p.id}</div>
        <h1>{p.title}</h1>
        {p.source_url && p.source_url !== "(local)" ? (
          <p className="muted" style={{ wordBreak: "break-all", fontFamily: "var(--font-mono)", fontSize: "0.86rem" }}>
            <a href={p.source_url} target="_blank" rel="noreferrer">{p.source_url}</a>
          </p>
        ) : null}

        <div className="chip-row" style={{ marginTop: 20 }}>
          <span className={s.className}>{s.label}</span>
          {engine ? <EngineBadge id={engine} /> : null}
          <span className="chip">원어 · {p.source_language}</span>
          <span className="chip chip--accent">→ {p.targets.join(", ").toUpperCase()}</span>
        </div>
      </section>

      <div className="grid-two">
        <div className="card">
          <div className="eyebrow">Pipeline</div>
          <h2 className="h2-section">스테이지</h2>
          <StageTimeline stages={stages} current={p.current_stage} status={p.status} />
        </div>

        <div className="card">
          <div className="eyebrow">Preview</div>
          <h2 className="h2-section">썸네일</h2>
          {thumb ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={thumb}
              alt={p.title}
              style={{ width: "100%", borderRadius: "var(--radius-md)", border: "1px solid var(--line)" }}
            />
          ) : (
            <div className="job-thumb" />
          )}

          {done ? (
            <div style={{ marginTop: 20 }}>
              <div className="eyebrow">업로드 준비</div>
              <p>아래 파일을 YouTube Studio에 업로드하면 됩니다.</p>
              <div className="list-block" style={{ marginTop: 12 }}>
                <div className="list-item">
                  <code>final.mp4</code>
                  <span className="muted">한국어 하드섭 완성본</span>
                </div>
                <div className="list-item">
                  <code>{p.id}.ko.srt</code>
                  <span className="muted">한국어 SRT (CC용)</span>
                </div>
              </div>
            </div>
          ) : (
            <p className="muted" style={{ marginTop: 16, fontSize: "0.9rem" }}>
              완료되면 여기에 다운로드 / 업로드 링크가 표시됩니다.
            </p>
          )}
        </div>
      </div>

      <div className="card">
        <ThumbnailPicker jobId={p.id} />
      </div>

      {p.artifacts && Object.keys(p.artifacts).length > 0 ? (
        <div className="card">
          <div className="eyebrow">Artifacts</div>
          <h2 className="h2-section">산출물</h2>
          <ul className="list-block" style={{ listStyle: "none", padding: 0, margin: 0 }}>
            {Object.entries(p.artifacts).map(([k, v]) => (
              <li key={k} className="list-item">
                <span className="muted" style={{ minWidth: 140 }}>{k}</span>
                <code>{String(v ?? "—")}</code>
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      {p.notes && p.notes.length > 0 ? (
        <div className="card">
          <div className="eyebrow">Log</div>
          <h2 className="h2-section">노트</h2>
          <ul className="list-block" style={{ listStyle: "none", padding: 0, margin: 0 }}>
            {p.notes.map((n, i) => (
              <li key={i} className="list-item" style={{ fontSize: "0.88rem" }}>{n}</li>
            ))}
          </ul>
        </div>
      ) : null}

      {data.log_tail ? (
        <div className="card">
          <div className="eyebrow">Runtime</div>
          <h2 className="h2-section">최근 로그</h2>
          <pre className="log-box">{data.log_tail}</pre>
        </div>
      ) : null}
    </div>
  );
}
