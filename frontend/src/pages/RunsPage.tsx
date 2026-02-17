import { useParams, useNavigate } from 'react-router-dom';
import { useState, useMemo } from 'react';
import { useProject, useInfiniteRuns } from '../api/client';
import type { RunFilters } from '../api/client';
import VirtualRunsTable from '../components/RunsTable/VirtualRunsTable';

export default function RunsPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const navigate = useNavigate();
  const [filters, setFilters] = useState<RunFilters>({
    project_id: parseInt(projectId || '0'),
  });
  const [sortBy, setSortBy] = useState<string>('created_at');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');
  const [selectedRunIds, setSelectedRunIds] = useState<number[]>([]);

  const { data: project, isLoading: projectLoading } = useProject(parseInt(projectId || '0'));
  const {
    data,
    isLoading: runsLoading,
    error,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
  } = useInfiniteRuns({
    ...filters,
    sort_by: sortBy,
    sort_order: sortOrder,
  });

  // Flatten all pages into a single array of runs
  const runs = useMemo(() => {
    return data?.pages.flatMap((page) => page.runs) ?? [];
  }, [data]);

  const total = data?.pages[0]?.total ?? 0;

  const isLoading = projectLoading || runsLoading;

  const handleSort = (key: string) => {
    if (sortBy === key) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
    } else {
      setSortBy(key);
      setSortOrder('asc');
    }
  };

  if (error) {
    return (
      <div className="p-8">
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-700">
          <h3 className="font-semibold mb-1">Error loading runs</h3>
          <p className="text-sm">{error.message}</p>
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
          <span className="text-gray-900">{project?.name}</span>
        </div>
        <h1 className="text-3xl font-bold text-gray-900">{project?.name}</h1>
        <p className="text-gray-600 mt-1">
          {total} {total === 1 ? 'run' : 'runs'}
        </p>
      </div>

      {/* Filters */}
      <div className="mb-4 flex gap-3 items-center justify-between">
        <div className="flex gap-3">
          <input
            type="text"
            placeholder="Search runs..."
            className="px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
            onChange={(e) =>
              setFilters({ ...filters, search: e.target.value || undefined })
            }
          />
          <select
            className="px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
            onChange={(e) =>
              setFilters({ ...filters, state: e.target.value || undefined })
            }
          >
            <option value="">All States</option>
            <option value="running">Running</option>
            <option value="completed">Completed</option>
            <option value="failed">Failed</option>
          </select>
        </div>

        {selectedRunIds.length > 0 && (
          <div className="flex gap-2 items-center">
            <span className="text-sm text-gray-600">
              {selectedRunIds.length} selected
            </span>
            <button
              onClick={() => navigate(`/compare?runs=${selectedRunIds.join(',')}`)}
              className="btn-primary text-sm"
              disabled={selectedRunIds.length < 2}
            >
              Compare Runs
            </button>
            <button
              onClick={() => setSelectedRunIds([])}
              className="text-sm text-gray-600 hover:text-gray-900 transition-colors"
            >
              Clear
            </button>
          </div>
        )}
      </div>

      {/* Virtual Runs Table */}
      <VirtualRunsTable
        runs={runs}
        isLoading={isLoading}
        hasMore={hasNextPage}
        fetchNextPage={fetchNextPage}
        isFetchingNextPage={isFetchingNextPage}
        onSort={handleSort}
        sortBy={sortBy}
        sortOrder={sortOrder}
        selectable={true}
        selectedRunIds={selectedRunIds}
        onSelectionChange={setSelectedRunIds}
      />
    </div>
  );
}
