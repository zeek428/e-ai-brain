import type { FormInstance } from 'antd';
import { Form, Modal } from 'antd';

import { PluginRunnerFormFields } from './PluginRunnerFormFields';
import {
  runnerDefaultPackageArch,
  runnerDefaultInstallMode,
  type AiExecutorRunnerFormValues,
} from './pluginRunnerHelpers';

type PluginRunnerModalProps = {
  form: FormInstance<AiExecutorRunnerFormValues>;
  isEditing: boolean;
  onCancel: () => void;
  onSubmit: () => void | Promise<void>;
  open: boolean;
};

function stringValue(value: unknown, fallback = '') {
  return typeof value === 'string' ? value : fallback;
}

export function PluginRunnerModal({
  form,
  isEditing,
  onCancel,
  onSubmit,
  open,
}: PluginRunnerModalProps) {
  return (
    <Modal
      cancelText="取消"
      okText="确定"
      onCancel={onCancel}
      onOk={() => void onSubmit()}
      open={open}
      style={{ maxWidth: 'calc(100vw - 32px)' }}
      styles={{ body: { maxHeight: '70vh', overflowY: 'auto' } }}
      title={isEditing ? '编辑执行器' : '新增执行器'}
      width={760}
    >
      <Form
        form={form}
        initialValues={{
          attestation_status: 'pending',
          endpoint_url: 'runner://local',
          executor_types: ['codex', 'openclaw'],
          heartbeat_timeout_seconds: 120,
          install_mode: 'systemd',
          max_concurrent_tasks: 1,
          metadata: '{}',
          package_arch: 'amd64',
          protocol: 'runner_polling',
          status: 'active',
          target_os: 'linux',
          trust_boundary_id: '',
          trust_domain: 'coding',
        }}
        layout="vertical"
        onValuesChange={(changedValues) => {
          if (Object.prototype.hasOwnProperty.call(changedValues, 'deployment_capability')) {
            form.setFieldValue(
              'trust_domain',
              changedValues.deployment_capability ? 'deployment' : 'coding',
            );
          }
          if (Object.prototype.hasOwnProperty.call(changedValues, 'target_os')) {
            const targetOs = stringValue(changedValues.target_os, 'linux');
            form.setFieldsValue({
              install_mode: runnerDefaultInstallMode(targetOs),
              package_arch: runnerDefaultPackageArch(targetOs),
            });
          }
        }}
      >
        <PluginRunnerFormFields editingRunner={isEditing} />
      </Form>
    </Modal>
  );
}
