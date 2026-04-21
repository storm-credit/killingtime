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

const STAGE_ETA_MIN: Record<string, number> = {
  intake: 3,
  source_probe: 1,
  subtitle_discovery: 1,
  source_extraction: 20, // ASR heavy; track pull is ~30s
  translation: 25,
  qa: 1,
  export: 10, // ffmpeg render
};

const STAGE_LABELS: Record<string, { label: string; desc: string }> = {
  intake: {
    label: "인테이크",
    desc: "URL과 대상 언어, 옵션을 정리해 파이프라인에 넘깁니다.",
  },
  source_probe: {
    label: "소스 감지",
    desc: "영상에 박힌 중/영 하드섭 여부와 자막 트랙 유무를 확인합니다.",
  },
  subtitle_discovery: {
    label: "자막 탐색",
    desc: "사용할 수 있는 자막 트랙을 정리하고 번역 소스를 정합니다.",
  },
  source_extraction: {
    label: "자막 추출",
    desc: "zh 트랙을 받거나(없으면 ASR) 원문 SRT를 만듭니다.",
  },
  translation: {
    label: "번역",
    desc: "Vertex/Claude/Gemini 중 선택한 엔진으로 한국어 자막을 만듭니다.",
  },
  qa: {
    label: "검수",
    desc: "큐 수와 타이밍이 원본과 맞는지, 어색한 번역이 없는지 점검합니다.",
  },
  export: {
    label: "패키징",
    desc: "MP4 · SRT · 업로드 가이드를 한 폴더로 묶어 완성합니다.",
  },
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
        const l = STAGE_LABELS[s.id] || { label: s.id, desc: s.success_definition };
        return (
          <div key={s.id} className={cls}>
            <div className="timeline-dot">{complete ? "✓" : i + 1}</div>
            <div className="timeline-label">
              <h4>{l.label}</h4>
              <p>{l.desc}</p>
            </div>
          </div>
        );
      })}
    </div>
  );
}

function parseStartTime(notes: string[] = []): number | null {
  for (const n of notes) {
    const m = n.match(/started\s+(\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2})/);
    if (m) {
      const iso = m[1].replace(" ", "T");
      const t = new Date(iso).getTime();
      if (Number.isFinite(t)) return t;
    }
  }
  return null;
}

function fmtDuration(sec: number): string {
  if (sec < 0) sec = 0;
  const h = Math.floor(sec / 3600);
  const m = Math.floor((sec % 3600) / 60);
  const s = Math.floor(sec % 60);
  if (h > 0) return `${h}시간 ${m}분`;
  if (m > 0) return `${m}분 ${s}초`;
  return `${s}초`;
}

function ProgressPanel({
  stages,
  current,
  status,
  startedAt,
}: {
  stages: Stage[];
  current: string;
  status: string;
  startedAt: number | null;
}) {
  const [now, setNow] = useState(Date.now());
  useEffect(() => {
    if (status === "completed") return;
    const t = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(t);
  }, [status]);

  const idx = Math.max(0, stages.findIndex((s) => s.id === current));
  const done = status === "completed";
  const total = stages.length;
  const progressPct = done
    ? 100
    : Math.round(((idx + 0.5) / total) * 100);

  const remainingMin = done
    ? 0
    : stages
        .slice(idx)
        .reduce((sum, s) => sum + (STAGE_ETA_MIN[s.id] ?? 5), 0);

  const elapsedSec = startedAt ? Math.max(0, (now - startedAt) / 1000) : 0;

  const currentLabel = STAGE_LABELS[current]?.label ?? current;

  return (
    <div className="progress-panel">
      <div className="progress-panel-head">
        <div>
          <div className="eyebrow">Progress</div>
          <h3 className="h3-card" style={{ margin: "4px 0 0", fontSize: "1.25rem" }}>
            {done ? "✓ 모든 단계 완료" : `${currentLabel} 진행 중`}
          </h3>
        </div>
        <div className="progress-stats">
          <div>
            <div className="stat-mini-value">{progressPct}%</div>
            <div className="stat-mini-label">{idx + (done ? 0 : 1)} / {total}</div>
          </div>
          {startedAt ? (
            <div>
              <div className="stat-mini-value">{fmtDuration(elapsedSec)}</div>
              <div className="stat-mini-label">경과</div>
            </div>
          ) : null}
          {!done ? (
            <div>
              <div className="stat-mini-value">~{remainingMin}분</div>
              <div className="stat-mini-label">남음 (예상)</div>
            </div>
          ) : null}
        </div>
      </div>
      <div className="progress-bar-track">
        <div
          className={`progress-bar-fill ${done ? "progress-bar-fill--done" : ""}`}
          style={{ width: `${progressPct}%` }}
        />
      </div>
    </div>
  );
}

function shortTitle(full: string, id: string): { display: string; sub: string | null } {
  if (!full || full === id) return { display: id, sub: null };
  const CAP = 48;
  const trimmed = full.trim();
  if (trimmed.length <= CAP) return { display: trimmed, sub: null };
  const clean = trimmed.split("\n")[0];
  const cut = clean.slice(0, CAP).replace(/[,，、、／/|•·\s]+$/, "");
  return { display: cut + "…", sub: clean };
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
        // Kick the queue worker on every poll so the next queued job
        // starts as soon as the current one completes.
        fetch(`/api/queue/tick`, { method: "POST" }).catch(() => {});
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

  const title = shortTitle(p.title, p.id);
  const startedAt = parseStartTime(p.notes);

  return (
    <div className="page-stack">
      <section className="hero">
        <div className="eyebrow">Job · {p.id}</div>
        <h1 title={title.sub ?? undefined}>{title.display}</h1>
        {title.sub ? (
          <p className="muted" style={{ marginTop: 8, fontSize: "0.92rem", lineHeight: 1.5 }}>
            {title.sub}
          </p>
        ) : null}
        {p.source_url && p.source_url !== "(local)" ? (
          <p className="muted" style={{ wordBreak: "break-all", fontFamily: "var(--font-mono)", fontSize: "0.82rem", marginTop: 10 }}>
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

      <ProgressPanel
        stages={stages}
        current={p.current_stage}
        status={p.status}
        startedAt={startedAt}
      />

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
