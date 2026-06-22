import { useCallback, useEffect, useRef, useState } from 'react';

import {
  fetchAssistantRuntimeStatus,
  getStoredCurrentUser,
  type AssistantRuntimeStatus,
} from '../../../services/aiBrain';

const RUNTIME_STATUS_FOCUS_REFRESH_TTL_MS = 30_000;

type RefreshRuntimeStatusOptions = {
  force?: boolean;
};

export function useAssistantRuntimeStatus() {
  const isMountedRef = useRef(true);
  const lastRefreshAttemptAtRef = useRef(0);
  const [isRefreshingRuntimeStatus, setIsRefreshingRuntimeStatus] = useState(false);
  const [runtimeStatusCheckedAt, setRuntimeStatusCheckedAt] = useState<string>();
  const [runtimeStatus, setRuntimeStatus] = useState<AssistantRuntimeStatus>();

  const refreshRuntimeStatus = useCallback(async (options?: RefreshRuntimeStatusOptions) => {
    const nowMs = Date.now();
    if (
      options?.force !== true
      && nowMs - lastRefreshAttemptAtRef.current < RUNTIME_STATUS_FOCUS_REFRESH_TTL_MS
    ) {
      return;
    }
    lastRefreshAttemptAtRef.current = nowMs;
    if (!getStoredCurrentUser()) {
      if (isMountedRef.current) {
        setRuntimeStatus(undefined);
        setRuntimeStatusCheckedAt(undefined);
      }
      return;
    }
    setIsRefreshingRuntimeStatus(true);
    try {
      const nextStatus = await fetchAssistantRuntimeStatus();
      if (!isMountedRef.current) {
        return;
      }
      setRuntimeStatus(nextStatus);
      setRuntimeStatusCheckedAt(new Date().toISOString());
    } catch {
      if (!isMountedRef.current) {
        return;
      }
      setRuntimeStatus(undefined);
      setRuntimeStatusCheckedAt(new Date().toISOString());
    } finally {
      if (isMountedRef.current) {
        setIsRefreshingRuntimeStatus(false);
      }
    }
  }, []);

  useEffect(() => {
    isMountedRef.current = true;
    const initialRefreshTimer = window.setTimeout(() => {
      void refreshRuntimeStatus({ force: true });
    }, 0);
    return () => {
      window.clearTimeout(initialRefreshTimer);
      isMountedRef.current = false;
    };
  }, [refreshRuntimeStatus]);

  useEffect(() => {
    const refreshOnFocus = () => {
      void refreshRuntimeStatus();
    };
    window.addEventListener('focus', refreshOnFocus);
    return () => window.removeEventListener('focus', refreshOnFocus);
  }, [refreshRuntimeStatus]);

  return {
    isRefreshingRuntimeStatus,
    refreshRuntimeStatus,
    runtimeStatus,
    runtimeStatusCheckedAt,
  };
}
