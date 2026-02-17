import { useParams, useNavigate } from 'react-router-dom';
import { useState } from 'react';
import { useRun, useRunSummary, useRunMetrics } from '../api/client';
import { MetricChart } from '../components/Charts';

export default function RunDetailPage() {
  const { runId } = useParams<{ runId: string }>();
  const navigate = useNavigate();
  const [selectedTab, setSelectedTab] = useState<'overview' | 'metrics' | 'config'>('overview');
  const [selectedMetrics, setSelectedMetrics] = useState<string[]>([]);

  const { data: run, isLoading: runLoading } = useRun(parseInt(runId || '0'));
  const { data: summary, isLoading: summaryLoading } = useRunSummary(parseInt(runId || '0'));
  const { data: metricNames, isLoading: metricsLoading } = useRunMetrics(parseInt(runId || '0'));

  const isLoading = runLoading || summaryLoading || metricsLoading;

  if (isLoading) {
    return (
      <div className="p-8">
        <div className="animate-pulse">
          <div className="h-8 bg-gray-200 rounded w-1/4 mb-6"></div>
          <div className="space-y-4">
            <div className="h-32 bg-gray-200 rounded"></div>
            <div className="h-64 bg-gray-200 rounded"></div>
          </div>
        </div>
      </div>
    );
  }

  if (!run) {
    return (
      <div className="p-8">
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-700">
          <h3 className="font-semibold mb-1">Run not found</h3>
          <p className="text-sm">The requested run does not exist.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="p-8">
      {/* Header */}
      <div className="mb-6">
        <div className="flex items-center gap-2 text-sm text-gray-600 mb-2">
          <button
            onClick={() => navigate('/projects')}
            className="hover:text-primary-600 transition-colors"
          >
            Projects
          </button>
          <span>/</span>
          <button
            onClick={() => navigate(`/projects/${run.project_id}/runs`)}
            className="hover:text-primary-600 transition-colors"
          >
            Runs
          </button>
          <span>/</span>
          <span className="text-gray-900">{run.run_id}</span>
        </div>
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">{run.name}</h1>
            <p className="text-gray-600 mt-1">
              <span className="font-mono text-primary-600">{run.run_id}</span>
              {run.group_name && (
                <span className="ml-3 text-gray-500">Group: {run.group_name}</span>
              )}
            </p>
          </div>
          <span
            className={`inline-flex px-3 py-1 text-sm font-semibold rounded-full ${
              run.state === 'running'
                ? 'bg-green-100 text-green-800'
                : run.state === 'completed'
                ? 'bg-blue-100 text-blue-800'
                : 'bg-red-100 text-red-800'
            }`}
          >
            {run.state}
          </span>
        </div>
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200 mb-6">
        <nav className="-mb-px flex space-x-8">
          {['overview', 'metrics', 'config'].map((tab) => (
            <button
              key={tab}
              onClick={() => setSelectedTab(tab as typeof selectedTab)}
              className={`${
                selectedTab === tab
                  ? 'border-primary-500 text-primary-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              } whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm capitalize transition-colors`}
            >
              {tab}
            </button>
          ))}
        </nav>
      </div>

      {/* Tab Content */}
      {selectedTab === 'overview' && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Run Info */}
          <div className="card">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Run Information</h3>
            <dl className="space-y-3">
              <div>
                <dt className="text-sm text-gray-500">Created</dt>
                <dd className="text-sm text-gray-900 mt-1">
                  {new Date(run.created_at).toLocaleString()}
                </dd>
              </div>
              <div>
                <dt className="text-sm text-gray-500">Updated</dt>
                <dd className="text-sm text-gray-900 mt-1">
                  {new Date(run.updated_at).toLocaleString()}
                </dd>
              </div>
              <div>
                <dt className="text-sm text-gray-500">State</dt>
                <dd className="text-sm text-gray-900 mt-1">{run.state}</dd>
              </div>
            </dl>
          </div>

          {/* Summary Stats */}
          {summary && Object.keys(summary).length > 0 && (
            <div className="card lg:col-span-2">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">Summary Metrics</h3>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                {Object.entries(summary).slice(0, 12).map(([key, value]) => (
                  <div key={key}>
                    <dt className="text-xs text-gray-500 truncate" title={key}>
                      {key}
                    </dt>
                    <dd className="text-lg font-semibold text-gray-900 mt-1">
                      {typeof value === 'number' ? value.toFixed(4) : String(value)}
                    </dd>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {selectedTab === 'metrics' && (
        <div className="space-y-6">
          {/* Metric Selector */}
          <div className="card">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">
              Available Metrics ({metricNames?.length || 0})
            </h3>
            {metricNames && metricNames.length > 0 ? (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-2">
                {metricNames.map((metricName) => {
                  const isSelected = selectedMetrics.includes(metricName);
                  return (
                    <button
                      key={metricName}
                      onClick={() => {
                        if (isSelected) {
                          setSelectedMetrics(selectedMetrics.filter((m) => m !== metricName));
                        } else {
                          setSelectedMetrics([...selectedMetrics, metricName]);
                        }
                      }}
                      className={`px-3 py-2 rounded text-sm font-mono text-left transition-colors ${
                        isSelected
                          ? 'bg-primary-100 text-primary-800 border-2 border-primary-500'
                          : 'bg-gray-50 text-gray-700 hover:bg-gray-100 border-2 border-transparent'
                      }`}
                    >
                      {metricName}
                    </button>
                  );
                })}
              </div>
            ) : (
              <p className="text-gray-500 text-center py-8">No metrics found for this run</p>
            )}

            {selectedMetrics.length > 0 && (
              <div className="mt-4 pt-4 border-t border-gray-200">
                <button
                  onClick={() => setSelectedMetrics([])}
                  className="text-sm text-gray-600 hover:text-gray-900 transition-colors"
                >
                  Clear selection ({selectedMetrics.length} selected)
                </button>
              </div>
            )}
          </div>

          {/* Charts for Selected Metrics */}
          {selectedMetrics.length > 0 && (
            <div className="space-y-6">
              {selectedMetrics.map((metricPath) => (
                <MetricChart
                  key={metricPath}
                  runId={parseInt(runId || '0')}
                  metricPath={metricPath}
                  height={400}
                />
              ))}
            </div>
          )}

          {selectedMetrics.length === 0 && metricNames && metricNames.length > 0 && (
            <div className="card text-center py-12">
              <p className="text-gray-500">Click on metrics above to visualize them</p>
            </div>
          )}
        </div>
      )}

      {selectedTab === 'config' && (
        <div className="card">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Configuration</h3>
          {summary && Object.keys(summary).length > 0 ? (
            <div className="bg-gray-50 rounded p-4 font-mono text-sm overflow-x-auto">
              <pre>{JSON.stringify(summary, null, 2)}</pre>
            </div>
          ) : (
            <p className="text-gray-500 text-center py-8">No configuration data available</p>
          )}
        </div>
      )}
    </div>
  );
}
