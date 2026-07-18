import { Alert, Button, Card, Descriptions, Form, Input, InputNumber, Spin, Tabs, Tag, Typography, message } from 'antd';
import { useCallback, useEffect, useMemo, useState } from 'react';

import {
  fetchRdCollaborationRun,
  fetchRdWorkItems,
  startRdCollaborationRun,
  type RdCollaborationRun,
  type RdWorkItem,
  type RdWorkItemDependency,
} from '../../services/rdCollaborationClient';
import { formatMutationError } from '../../utils/managementCrud';
import { DecisionPanel } from './DecisionPanel';
import { DeploymentPanel } from './DeploymentPanel';
import { WorkItemDag } from './WorkItemDag';

type StartRunFormValues = {
  scopeVersion: number;
  versionId: string;
};

function readRunId() {
  return new URLSearchParams(window.location.search).get('run_id') ?? undefined;
}

export default function RdCollaborationPage() {
  const [form] = Form.useForm<StartRunFormValues>();
  const [runId, setRunId] = useState(readRunId);
  const [run, setRun] = useState<RdCollaborationRun>();
  const [items, setItems] = useState<RdWorkItem[]>([]);
  const [dependencies, setDependencies] = useState<RdWorkItemDependency[]>([]);
  const [loading, setLoading] = useState(false);
  const [starting, setStarting] = useState(false);
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

  const start = async () => {
    const values = await form.validateFields();
    setStarting(true);
    try {
      const created = await startRdCollaborationRun(values.versionId.trim(), {
        request_id: crypto.randomUUID(),
        scope_version: values.scopeVersion,
      });
      setRunId(created.id);
      window.history.replaceState({}, '', `/delivery/rd-collaboration?run_id=${encodeURIComponent(created.id)}`);
      message.success('研发协作运行已启动，平台将按冻结策略创建并调度工作项');
    } catch (startError) {
      message.error(formatMutationError(startError));
    } finally {
      setStarting(false);
    }
  };

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
        <Card style={{ marginTop: 16 }} title="启动版本协作">
          <Form form={form} layout="inline" initialValues={{ scopeVersion: 1 }}>
            <Form.Item label="规划版本 ID" name="versionId" rules={[{ required: true, whitespace: true }]}>
              <Input placeholder="例如 version_202607" />
            </Form.Item>
            <Form.Item label="范围版本" name="scopeVersion" rules={[{ required: true }]}>
              <InputNumber min={1} />
            </Form.Item>
            <Button loading={starting} type="primary" onClick={() => void start()}>启动协作运行</Button>
          </Form>
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
