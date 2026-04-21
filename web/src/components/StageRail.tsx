type StageRailProps = {
  stages: Array<{
    id: string;
    owner: string;
    output: string;
    success_definition: string;
  }>;
  currentStage: string;
};

export function StageRail({ stages, currentStage }: StageRailProps) {
  return (
    <div className="stage-rail">
      {stages.map((stage, index) => {
        const active = stage.id === currentStage;
        return (
          <article key={stage.id} className={active ? "stage-card stage-card--active" : "stage-card"}>
            <div className="stage-index">{String(index + 1).padStart(2, "0")}</div>
            <h3>{stage.id.replaceAll("_", " ")}</h3>
            <p className="muted">Owner: {stage.owner}</p>
            <p>{stage.success_definition}</p>
            <div className="chip">{stage.output}</div>
          </article>
        );
      })}
    </div>
  );
}

