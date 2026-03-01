import { useSearchParams, useNavigate } from 'react-router-dom';
import { useState, useMemo } from 'react';
import { useRun, useRunSummary } from '../api/client';
import { MultiMetricChart } from '../components/Charts';

export default function CompareRunsPage() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const [highlightDifferences, setHighlightDifferences] = useState(true);
  const [selectedMetrics, setSelectedMetrics] = useState<string[]>([]);

  // Get run IDs from query params (e.g., ?runs=1,2,3)
  const runIds = useMemo(() => {
    const runsParam = searchParams.get('runs');
    if (!runsParam) return [];
    return runsParam.split(',').map((id) => parseInt(id.trim())).filter((id) => !isNaN(id));
  }, [searchParams]);

  // Fetch data for each run
  const runsData = runIds.map((runId) => ({
    runId,
    // eslint-disable-next-line react-hooks/rules-of-hooks
    run: useRun(runId),
    // eslint-disable-next-line react-hooks/rules-of-hooks
    summary: useRunSummary(runId),
  }));

  const isLoading = runsData.some((r) => r.run.isLoading || r.summary.isLoading);
  const error = runsData.find((r) => r.run.error || r.summary.error);

  // Get all unique metric keys across all runs
  const allMetricKeys = useMemo(() => {
    const keysSet = new Set<string>();
    runsData.forEach((r) => {
      if (r.summary.data) {
        Object.keys(r.summary.data).forEach((key) => keysSet.add(key));
      }
    });
    return Array.from(keysSet).sort();
  }, [runsData]);

  // Check if a value differs across runs
  const isDifferent = (key: string) => {
    const values = runsData.map((r) => r.summary.data?.[key]);
    const uniqueValues = new Set(values.map((v) => JSON.stringify(v)));
    return uniqueValues.size > 1;
  };

  // Export to CSV
  const exportToCSV = () => {
    const headers = ['Metric', ...runsData.map((r) => r.run.data?.run_id || `Run ${r.runId}`)];
    const rows = allMetricKeys.map((key) => [
      key,
      ...runsData.map((r) => {
        const value = r.summary.data?.[key];
        return typeof value === 'number' ? value.toFixed(6) : String(value ?? '');
      }),
    ]);

    const csvContent = [
      headers.join(','),
      ...rows.map((row) => row.join(',')),
    ].join('\n');

    const blob = new Blob([csvContent], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `runs_comparison_${new Date().toISOString().slice(0, 10)}.csv`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  if (runIds.length === 0) {
    return (
      <div className="p-8">
        <div className="card text-center py-12">
          <p className="text-gray-500 text-lg">No runs selected for comparison</p>
          <p className="text-gray-400 text-sm mt-2">
            Select runs from the runs table and click "Compare" to view them side-by-side
          </p>
          <button
            onClick={() => navigate(-1)}
            className="mt-4 btn-secondary"
          >
            Go Back
          </button>
        </div>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="p-8">
        <div className="animate-pulse">
          <div className="h-8 bg-gray-200 rounded w-1/4 mb-6"></div>
          <div className="bg-white rounded-lg border border-gray-200 p-4">
            <div className="space-y-3">
              {[1, 2, 3, 4, 5].map((i) => (
                <div key={i} className="h-12 bg-gray-200 rounded"></div>
              ))}
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-8">
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-700">
          <h3 className="font-semibold mb-1">Error loading runs</h3>
          <p className="text-sm">{error.run?.error?.message || error.summary?.error?.message}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="p-8">
      {/* Header */}
      <div className="mb-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Compare Runs</h1>
            <p className="text-gray-600 mt-1">
              Comparing {runIds.length} {runIds.length === 1 ? 'run' : 'runs'}
            </p>
          </div>
          <div className="flex gap-3">
            <button
              onClick={() => setHighlightDifferences(!highlightDifferences)}
              className={`px-4 py-2 text-sm rounded-md transition-colors ${
                highlightDifferences
                  ? 'bg-primary-100 text-primary-700 border border-primary-300'
                  : 'bg-gray-100 text-gray-700 border border-gray-300'
              }`}
            >
              {highlightDifferences ? '✓ ' : ''}Highlight Differences
            </button>
            <button onClick={exportToCSV} className="btn-secondary text-sm">
              Export CSV
            </button>
            <button onClick={() => navigate(-1)} className="btn-secondary text-sm">
              Back
            </button>
          </div>
        </div>
      </div>

      {/* Run Info Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-6">
        {runsData.map(({ runId, run, summary }) => (
          <div key={runId} className="card">
            <div className="flex items-start justify-between mb-2">
              <h3 className="text-lg font-semibold text-gray-900 truncate">
                {run.data?.name}
              </h3>
              <span
                className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
                  run.data?.state === 'running'
                    ? 'bg-green-100 text-green-800'
                    : run.data?.state === 'completed'
                    ? 'bg-blue-100 text-blue-800'
                    : 'bg-red-100 text-red-800'
                }`}
              >
                {run.data?.state}
              </span>
            </div>
            <p className="text-sm font-mono text-primary-600 mb-2">{run.data?.run_id}</p>
            {run.data?.group_name && (
              <p className="text-sm text-gray-600">Group: {run.data.group_name}</p>
            )}
            <p className="text-xs text-gray-500 mt-2">
              {summary.data ? Object.keys(summary.data).length : 0} metrics
            </p>
          </div>
        ))}
      </div>

      {/* Comparison Table */}
      <div className="card mb-6">
        <h2 className="text-xl font-semibold text-gray-900 mb-4">Metrics Comparison</h2>
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider sticky left-0 bg-gray-50 z-10">
                  Metric
                </th>
                {runsData.map(({ runId, run }) => (
                  <th
                    key={runId}
                    className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
                  >
                    <div className="truncate max-w-xs" title={run.data?.run_id}>
                      {run.data?.run_id}
                    </div>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {allMetricKeys.map((key) => {
                const different = isDifferent(key);
                const shouldHighlight = highlightDifferences && different;

                return (
                  <tr
                    key={key}
                    className={shouldHighlight ? 'bg-yellow-50' : 'hover:bg-gray-50'}
                  >
                    <td className="px-4 py-3 text-sm font-mono text-gray-900 sticky left-0 bg-inherit">
                      <button
                        onClick={() => {
                          if (selectedMetrics.includes(key)) {
                            setSelectedMetrics(selectedMetrics.filter((m) => m !== key));
                          } else {
                            setSelectedMetrics([...selectedMetrics, key]);
                          }
                        }}
                        className={`text-left hover:text-primary-600 transition-colors ${
                          selectedMetrics.includes(key) ? 'text-primary-600 font-semibold' : ''
                        }`}
                        title="Click to visualize"
                      >
                        {key}
                      </button>
                    </td>
                    {runsData.map(({ runId, summary }) => {
                      const value = summary.data?.[key];
                      return (
                        <td key={runId} className="px-4 py-3 text-sm text-gray-700">
                          {typeof value === 'number'
                            ? value.toFixed(6)
                            : value === null || value === undefined
                            ? '-'
                            : String(value)}
                        </td>
                      );
                    })}
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Metric Charts */}
      {selectedMetrics.length > 0 && (
        <div className="space-y-6">
          <h2 className="text-xl font-semibold text-gray-900">Selected Metrics</h2>
          {selectedMetrics.map((metricPath) => (
            <MultiMetricChart
              key={metricPath}
              metrics={runIds.map((runId, idx) => ({
                runId,
                metricPath,
                name: runsData[idx].run.data?.run_id || `Run ${runId}`,
              }))}
              title={metricPath}
              height={400}
            />
          ))}
        </div>
      )}

      {selectedMetrics.length === 0 && allMetricKeys.length > 0 && (
        <div className="card text-center py-8">
          <p className="text-gray-500">Click on metric names in the table to visualize them</p>
        </div>
      )}
    </div>
  );
}
