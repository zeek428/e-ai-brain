import { DownOutlined, UpOutlined } from '@ant-design/icons';
import { Button, Modal, Space, Tag, Typography } from 'antd';
import { useState } from 'react';

import { type AssistantReference } from '../../../services/aiBrain';
import {
  assistantReferenceFullChainHref,
  referenceInjectionText,
  referenceMetaText,
  referenceSourceModule,
  referenceSummaryText,
  referenceTypeLabel,
  referenceUpdatedDate,
  selectedReferenceInjectionSummary,
} from './referencePresentation';

const { Text } = Typography;

export type AssistantQueryReferenceResolution = {
  message?: string;
  referenceId: string;
  referenceType: string;
  status: 'failed' | 'loading' | 'resolved';
  title?: string;
};

function queryReferenceResolutionLabel(status: AssistantQueryReferenceResolution['status']) {
  if (status === 'loading') {
    return { color: 'processing', text: '解析中' };
  }
  if (status === 'resolved') {
    return { color: 'green', text: '已带入' };
  }
  return { color: 'red', text: '未带入' };
}

function queryReferenceResolutionText(resolution: AssistantQueryReferenceResolution) {
  const label = referenceTypeLabel(resolution.referenceType);
  if (resolution.status === 'loading') {
    return `正在解析${label}引用：${resolution.referenceId}`;
  }
  if (resolution.status === 'resolved') {
    return `已从链接带入${label}：${resolution.title || resolution.referenceId}`;
  }
  return `引用解析失败：${label} ${resolution.referenceId} ${resolution.message || '不存在或无权限'}`;
}

function AssistantReferenceDetailModal({
  reference,
  onClose,
}: {
  reference?: AssistantReference;
  onClose: () => void;
}) {
  const fullChainHref = reference ? assistantReferenceFullChainHref(reference) : undefined;
  return (
    <Modal
      footer={null}
      open={Boolean(reference)}
      title={`引用摘要 - ${reference?.title ?? '引用'}`}
      width={640}
      onCancel={onClose}
    >
      {reference ? (
        <div className="assistant-reference-detail">
          <div className="assistant-reference-detail-grid">
            <span>
              <Text type="secondary">引用类型</Text>
              <Text>{referenceTypeLabel(reference.type)}</Text>
            </span>
            <span>
              <Text type="secondary">来源模块</Text>
              <Text>{reference.source_module ?? referenceSourceModule(reference.type)}</Text>
            </span>
            <span>
              <Text type="secondary">权限状态</Text>
              <Text>{reference.permission_label ?? '可引用'}</Text>
            </span>
            <span>
              <Text type="secondary">更新时间</Text>
              <Text>{referenceUpdatedDate(reference) ?? '-'}</Text>
            </span>
            <span>
              <Text type="secondary">注入口径</Text>
              <Text>{referenceInjectionText(reference)}</Text>
            </span>
          </div>
          <div className="assistant-reference-detail-section">
            <Text strong>摘要</Text>
            <Text>{referenceSummaryText(reference)}</Text>
          </div>
          <Button href={reference.url} size="small" type="link">
            查看来源
          </Button>
          {fullChainHref ? (
            <Button href={fullChainHref} size="small" type="link">
              查看全链路
            </Button>
          ) : null}
        </div>
      ) : null}
    </Modal>
  );
}

export function AssistantReferenceContext({
  isExpanded,
  queryReferenceResolution,
  selectedReferences,
  onRemoveReference,
  onToggleExpanded,
}: {
  isExpanded: boolean;
  queryReferenceResolution?: AssistantQueryReferenceResolution;
  selectedReferences: AssistantReference[];
  onRemoveReference: (reference: AssistantReference) => void;
  onToggleExpanded: () => void;
}) {
  const [detailReference, setDetailReference] = useState<AssistantReference>();
  const selectedReferenceInjectionText = selectedReferenceInjectionSummary(selectedReferences);
  if (!selectedReferences.length && !queryReferenceResolution) {
    return null;
  }

  return (
    <div
      aria-label="本次上下文"
      className={`assistant-selected-reference-list ${
        isExpanded ? 'assistant-selected-reference-list-expanded' : 'assistant-selected-reference-list-compact'
      }`}
    >
      <div className="assistant-selected-reference-header">
        <Space className="assistant-selected-reference-summary-line" size={6} wrap>
          <Text strong>本次上下文</Text>
          <Tag color={selectedReferences.length ? 'blue' : 'default'}>
            {selectedReferences.length} 个显式引用
          </Tag>
          <Tag color={selectedReferences.length ? 'green' : 'default'}>
            {selectedReferences.length ? selectedReferenceInjectionText : '0 个知识 chunk 注入模型'}
          </Tag>
        </Space>
        <Button
          aria-label={isExpanded ? '收起本次上下文' : '展开本次上下文'}
          icon={isExpanded ? <UpOutlined /> : <DownOutlined />}
          size="small"
          type="text"
          onClick={onToggleExpanded}
        >
          {isExpanded ? '收起' : '展开'}
        </Button>
      </div>
      {queryReferenceResolution ? (
        <div
          aria-label="链接引用状态"
          className={`assistant-query-reference-status assistant-query-reference-status-${queryReferenceResolution.status}`}
        >
          <Space size={6} wrap>
            <Tag color={queryReferenceResolutionLabel(queryReferenceResolution.status).color}>
              {queryReferenceResolutionLabel(queryReferenceResolution.status).text}
            </Tag>
            <Text type={queryReferenceResolution.status === 'failed' ? 'danger' : 'secondary'}>
              {queryReferenceResolutionText(queryReferenceResolution)}
            </Text>
          </Space>
        </div>
      ) : null}
      {!isExpanded && selectedReferences.length ? (
        <div className="assistant-selected-reference-chip-row">
          {selectedReferences.slice(0, 5).map((reference) => (
            <Tag color="blue" key={`${reference.type}:${reference.id}`}>
              {referenceTypeLabel(reference.type)}：{reference.title}
            </Tag>
          ))}
          {selectedReferences.length > 5 ? (
            <Tag color="default">+{selectedReferences.length - 5}</Tag>
          ) : null}
        </div>
      ) : null}
      {isExpanded ? (
        selectedReferences.length ? (
          <div className="assistant-selected-reference-tags">
            {selectedReferences.map((reference) => {
              const fullChainHref = assistantReferenceFullChainHref(reference);
              return (
                <div
                  className="assistant-selected-reference-card"
                  key={`${reference.type}:${reference.id}`}
                >
                  <div className="assistant-selected-reference-card-header">
                    <Space size={6} wrap>
                      <Tag color="blue">{referenceTypeLabel(reference.type)}</Tag>
                      <Text strong>{reference.title}</Text>
                    </Space>
                    <Button
                      aria-label={`移除 ${reference.title}`}
                      size="small"
                      type="text"
                      onClick={() => onRemoveReference(reference)}
                    >
                      移除
                    </Button>
                  </div>
                  <Text className="assistant-selected-reference-meta" type="secondary">
                    {referenceMetaText(reference)}
                  </Text>
                  <Text className="assistant-selected-reference-summary">
                    {referenceSummaryText(reference)}
                  </Text>
                  <Space size={6} wrap>
                    <Tag
                      color={
                        reference.type === 'knowledge_document'
                        || reference.type === 'knowledge_chunk'
                        || reference.type === 'knowledge_folder'
                        || reference.type === 'knowledge_space'
                          ? 'green'
                          : 'default'
                      }
                    >
                      {referenceInjectionText(reference)}
                    </Tag>
                    <Button
                      aria-label={`查看摘要 ${reference.title}`}
                      size="small"
                      onClick={() => setDetailReference(reference)}
                    >
                      查看摘要
                    </Button>
                    <Button href={reference.url} size="small" type="link">
                      查看来源
                    </Button>
                    {fullChainHref ? (
                      <Button href={fullChainHref} size="small" type="link">
                        全链路
                      </Button>
                    ) : null}
                  </Space>
                </div>
              );
            })}
          </div>
        ) : null
      ) : null}
      <AssistantReferenceDetailModal
        reference={detailReference}
        onClose={() => setDetailReference(undefined)}
      />
    </div>
  );
}
