import { PlayCircleOutlined, PlusOutlined, ReloadOutlined } from '@ant-design/icons';
import { PageContainer } from '@ant-design/pro-components';
import { Button, Form, Input, InputNumber, Modal, Select, Space, Table, Tabs, Tag, Switch, message } from 'antd';
import { useCallback, useEffect, useState } from 'react';

import {
  createScheduledJob,
  fetchScheduledJobRuns,
  fetchScheduledJobs,
  runScheduledJob,
  type ScheduledJobRecord,
  type ScheduledJobRunRecord,
} from '../../services/aiBrain';

type ScheduledJobFormValues = {
  agent_id?: string;
  cron_expression?: string;
  enabled: boolean;
  execution_mode: string;
  interval_seconds?: number;
  job_type: string;
  name: string;
  product_id?: string;
  schedule_type: string;
  skill_ids?: string;
  source_system: string;
};

const jobTypeOptions = [
  'iteration_plan_suggestion_generate',
  'online_log_ai_analysis',
  'user_usage_metric_collect',
  'user_feedback_collect',
  'online_log_metric_collect',
  'dashboard_snapshot_refresh',
].map((value) => ({ label: value, value }));

export default function ScheduledJobsPage() {
  const [form] = Form.useForm<ScheduledJobFormValues>();
  const [jobs, setJobs] = useState<ScheduledJobRecord[]>([]);
  const [runs, setRuns] = useState<ScheduledJobRunRecord[]>([]);
  const [loading, setLoading] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);

  const reload = useCallback(async () => {
    setLoading(true);
    try {
      const [nextJobs, nextRuns] = await Promise.all([fetchScheduledJobs(), fetchScheduledJobRuns()]);
      setJobs(nextJobs);
      setRuns(nextRuns);
    } catch (error) {
      message.error(error instanceof Error ? error.message : '定时作业加载失败');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void reload();
  }, [reload]);

  const submitJob = async () => {
    const values = await form.validateFields();
    await createScheduledJob({
      ...values,
      skill_ids: values.skill_ids ? values.skill_ids.split(',').map((item) => item.trim()).filter(Boolean) : [],
    });
    message.success('定时作业已创建');
    setModalOpen(false);
    form.resetFields();
    await reload();
  };

  const triggerJob = async (job: ScheduledJobRecord) => {
    await runScheduledJob(job.id);
    message.success('已触发作业运行');
    await reload();
  };

  return (
    <PageContainer title="定时作业">
      <Tabs
        items={[
          {
            key: 'jobs',
            label: '作业配置',
            children: (
              <Table<ScheduledJobRecord>
                loading={loading}
                rowKey="id"
                dataSource={jobs}
                tableLayout="fixed"
                title={() => (
                  <Space>
                    <Button icon={<PlusOutlined />} type="primary" onClick={() => setModalOpen(true)}>
                      新增作业
                    </Button>
                    <Button icon={<ReloadOutlined />} onClick={reload}>
                      刷新
                    </Button>
                  </Space>
                )}
                columns={[
                  { dataIndex: 'name', title: '名称', ellipsis: true },
                  { dataIndex: 'job_type', title: '类型', ellipsis: true },
                  { dataIndex: 'execution_mode', title: '执行模式', width: 150 },
                  { dataIndex: 'schedule_type', title: '调度', width: 120 },
                  { dataIndex: 'next_run_at', title: '下次运行', ellipsis: true, render: (value) => value || '-' },
                  {
                    dataIndex: 'status',
                    title: '状态',
                    width: 120,
                    render: (value, row) => <Tag color={row.enabled ? 'green' : 'default'}>{String(value ?? '-')}</Tag>,
                  },
                  {
                    key: 'actions',
                    title: '操作',
                    width: 140,
                    render: (_, row) => (
                      <Button icon={<PlayCircleOutlined />} onClick={() => triggerJob(row)}>
                        运行
                      </Button>
                    ),
                  },
                ]}
              />
            ),
          },
          {
            key: 'runs',
            label: '运行记录',
            children: (
              <Table<ScheduledJobRunRecord>
                loading={loading}
                rowKey="id"
                dataSource={runs}
                tableLayout="fixed"
                columns={[
                  { dataIndex: 'id', title: '运行 ID', ellipsis: true },
                  { dataIndex: 'scheduled_job_id', title: '作业 ID', ellipsis: true },
                  { dataIndex: 'status', title: '状态', width: 120 },
                  { dataIndex: 'trigger_type', title: '触发方式', width: 120 },
                  { dataIndex: 'collector_run_id', title: '采集运行', ellipsis: true, render: (value) => value || '-' },
                  { dataIndex: 'records_imported', title: '导入数', width: 100 },
                  { dataIndex: 'error_message', title: '错误', ellipsis: true, render: (value) => value || '-' },
                ]}
              />
            ),
          },
        ]}
      />

      <Modal open={modalOpen} title="新增定时作业" onCancel={() => setModalOpen(false)} onOk={submitJob}>
        <Form
          form={form}
          layout="vertical"
          initialValues={{
            enabled: true,
            execution_mode: 'deterministic',
            schedule_type: 'manual',
            source_system: 'ai-brain',
          }}
        >
          <Form.Item label="名称" name="name" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item label="作业类型" name="job_type" rules={[{ required: true }]}>
            <Select options={jobTypeOptions} />
          </Form.Item>
          <Space>
            <Form.Item label="启用" name="enabled" valuePropName="checked">
              <Switch />
            </Form.Item>
            <Form.Item label="执行模式" name="execution_mode">
              <Select
                options={[
                  { label: 'deterministic', value: 'deterministic' },
                  { label: 'ai_assisted', value: 'ai_assisted' },
                  { label: 'ai_generated', value: 'ai_generated' },
                ]}
              />
            </Form.Item>
            <Form.Item label="调度方式" name="schedule_type">
              <Select
                options={[
                  { label: 'manual', value: 'manual' },
                  { label: 'cron', value: 'cron' },
                  { label: 'interval', value: 'interval' },
                ]}
              />
            </Form.Item>
          </Space>
          <Form.Item label="产品 ID" name="product_id">
            <Input />
          </Form.Item>
          <Form.Item label="Agent ID" name="agent_id">
            <Input />
          </Form.Item>
          <Form.Item label="Skill IDs" name="skill_ids">
            <Input placeholder="多个 ID 用英文逗号分隔" />
          </Form.Item>
          <Form.Item label="Cron 表达式" name="cron_expression">
            <Input />
          </Form.Item>
          <Form.Item label="间隔秒数" name="interval_seconds">
            <InputNumber min={1} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item label="来源系统" name="source_system" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
        </Form>
      </Modal>
    </PageContainer>
  );
}
