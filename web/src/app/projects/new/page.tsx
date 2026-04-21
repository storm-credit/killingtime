'use client';

import { useMemo, useState } from "react";
import { InfoCard } from "@/components/InfoCard";

export default function NewProjectPage() {
  const [url, setUrl] = useState("");
  const [existingPath, setExistingPath] = useState("");
  const [existingSub, setExistingSub] = useState("");
  const [videoId, setVideoId] = useState("");
  const [sourceLang, setSourceLang] = useState("");
  const [targets, setTargets] = useState<{ ko: boolean; es: boolean }>({ ko: true, es: true });
  const [cleanHardsub, setCleanHardsub] = useState(false);
  const [skipProbe, setSkipProbe] = useState(false);
  const [asrModel, setAsrModel] = useState("small");
  const [engine, setEngine] = useState<"local" | "claude" | "gemini" | "gpt">("local");

  const command = useMemo(() => {
    const parts: string[] = ["npm run orchestra --"];
    if (existingPath) {
      parts.push(`--existing "${existingPath}"`);
      if (videoId) parts.push(`--video-id ${videoId}`);
    } else {
      parts.push(`"${url || "<YouTube URL>"}"`);
    }
    if (existingSub) {
      parts.push(`--sub "${existingSub}"`);
      if (sourceLang) parts.push(`--source-lang ${sourceLang}`);
    }
    const t = [targets.ko ? "ko" : "", targets.es ? "es" : ""].filter(Boolean).join(" ") || "ko es";
    parts.push(`--targets ${t}`);
    if (engine !== "local") parts.push(`--engine ${engine}`);
    if (cleanHardsub) parts.push("--clean-hardsub");
    if (skipProbe) parts.push("--skip-hardsub-probe");
    if (!existingSub && asrModel !== "small") parts.push(`--asr-model ${asrModel}`);
    return parts.join(" ");
  }, [url, existingPath, existingSub, videoId, sourceLang, targets, cleanHardsub, skipProbe, asrModel, engine]);

  const engineHint: Record<typeof engine, string> = {
    local: "Ollama 데몬이 localhost:11434 에서 돌고 있어야 합니다. `ollama pull qwen2.5:7b`",
    claude: "ANTHROPIC_API_KEY 필요. `pip install anthropic`",
    gemini: "GEMINI_API_KEY 필요. `pip install google-generativeai`",
    gpt: "OPENAI_API_KEY 필요. `pip install openai`",
  };

  return (
    <div className="page-stack">
      <section className="hero hero--compact">
        <div className="eyebrow">Intake</div>
        <h1>YouTube URL 또는 기존 영상으로 오케스트라 실행</h1>
        <p>
          필드를 채우면 CLI 명령이 조립됩니다. 트랙 자막이 있으면 Claude로 그 위에 한/스를
          얹고, 없으면 faster-whisper로 음성을 받아씁니다. 기본값은 영상을 건드리지 않는
          `keep` 모드입니다.
        </p>
      </section>

      <InfoCard title="1. Source" eyebrow="URL 또는 파일">
        <label className="muted" htmlFor="url">YouTube URL</label>
        <input
          id="url"
          type="url"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          placeholder="https://www.youtube.com/watch?v=..."
          style={{ width: "100%", padding: "8px 10px", marginTop: 6 }}
        />
        <p className="muted" style={{ marginTop: 12 }}>또는 기존 영상 재사용:</p>
        <input
          type="text"
          value={existingPath}
          onChange={(e) => setExistingPath(e.target.value)}
          placeholder="outputs/downloads/1CELx9LRI-Y.hq.mp4"
          style={{ width: "100%", padding: "8px 10px", marginTop: 6 }}
        />
        <label className="muted" htmlFor="vid" style={{ display: "block", marginTop: 8 }}>Video ID (파일명과 다를 때)</label>
        <input
          id="vid"
          type="text"
          value={videoId}
          onChange={(e) => setVideoId(e.target.value)}
          placeholder="1CELx9LRI-Y"
          style={{ width: "100%", padding: "8px 10px", marginTop: 4 }}
        />
      </InfoCard>

      <InfoCard title="2. Source SRT (선택)" eyebrow="이미 받아둔 자막">
        <p className="muted">트랙 자막을 이미 받아뒀으면 경로를 넣어 추출 단계를 건너뜁니다.</p>
        <input
          type="text"
          value={existingSub}
          onChange={(e) => setExistingSub(e.target.value)}
          placeholder="outputs/subtitles/1CELx9LRI-Y.zh-Hans.srt"
          style={{ width: "100%", padding: "8px 10px", marginTop: 6 }}
        />
        <label className="muted" htmlFor="srclang" style={{ display: "block", marginTop: 8 }}>Source language code</label>
        <input
          id="srclang"
          type="text"
          value={sourceLang}
          onChange={(e) => setSourceLang(e.target.value)}
          placeholder="zh-Hans"
          style={{ width: "100%", padding: "8px 10px", marginTop: 4 }}
        />
      </InfoCard>

      <InfoCard title="3. Targets" eyebrow="최종 자막">
        <label style={{ display: "block" }}>
          <input type="checkbox" checked={targets.ko} onChange={(e) => setTargets({ ...targets, ko: e.target.checked })} /> Korean (ko)
        </label>
        <label style={{ display: "block" }}>
          <input type="checkbox" checked={targets.es} onChange={(e) => setTargets({ ...targets, es: e.target.checked })} /> Spanish (es)
        </label>
        <p className="muted" style={{ marginTop: 8 }}>
          중/영 자막은 최종 산출물에서 제외되지만 번역 **소스**로는 사용됩니다 (타이밍 보존).
        </p>
      </InfoCard>

      <InfoCard title="4. Hardsub" eyebrow="영상 품질 정책">
        <label style={{ display: "block" }}>
          <input type="checkbox" checked={cleanHardsub} onChange={(e) => setCleanHardsub(e.target.checked)} /> `--clean-hardsub` 켜기 (delogo로 박힌 자막 제거 시도, 해당 영역 약간 뭉개짐)
        </label>
        <label style={{ display: "block", marginTop: 6 }}>
          <input type="checkbox" checked={skipProbe} onChange={(e) => setSkipProbe(e.target.checked)} /> 하드섭 감지 건너뛰기 (빠름, 덜 안전)
        </label>
        <p className="muted" style={{ marginTop: 8 }}>
          끄면 (기본값) 영상은 그대로 두고, 한/스 SRT만 옆에 붙습니다. 영상 품질 100% 유지.
        </p>
      </InfoCard>

      <InfoCard title="5. ASR Fallback" eyebrow="자막 트랙 0개일 때">
        <label className="muted" htmlFor="asr">faster-whisper model</label>
        <select id="asr" value={asrModel} onChange={(e) => setAsrModel(e.target.value)} style={{ padding: "8px 10px", marginTop: 6 }}>
          <option value="tiny">tiny (가장 빠름)</option>
          <option value="base">base</option>
          <option value="small">small (기본)</option>
          <option value="medium">medium</option>
          <option value="large-v3">large-v3 (가장 정확)</option>
        </select>
      </InfoCard>

      <InfoCard title="6. Translation Engine" eyebrow="로컬 기본">
        <div className="chip-row">
          {(["local", "claude", "gemini", "gpt"] as const).map((e) => (
            <label key={e} style={{ display: "inline-flex", alignItems: "center", gap: 6 }}>
              <input
                type="radio"
                name="engine"
                value={e}
                checked={engine === e}
                onChange={() => setEngine(e)}
              />
              {e === "local" ? "Local (Ollama, 무료)" : e === "claude" ? "Claude" : e === "gemini" ? "Gemini" : "GPT"}
            </label>
          ))}
        </div>
        <p className="muted" style={{ marginTop: 8 }}>{engineHint[engine]}</p>
      </InfoCard>

      <InfoCard title="7. Run" eyebrow="CLI">
        <p className="muted">터미널에 복사해 실행하세요.</p>
        <pre style={{ background: "#0b0b0d", color: "#eae6df", padding: 12, borderRadius: 8, overflowX: "auto" }}>
          <code>{command}</code>
        </pre>
      </InfoCard>
    </div>
  );
}
