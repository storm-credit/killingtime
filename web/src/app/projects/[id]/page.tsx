import { ProjectDetail } from "./detail-client";
import { loadDashboardData } from "@/lib/config";

export default async function ProjectDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const data = loadDashboardData();
  return <ProjectDetail id={id} stages={data.harness.stages} />;
}
