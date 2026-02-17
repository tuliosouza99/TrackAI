import { useNavigate } from 'react-router-dom';
import { useRuns } from '../../api/client';

interface RecentRunsWidgetProps {
  projectId: number;
  limit?: number;
}

export default function RecentRunsWidget({ projectId, limit = 5 }: RecentRunsWidgetProps) {
  const navigate = useNavigate();
  const { data, isLoading, error } = useRuns({
    project_id: projectId,
    sort_by: 'created_at',
    sort_order: 'desc',
  });

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
        <p className="text-red-600 text-sm">Error loading runs</p>
      </div>
    );
  }

  const runs = data?.runs.slice(0, limit) || [];

  return (
    <div className="h-full bg-white rounded border border-gray-200 p-4 overflow-auto">
      <h3 className="text-sm font-semibold text-gray-900 mb-3">Recent Runs</h3>
      <div className="space-y-2">
        {runs.map((run) => (
          <div
            key={run.id}
            onClick={() => navigate(`/runs/${run.id}`)}
            className="p-2 rounded hover:bg-gray-50 cursor-pointer transition-colors border border-gray-100"
          >
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium text-primary-600 font-mono truncate">
                {run.run_id}
              </span>
              <span
                className={`text-xs px-2 py-0.5 rounded-full ${
                  run.state === 'running'
                    ? 'bg-green-100 text-green-700'
                    : run.state === 'completed'
                    ? 'bg-blue-100 text-blue-700'
                    : 'bg-red-100 text-red-700'
                }`}
              >
                {run.state}
              </span>
            </div>
            <p className="text-xs text-gray-600 mt-1 truncate">{run.name}</p>
          </div>
        ))}
      </div>
      {runs.length === 0 && (
        <p className="text-gray-400 text-sm text-center py-4">No runs yet</p>
      )}
    </div>
  );
}
