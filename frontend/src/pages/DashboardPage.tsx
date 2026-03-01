import { useParams, useNavigate } from 'react-router-dom';
import { useState, useEffect, useRef } from 'react';
import { Responsive } from 'react-grid-layout';
import type { Layout } from 'react-grid-layout';
import 'react-grid-layout/css/styles.css';
import 'react-resizable/css/styles.css';
import { useProject } from '../api/client';
import MetricCardWidget from '../components/Dashboard/MetricCardWidget';
import ChartWidget from '../components/Dashboard/ChartWidget';
import RecentRunsWidget from '../components/Dashboard/RecentRunsWidget';

interface Widget {
  i: string;
  type: 'metric-card' | 'chart' | 'recent-runs';
  config: {
    runId?: number;
    metricPath?: string;
    title?: string;
    projectId?: number;
  };
}

export default function DashboardPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const navigate = useNavigate();
  const { data: project, isLoading: projectLoading } = useProject(parseInt(projectId || '0'));

  const containerRef = useRef<HTMLDivElement>(null);
  const [width, setWidth] = useState(1200);

  useEffect(() => {
    const updateWidth = () => {
      if (containerRef.current) {
        setWidth(containerRef.current.offsetWidth);
      }
    };
    updateWidth();
    window.addEventListener('resize', updateWidth);
    return () => window.removeEventListener('resize', updateWidth);
  }, []);

  // Default dashboard widgets
  const [widgets, setWidgets] = useState<Widget[]>([
    {
      i: 'recent-runs',
      type: 'recent-runs',
      config: { projectId: parseInt(projectId || '0') },
    },
    {
      i: 'metric-1',
      type: 'metric-card',
      config: { runId: 1, metricPath: 'train/acc', title: 'Training Accuracy' },
    },
    {
      i: 'chart-1',
      type: 'chart',
      config: { runId: 1, metricPath: 'train/loss', title: 'Training Loss' },
    },
  ]);

  const [layouts, setLayouts] = useState<any>({
    lg: [
      { i: 'recent-runs', x: 0, y: 0, w: 4, h: 4 },
      { i: 'metric-1', x: 4, y: 0, w: 2, h: 2 },
      { i: 'chart-1', x: 6, y: 0, w: 6, h: 4 },
    ],
  });

  const [isEditMode, setIsEditMode] = useState(false);

  const renderWidget = (widget: Widget) => {
    switch (widget.type) {
      case 'metric-card':
        return (
          <MetricCardWidget
            runId={widget.config.runId!}
            metricPath={widget.config.metricPath!}
            title={widget.config.title}
          />
        );
      case 'chart':
        return (
          <ChartWidget
            runId={widget.config.runId!}
            metricPath={widget.config.metricPath!}
            title={widget.config.title}
          />
        );
      case 'recent-runs':
        return <RecentRunsWidget projectId={widget.config.projectId!} />;
      default:
        return <div className="h-full bg-gray-100 rounded p-4">Unknown widget type</div>;
    }
  };

  const handleLayoutChange = (_layout: Layout, allLayouts: any) => {
    setLayouts(allLayouts);
  };

  const handleAddWidget = () => {
    const newWidget: Widget = {
      i: `widget-${Date.now()}`,
      type: 'metric-card',
      config: { runId: 1, metricPath: 'train/acc', title: 'New Metric' },
    };

    setWidgets([...widgets, newWidget]);

    // Add layout for the new widget
    const newLayout = {
      i: newWidget.i,
      x: 0,
      y: Infinity, // Place at the bottom
      w: 2,
      h: 2,
    };

    setLayouts({
      ...layouts,
      lg: [...(layouts.lg || []), newLayout],
    });
  };

  const handleRemoveWidget = (widgetId: string) => {
    setWidgets(widgets.filter((w) => w.i !== widgetId));
    setLayouts({
      ...layouts,
      lg: (layouts.lg || []).filter((l: any) => l.i !== widgetId),
    });
  };

  const handleSaveDashboard = () => {
    const dashboardData = {
      widgets,
      layouts,
    };
    localStorage.setItem(`dashboard-${projectId}`, JSON.stringify(dashboardData));
    alert('Dashboard saved!');
  };

  const handleLoadDashboard = () => {
    const saved = localStorage.getItem(`dashboard-${projectId}`);
    if (saved) {
      const dashboardData = JSON.parse(saved);
      setWidgets(dashboardData.widgets);
      setLayouts(dashboardData.layouts);
      alert('Dashboard loaded!');
    } else {
      alert('No saved dashboard found');
    }
  };

  if (projectLoading) {
    return (
      <div className="p-8">
        <div className="animate-pulse">
          <div className="h-8 bg-gray-200 rounded w-1/4 mb-6"></div>
          <div className="grid grid-cols-3 gap-4">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-48 bg-gray-200 rounded"></div>
            ))}
          </div>
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
            onClick={() => navigate(`/projects/${projectId}/runs`)}
            className="hover:text-primary-600 transition-colors"
          >
            {project?.name}
          </button>
          <span>/</span>
          <span className="text-gray-900">Dashboard</span>
        </div>
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Dashboard</h1>
            <p className="text-gray-600 mt-1">{project?.name}</p>
          </div>
          <div className="flex gap-2">
            <button onClick={handleLoadDashboard} className="btn-secondary text-sm">
              Load
            </button>
            <button onClick={handleSaveDashboard} className="btn-secondary text-sm">
              Save
            </button>
            <button onClick={handleAddWidget} className="btn-secondary text-sm">
              + Add Widget
            </button>
            <button
              onClick={() => setIsEditMode(!isEditMode)}
              className={`px-4 py-2 text-sm rounded-md transition-colors ${
                isEditMode
                  ? 'bg-primary-600 text-white'
                  : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
              }`}
            >
              {isEditMode ? 'Done Editing' : 'Edit Mode'}
            </button>
          </div>
        </div>
      </div>

      {/* Grid Layout */}
      <div ref={containerRef}>
        {/* @ts-ignore */}
        <Responsive
          className="layout"
          layouts={layouts}
          breakpoints={{ lg: 1200, md: 996, sm: 768, xs: 480, xxs: 0 }}
          cols={{ lg: 12, md: 10, sm: 6, xs: 4, xxs: 2 }}
          rowHeight={100}
          width={width}
          onLayoutChange={handleLayoutChange}
          isDraggable={isEditMode}
          isResizable={isEditMode}
          draggableHandle=".widget-drag-handle"
        >
          {widgets.map((widget) => (
            <div key={widget.i} className="relative">
              {isEditMode && (
                <div className="absolute top-0 left-0 right-0 z-10 bg-gray-800 bg-opacity-90 text-white px-2 py-1 flex items-center justify-between widget-drag-handle cursor-move">
                  <span className="text-xs font-medium">{widget.type}</span>
                  <button
                    onClick={() => handleRemoveWidget(widget.i)}
                    className="text-red-300 hover:text-red-100 text-xs"
                  >
                    ✕
                  </button>
                </div>
              )}
              <div className={isEditMode ? 'mt-6' : ''}>{renderWidget(widget)}</div>
            </div>
          ))}
        </Responsive>
      </div>

      {widgets.length === 0 && (
        <div className="card text-center py-12 mt-6">
          <p className="text-gray-500 text-lg">No widgets on this dashboard</p>
          <button onClick={handleAddWidget} className="mt-4 btn-primary">
            Add Your First Widget
          </button>
        </div>
      )}
    </div>
  );
}
