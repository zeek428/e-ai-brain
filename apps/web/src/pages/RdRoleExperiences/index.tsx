import { Alert, Button, Card, Form, Input, InputNumber, Select, Space, Spin, Table, Tag, Typography, message } from 'antd';
import { useState } from 'react';

import { ApiRequestError } from '../../services/apiClient';
import {
  decideRdRoleExperience,
  fetchRdRoleExperiences,
  type RdRoleExperience,
  type RdRoleExperienceFilters,
} from '../../services/rdRoleExperienceClient';
import { formatMutationError } from '../../utils/managementCrud';

type FilterValues = Omit<RdRoleExperienceFilters, 'page' | 'page_size'>;

const statusOptions = [
  { label: '待审核', value: 'pending' },
  { label: '已批准', value: 'approved' },
  { label: '已拒绝', value: 'rejected' },
  { label: '已退役', value: 'retired' },
];

function scopeTags(values?: string[]) {
  return values?.length ? values.map((value) => <Tag key={value}>{value}</Tag>) : '-';
}

export default function RdRoleExperiencesPage() {
  const [form] = Form.useForm<FilterValues>();
  const [rows, setRows] = useState<RdRoleExperience[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string>();
  const [disabled, setDisabled] = useState(false);

  const load = async (filters: FilterValues) => {
    setLoading(true);
    setDisabled(false);
    setError(undefined);
    try {
      const result = await fetchRdRoleExperiences({ ...filters, page: 1, page_size: 20 });
      setRows(result.items);
      setTotal(result.total);
    } catch (loadError) {
      setRows([]);
      setTotal(0);
      if (loadError instanceof ApiRequestError && loadError.code === 'RD_ROLE_EXPERIENCE_DISABLED') {
        setDisabled(true);
      } else {
        setError(formatMutationError(loadError));
      }
    } finally {
      setLoading(false);
    }
  };

  const decide = async (experience: RdRoleExperience, decision: 'approve' | 'reject' | 'retire') => {
    try {
      const updated = await decideRdRoleExperience(experience.id, {
        decision,
        version: experience.review_version,
      });
      setRows((current) => current.map((row) => (row.id === updated.id ? { ...row, ...updated } : row)));
      message.success('经验审核结论已记录；只有批准版本可在后续协同中作为受控上下文被检索。');
    } catch (decisionError) {
      message.error(formatMutationError(decisionError));
    }
  };

  return (
    <main>
      <Typography.Title level={2}>研发岗位经验沉淀</Typography.Title>
      <Typography.Paragraph type="secondary">
        经验是从岗位反馈派生的候选证据，不是自动执行规则。只有经独立审核批准、范围和可信域均匹配的版本，才会以可追溯上下文参与后续协同。
      </Typography.Paragraph>
      <Card>
        <Form form={form} initialValues={{ status: 'pending' }} layout="vertical" onFinish={(values) => void load(values)}>
          <Space wrap align="start">
            <Form.Item label="状态" name="status"><Select allowClear options={statusOptions} style={{ width: 120 }} /></Form.Item>
            <Form.Item label="业务大脑" name="brain_app_id"><Input style={{ width: 150 }} /></Form.Item>
            <Form.Item label="产品 ID" name="product_id"><Input style={{ width: 150 }} /></Form.Item>
            <Form.Item label="岗位" name="role_code"><Input style={{ width: 130 }} /></Form.Item>
            <Form.Item label="工作项类型" name="work_item_type"><Input style={{ width: 150 }} /></Form.Item>
            <Form.Item label="场景" name="scenario"><Input style={{ width: 130 }} /></Form.Item>
            <Form.Item label="最大风险" name="risk_level"><Input style={{ width: 130 }} /></Form.Item>
            <Form.Item label="仓库可信域" name="repository_trust_domain"><Input style={{ width: 150 }} /></Form.Item>
            <Form.Item label="工具可信域" name="tool_trust_domain"><Input style={{ width: 150 }} /></Form.Item>
            <Form.Item label="最低置信度" name="minimum_confidence"><InputNumber max={1} min={0} step={0.05} /></Form.Item>
            <Form.Item label="经验版本" name="version"><InputNumber min={1} /></Form.Item>
            <Form.Item label="证据主体" name="evidence_subject_id"><Input style={{ width: 150 }} /></Form.Item>
            <Form.Item label=" "><Button htmlType="submit" loading={loading} type="primary">查询经验</Button></Form.Item>
          </Space>
        </Form>
      </Card>
      {disabled ? <Alert style={{ marginTop: 16 }} title="经验沉淀功能当前未启用" type="info" showIcon /> : null}
      {error ? <Alert style={{ marginTop: 16 }} title={error} type="error" showIcon /> : null}
      <Card style={{ marginTop: 16 }} title={`经验候选（${total}）`}>
        <Spin spinning={loading}>
          <Table
            dataSource={rows}
            pagination={false}
            rowKey="id"
            columns={[
              { dataIndex: 'role_code', title: '岗位' },
              { dataIndex: 'work_item_type', title: '工作项' },
              { dataIndex: 'scenario', title: '场景' },
              { dataIndex: ['risk_scope', 'maximum'], title: '最大风险' },
              { dataIndex: 'confidence', title: '置信度', render: (value: number) => `${Math.round(value * 100)}%` },
              { dataIndex: 'repository_trust_domains', title: '仓库可信域', render: scopeTags },
              { dataIndex: 'tool_trust_domains', title: '工具可信域', render: scopeTags },
              { dataIndex: 'content', title: '经验内容', render: (content: Record<string, unknown>) => JSON.stringify(content) },
              { dataIndex: 'review_version', title: '审核版本', render: (version: number) => `v${version}` },
              { dataIndex: 'status', title: '状态', render: (status: string) => <Tag>{status}</Tag> },
              {
                title: '审核',
                render: (_, record: RdRoleExperience) => (
                  <Space>
                    {record.status === 'pending' ? <Button type="link" onClick={() => void decide(record, 'approve')}>批准</Button> : null}
                    {record.status === 'pending' ? <Button danger type="link" onClick={() => void decide(record, 'reject')}>拒绝</Button> : null}
                    {record.status === 'approved' ? <Button danger type="link" onClick={() => void decide(record, 'retire')}>退役</Button> : null}
                  </Space>
                ),
              },
            ]}
          />
        </Spin>
      </Card>
    </main>
  );
}
