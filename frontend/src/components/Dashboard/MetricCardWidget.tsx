import { useRunSummary } from '../../api/client';

interface MetricCardWidgetProps {
  runId: number;
  metricPath: string;
  title?: string;
}

export default function MetricCardWidget({ runId, metricPath, title }: MetricCardWidgetProps) {
  const { data: summary, isLoading, error } = useRunSummary(runId);

  if (isLoading) {
    return (
      <div className="h-full flex items-center justify-center bg-white rounded border border-gray-200 p-4">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="h-full flex items-center justify-center bg-red-50 rounded border border-red-200 p-4">
        <p className="text-red-600 text-sm">Error loading metric</p>
      </div>
    );
  }

  const value = summary?.[metricPath];
  const displayValue =
    typeof value === 'number'
      ? value.toFixed(4)
      : value === null || value === undefined
      ? 'N/A'
      : String(value);

  return (
    <div className="h-full bg-gradient-to-br from-primary-50 to-white rounded border border-primary-200 p-6 flex flex-col justify-between">
      <div>
        <h3 className="text-sm font-medium text-gray-600 mb-2 truncate" title={title || metricPath}>
          {title || metricPath}
        </h3>
        <p className="text-4xl font-bold text-primary-700">{displayValue}</p>
      </div>
      <div className="text-xs text-gray-500 mt-4">Run #{runId}</div>
    </div>
  );
}
