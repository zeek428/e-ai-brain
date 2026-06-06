import { Alert, Descriptions, Modal, Space } from 'antd';

export type ManagementBatchSkippedItem = {
  code: string;
  id: string;
  message: string;
};

export type ManagementBatchResultSection = {
  items: Array<{
    id: string;
    lines: string[];
  }>;
  title: string;
};

export type ManagementBatchResult = {
  batchId: string;
  primaryCount: number;
  primaryLabel: string;
  secondary?: Array<{ label: string; value: number }>;
  sections?: ManagementBatchResultSection[];
  skipped: ManagementBatchSkippedItem[];
  title: string;
};

type ManagementBatchResultModalProps = {
  onClose: () => void;
  result: ManagementBatchResult | null;
  width?: number;
};

export function ManagementBatchResultModal({
  onClose,
  result,
  width = 720,
}: ManagementBatchResultModalProps) {
  return (
    <Modal
      footer={null}
      onCancel={onClose}
      open={Boolean(result)}
      title={result?.title ?? '批量操作结果'}
      width={width}
    >
      {result ? (
        <Space orientation="vertical" size={16} style={{ width: '100%' }}>
          <Descriptions bordered column={3} size="small">
            <Descriptions.Item label="批次号" span={3}>
              {result.batchId}
            </Descriptions.Item>
            <Descriptions.Item label={result.primaryLabel}>{result.primaryCount}</Descriptions.Item>
            <Descriptions.Item label="跳过数">{result.skipped.length}</Descriptions.Item>
            {result.secondary?.map((item) => (
              <Descriptions.Item key={item.label} label={item.label}>
                {item.value}
              </Descriptions.Item>
            ))}
          </Descriptions>
          {result.sections?.map((section) =>
            section.items.length ? (
              <div className="management-batch-result-list" key={section.title}>
                <div className="management-batch-result-list-title">{section.title}</div>
                {section.items.map((item) => (
                  <div className="management-batch-result-item" key={item.id}>
                    <Space orientation="vertical" size={2}>
                      <strong>{item.id}</strong>
                      {item.lines.map((line, index) => (
                        <span key={`${item.id}-${index}`}>{line}</span>
                      ))}
                    </Space>
                  </div>
                ))}
              </div>
            ) : null,
          )}
          {result.skipped.length ? (
            <div className="management-batch-result-list">
              <div className="management-batch-result-list-title">跳过明细</div>
              {result.skipped.map((item) => (
                <div className="management-batch-result-item" key={`${item.id}-${item.code}`}>
                  <Space orientation="vertical" size={2}>
                    <strong>{item.id}</strong>
                    <span>{item.code} · {item.message}</span>
                  </Space>
                </div>
              ))}
            </div>
          ) : result.sections?.some((section) => section.items.length) ? null : (
            <Alert showIcon title="全部处理成功" type="success" />
          )}
        </Space>
      ) : null}
    </Modal>
  );
}
