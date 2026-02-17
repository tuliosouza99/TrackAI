import { useVirtualizer } from '@tanstack/react-virtual';
import { useNavigate } from 'react-router-dom';
import { useRef, useEffect } from 'react';
import type { Run } from '../../api/client';

interface Column {
  key: string;
  label: string;
  width: string;
  render: (run: Run) => React.ReactNode;
}

interface VirtualRunsTableProps {
  runs: Run[];
  isLoading?: boolean;
  hasMore?: boolean;
  fetchNextPage?: () => void;
  isFetchingNextPage?: boolean;
  onSort?: (key: string) => void;
  sortBy?: string;
  sortOrder?: 'asc' | 'desc';
  selectable?: boolean;
  selectedRunIds?: number[];
  onSelectionChange?: (selectedIds: number[]) => void;
}

export default function VirtualRunsTable({
  runs,
  isLoading,
  hasMore,
  fetchNextPage,
  isFetchingNextPage,
  onSort,
  sortBy,
  sortOrder,
  selectable = false,
  selectedRunIds = [],
  onSelectionChange,
}: VirtualRunsTableProps) {
  const navigate = useNavigate();
  const parentRef = useRef<HTMLDivElement>(null);

  const handleToggleSelection = (runId: number) => {
    if (!onSelectionChange) return;

    if (selectedRunIds.includes(runId)) {
      onSelectionChange(selectedRunIds.filter((id) => id !== runId));
    } else {
      onSelectionChange([...selectedRunIds, runId]);
    }
  };

  const handleToggleAll = () => {
    if (!onSelectionChange) return;

    if (selectedRunIds.length === runs.length) {
      onSelectionChange([]);
    } else {
      onSelectionChange(runs.map((r) => r.id));
    }
  };

  const columns: Column[] = selectable
    ? [
        {
          key: 'select',
          label: '',
          width: '50px',
          render: (run) => (
            <input
              type="checkbox"
              checked={selectedRunIds.includes(run.id)}
              onChange={(e) => {
                e.stopPropagation();
                handleToggleSelection(run.id);
              }}
              onClick={(e) => e.stopPropagation()}
              className="w-4 h-4 text-primary-600 rounded border-gray-300 focus:ring-primary-500"
            />
          ),
        },
        {
          key: 'run_id',
      label: 'Run ID',
      width: '150px',
      render: (run) => (
        <span className="text-sm font-medium text-primary-600 font-mono">
          {run.run_id}
        </span>
      ),
    },
    {
      key: 'name',
      label: 'Name',
      width: '250px',
      render: (run) => (
        <span className="text-sm text-gray-900 truncate block" title={run.name}>
          {run.name}
        </span>
      ),
    },
    {
      key: 'group_name',
      label: 'Group',
      width: '200px',
      render: (run) => (
        <span className="text-sm text-gray-600 truncate block" title={run.group_name || '-'}>
          {run.group_name || '-'}
        </span>
      ),
    },
    {
      key: 'state',
      label: 'State',
      width: '120px',
      render: (run) => (
        <span
          className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
            run.state === 'running'
              ? 'bg-green-100 text-green-800'
              : run.state === 'completed'
              ? 'bg-blue-100 text-blue-800'
              : 'bg-red-100 text-red-800'
          }`}
        >
          {run.state}
        </span>
      ),
    },
    {
      key: 'created_at',
      label: 'Created',
      width: '180px',
      render: (run) => (
        <span className="text-sm text-gray-600">
          {new Date(run.created_at).toLocaleString()}
        </span>
      ),
    },
      ]
    : [
        {
          key: 'run_id',
          label: 'Run ID',
          width: '150px',
          render: (run) => (
            <span className="text-sm font-medium text-primary-600 font-mono">
              {run.run_id}
            </span>
          ),
        },
        {
          key: 'name',
          label: 'Name',
          width: '250px',
          render: (run) => (
            <span className="text-sm text-gray-900 truncate block" title={run.name}>
              {run.name}
            </span>
          ),
        },
        {
          key: 'group_name',
          label: 'Group',
          width: '200px',
          render: (run) => (
            <span className="text-sm text-gray-600 truncate block" title={run.group_name || '-'}>
              {run.group_name || '-'}
            </span>
          ),
        },
        {
          key: 'state',
          label: 'State',
          width: '120px',
          render: (run) => (
            <span
              className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
                run.state === 'running'
                  ? 'bg-green-100 text-green-800'
                  : run.state === 'completed'
                  ? 'bg-blue-100 text-blue-800'
                  : 'bg-red-100 text-red-800'
              }`}
            >
              {run.state}
            </span>
          ),
        },
        {
          key: 'created_at',
          label: 'Created',
          width: '180px',
          render: (run) => (
            <span className="text-sm text-gray-600">
              {new Date(run.created_at).toLocaleString()}
            </span>
          ),
        },
      ];

  const rowVirtualizer = useVirtualizer({
    count: hasMore ? runs.length + 1 : runs.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 52, // Height of each row in pixels
    overscan: 5, // Number of rows to render outside viewport
  });

  const virtualItems = rowVirtualizer.getVirtualItems();

  // Infinite scroll: fetch more when scrolling near the end
  useEffect(() => {
    const [lastItem] = [...virtualItems].reverse();

    if (!lastItem) {
      return;
    }

    if (
      lastItem.index >= runs.length - 1 &&
      hasMore &&
      !isFetchingNextPage
    ) {
      fetchNextPage?.();
    }
  }, [
    hasMore,
    fetchNextPage,
    runs.length,
    isFetchingNextPage,
    virtualItems,
  ]);

  const handleHeaderClick = (key: string) => {
    if (onSort) {
      onSort(key);
    }
  };

  if (isLoading && runs.length === 0) {
    return (
      <div className="bg-white rounded-lg border border-gray-200 p-8">
        <div className="animate-pulse space-y-3">
          {[1, 2, 3, 4, 5].map((i) => (
            <div key={i} className="h-12 bg-gray-200 rounded"></div>
          ))}
        </div>
      </div>
    );
  }

  if (runs.length === 0) {
    return (
      <div className="bg-white rounded-lg border border-gray-200 p-12 text-center">
        <p className="text-gray-500 text-lg">No runs found</p>
        <p className="text-gray-400 text-sm mt-2">
          Try adjusting your filters or start a new experiment
        </p>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
      {/* Table Header */}
      <div className="bg-gray-50 border-b border-gray-200 flex items-center" style={{ minWidth: '900px' }}>
        {columns.map((column) => (
          <div
            key={column.key}
            className={`px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider flex items-center gap-1 ${
              onSort && column.key !== 'select' ? 'cursor-pointer hover:bg-gray-100' : ''
            }`}
            style={{ width: column.width, minWidth: column.width }}
            onClick={() => column.key !== 'select' && handleHeaderClick(column.key)}
          >
            {column.key === 'select' ? (
              <input
                type="checkbox"
                checked={runs.length > 0 && selectedRunIds.length === runs.length}
                onChange={handleToggleAll}
                className="w-4 h-4 text-primary-600 rounded border-gray-300 focus:ring-primary-500"
              />
            ) : (
              <>
                <span>{column.label}</span>
                {sortBy === column.key && (
                  <span className="text-primary-600">
                    {sortOrder === 'asc' ? '↑' : '↓'}
                  </span>
                )}
              </>
            )}
          </div>
        ))}
      </div>

      {/* Virtual Scrolling Container */}
      <div
        ref={parentRef}
        className="overflow-auto"
        style={{ height: '600px', minWidth: '900px' }}
      >
        <div
          style={{
            height: `${rowVirtualizer.getTotalSize()}px`,
            width: '100%',
            position: 'relative',
          }}
        >
          {virtualItems.map((virtualRow) => {
            const isLoaderRow = virtualRow.index > runs.length - 1;
            const run = runs[virtualRow.index];

            return (
              <div
                key={virtualRow.index}
                className={`absolute top-0 left-0 w-full flex items-center ${
                  !isLoaderRow
                    ? 'hover:bg-gray-50 cursor-pointer border-b border-gray-200'
                    : ''
                }`}
                style={{
                  height: `${virtualRow.size}px`,
                  transform: `translateY(${virtualRow.start}px)`,
                }}
                onClick={() => !isLoaderRow && navigate(`/runs/${run.id}`)}
              >
                {isLoaderRow ? (
                  <div className="w-full px-6 py-4 text-center text-sm text-gray-500">
                    {isFetchingNextPage ? 'Loading more...' : 'Load more'}
                  </div>
                ) : (
                  <>
                    {columns.map((column) => (
                      <div
                        key={column.key}
                        className="px-6 py-3"
                        style={{ width: column.width, minWidth: column.width }}
                      >
                        {column.render(run)}
                      </div>
                    ))}
                  </>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* Footer with count */}
      <div className="bg-gray-50 border-t border-gray-200 px-6 py-3 text-sm text-gray-600">
        Showing {runs.length} {runs.length === 1 ? 'run' : 'runs'}
        {hasMore && ' (scroll for more)'}
      </div>
    </div>
  );
}
