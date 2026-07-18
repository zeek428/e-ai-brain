import { Button, Card, Empty, Form, Input, Modal, Select, Space, Tag, Typography, message } from 'antd';
import { useState } from 'react';

import type {
  CreateRdRolePayload,
  RdAiEmployee,
  RdExecutorProfile,
  RdPolicyRoleBinding,
  RdRoleDefinition,
} from '../../services/rdCollaborationClient';
import { createRdRole } from '../../services/rdCollaborationClient';
import { formatMutationError } from '../../utils/managementCrud';

type Props = {
  aiEmployees: RdAiEmployee[];
  executorProfiles: RdExecutorProfile[];
  onChange: (bindings: RdPolicyRoleBinding[]) => void;
  onRoleCreated: (role: RdRoleDefinition) => void;
  roles: RdRoleDefinition[];
  value?: RdPolicyRoleBinding[];
};

const actorModeOptions = [
  { label: 'AI 数字员工', value: 'ai' },
  { label: '真人账号', value: 'human' },
  { label: '人机协同', value: 'hybrid' },
];

function activeBindingForRole(roleCode: string, bindings: RdPolicyRoleBinding[]) {
  return bindings.find((binding) => binding.role_code === roleCode);
}

function idsFromText(value: string) {
  return value.split(/[，,]/).map((item) => item.trim()).filter(Boolean);
}

type RoleFormValues = {
  capabilities: string;
  code: string;
  name: string;
  responsibilities: string;
  risk: CreateRdRolePayload['maximum_risk_level'];
};

export function PolicyRoleBindings({
  aiEmployees,
  executorProfiles,
  onChange,
  onRoleCreated,
  roles,
  value = [],
}: Props) {
  const [roleForm] = Form.useForm<RoleFormValues>();
  const [roleModalOpen, setRoleModalOpen] = useState(false);
  const [roleSaving, setRoleSaving] = useState(false);
  const activeRoles = roles.filter((role) => role.status === 'active');
  const selectedRoleCodes = value.map((binding) => binding.role_code);

  const updateRoleSelection = (roleCodes: string[]) => {
    const next = roleCodes.map((roleCode) => {
      const existing = activeBindingForRole(roleCode, value);
      const role = activeRoles.find((item) => item.code === roleCode);
      const matchingProfile = executorProfiles.find(
        (profile) => profile.status === 'active' && profile.supported_role_codes.includes(roleCode),
      );
      return (
        existing ?? {
          actor_mode: role?.assignable_subject_types.includes('ai_employee') ? 'ai' : 'human',
          candidate_ai_employee_ids: [],
          primary_executor_profile_id: matchingProfile?.id ?? null,
          role_code: roleCode,
          status: 'active',
        } as RdPolicyRoleBinding
      );
    });
    onChange(next);
  };

  const updateBinding = (roleCode: string, changes: Partial<RdPolicyRoleBinding>) => {
    onChange(
      value.map((binding) =>
        binding.role_code === roleCode ? { ...binding, ...changes } : binding,
      ),
    );
  };

  const createRole = async () => {
    const values = await roleForm.validateFields();
    setRoleSaving(true);
    try {
      const role = await createRdRole({
        assignable_subject_types: ['human_user', 'ai_employee'],
        capabilities: idsFromText(values.capabilities),
        code: values.code.trim(),
        maximum_risk_level: values.risk,
        name: values.name.trim(),
        responsibilities: idsFromText(values.responsibilities),
      });
      onRoleCreated(role);
      setRoleModalOpen(false);
      roleForm.resetFields();
      message.success('岗位已新增，可立即加入研发执行策略');
    } catch (error) {
      message.error(formatMutationError(error));
    } finally {
      setRoleSaving(false);
    }
  };

  return (
    <Card size="small" title="岗位与交付主体">
      <Typography.Paragraph type="secondary">
        每个岗位配置一位责任主体。平台使用这份配置冻结策略快照；AI 只负责提出工作计划，不能自行绕过岗位、权限或人工关卡。
      </Typography.Paragraph>
      <Space.Compact style={{ width: '100%' }}>
        <Select
          aria-label="参与岗位"
          mode="multiple"
          options={activeRoles.map((role) => ({
            label: `${role.name}（${role.code}）`,
            value: role.code,
          }))}
          placeholder="选择本策略需要的岗位"
          style={{ width: '100%' }}
          value={selectedRoleCodes}
          onChange={updateRoleSelection}
        />
        <Button onClick={() => setRoleModalOpen(true)}>新增岗位</Button>
      </Space.Compact>
      {!value.length ? (
        <Empty description="至少选择一个岗位并配置责任主体" image={Empty.PRESENTED_IMAGE_SIMPLE} />
      ) : (
        <Space orientation="vertical" size="middle" style={{ marginTop: 16, width: '100%' }}>
          {value.map((binding) => {
            const role = activeRoles.find((item) => item.code === binding.role_code);
            const profiles = executorProfiles.filter(
              (profile) =>
                profile.status === 'active' && profile.supported_role_codes.includes(binding.role_code),
            );
            return (
              <Card key={binding.role_code} size="small" type="inner" title={role?.name ?? binding.role_code}>
                <Space orientation="vertical" style={{ width: '100%' }}>
                  <Space wrap>
                    <Tag color="blue">{binding.role_code}</Tag>
                    <Tag>{role?.maximum_risk_level ?? 'unknown'} 风险上限</Tag>
                  </Space>
                  <Select
                    aria-label={`${binding.role_code} 主体模式`}
                    options={actorModeOptions.filter((option) =>
                      role?.assignable_subject_types.includes(
                        option.value === 'ai' ? 'ai_employee' : 'human_user',
                      ) || option.value === 'hybrid',
                    )}
                    value={binding.actor_mode}
                    onChange={(actor_mode) => updateBinding(binding.role_code, { actor_mode })}
                  />
                  {binding.actor_mode !== 'ai' ? (
                    <Input
                      aria-label={`${binding.role_code} 真人账号`}
                      placeholder="真人账号 ID（以逗号分隔）"
                      value={(binding.candidate_human_user_ids ?? []).join(', ')}
                      onChange={(event) =>
                        updateBinding(binding.role_code, {
                          candidate_human_user_ids: idsFromText(event.target.value),
                        })
                      }
                    />
                  ) : null}
                  {binding.actor_mode !== 'human' ? (
                    <Select
                      aria-label={`${binding.role_code} AI数字员工`}
                      mode="multiple"
                      options={aiEmployees
                        .filter((employee) => employee.status === 'active')
                        .map((employee) => ({
                          label: `${employee.name}（${employee.code}）`,
                          value: employee.id,
                        }))}
                      placeholder="可选 AI 数字员工"
                      value={binding.candidate_ai_employee_ids ?? []}
                      onChange={(candidate_ai_employee_ids) =>
                        updateBinding(binding.role_code, { candidate_ai_employee_ids })
                      }
                    />
                  ) : null}
                  {binding.actor_mode !== 'human' ? (
                    <Select
                      aria-label={`${binding.role_code} 执行配置`}
                      allowClear
                      options={profiles.map((profile) => ({
                        label: `${profile.name}（${profile.executor_type}）`,
                        value: profile.id,
                      }))}
                      placeholder="选择经过准入的执行配置"
                      value={binding.primary_executor_profile_id ?? undefined}
                      onChange={(primary_executor_profile_id) =>
                        updateBinding(binding.role_code, { primary_executor_profile_id: primary_executor_profile_id ?? null })
                      }
                    />
                  ) : null}
                  <Button size="small" type="link" onClick={() => updateRoleSelection(selectedRoleCodes.filter((code) => code !== binding.role_code))}>
                    移除岗位
                  </Button>
                </Space>
              </Card>
            );
          })}
        </Space>
      )}
      <Modal
        destroyOnHidden
        open={roleModalOpen}
        title="新增研发岗位"
        confirmLoading={roleSaving}
        onCancel={() => setRoleModalOpen(false)}
        onOk={() => void createRole()}
      >
        <Form form={roleForm} initialValues={{ risk: 'medium' }} layout="vertical">
          <Form.Item label="岗位名称" name="name" rules={[{ required: true, whitespace: true }]}><Input /></Form.Item>
          <Form.Item label="岗位编码" name="code" rules={[{ required: true, whitespace: true }]}><Input placeholder="例如 security_reviewer" /></Form.Item>
          <Form.Item label="能力" name="capabilities" rules={[{ required: true, whitespace: true }]}><Input placeholder="以逗号分隔" /></Form.Item>
          <Form.Item label="职责" name="responsibilities" rules={[{ required: true, whitespace: true }]}><Input placeholder="以逗号分隔" /></Form.Item>
          <Form.Item label="风险上限" name="risk" rules={[{ required: true }]}>
            <Select options={['low', 'medium', 'high', 'critical'].map((value) => ({ label: value, value }))} />
          </Form.Item>
        </Form>
      </Modal>
    </Card>
  );
}
