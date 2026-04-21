'use client';

import { useMemo, useState } from "react";
import { InfoCard } from "@/components/InfoCard";

export default function NewProjectPage() {
  const [url, setUrl] = useState("");
  const [targets, setTargets] = useState<{ ko: boolean; es: boolean }>({ ko: true, es: true });
  const [skipProbe, setSkipProbe] = useState(false);

  const command = useMemo(() => {
    const t = [targets.ko ? "ko" : "", targets.es ? "es" : ""].filter(Boolean).join(" ") || "ko es";
    const flags = [`"${url || "<YouTube URL>"}"`, "--targets", t];
    if (skipProbe) flags.push("--skip-hardsub-probe");
    return `npm run orchestra -- ${flags.join(" ")}`;
  }, [url, targets, skipProbe]);

  return (
    <div className="page-stack">
      <section className="hero hero--compact">
        <div className="eyebrow">Intake</div>
        <h1>YouTube URL을 넣고 오케스트라 명령을 받아가세요</h1>
        <p>
          MVP는 로컬 파이프라인이 CLI로 돌아갑니다. 아래 필드를 채우면 실행 명령이 조립됩니다.
          실행 결과는 Projects 목록과 `outputs/` 폴더에 나타납니다.
        </p>
      </section>

      <InfoCard title="1. Source" eyebrow="Step">
        <label className="muted" htmlFor="url">YouTube URL</label>
        <input
          id="url"
          type="url"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          placeholder="https://www.youtube.com/watch?v=..."
          style={{ width: "100%", padding: "8px 10px", marginTop: 6 }}
        />
      </InfoCard>

      <InfoCard title="2. Targets" eyebrow="Step">
        <label style={{ display: "block" }}>
          <input type="checkbox" checked={targets.ko} onChange={(e) => setTargets({ ...targets, ko: e.target.checked })} /> Korean (ko)
        </label>
        <label style={{ display: "block" }}>
          <input type="checkbox" checked={targets.es} onChange={(e) => setTargets({ ...targets, es: e.target.checked })} /> Spanish (es)
        </label>
      </InfoCard>

      <InfoCard title="3. Options" eyebrow="Step">
        <label>
          <input type="checkbox" checked={skipProbe} onChange={(e) => setSkipProbe(e.target.checked)} /> Skip hardsub probe (faster, less safe)
        </label>
      </InfoCard>

      <InfoCard title="4. Run" eyebrow="CLI">
        <p className="muted">아래 명령을 터미널에 복사해 실행하세요. ANTHROPIC_API_KEY가 .env에 설정되어 있어야 합니다.</p>
        <pre style={{ background: "#0b0b0d", color: "#eae6df", padding: 12, borderRadius: 8, overflowX: "auto" }}>
          <code>{command}</code>
        </pre>
      </InfoCard>
    </div>
  );
}
