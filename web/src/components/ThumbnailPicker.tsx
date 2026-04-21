'use client';

import { useCallback, useEffect, useState } from "react";

type Candidate = {
  index: number;
  timestamp: number;
  path: string;
  filename: string;
};

type ThumbnailManifest = {
  selected: number | null;
  candidates: Candidate[];
};

export function ThumbnailPicker({ jobId }: { jobId: string }) {
  const [data, setData] = useState<ThumbnailManifest>({ selected: null, candidates: [] });
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [bust, setBust] = useState(0);

  const fetchManifest = useCallback(async () => {
    try {
      const res = await fetch(`/api/projects/${jobId}/thumbnails`, { cache: "no-store" });
      const j = (await res.json()) as ThumbnailManifest;
      setData(j);
    } catch {
      /* ignore */
    }
  }, [jobId]);

  useEffect(() => {
    fetchManifest();
  }, [fetchManifest]);

  useEffect(() => {
    if (!generating) return;
    const interval = setInterval(async () => {
      await fetchManifest();
      setBust((b) => b + 1);
    }, 2500);
    const timeout = setTimeout(() => {
      setGenerating(false);
    }, 60_000);
    return () => {
      clearInterval(interval);
      clearTimeout(timeout);
    };
  }, [generating, fetchManifest]);

  useEffect(() => {
    if (generating && data.candidates.length >= 3) {
      setGenerating(false);
    }
  }, [generating, data.candidates.length]);

  async function regenerate() {
    setError(null);
    setGenerating(true);
    try {
      const res = await fetch(`/api/projects/${jobId}/thumbnails`, { method: "POST" });
      if (!res.ok) {
        const j = await res.json().catch(() => ({}));
        throw new Error(j?.error || "failed");
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "failed");
      setGenerating(false);
    }
  }

  async function select(n: number) {
    try {
      const res = await fetch(`/api/projects/${jobId}/thumbnails/${n}/select`, { method: "POST" });
      if (res.ok) {
        setData((prev) => ({ ...prev, selected: n }));
      }
    } catch {
      /* ignore */
    }
  }

  const hasAny = data.candidates.length > 0;

  return (
    <div>
      <div className="section-heading">
        <div>
          <div className="eyebrow">Thumbnails</div>
          <h2 className="h2-section">롱폼 썸네일 (3장)</h2>
        </div>
        <button className="ghost-button" onClick={regenerate} disabled={generating}>
          {generating ? "생성 중..." : hasAny ? "다시 생성" : "생성 시작"}
        </button>
      </div>

      {error ? <div className="error-banner" style={{ marginTop: 12 }}>{error}</div> : null}

      {!hasAny && !generating ? (
        <p className="muted" style={{ marginTop: 12 }}>
          영상 렌더 완료 후 `생성 시작`을 누르면 영상에서 3장을 뽑아 애니메이션풍으로 스타일링합니다.
        </p>
      ) : null}

      {generating && !hasAny ? (
        <p className="muted" style={{ marginTop: 12 }}>🎬 장면 탐지 중...</p>
      ) : null}

      {hasAny ? (
        <div
          className="grid-auto"
          style={{ marginTop: 16, gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))" }}
        >
          {data.candidates.map((c) => {
            const isSelected = data.selected === c.index;
            const src = `/api/projects/${jobId}/thumbnails/image/${c.filename}?v=${bust}`;
            return (
              <button
                key={c.index}
                onClick={() => select(c.index)}
                className="thumb-tile"
                style={{
                  padding: 0,
                  border: isSelected ? "3px solid var(--accent)" : "1px solid var(--line-strong)",
                  borderRadius: "var(--radius-md)",
                  overflow: "hidden",
                  background: "var(--paper-solid)",
                  cursor: "pointer",
                  transition: "transform 0.18s ease, box-shadow 0.18s ease",
                  boxShadow: isSelected ? "var(--shadow-md)" : "var(--shadow-sm)",
                }}
              >
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src={src}
                  alt={`thumb ${c.index + 1}`}
                  style={{ width: "100%", display: "block", aspectRatio: "16 / 9", objectFit: "cover" }}
                />
                <div style={{ padding: "10px 14px", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <span style={{ fontFamily: "var(--font-mono)", fontSize: "0.82rem", color: "var(--muted)" }}>
                    @{c.timestamp.toFixed(1)}s
                  </span>
                  {isSelected ? (
                    <span className="chip chip--success" style={{ fontSize: "0.76rem" }}>선택됨</span>
                  ) : (
                    <span className="muted" style={{ fontSize: "0.82rem" }}>클릭해서 선택</span>
                  )}
                </div>
              </button>
            );
          })}
        </div>
      ) : null}
    </div>
  );
}
