import { message as toast } from 'antd';
import { useCallback, useState } from 'react';

import {
  exportAssistantMetrics,
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
  const [isExportingMetrics, setIsExportingMetrics] = useState(false);
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

  const exportAssistantMetricsFile = useCallback(async () => {
    setIsExportingMetrics(true);
    try {
      const payload = await exportAssistantMetrics({
        format: 'csv',
        windowDays: assistantMetricsWindowDays,
      });
      if (
        typeof document !== 'undefined'
        && typeof URL !== 'undefined'
        && typeof URL.createObjectURL === 'function'
        && typeof payload.content === 'string'
      ) {
        const blob = new Blob([payload.content], { type: payload.contentType || 'text/csv' });
        const href = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = href;
        link.download = payload.filename || 'assistant_metrics.csv';
        document.body.appendChild(link);
        link.click();
        link.remove();
        URL.revokeObjectURL?.(href);
      }
      toast.success('指标已导出');
    } catch (error) {
      toast.error(formatMutationError(error));
    } finally {
      setIsExportingMetrics(false);
    }
  }, [assistantMetricsWindowDays]);

  return {
    assistantMetricDetails,
    assistantMetrics,
    assistantMetricsWindowDays,
    changeAssistantMetricsWindow,
    exportAssistantMetricsFile,
    isExportingMetrics,
    isLoadingMetricDetails,
    isLoadingMetrics,
    loadAssistantMetrics,
    metricsPanelOpened,
    openAssistantMetricDetails,
    openMetricsPanel,
    setMetricsPanelOpened,
  };
}
