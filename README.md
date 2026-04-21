# Killing Time

Killing Time is an orchestra-first subtitle translation workspace for long-form video.

The system is designed around a shared harness:

- `orchestra` owns prioritization, routing, approval, and integration
- fixed agents define the default operating team
- dynamic agents, skills, hooks, and MCP connectors can be added without reshaping the project
- `web/` provides a local dashboard for the harness

The current harness is optimized for:

- source video intake
- subtitle discovery and extraction
- ASR and OCR fallback
- Korean and Spanish localization
- subtitle QA and export packaging

## Workspace Layout

```text
killingtime/
  configs/
  docs/
  harness/
  outputs/
  web/
```

## Quick Start

Install all workspace dependencies:

```powershell
npm install
```

Run the dashboard:

```powershell
npm run dev:web
```

## Ports

- Web: `3201`

## Design Principles

- Fixed core, extendable edge
- Config-first orchestration
- Human-reviewable harness documents
- Subtitle-first workflow, not raw transcript dumping
- Local fallback for MCP until external connectors become recurring
- No video compositing unless the pipeline truly needs it
