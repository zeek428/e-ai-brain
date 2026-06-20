import { message as toast } from 'antd';
import { useCallback, useState } from 'react';

import {
  fetchAssistantMetricDetails,
  fetchAssistantMetrics,
  type AssistantMetricDetails,
  type AssistantMetrics,
} from '../../../services/aiBrain';
import { formatMutationError } from '../../../utils/managementCrud';

export function useAssistantMetricsPanel() {
  const [assistantMetrics, setAssistantMetrics] = useState<AssistantMetrics>();
  const [assistantMetricDetails, setAssistantMetricDetails] = useState<AssistantMetricDetails>();
  const [assistantMetricsWindowDays, setAssistantMetricsWindowDays] = useState<number | undefined>();
  const [isLoadingMetricDetails, setIsLoadingMetricDetails] = useState(false);
  const [isLoadingMetrics, setIsLoadingMetrics] = useState(false);
  const [metricsPanelOpened, setMetricsPanelOpened] = useState(false);

  const loadAssistantMetrics = useCallback(async (windowDays = assistantMetricsWindowDays) => {
    setIsLoadingMetrics(true);
    try {
      setAssistantMetrics(await fetchAssistantMetrics({ windowDays }));
    } catch (error) {
      toast.error(formatMutationError(error));
    } finally {
      setIsLoadingMetrics(false);
    }
  }, [assistantMetricsWindowDays]);

  const loadAssistantMetricDetails = useCallback(async (
    metric: string,
    windowDays = assistantMetricsWindowDays,
  ) => {
    setIsLoadingMetricDetails(true);
    try {
      setAssistantMetricDetails(await fetchAssistantMetricDetails({
        limit: 50,
        metric,
        windowDays,
      }));
    } catch (error) {
      toast.error(formatMutationError(error));
    } finally {
      setIsLoadingMetricDetails(false);
    }
  }, [assistantMetricsWindowDays]);

  const changeAssistantMetricsWindow = useCallback((windowDays?: number) => {
    setAssistantMetricsWindowDays(windowDays);
    void loadAssistantMetrics(windowDays);
    if (assistantMetricDetails?.metric) {
      void loadAssistantMetricDetails(assistantMetricDetails.metric, windowDays);
    }
  }, [assistantMetricDetails, loadAssistantMetricDetails, loadAssistantMetrics]);

  const openAssistantMetricDetails = useCallback((metric: string) => {
    void loadAssistantMetricDetails(metric);
  }, [loadAssistantMetricDetails]);

  const openMetricsPanel = useCallback(() => {
    setMetricsPanelOpened(true);
    void loadAssistantMetrics();
  }, [loadAssistantMetrics]);

  return {
    assistantMetricDetails,
    assistantMetrics,
    assistantMetricsWindowDays,
    changeAssistantMetricsWindow,
    isLoadingMetricDetails,
    isLoadingMetrics,
    loadAssistantMetrics,
    metricsPanelOpened,
    openAssistantMetricDetails,
    openMetricsPanel,
    setMetricsPanelOpened,
  };
}
