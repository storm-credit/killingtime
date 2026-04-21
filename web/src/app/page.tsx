import { IntakeLanding } from "./intake-landing";
import { listProjects } from "@/lib/projects";

export default function HomePage() {
  const recent = listProjects().slice(0, 4);
  return <IntakeLanding recent={recent} />;
}
