import type { FormInstance } from 'antd';
import { Form, Modal } from 'antd';

import { PluginRunnerFormFields } from './PluginRunnerFormFields';
import {
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
      title={isEditing ? '编辑执行器' : '新增执行器'}
      width={760}
    >
      <Form
        form={form}
        initialValues={{
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
        }}
        layout="vertical"
        onValuesChange={(changedValues) => {
          if (!Object.prototype.hasOwnProperty.call(changedValues, 'target_os')) {
            return;
          }
          const targetOs = stringValue(changedValues.target_os, 'linux');
          form.setFieldValue('install_mode', runnerDefaultInstallMode(targetOs));
          if (targetOs === 'manual') {
            form.setFieldValue('package_arch', 'universal');
          } else if (!form.getFieldValue('package_arch')) {
            form.setFieldValue('package_arch', 'amd64');
          }
        }}
      >
        <PluginRunnerFormFields editingRunner={isEditing} />
      </Form>
    </Modal>
  );
}
