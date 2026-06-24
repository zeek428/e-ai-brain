import { Alert, Button, Space, Table, Tag, Typography } from 'antd';

import {
  type PluginActionTrialResult,
  type AiExecutorRunnerRecord,
  type AiExecutorRunnerTestResult,
  type PluginConnectionRecord,
  type PluginConnectionRepairSuggestion,
  type PluginConnectionTestHistoryRecord,
  type PluginConnectionTestResult,
  type PluginMarketplaceItem,
} from '../../../services/aiBrain';
import {
  compactJson,
  connectionTestStatusColor,
  runnerHealthStatusColor,
} from './pluginDiagnosticsHelpers';

function isPlainRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function diagnosticText(value: unknown): string {
  if (value === undefined || value === null || value === '') {
    return '-';
  }
  if (typeof value === 'string' || typeof value === 'number' || typeof value === 'boolean') {
    return String(value);
  }
  return compactJson(value);
}

export function JsonDiagnosticsBlock({ title, value }: { title: string; value?: unknown }) {
  if (value === undefined || value === null) {
    return null;
  }
  return (
    <div>
      <Typography.Text strong>{title}</Typography.Text>
      <pre
        style={{
          background: '#f8fafc',
          border: '1px solid #e5e7eb',
          borderRadius: 6,
          margin: '8px 0 0',
          maxHeight: 260,
          overflow: 'auto',
          padding: 12,
          whiteSpace: 'pre-wrap',
          wordBreak: 'break-word',
        }}
      >
        {compactJson(value)}
      </pre>
    </div>
  );
}

export function TrialWritePreviewBlock({ value }: { value?: PluginActionTrialResult['write_preview'] }) {
  if (!value) {
    return null;
  }
  const writeTargetLabel = value.write_target_label || value.write_target || '-';
  const sampleRecords = value.sample_records ?? [];
  const hasReportPreview = value.report_preview && Object.keys(value.report_preview).length > 0;
  const hasPreviewValue = value.preview_value !== undefined;
  return (
    <Space
      orientation="vertical"
      size={8}
      style={{
        background: '#f8fafc',
        border: '1px solid #e5e7eb',
        borderRadius: 8,
        padding: 12,
        width: '100%',
      }}
    >
      <Typography.Text strong>写入预览</Typography.Text>
      <Space wrap>
        <Tag color="blue">写入目标：{writeTargetLabel}</Tag>
        <Tag color="green">预计写入：{value.records_imported ?? 0}</Tag>
        <Tag>候选记录：{value.candidate_count ?? 0}</Tag>
        {value.source_row_count !== undefined && value.source_row_count !== null ? (
          <Tag>源数据：{value.source_row_count}</Tag>
        ) : null}
      </Space>
      {hasReportPreview ? (
        <>
          <Typography.Text type="secondary">报告字段预览</Typography.Text>
          <pre style={{ margin: 0, whiteSpace: 'pre-wrap' }}>{compactJson(value.report_preview)}</pre>
        </>
      ) : null}
      {sampleRecords.length ? (
        <>
          <Typography.Text type="secondary">样例记录</Typography.Text>
          <pre style={{ margin: 0, whiteSpace: 'pre-wrap' }}>{compactJson(sampleRecords)}</pre>
        </>
      ) : null}
      {hasPreviewValue ? (
        <>
          <Typography.Text type="secondary">预览值</Typography.Text>
          <pre style={{ margin: 0, whiteSpace: 'pre-wrap' }}>{compactJson(value.preview_value)}</pre>
        </>
      ) : null}
    </Space>
  );
}

function marketplaceConnectionSchemaFields(item: PluginMarketplaceItem) {
  return (item.connection_schema?.sections ?? []).flatMap((section) =>
    (section.fields ?? []).map((field) => ({
      ...field,
      sectionTitle: section.title,
    })),
  );
}

export function MarketplaceConnectionSchemaSummary({ item }: { item: PluginMarketplaceItem }) {
  const fields = marketplaceConnectionSchemaFields(item);
  if (!fields.length) {
    return <Typography.Text type="secondary">按默认连接模板配置</Typography.Text>;
  }
  return (
    <Space wrap size={4}>
      {fields.slice(0, 5).map((field) => (
        <Tag color={field.required ? 'orange' : 'default'} key={`${field.sectionTitle}-${field.key}`}>
          {field.label}
        </Tag>
      ))}
      {fields.length > 5 ? <Tag>+{fields.length - 5}</Tag> : null}
    </Space>
  );
}

export function MarketplaceConnectionSchemaDetail({ item }: { item: PluginMarketplaceItem }) {
  const fields = marketplaceConnectionSchemaFields(item);
  if (!fields.length) {
    return <Typography.Text type="secondary">该官方插件暂未声明连接表单 schema，将使用默认连接模板。</Typography.Text>;
  }
  return (
    <Table
      columns={[
        { dataIndex: 'sectionTitle', title: '分组', width: 160 },
        {
          dataIndex: 'label',
          title: '字段',
          width: 180,
          render: (value, row) => (
            <Space size={4}>
              <Typography.Text>{String(value)}</Typography.Text>
              {row.required ? <Tag color="orange">必填</Tag> : null}
              {row.supports_system_variables ? <Tag color="blue">变量</Tag> : null}
            </Space>
          ),
        },
        { dataIndex: 'path', title: '写入路径', width: 260 },
        { dataIndex: 'type', title: '类型', width: 120 },
        { dataIndex: 'description', title: '说明', ellipsis: true },
      ]}
      dataSource={fields}
      pagination={false}
      rowKey={(row) => `${row.sectionTitle}-${row.key}`}
      scroll={{ x: 920 }}
      size="small"
    />
  );
}

export function ConnectionLastTestSummary({ connection }: { connection: PluginConnectionRecord }) {
  const summary = connection.last_test_summary;
  if (!summary?.status) {
    return <Typography.Text type="secondary">未测试</Typography.Text>;
  }
  const detail = summary.error_code
    || summary.failed_step
    || (summary.response_status_code ? `HTTP ${summary.response_status_code}` : undefined)
    || summary.checked_at
    || '-';
  return (
    <Space orientation="vertical" size={2} style={{ width: '100%' }}>
      <Space size={6} wrap>
        <Tag color={connectionTestStatusColor(String(summary.status))}>{summary.status}</Tag>
        {typeof summary.latency_ms === 'number' ? (
          <Typography.Text>{summary.latency_ms}ms</Typography.Text>
        ) : null}
      </Space>
      <Typography.Text
        ellipsis={{ tooltip: summary.error_message || detail }}
        style={{ display: 'block', maxWidth: '100%' }}
        type={summary.status === 'failed' ? 'danger' : 'secondary'}
      >
        {detail}
      </Typography.Text>
    </Space>
  );
}

export function RunnerTestDiagnosticsContent({
  result,
  runner,
}: {
  result: AiExecutorRunnerTestResult;
  runner: AiExecutorRunnerRecord;
}) {
  const resultRunner = result.runner ?? runner;
  return (
    <Space orientation="vertical" size={10} style={{ width: '100%' }}>
      <Space size={8} wrap>
        <Typography.Text strong>{resultRunner.name ?? runner.name}</Typography.Text>
        <Tag color={connectionTestStatusColor(result.status)}>{result.status}</Tag>
        {result.health_status ? (
          <Tag color={runnerHealthStatusColor(result.health_status)}>{result.health_status}</Tag>
        ) : null}
        <Typography.Text type="secondary">
          耗时 {result.latency_ms ?? '-'}ms
        </Typography.Text>
        {result.checked_at ? (
          <Typography.Text type="secondary">
            检测时间 {result.checked_at}
          </Typography.Text>
        ) : null}
      </Space>
      <Table
        columns={[
          { dataIndex: 'name', title: '检查项', width: 190 },
          {
            dataIndex: 'status',
            title: '状态',
            width: 120,
            render: (value: string) => <Tag color={connectionTestStatusColor(value)}>{value}</Tag>,
          },
          {
            dataIndex: 'detail',
            title: '说明',
            render: (value?: string | null) => (
              <Typography.Text style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
                {value ?? '-'}
              </Typography.Text>
            ),
          },
          { dataIndex: 'latency_ms', title: '耗时 ms', width: 100, render: (value?: number | null) => value ?? '-' },
        ]}
        dataSource={result.diagnostics ?? []}
        pagination={false}
        rowKey="name"
        scroll={{ x: 760 }}
        size="small"
      />
    </Space>
  );
}

export function PluginConnectionTestDiagnosticsContent({
  connection,
  onCopyAsActionTemplate,
  result,
}: {
  connection: PluginConnectionRecord;
  result: PluginConnectionTestResult;
  onCopyAsActionTemplate?: () => void;
}) {
  const requestSummary = isPlainRecord(result.request_summary) ? result.request_summary : {};
  const placeholderHeaders = Array.isArray(requestSummary.masked_placeholder_headers)
    ? requestSummary.masked_placeholder_headers.map(String)
    : [];

  return (
    <Space orientation="vertical" size={10} style={{ width: '100%' }}>
      <Typography.Text strong>{connection.name}</Typography.Text>
      <div>
        状态：<Tag color={result.status === 'succeeded' ? 'green' : 'red'}>{result.status}</Tag>
        耗时：{result.latency_ms}ms
      </div>
      {placeholderHeaders.length > 0 ? (
        <Alert
          description={`最终请求仍包含脱敏占位：${placeholderHeaders.join('、')}。请重新填写真实 Header 值，或改用认证配置字段维护 Authorization。`}
          showIcon
          title="Authorization 等敏感 Header 不能使用 *** 占位发起请求"
          type="error"
        />
      ) : null}
      {result.error_message ? (
        <Alert description={result.error_message} showIcon title="错误信息" type="error" />
      ) : null}
      <Table
        columns={[
          { dataIndex: 'name', title: '检查项', width: 190 },
          {
            dataIndex: 'status',
            title: '状态',
            width: 130,
            render: (value: string) => <Tag>{value}</Tag>,
          },
          {
            dataIndex: 'detail',
            title: '说明',
            render: (value?: string) => (
              <Typography.Text style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
                {value ?? '-'}
              </Typography.Text>
            ),
          },
          { dataIndex: 'latency_ms', title: '耗时 ms', width: 100, render: (value?: number) => value ?? '-' },
        ]}
        dataSource={result.diagnostics ?? []}
        pagination={false}
        rowKey="name"
        scroll={{ x: 920 }}
        size="small"
      />
      <ConnectionRequestDebugPanel
        repairSuggestions={result.repair_suggestions}
        requestSummary={requestSummary}
        testHistory={result.test_history}
        onCopyAsActionTemplate={onCopyAsActionTemplate}
      />
      <JsonDiagnosticsBlock title="远端响应信息" value={result.response_summary} />
    </Space>
  );
}

export function ConnectionRequestDebugPanel({
  onCopyAsActionTemplate,
  repairSuggestions = [],
  requestSummary,
  testHistory = [],
}: {
  onCopyAsActionTemplate?: () => void;
  repairSuggestions?: PluginConnectionRepairSuggestion[];
  requestSummary?: unknown;
  testHistory?: PluginConnectionTestHistoryRecord[];
}) {
  if (!isPlainRecord(requestSummary)) {
    return null;
  }
  const headers = isPlainRecord(requestSummary.headers) ? requestSummary.headers : {};
  const headerSources = isPlainRecord(requestSummary.header_sources) ? requestSummary.header_sources : {};
  const headerNames = Array.from(new Set([...Object.keys(headers), ...Object.keys(headerSources)]));
  const headerRows = headerNames.map((name) => ({
    name,
    source: diagnosticText(headerSources[name]),
    value: diagnosticText(headers[name]),
  }));
  const variableResolutions = Array.isArray(requestSummary.variable_resolutions)
    ? requestSummary.variable_resolutions.filter(isPlainRecord)
    : [];
  const variableRows = variableResolutions.map((item, index) => ({
    expression: diagnosticText(item.expression),
    name: diagnosticText(item.name),
    offset_days: item.offset_days === undefined || item.offset_days === null
      ? '-'
      : diagnosticText(item.offset_days),
    path: diagnosticText(item.path),
    resolved_text: diagnosticText(item.resolved_text),
    resolved_value: diagnosticText(item.resolved_value),
    rowKey: `${diagnosticText(item.path)}-${diagnosticText(item.token)}-${index}`,
    status: diagnosticText(item.status),
    token: diagnosticText(item.token),
  }));
  const variableDiffRows = variableRows.map((item) => ({
    after: item.resolved_text,
    before: item.expression,
    path: item.path,
    rowKey: item.rowKey,
    status: item.status,
  }));
  const historyRows = testHistory.map((item, index) => {
    const historyRequest = isPlainRecord(item.request_summary) ? item.request_summary : {};
    const historyResponse = isPlainRecord(item.response_summary) ? item.response_summary : {};
    return {
      action_template_draft: item.action_template_draft,
      checked_at: diagnosticText(item.checked_at),
      error_message: diagnosticText(item.error_message),
      latency_ms: item.latency_ms === undefined || item.latency_ms === null ? '-' : `${item.latency_ms}ms`,
      method: diagnosticText(historyRequest.method),
      repair_suggestions: item.repair_suggestions ?? [],
      request_summary: historyRequest,
      response_status: diagnosticText(historyResponse.status_code),
      response_summary: historyResponse,
      rowKey: `${diagnosticText(item.checked_at)}-${index}`,
      status: diagnosticText(item.status),
      url: diagnosticText(historyRequest.url),
    };
  });
  const curlCommand = diagnosticText(requestSummary.curl_command);

  return (
    <Space orientation="vertical" size={10} style={{ width: '100%' }}>
      <Typography.Text strong>请求调试台</Typography.Text>
      <div
        style={{
          border: '1px solid #e5e7eb',
          borderRadius: 8,
          padding: 12,
        }}
      >
        <Space orientation="vertical" size={8} style={{ width: '100%' }}>
          <div>
            <Typography.Text style={{ color: '#64748b', display: 'block', marginBottom: 4 }}>
              最终请求 URL
            </Typography.Text>
            <Typography.Text copyable style={{ wordBreak: 'break-all' }}>
              {diagnosticText(requestSummary.url)}
            </Typography.Text>
          </div>
          <Space wrap>
            <Tag>Method: {diagnosticText(requestSummary.method)}</Tag>
            <Tag>Protocol: {diagnosticText(requestSummary.protocol)}</Tag>
          </Space>
          {curlCommand !== '-' ? (
            <div>
              <Typography.Text style={{ color: '#64748b', display: 'block', marginBottom: 4 }}>
                可复制 cURL
              </Typography.Text>
              <Typography.Text copyable style={{ wordBreak: 'break-all' }}>
                {curlCommand}
              </Typography.Text>
            </div>
          ) : null}
          <JsonDiagnosticsBlock title="Query 参数" value={requestSummary.query} />
          <JsonDiagnosticsBlock title="请求 Body" value={requestSummary.body} />
        </Space>
      </div>
      <div>
        <Space align="center" style={{ justifyContent: 'space-between', marginBottom: 8, width: '100%' }} wrap>
          <Space size={8} wrap>
            <Typography.Text strong>请求回放台</Typography.Text>
            <Typography.Text type="secondary">最近测试记录</Typography.Text>
          </Space>
          {onCopyAsActionTemplate ? (
            <Button size="small" onClick={onCopyAsActionTemplate}>
              复制为动作模板
            </Button>
          ) : null}
        </Space>
        {historyRows.length > 0 ? (
          <Table
            columns={[
              { dataIndex: 'checked_at', title: '测试时间', width: 190 },
              { dataIndex: 'status', title: '状态', width: 110, render: (value: string) => <Tag>{value}</Tag> },
              { dataIndex: 'latency_ms', title: '耗时', width: 90 },
              { dataIndex: 'method', title: '方法', width: 90 },
              {
                dataIndex: 'url',
                title: '请求 URL',
                render: (value: string) => (
                  <Typography.Text copyable style={{ wordBreak: 'break-word' }}>
                    {value}
                  </Typography.Text>
                ),
              },
              { dataIndex: 'response_status', title: '响应码', width: 100 },
            ]}
            dataSource={historyRows}
            expandable={{
              expandedRowRender: (record) => (
                <Space orientation="vertical" size={8} style={{ width: '100%' }}>
                  <Space orientation="vertical" size={4} style={{ width: '100%' }}>
                    <Typography.Text strong>历史请求详情</Typography.Text>
                    {record.error_message !== '-' ? (
                      <Alert description={record.error_message} showIcon title="历史错误信息" type="error" />
                    ) : null}
                  </Space>
                  {record.repair_suggestions.length > 0 ? (
                    <Space orientation="vertical" size={6} style={{ width: '100%' }}>
                      <Typography.Text strong>历史修复建议</Typography.Text>
                      {record.repair_suggestions.map((suggestion) => (
                        <Alert
                          description={suggestion.detail}
                          key={suggestion.code}
                          showIcon
                          title={suggestion.title}
                          type="warning"
                        />
                      ))}
                    </Space>
                  ) : null}
                  <JsonDiagnosticsBlock title="历史完整请求 JSON" value={record.request_summary} />
                  <JsonDiagnosticsBlock title="历史远端响应信息" value={record.response_summary} />
                  <JsonDiagnosticsBlock title="历史动作模板草案" value={record.action_template_draft} />
                </Space>
              ),
              rowExpandable: () => true,
            }}
            pagination={false}
            rowKey="rowKey"
            scroll={{ x: 980 }}
            size="small"
          />
        ) : (
          <Typography.Text type="secondary">暂无历史测试记录，本次结果会作为第一条回放保存。</Typography.Text>
        )}
      </div>
      {repairSuggestions.length > 0 ? (
        <div>
          <Typography.Text strong>修复建议</Typography.Text>
          <Space orientation="vertical" size={8} style={{ marginTop: 8, width: '100%' }}>
            {repairSuggestions.map((suggestion) => (
              <Alert
                description={suggestion.detail}
                key={suggestion.code}
                showIcon
                title={suggestion.title}
                type="warning"
              />
            ))}
          </Space>
        </div>
      ) : null}
      <div>
        <Space size={8} style={{ marginBottom: 8 }} wrap>
          <Typography.Text strong>动态变量解析</Typography.Text>
          <Tag>Timezone: {diagnosticText(requestSummary.variable_resolution_timezone)}</Tag>
        </Space>
        {variableDiffRows.length > 0 ? (
          <div style={{ marginBottom: 10 }}>
            <Typography.Text strong>变量解析前 / 后差异</Typography.Text>
            <Table
              columns={[
                { dataIndex: 'path', title: '位置', width: 180 },
                {
                  dataIndex: 'before',
                  title: '解析前',
                  render: (value: string) => (
                    <Typography.Text copyable style={{ wordBreak: 'break-word' }}>
                      {value}
                    </Typography.Text>
                  ),
                },
                {
                  dataIndex: 'after',
                  title: '解析后',
                  render: (value: string) => (
                    <Typography.Text copyable style={{ wordBreak: 'break-word' }}>
                      {value}
                    </Typography.Text>
                  ),
                },
                { dataIndex: 'status', title: '状态', width: 110, render: (value: string) => <Tag>{value}</Tag> },
              ]}
              dataSource={variableDiffRows}
              pagination={false}
              rowKey="rowKey"
              scroll={{ x: 760 }}
              size="small"
            />
          </div>
        ) : null}
        {variableRows.length > 0 ? (
          <Table
            columns={[
              { dataIndex: 'path', title: '位置', width: 180 },
              {
                dataIndex: 'expression',
                title: '原始表达式',
                width: 220,
                render: (value: string) => (
                  <Typography.Text style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
                    {value}
                  </Typography.Text>
                ),
              },
              { dataIndex: 'token', title: '变量', width: 160 },
              { dataIndex: 'offset_days', title: '偏移天数', width: 100 },
              {
                dataIndex: 'resolved_value',
                title: '解析值',
                width: 180,
                render: (value: string) => (
                  <Typography.Text copyable style={{ wordBreak: 'break-word' }}>
                    {value}
                  </Typography.Text>
                ),
              },
              {
                dataIndex: 'resolved_text',
                title: '最终值',
                render: (value: string) => (
                  <Typography.Text copyable style={{ wordBreak: 'break-word' }}>
                    {value}
                  </Typography.Text>
                ),
              },
              { dataIndex: 'status', title: '状态', width: 110, render: (value: string) => <Tag>{value}</Tag> },
            ]}
            dataSource={variableRows}
            pagination={false}
            rowKey="rowKey"
            scroll={{ x: 1120 }}
            size="small"
          />
        ) : (
          <Typography.Text type="secondary">未检测到动态变量，当前请求参数按保存值直接发送。</Typography.Text>
        )}
      </div>
      {headerRows.length > 0 ? (
        <div>
          <Typography.Text strong>Header 来源</Typography.Text>
          <Table
            columns={[
              { dataIndex: 'name', title: 'Header', width: 220 },
              {
                dataIndex: 'value',
                title: '最终值',
                render: (value: string) => (
                  <Typography.Text style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
                    {value}
                  </Typography.Text>
                ),
              },
              {
                dataIndex: 'source',
                title: '来源',
                width: 240,
                render: (value: string) => (
                  <Typography.Text style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
                    {value}
                  </Typography.Text>
                ),
              },
            ]}
            dataSource={headerRows}
            pagination={false}
            rowKey="name"
            scroll={{ x: 760 }}
            size="small"
          />
        </div>
      ) : null}
      <JsonDiagnosticsBlock title="原始请求配置" value={requestSummary.original_request_config} />
      <JsonDiagnosticsBlock title="完整请求 JSON" value={requestSummary} />
    </Space>
  );
}
