import { Alert, Button, Card, Descriptions, Spin, Tabs, Tag, Typography } from 'antd';
import { useCallback, useEffect, useMemo, useState } from 'react';

import {
  fetchRdCollaborationRun,
  fetchRdWorkItems,
  type RdCollaborationRun,
  type RdWorkItem,
  type RdWorkItemDependency,
} from '../../services/rdCollaborationClient';
import { formatMutationError } from '../../utils/managementCrud';
import { DecisionPanel } from './DecisionPanel';
import { DeploymentPanel } from './DeploymentPanel';
import { WorkItemDag } from './WorkItemDag';

function readRunId() {
  return new URLSearchParams(window.location.search).get('run_id') ?? undefined;
}

export default function RdCollaborationPage() {
  const runId = readRunId();
  const [run, setRun] = useState<RdCollaborationRun>();
  const [items, setItems] = useState<RdWorkItem[]>([]);
  const [dependencies, setDependencies] = useState<RdWorkItemDependency[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string>();

  const reload = useCallback(async () => {
    if (!runId) {
      setRun(undefined);
      setItems([]);
      setDependencies([]);
      return;
    }
    setLoading(true);
    setError(undefined);
    try {
      const [nextRun, work] = await Promise.all([
        fetchRdCollaborationRun(runId),
        fetchRdWorkItems(runId),
      ]);
      setRun(nextRun);
      setItems(work.items);
      setDependencies(work.dependencies);
    } catch (loadError) {
      setError(formatMutationError(loadError));
    } finally {
      setLoading(false);
    }
  }, [runId]);

  useEffect(() => {
    const timer = globalThis.setTimeout(() => void reload(), 0);
    return () => globalThis.clearTimeout(timer);
  }, [reload]);

  const completedCount = useMemo(
    () => items.filter((item) => item.status === 'completed').length,
    [items],
  );

  return (
    <main>
      <Typography.Title level={2}>研发协同运行</Typography.Title>
      <Typography.Paragraph type="secondary">
        协同运行把版本范围固化为带负责人和依赖关系的工作项。可并行任务由平台调度，审核、返工和超权限问题会停在明确的人类决策点；所有输出继续归因到岗位和冻结策略快照。
      </Typography.Paragraph>
      <Alert
        showIcon
        title="P0 交付边界：开发、测试、质量门禁和远程提交完成后停在待发布。此工作台不提供部署操作。"
        type="info"
      />
      {!runId ? (
        <Card style={{ marginTop: 16 }} title="从迭代版本进入">
          <Alert
            action={<Button href="/delivery/versions" size="small" type="primary">前往迭代版本</Button>}
            description="请从迭代版本总览启动或继续研发协同。版本页会冻结范围和研发执行策略，避免手工输入版本标识绕过版本治理。"
            showIcon
            type="info"
          />
        </Card>
      ) : null}
      {error ? <Alert action={<Button size="small" onClick={() => void reload()}>重试</Button>} style={{ marginTop: 16 }} title={error} type="error" /> : null}
      {runId ? (
        <Spin spinning={loading}>
          <Card style={{ marginTop: 16 }}>
            {run ? (
              <>
                <Descriptions bordered column={2} size="small">
                  <Descriptions.Item label="协同运行">{run.id}</Descriptions.Item>
                  <Descriptions.Item label="状态"><Tag color={run.status === 'completed' ? 'green' : 'blue'}>{run.status}</Tag></Descriptions.Item>
                  <Descriptions.Item label="产品版本">{run.product_version_id}</Descriptions.Item>
                  <Descriptions.Item label="策略快照">{run.strategy_snapshot_id ?? run.policy_snapshot_id ?? '-'}</Descriptions.Item>
                  <Descriptions.Item label="交付终点" span={2}>
                    {run.delivery_target === 'ready_for_release' ? '远程提交后待发布' : '当前工作台不开放该交付终点'}
                  </Descriptions.Item>
                </Descriptions>
                <Tabs
                  style={{ marginTop: 16 }}
                  items={[
                    {
                      key: 'work',
                      label: `工作项 DAG（${completedCount}/${items.length}）`,
                      children: <WorkItemDag dependencies={dependencies} items={items} />,
                    },
                    {
                      key: 'decision',
                      label: '人工决策',
                      children: <DecisionPanel decisionRequestId={run.suspended_decision_request_id} onDecided={() => void reload()} />,
                    },
                  ]}
                />
              </>
            ) : null}
          </Card>
        </Spin>
      ) : null}
      {run ? <DeploymentPanel run={run} /> : null}
    </main>
  );
}
