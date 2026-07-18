import { Alert, Button, Descriptions, Drawer, Empty, Form, Input, Modal, Space, Spin, Tag, Typography, message } from 'antd';
import { useCallback, useEffect, useState } from 'react';

import {
  decideRequirementAssessment,
  fetchLatestRequirementAssessment,
  fetchRequirementDetail,
  startRequirementAssessment,
  submitRequirementAssessmentAnswers,
  type RequirementAssessment,
  type RequirementDetail,
} from '../../services/requirementClient';
import { ApiRequestError } from '../../services/apiClient';
import { formatMutationError } from '../../utils/managementCrud';

type Props = {
  onChanged: () => void;
  onClose: () => void;
  open: boolean;
  requirementId?: string;
  requirementTitle?: string;
};

function assessmentStatusLabel(status: string) {
  const labels: Record<string, { color: string; label: string }> = {
    accepted: { color: 'green', label: '已接受，正在归组' },
    evaluating: { color: 'blue', label: '评估中' },
    needs_info: { color: 'orange', label: '待补充信息' },
    rework_required: { color: 'orange', label: '待返工' },
    waiting_human: { color: 'gold', label: '等待人工决策' },
  };
  return labels[status] ?? { color: 'default', label: status };
}

export function RequirementAssessmentDrawer({
  onChanged,
  onClose,
  open,
  requirementId,
  requirementTitle,
}: Props) {
  const [assessment, setAssessment] = useState<RequirementAssessment>();
  const [answerForm] = Form.useForm<{ additionalContext: string }>();
  const [answerOpen, setAnswerOpen] = useState(false);
  const [detail, setDetail] = useState<RequirementDetail>();
  const [error, setError] = useState<string>();
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);

  const load = useCallback(async () => {
    if (!requirementId || !open) {
      return;
    }
    setLoading(true);
    setError(undefined);
    try {
      const requirement = await fetchRequirementDetail(requirementId);
      setDetail(requirement);
      try {
        setAssessment(await fetchLatestRequirementAssessment(requirementId));
      } catch (loadError) {
        if (loadError instanceof ApiRequestError && loadError.status === 404) {
          setAssessment(undefined);
        } else {
          throw loadError;
        }
      }
    } catch (loadError) {
      setError(formatMutationError(loadError));
    } finally {
      setLoading(false);
    }
  }, [open, requirementId]);

  useEffect(() => {
    const timer = globalThis.setTimeout(() => void load(), 0);
    return () => globalThis.clearTimeout(timer);
  }, [load]);

  const start = async () => {
    if (!requirementId || !detail) {
      return;
    }
    setSaving(true);
    try {
      const created = await startRequirementAssessment(requirementId, {
        request_id: crypto.randomUUID(),
        requirement_revision: detail.assessment_revision ?? detail.revision ?? 1,
      });
      setAssessment(created);
      message.success('需求评估已启动，AI 岗位将按冻结策略提出意见');
      onChanged();
    } catch (startError) {
      message.error(formatMutationError(startError));
    } finally {
      setSaving(false);
    }
  };

  const decide = async (decision: 'accept' | 'request_more_info' | 'request_rework') => {
    if (!assessment) {
      return;
    }
    setSaving(true);
    try {
      const updated = await decideRequirementAssessment(assessment.id, {
        decision,
        version: assessment.version,
      });
      setAssessment(updated);
      message.success(decision === 'accept' ? '评估结论已接受，系统将优先归入兼容的规划版本' : '已记录人工处理决定');
      onChanged();
    } catch (decisionError) {
      message.error(formatMutationError(decisionError));
    } finally {
      setSaving(false);
    }
  };

  const submitAnswers = async () => {
    if (!assessment) {
      return;
    }
    const values = await answerForm.validateFields();
    setSaving(true);
    try {
      const updated = await submitRequirementAssessmentAnswers(assessment.id, {
        answers: { additional_context: values.additionalContext.trim() },
        expected_version: assessment.version,
      });
      setAssessment(updated);
      setAnswerOpen(false);
      answerForm.resetFields();
      message.success('补充信息已提交，评估将从冻结版本继续处理');
      onChanged();
    } catch (answerError) {
      message.error(formatMutationError(answerError));
    } finally {
      setSaving(false);
    }
  };

  const status = assessment ? assessmentStatusLabel(assessment.status) : undefined;
  return (
    <Drawer
      destroyOnHidden
      open={open}
      size="large"
      title={`研发需求评估${requirementTitle ? ` · ${requirementTitle}` : ''}`}
      onClose={onClose}
    >
      <Spin spinning={loading}>
        {error ? <Alert action={<Button size="small" onClick={() => void load()}>重试</Button>} title={error} type="error" /> : null}
        {!error && detail && !assessment ? (
          <Space orientation="vertical" size={16} style={{ width: '100%' }}>
            <Alert
              showIcon
              title="评估将冻结当前研发执行策略，并由各岗位输出可追溯的意见。高风险、策略冲突和归组并列会自动停在人工决策点。"
              type="info"
            />
            <Descriptions bordered column={1} size="small">
              <Descriptions.Item label="需求状态">{detail.status}</Descriptions.Item>
              <Descriptions.Item label="评估版本">{detail.assessment_revision ?? detail.revision ?? 1}</Descriptions.Item>
            </Descriptions>
            <Button loading={saving} type="primary" onClick={() => void start()}>启动需求评估</Button>
          </Space>
        ) : null}
        {!error && assessment ? (
          <Space orientation="vertical" size={16} style={{ width: '100%' }}>
            <Alert
              showIcon
              title="评估结果不会直接驱动开发。接受后由平台按策略优先归入兼容的规划版本；无兼容版本时才创建新版本。"
              type="info"
            />
            <Descriptions bordered column={1} size="small">
              <Descriptions.Item label="评估状态"><Tag color={status?.color}>{status?.label}</Tag></Descriptions.Item>
              <Descriptions.Item label="策略快照">{assessment.id}</Descriptions.Item>
              <Descriptions.Item label="需求修订">{assessment.requirement_revision}</Descriptions.Item>
              <Descriptions.Item label="意见轮次">{assessment.opinion_round ?? 1}</Descriptions.Item>
            </Descriptions>
            <Typography.Title level={5}>岗位意见</Typography.Title>
            {assessment.opinions?.length ? assessment.opinions.map((opinion) => (
              <Descriptions key={opinion.role_code} bordered column={1} size="small">
                <Descriptions.Item label="岗位">{opinion.role_code}</Descriptions.Item>
                <Descriptions.Item label="结论">{opinion.outcome_code ?? '待输出'}</Descriptions.Item>
                <Descriptions.Item label="风险">{opinion.risk_level ?? '-'}</Descriptions.Item>
                <Descriptions.Item label="置信度">{opinion.confidence ?? '-'}</Descriptions.Item>
              </Descriptions>
            )) : <Empty description="等待岗位意见" image={Empty.PRESENTED_IMAGE_SIMPLE} />}
            {assessment.status === 'waiting_human' ? (
              <Space wrap>
                <Button loading={saving} type="primary" onClick={() => void decide('accept')}>接受评估并归组</Button>
                <Button loading={saving} onClick={() => void decide('request_more_info')}>要求补充信息</Button>
                <Button loading={saving} onClick={() => void decide('request_rework')}>要求重新评估</Button>
              </Space>
            ) : null}
            {assessment.status === 'needs_info' ? (
              <Button loading={saving} onClick={() => setAnswerOpen(true)}>补充评估信息</Button>
            ) : null}
          </Space>
        ) : null}
      </Spin>
      <Modal
        confirmLoading={saving}
        open={answerOpen}
        title="补充评估信息"
        onCancel={() => setAnswerOpen(false)}
        onOk={() => void submitAnswers()}
        okText="提交补充信息"
      >
        <Form form={answerForm} layout="vertical">
          <Form.Item label="补充说明" name="additionalContext" rules={[{ required: true, whitespace: true, message: '请填写补充说明' }]}>
            <Input.TextArea autoSize={{ minRows: 4, maxRows: 10 }} placeholder="补充业务范围、目标用户、约束条件或验收事实" />
          </Form.Item>
        </Form>
      </Modal>
    </Drawer>
  );
}
