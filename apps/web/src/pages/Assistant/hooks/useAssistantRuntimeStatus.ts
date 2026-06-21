import { useCallback, useEffect, useRef, useState } from 'react';

import {
  fetchAssistantRuntimeStatus,
  getStoredCurrentUser,
  type AssistantRuntimeStatus,
} from '../../../services/aiBrain';

export function useAssistantRuntimeStatus() {
  const isMountedRef = useRef(true);
  const [isRefreshingRuntimeStatus, setIsRefreshingRuntimeStatus] = useState(false);
  const [runtimeStatusCheckedAt, setRuntimeStatusCheckedAt] = useState<string>();
  const [runtimeStatus, setRuntimeStatus] = useState<AssistantRuntimeStatus>();

  const refreshRuntimeStatus = useCallback(async () => {
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
    void refreshRuntimeStatus();
    return () => {
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
