'use client';

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useMemo, useState } from "react";
import type { Project } from "@/lib/projects";

type Engine = "vertex" | "claude" | "gemini" | "gpt" | "local";

const ENGINES: Array<{ id: Engine; label: string; sub: string }> = [
  { id: "vertex", label: "Vertex AI", sub: "Gemini 2.5 Flash · 기본" },
  { id: "claude", label: "Claude", sub: "Sonnet 4.6" },
  { id: "gemini", label: "Gemini API", sub: "무료 티어" },
  { id: "gpt", label: "GPT-4o-mini", sub: "OpenAI" },
  { id: "local", label: "Local", sub: "Ollama" },
];

function thumbUrl(sourceUrl: string): string | null {
  const m = sourceUrl.match(/[?&]v=([a-zA-Z0-9_-]{11})|youtu\.be\/([a-zA-Z0-9_-]{11})|\/shorts\/([a-zA-Z0-9_-]{11})/);
  const id = m?.[1] || m?.[2] || m?.[3] || sourceUrl;
  if (!/^[a-zA-Z0-9_-]{11}$/.test(id)) return null;
  return `https://i.ytimg.com/vi/${id}/hqdefault.jpg`;
}

function shortTitle(full: string, id: string, cap = 38): string {
  if (!full || full === id) return id;
  const clean = full.trim().split("\n")[0];
  if (clean.length <= cap) return clean;
  return clean.slice(0, cap).replace(/[,，、、／/|•·\s]+$/, "") + "…";
}

function statusChipClass(status: string): string {
  if (status === "completed") return "chip chip--success";
  if (status === "queued") return "chip chip--muted";
  if (status === "empty") return "chip chip--muted";
  return "chip chip--accent";
}

function statusLabel(status: string): string {
  switch (status) {
    case "completed": return "완료";
    case "in_progress": return "진행 중";
    case "queued": return "대기";
    case "needs_review": return "검토 필요";
    case "empty": return "시작 전";
    default: return status;
  }
}

export function IntakeLanding({ recent }: { recent: Project[] }) {
  const router = useRouter();
  const [url, setUrl] = useState("");
  const [engine, setEngine] = useState<Engine>("vertex");
  const [ko, setKo] = useState(true);
  const [es, setEs] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [cleanHardsub, setCleanHardsub] = useState(false);

  const disabled = submitting || !url;

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    if (!url) return;
    const targets: string[] = [];
    if (ko) targets.push("ko");
    if (es) targets.push("es");
    if (targets.length === 0) targets.push("ko");
    setSubmitting(true);
    try {
      const res = await fetch("/api/projects", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url, engine, targets, cleanHardsub }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data?.error || "failed");
      router.push(data.redirect || `/projects/${data.videoId}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "failed");
      setSubmitting(false);
    }
  }

  return (
    <div className="page-stack">
      <section className="hero">
        <div className="eyebrow">YouTube → 한국어 자막 영상</div>
        <h1>URL 한 줄로<br />번역본을 만들어요</h1>
        <p>
          링크만 붙여넣으면 다운로드 · 자막 추출 · 번역 · 렌더까지 자동 진행. 중국 드라마 숏츠에
          자연스러운 한국어를 입혀 그대로 업로드할 수 있는 MP4로 내보냅니다.
        </p>

        <form onSubmit={submit}>
          <div className="paste-box">
            <input
              type="url"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              placeholder="https://www.youtube.com/watch?v=..."
              disabled={submitting}
              autoFocus
            />
            <button type="submit" className="primary-button" disabled={disabled}>
              {submitting ? "시작 중..." : "시작 →"}
            </button>
          </div>

          <div className="chip-row" style={{ marginTop: 20 }}>
            <label className={`toggle-chip ${ko ? "toggle-chip--on" : ""}`}>
              <input type="checkbox" checked={ko} onChange={(e) => setKo(e.target.checked)} disabled={submitting} />
              한국어
            </label>
            <label className={`toggle-chip ${es ? "toggle-chip--on" : ""}`}>
              <input type="checkbox" checked={es} onChange={(e) => setEs(e.target.checked)} disabled={submitting} />
              스페인어
            </label>
            <button
              type="button"
              className="ghost-button"
              onClick={() => setShowAdvanced((v) => !v)}
              style={{ marginLeft: "auto" }}
            >
              {showAdvanced ? "간단히 ↑" : "고급 설정 ↓"}
            </button>
          </div>

          {showAdvanced ? (
            <>
              <div className="eyebrow" style={{ marginTop: 28 }}>번역 엔진</div>
              <div className="options-panel">
                {ENGINES.map((e) => (
                  <label
                    key={e.id}
                    className={`option-tile ${engine === e.id ? "option-tile--active" : ""}`}
                  >
                    <input
                      type="radio"
                      name="engine"
                      checked={engine === e.id}
                      onChange={() => setEngine(e.id)}
                      disabled={submitting}
                    />
                    <div>
                      <strong>{e.label}</strong>
                      <p>{e.sub}</p>
                    </div>
                  </label>
                ))}
              </div>

              <label className="option-tile" style={{ marginTop: 16 }}>
                <input
                  type="checkbox"
                  checked={cleanHardsub}
                  onChange={(e) => setCleanHardsub(e.target.checked)}
                  disabled={submitting}
                />
                <div>
                  <strong>박힌 중/영 자막 제거 시도 (delogo)</strong>
                  <p>영역 블러로 지움. 영상 일부 품질 손상됨. 보통은 끈 채로 한국어만 위에 얹기.</p>
                </div>
              </label>
            </>
          ) : null}

          {error ? <div className="error-banner" style={{ marginTop: 20 }}>{error}</div> : null}
        </form>
      </section>

      {recent.length > 0 ? (
        <>
          <div className="section-heading">
            <h2 className="h2-section">최근 작업</h2>
            <Link href="/projects" className="ghost-button">전체 보기 →</Link>
          </div>
          <div className="grid-auto">
            {recent.map((p) => {
              const thumb = thumbUrl(p.source_url || p.id);
              return (
                <Link key={p.id} href={`/projects/${p.id}`} className="job-card">
                  <div
                    className="job-thumb"
                    style={thumb ? { backgroundImage: `url(${thumb})` } : undefined}
                  />
                  <div className="job-body">
                    <h3 title={p.title}>{shortTitle(p.title, p.id)}</h3>
                    <p className="job-meta">{p.id}</p>
                    <div className="chip-row">
                      <span className={statusChipClass(p.status)}>{statusLabel(p.status)}</span>
                      <span className="chip chip--muted">stage · {p.current_stage}</span>
                      <span className="chip chip--muted">→ {p.targets.join(", ").toUpperCase()}</span>
                    </div>
                  </div>
                </Link>
              );
            })}
          </div>
        </>
      ) : null}
    </div>
  );
}
