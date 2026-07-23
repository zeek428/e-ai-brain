import { Form, Input, InputNumber, Select, Space, Switch, Typography } from 'antd';

import {
  aiExecutorRunnerArchOptions,
  aiExecutorRunnerProtocolOptions,
  aiExecutorRunnerTargetOsOptions,
  aiExecutorRunnerTrustDomainOptions,
  aiExecutorTypeOptions,
  runnerInstallModeOptions,
} from './pluginRunnerHelpers';

export function PluginRunnerFormFields({ editingRunner }: { editingRunner: boolean }) {
  return (
    <>
      <Form.Item label="名称" name="name" rules={[{ required: true, message: '请输入执行器名称' }]}>
        <Input placeholder="Zeek Mac 本地执行器" />
      </Form.Item>
      <Space wrap>
        <Form.Item
          extra="当前本地 Runner 安装包和任务队列闭环使用 Runner Polling；WebSocket/MCP 为预留协议。"
          label="协议"
          name="protocol"
          rules={[{ required: true }]}
        >
          <Select options={aiExecutorRunnerProtocolOptions} style={{ width: 180 }} />
        </Form.Item>
        <Form.Item label="状态" name="status" rules={[{ required: true }]}>
          <Select
            options={[
              { label: 'active', value: 'active' },
              { label: 'offline', value: 'offline' },
              { label: 'disabled', value: 'disabled' },
            ]}
            style={{ width: 150 }}
          />
        </Form.Item>
        <Form.Item label="心跳超时秒数" name="heartbeat_timeout_seconds">
          <InputNumber min={10} style={{ width: 160 }} />
        </Form.Item>
        <Form.Item label="最大并发" name="max_concurrent_tasks">
          <InputNumber min={1} style={{ width: 130 }} />
        </Form.Item>
      </Space>
      <Form.Item label="Endpoint" name="endpoint_url" rules={[{ required: true }]}>
        <Input placeholder="runner://local 或 mcp://runner" />
      </Form.Item>
      <Form.Item label="执行器类型" name="executor_types" rules={[{ required: true, message: '请选择至少一个执行器类型' }]}>
        <Select mode="multiple" options={aiExecutorTypeOptions} />
      </Form.Item>
      <Form.Item
        extra="启用后会固定为部署信任域，只能认领绑定到本机白名单目标的 SSH 或 Docker 部署任务。"
        label="部署执行能力"
        name="deployment_capability"
        valuePropName="checked"
      >
        <Switch aria-label="部署执行能力" />
      </Form.Item>
      <Form.Item noStyle shouldUpdate={(prev, current) => prev.deployment_capability !== current.deployment_capability}>
        {({ getFieldValue }) => {
          const isDeploymentRunner = Boolean(getFieldValue('deployment_capability'));
          return (
            <Form.Item label="运行信任域" name="trust_domain" rules={[{ required: true }]}>
              <Select
                disabled={isDeploymentRunner}
                options={isDeploymentRunner
                  ? aiExecutorRunnerTrustDomainOptions.filter((option) => option.value === 'deployment')
                  : aiExecutorRunnerTrustDomainOptions.filter((option) => option.value !== 'deployment')}
              />
            </Form.Item>
          );
        }}
      </Form.Item>
      <Typography.Text strong>可信证明</Typography.Text>
      <Space wrap>
        <Form.Item
          extra="不同的编码、验证或部署 Runner 必须使用不同的信任边界。"
          label="信任边界 ID"
          name="trust_boundary_id"
        >
          <Input placeholder="例如：ai-brain-coding-boundary" style={{ width: 280 }} />
        </Form.Item>
        <Form.Item
          extra="本地安装包首次启动会用 Runner Token 注册公钥；审核指纹后才可激活。"
          label="可信证明状态"
          name="attestation_status"
        >
          <Select
            options={[
              { label: '待激活（推荐）', value: 'pending' },
              { label: '已激活', value: 'active' },
              { label: '已撤销', value: 'revoked' },
            ]}
            style={{ width: 190 }}
          />
        </Form.Item>
      </Space>
      <Typography.Text strong>执行器命令配置</Typography.Text>
      <Space wrap>
        <Form.Item label="Codex 命令" name="codex_command">
          <Input placeholder="codex" style={{ width: 220 }} />
        </Form.Item>
        <Form.Item label="Claude Code 命令" name="claude_command">
          <Input placeholder="claude" style={{ width: 220 }} />
        </Form.Item>
        <Form.Item label="Hermes 命令" name="hermes_command">
          <Input placeholder="hermes" style={{ width: 220 }} />
        </Form.Item>
        <Form.Item label="OpenClaw 命令" name="openclaw_command">
          <Input placeholder="openclaw" style={{ width: 220 }} />
        </Form.Item>
      </Space>
      <Typography.Text strong>Runner 安装包配置</Typography.Text>
      <Space wrap>
        <Form.Item label="目标系统" name="target_os" rules={[{ required: true, message: '请选择目标系统' }]}>
          <Select options={aiExecutorRunnerTargetOsOptions} style={{ width: 180 }} />
        </Form.Item>
        <Form.Item noStyle shouldUpdate={(prev, current) => prev.package_arch !== current.package_arch}>
          {({ getFieldValue }) => {
            const selectedArch = getFieldValue('package_arch');
            return (
              <Form.Item label="CPU 架构" name="package_arch" rules={[{ required: true, message: '请选择 CPU 架构' }]}>
                <Select
                  labelRender={({ value }) =>
                    aiExecutorRunnerArchOptions.find((option) => option.value === value)?.label ?? String(value)
                  }
                  options={aiExecutorRunnerArchOptions.filter((option) => option.value !== selectedArch)}
                  style={{ width: 250 }}
                />
              </Form.Item>
            );
          }}
        </Form.Item>
        <Form.Item noStyle shouldUpdate={(prev, current) => prev.target_os !== current.target_os}>
          {({ getFieldValue }) => (
            <Form.Item label="安装模式" name="install_mode" rules={[{ required: true, message: '请选择安装模式' }]}>
              <Select
                options={runnerInstallModeOptions(getFieldValue('target_os'))}
                style={{ width: 190 }}
              />
            </Form.Item>
          )}
        </Form.Item>
      </Space>
      <Form.Item label="工作区白名单" name="workspace_roots">
        <Input.TextArea
          placeholder="/Users/zeek/source/e-ai-brain"
          rows={3}
        />
      </Form.Item>
      <Form.Item label="Runner Token" name="runner_token">
        <Input.Password placeholder={editingRunner ? '留空表示不修改 Token' : '留空自动生成'} />
      </Form.Item>
      <Form.Item label="Metadata JSON" name="metadata">
        <Input.TextArea rows={4} placeholder='{"codex_path":"/Applications/Codex.app/Contents/Resources/codex"}' />
      </Form.Item>
    </>
  );
}
