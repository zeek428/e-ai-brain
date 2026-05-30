import { useCallback, useEffect, useState } from 'react';

export type RemoteRowsError = {
  code?: string;
  message: string;
  traceId?: string;
};

export type RemoteRowsState<Row> = {
  error?: RemoteRowsError;
  rows: Row[];
  status: 'fallback' | 'loading' | 'ready';
};

export type RemoteRowsResult<Row> = RemoteRowsState<Row> & {
  reload: () => Promise<void>;
};

function normalizeError(error: unknown): RemoteRowsError {
  if (error instanceof Error) {
    const errorWithDetails = error as Error & {
      code?: string;
      traceId?: string;
    };
    return {
      code: errorWithDetails.code,
      message: error.message,
      traceId: errorWithDetails.traceId,
    };
  }
  return { message: '接口请求失败' };
}

export function formatRemoteRowsError(error?: RemoteRowsError) {
  if (!error) {
    return undefined;
  }
  const details = [error.code, error.message, error.traceId ? `trace_id=${error.traceId}` : undefined]
    .filter(Boolean)
    .join(' · ');
  return `接口异常，当前展示示例数据${details ? `：${details}` : ''}`;
}

export function useRemoteRows<Row>(
  fallbackRows: Row[],
  loadRows: () => Promise<Row[]>,
): RemoteRowsResult<Row> {
  const [state, setState] = useState<RemoteRowsState<Row>>({
    rows: fallbackRows,
    status: 'loading',
  });

  const reload = useCallback(async () => {
    setState((current) => ({
      rows: current.rows.length ? current.rows : fallbackRows,
      status: 'loading',
    }));

    try {
      const loadedRows = await loadRows();
      setState({ rows: loadedRows, status: 'ready' });
    } catch (error: unknown) {
      setState({
        error: normalizeError(error),
        rows: fallbackRows,
        status: 'fallback',
      });
    }
  }, [fallbackRows, loadRows]);

  useEffect(() => {
    let isCurrent = true;

    loadRows()
      .then((loadedRows) => {
        if (isCurrent) {
          setState({ rows: loadedRows, status: 'ready' });
        }
      })
      .catch((error: unknown) => {
        if (isCurrent) {
          setState({
            error: normalizeError(error),
            rows: fallbackRows,
            status: 'fallback',
          });
        }
      });

    return () => {
      isCurrent = false;
    };
  }, [fallbackRows, loadRows]);

  return { ...state, reload };
}
