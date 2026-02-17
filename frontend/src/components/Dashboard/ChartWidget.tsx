import { MetricChart } from '../Charts';

interface ChartWidgetProps {
  runId: number;
  metricPath: string;
  title?: string;
}

export default function ChartWidget({ runId, metricPath, title }: ChartWidgetProps) {
  return (
    <div className="h-full">
      <MetricChart runId={runId} metricPath={metricPath} title={title} height={300} showLegend={false} />
    </div>
  );
}
