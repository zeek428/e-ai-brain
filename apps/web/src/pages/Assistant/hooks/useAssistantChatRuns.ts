import { message as toast } from 'antd';
import { useCallback, useEffect, useState } from 'react';

import {
  fetchAssistantChatRuns,
  type AssistantChatRun,
} from '../../../services/aiBrain';
import { formatMutationError } from '../../../utils/managementCrud';

const ASSISTANT_CHAT_RUN_RECOVERY_POLL_INTERVAL_MS = 5000;

export function useAssistantChatRuns({ enabled }: { enabled: boolean }) {
  const [isLoadingChatRuns, setIsLoadingChatRuns] = useState(false);
  const [isRecoveryDismissed, setIsRecoveryDismissed] = useState(false);
  const [recentlyCancelledChatRuns, setRecentlyCancelledChatRuns] = useState<AssistantChatRun[]>([]);
  const [runningChatRuns, setRunningChatRuns] = useState<AssistantChatRun[]>([]);

  const refreshChatRuns = useCallback(async () => {
    if (!enabled) {
      return;
    }
    setIsLoadingChatRuns(true);
    try {
      const [runningRuns, cancelledRuns] = await Promise.all([
        fetchAssistantChatRuns({ limit: 5, status: 'running' }),
        fetchAssistantChatRuns({ limit: 3, status: 'cancelled' }),
      ]);
      setRunningChatRuns(runningRuns);
      setRecentlyCancelledChatRuns(cancelledRuns);
      setIsRecoveryDismissed(false);
    } catch (error) {
      toast.error(formatMutationError(error));
    } finally {
      setIsLoadingChatRuns(false);
    }
  }, [enabled]);

  useEffect(() => {
    if (!enabled) {
      return;
    }
    const refreshTimer = window.setTimeout(() => {
      void refreshChatRuns();
    }, 0);
    return () => window.clearTimeout(refreshTimer);
  }, [enabled, refreshChatRuns]);

  useEffect(() => {
    if (!enabled || !runningChatRuns.length) {
      return;
    }
    const pollTimer = window.setInterval(() => {
      void refreshChatRuns();
    }, ASSISTANT_CHAT_RUN_RECOVERY_POLL_INTERVAL_MS);
    return () => window.clearInterval(pollTimer);
  }, [enabled, refreshChatRuns, runningChatRuns.length]);

  return {
    dismissRunRecovery: () => setIsRecoveryDismissed(true),
    isLoadingChatRuns: enabled ? isLoadingChatRuns : false,
    isRecoveryDismissed: enabled ? isRecoveryDismissed : false,
    recentlyCancelledChatRuns: enabled ? recentlyCancelledChatRuns : [],
    refreshChatRuns,
    runningChatRuns: enabled ? runningChatRuns : [],
  };
}
