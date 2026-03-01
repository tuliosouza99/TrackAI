import { useMemo } from 'react';
import Plot from 'react-plotly.js';
import { useMetricValues } from '../../api/client';
import type { MetricValue } from '../../api/client';

interface MetricViewerProps {
  runId: number;
  metricPath: string;
  onClose: () => void;
}

export default function MetricViewer({ runId, metricPath, onClose }: MetricViewerProps) {
  const { data, isLoading, error } = useMetricValues(runId, metricPath);

  const metricAnalysis = useMemo(() => {
    if (!data?.data || data.data.length === 0) {
      return { type: 'empty', values: [] };
    }

    const values = data.data;
    const numericValues = values.filter(
      (v: MetricValue) => typeof v.value === 'number'
    );

    // Single value - show as card
    if (values.length === 1) {
      return {
        type: 'single',
        value: values[0].value,
        step: values[0].step,
        timestamp: values[0].timestamp,
      };
    }

    // Multiple numeric values - show as chart
    if (numericValues.length > 1) {
      const hasSteps = numericValues.some((v: MetricValue) => v.step !== null);
      return {
        type: 'chart',
        values: numericValues,
        hasSteps,
      };
    }

    // Multiple non-numeric or mixed values - show as list
    return {
      type: 'list',
      values,
    };
  }, [data]);

  const chartData = useMemo(() => {
    if (metricAnalysis.type !== 'chart') return [];

    const values = metricAnalysis.values as MetricValue[];
    const hasSteps = metricAnalysis.hasSteps;

    return [
      {
        type: 'scatter',
        mode: 'lines+markers',
        name: metricPath,
        x: hasSteps
          ? values.map((v: MetricValue) => v.step)
          : values.map((_, i: number) => i),
        y: values.map((v: MetricValue) => v.value as number),
        marker: {
          size: 4,
          color: '#1976d2',
        },
        line: {
          color: '#1976d2',
          width: 2,
        },
        hovertemplate: hasSteps
          ? '<b>Step:</b> %{x}<br><b>Value:</b> %{y:.6f}<extra></extra>'
          : '<b>Index:</b> %{x}<br><b>Value:</b> %{y:.6f}<extra></extra>',
      },
    ];
  }, [metricAnalysis, metricPath]);

  const layout = useMemo(() => {
    if (metricAnalysis.type !== 'chart') return {};

    const hasSteps = metricAnalysis.hasSteps;
    return {
      title: metricPath,
      autosize: true,
      height: 400,
      margin: { t: 50, r: 30, b: 50, l: 60 },
      xaxis: {
        title: hasSteps ? 'Step' : 'Index',
        showgrid: true,
        gridcolor: '#e5e7eb',
        zeroline: false,
      },
      yaxis: {
        title: 'Value',
        showgrid: true,
        gridcolor: '#e5e7eb',
        zeroline: false,
      },
      showlegend: false,
      hovermode: 'closest',
      plot_bgcolor: '#ffffff',
      paper_bgcolor: '#ffffff',
    };
  }, [metricAnalysis, metricPath]);

  const config = useMemo(
    () => ({
      responsive: true,
      displayModeBar: true,
      displaylogo: false,
      modeBarButtonsToRemove: ['lasso2d', 'select2d'],
      toImageButtonOptions: {
        format: 'png',
        filename: `${metricPath.replace(/\//g, '_')}_chart`,
        height: 800,
        width: 1200,
        scale: 2,
      },
    }),
    [metricPath]
  );

  if (isLoading) {
    return (
      <div className="card">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-gray-900 font-mono">{metricPath}</h3>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 transition-colors"
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
        <div className="flex items-center justify-center py-12">
          <div className="text-center">
            <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
            <p className="mt-2 text-sm text-gray-600">Loading metric...</p>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="card">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-gray-900 font-mono">{metricPath}</h3>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 transition-colors"
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
        <div className="bg-red-50 rounded-lg border border-red-200 p-4">
          <p className="text-red-700 font-semibold">Error loading metric</p>
          <p className="text-red-600 text-sm mt-1">{error.message}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="card">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-gray-900 font-mono">{metricPath}</h3>
        <button
          onClick={onClose}
          className="text-gray-400 hover:text-gray-600 transition-colors"
        >
          <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      {metricAnalysis.type === 'empty' && (
        <div className="bg-gray-50 rounded-lg border border-gray-200 p-8 text-center">
          <p className="text-gray-500">No data available for this metric</p>
        </div>
      )}

      {metricAnalysis.type === 'single' && (
        <div className="bg-gradient-to-br from-primary-50 to-blue-50 rounded-lg border border-primary-200 p-8">
          <div className="text-center">
            <p className="text-sm text-gray-600 mb-2">Value</p>
            <p className="text-4xl font-bold text-gray-900">
              {typeof metricAnalysis.value === 'number'
                ? metricAnalysis.value.toFixed(6)
                : String(metricAnalysis.value)}
            </p>
            {metricAnalysis.step !== null && (
              <p className="text-sm text-gray-500 mt-4">Step: {metricAnalysis.step}</p>
            )}
            {metricAnalysis.timestamp && (
              <p className="text-sm text-gray-500 mt-1">
                {new Date(metricAnalysis.timestamp).toLocaleString()}
              </p>
            )}
          </div>
        </div>
      )}

      {metricAnalysis.type === 'chart' && chartData.length > 0 && (
        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <Plot data={chartData as any} layout={layout as any} config={config as any} style={{ width: '100%' }} />
        </div>
      )}

      {metricAnalysis.type === 'list' && (
        <div className="bg-gray-50 rounded-lg border border-gray-200 p-4">
          <div className="space-y-2 max-h-96 overflow-y-auto">
            {(metricAnalysis.values as MetricValue[]).map((item, idx) => (
              <div key={idx} className="bg-white rounded p-3 border border-gray-200">
                <div className="flex items-center justify-between">
                  <span className="font-semibold text-gray-900">{String(item.value)}</span>
                  <div className="text-xs text-gray-500">
                    {item.step !== null && <span>Step: {item.step}</span>}
                    {item.timestamp && (
                      <span className="ml-2">{new Date(item.timestamp).toLocaleString()}</span>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
