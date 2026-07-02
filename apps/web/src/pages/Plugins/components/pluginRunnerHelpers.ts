export type AiExecutorRunnerFormValues = {
  claude_command?: string;
  codex_command?: string;
  endpoint_url: string;
  executor_types: string[];
  hermes_command?: string;
  heartbeat_timeout_seconds: number;
  install_mode?: string;
  max_concurrent_tasks: number;
  metadata?: string;
  name: string;
  openclaw_command?: string;
  package_arch?: string;
  protocol: string;
  runner_token?: string;
  status: string;
  target_os?: string;
  workspace_roots?: string;
};

export const aiExecutorTypeOptions = [
  { label: 'Codex', value: 'codex' },
  { label: 'Claude Code', value: 'claude' },
  { label: 'Hermes', value: 'hermes' },
  { label: 'OpenClaw', value: 'openclaw' },
];

const aiExecutorCommandFieldByType = new Map([
  ['codex', 'codex_command'],
  ['claude', 'claude_command'],
  ['hermes', 'hermes_command'],
  ['openclaw', 'openclaw_command'],
] as const);

export const aiExecutorRunnerTargetOsOptions = [
  { label: 'Linux', value: 'linux' },
  { label: 'macOS', value: 'macos' },
  { label: 'Windows', value: 'windows' },
  { label: 'Docker', value: 'docker' },
  { label: '通用手动安装', value: 'manual' },
];

export const aiExecutorRunnerArchOptions = [
  { label: 'amd64', value: 'amd64' },
  { label: 'arm64', value: 'arm64' },
  { label: 'universal', value: 'universal' },
];

const defaultInstallModeByTargetOs = new Map([
  ['docker', 'docker'],
  ['linux', 'systemd'],
  ['macos', 'launchd'],
  ['manual', 'manual'],
  ['windows', 'service'],
]);

const installModeOptionsByTargetOs = new Map([
  ['docker', [{ label: 'Docker Compose', value: 'docker' }]],
  ['linux', [
    { label: 'systemd 服务', value: 'systemd' },
    { label: 'Shell 脚本', value: 'shell' },
  ]],
  ['macos', [
    { label: 'launchd 服务', value: 'launchd' },
    { label: 'Shell 脚本', value: 'shell' },
  ]],
  ['manual', [{ label: '手动启动脚本', value: 'manual' }]],
  ['windows', [
    { label: 'Windows Service', value: 'service' },
    { label: 'PowerShell 脚本', value: 'powershell' },
  ]],
]);

export const aiExecutorRunnerProtocolOptions = [
  { label: 'Runner Polling（当前支持）', value: 'runner_polling' },
  { disabled: true, label: 'Runner WebSocket（预留）', value: 'runner_websocket' },
  { disabled: true, label: 'MCP HTTP（预留）', value: 'mcp_http' },
  { disabled: true, label: 'MCP Stdio（预留）', value: 'mcp_stdio' },
];

function runnerStringValue(value: unknown, fallback = '') {
  return typeof value === 'string' ? value : fallback;
}

export function runnerExecutorCommandsFromValues(values: AiExecutorRunnerFormValues): Record<string, string> {
  return Object.fromEntries(
    Array.from(aiExecutorCommandFieldByType.entries())
      .map(([executorType, field]) => [executorType, runnerStringValue(values[field]).trim()] as const)
      .filter(([, command]) => Boolean(command)),
  );
}

export function runnerExecutorCommandsFromMetadata(metadata: Record<string, unknown> | undefined): Record<string, string> {
  const commands =
    typeof metadata?.executor_commands === 'object'
    && metadata.executor_commands !== null
    && !Array.isArray(metadata.executor_commands)
      ? metadata.executor_commands as Record<string, unknown>
      : {};
  return Object.fromEntries(
    Array.from(aiExecutorCommandFieldByType.keys())
      .map((executorType) => [executorType, runnerStringValue(commands[executorType])] as const)
      .filter(([, command]) => Boolean(command)),
  );
}

export function runnerInstallModeOptions(targetOs: unknown) {
  const key = runnerStringValue(targetOs, 'linux');
  return installModeOptionsByTargetOs.get(key) ?? installModeOptionsByTargetOs.get('linux') ?? [];
}

export function runnerDefaultInstallMode(targetOs: unknown) {
  const key = runnerStringValue(targetOs, 'linux');
  return defaultInstallModeByTargetOs.get(key) ?? 'systemd';
}

export function runnerPackageOptionsFromMetadata(metadata: Record<string, unknown> | undefined) {
  const targetOs = runnerStringValue(metadata?.target_os, 'linux');
  return {
    arch: runnerStringValue(metadata?.package_arch, targetOs === 'manual' ? 'universal' : 'amd64'),
    install_mode: runnerStringValue(metadata?.install_mode, runnerDefaultInstallMode(targetOs)),
    target_os: targetOs,
  };
}
