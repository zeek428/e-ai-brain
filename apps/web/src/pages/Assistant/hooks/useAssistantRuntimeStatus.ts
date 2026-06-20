import { useEffect, useState } from 'react';

import {
  fetchAssistantRuntimeStatus,
  getStoredCurrentUser,
  type AssistantRuntimeStatus,
} from '../../../services/aiBrain';

export function useAssistantRuntimeStatus() {
  const [runtimeStatus, setRuntimeStatus] = useState<AssistantRuntimeStatus>();

  useEffect(() => {
    if (!getStoredCurrentUser()) {
      return undefined;
    }
    let didCancel = false;
    fetchAssistantRuntimeStatus()
      .then((status) => {
        if (!didCancel) {
          setRuntimeStatus(status);
        }
      })
      .catch(() => {
        if (!didCancel) {
          setRuntimeStatus(undefined);
        }
      });
    return () => {
      didCancel = true;
    };
  }, []);

  return runtimeStatus;
}
