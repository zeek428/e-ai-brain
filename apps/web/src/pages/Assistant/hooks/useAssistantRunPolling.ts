import { message as toast } from 'antd';
import { useEffect, useMemo, useState } from 'react';

import {
  fetchScheduledJobRuns,
  type ScheduledJobRunRecord,
} from '../../../services/aiBrain';
import { formatMutationError } from '../../../utils/managementCrud';
import type { ChatMessage } from './useAssistantConversation';
import {
  scheduledJobRunPollTargets,
  scheduledJobRunRecordChanged,
} from '../assistantRunPresentation';

const SCHEDULED_JOB_RUN_POLL_INTERVAL_MS = 5000;

export function useAssistantRunPolling(messages: ChatMessage[]) {
  const [scheduledJobRunById, setScheduledJobRunById] = useState<Record<string, ScheduledJobRunRecord>>({});
  const activeRunPollTargets = useMemo(
    () => scheduledJobRunPollTargets(messages, scheduledJobRunById),
    [messages, scheduledJobRunById],
  );

  useEffect(() => {
    if (!activeRunPollTargets.length) {
      return undefined;
    }
    let didCancel = false;
    let didShowError = false;

    const pollRuns = async () => {
      const runIds = [...new Set(activeRunPollTargets.map((target) => target.id))];
      try {
        const runs = await fetchScheduledJobRuns({ runIds });
        if (didCancel || !runs.length) {
          return;
        }
        const targetRunIds = new Set(runIds);
        const relevantRuns = runs.filter((run) => targetRunIds.has(run.id));
        if (!relevantRuns.length) {
          return;
        }
        setScheduledJobRunById((currentItems) => {
          let changed = false;
          const nextItems = { ...currentItems };
          relevantRuns.forEach((run) => {
            if (!scheduledJobRunRecordChanged(currentItems[run.id], run)) {
              return;
            }
            nextItems[run.id] = run;
            changed = true;
          });
          return changed ? nextItems : currentItems;
        });
      } catch (error) {
        if (!didCancel && !didShowError) {
          didShowError = true;
          toast.error(formatMutationError(error));
        }
      }
    };

    void pollRuns();
    const pollTimer = window.setInterval(() => {
      void pollRuns();
    }, SCHEDULED_JOB_RUN_POLL_INTERVAL_MS);
    return () => {
      didCancel = true;
      window.clearInterval(pollTimer);
    };
  }, [activeRunPollTargets]);

  return { scheduledJobRunById };
}
