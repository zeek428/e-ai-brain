import { EyeOutlined, PictureOutlined, SearchOutlined, UploadOutlined } from '@ant-design/icons';
import { Button, Empty, Image, Modal, Select, Space, Table, Tag, Typography, Upload, message } from 'antd';
import type { ClipboardEvent } from 'react';
import { useMemo, useState } from 'react';

import {
  fetchKnowledgeAssetPreview,
  searchKnowledgeVisuallyWithFile,
  type KnowledgeAssetPreview,
  type KnowledgeProcessingProfileRecord,
  type KnowledgeVisualSearchResultRecord,
} from '../../../services/aiBrain';

const { Text } = Typography;

export function KnowledgeVisualSearchPanel({
  profiles,
}: {
  profiles: KnowledgeProcessingProfileRecord[];
}) {
  const imageProfiles = useMemo(
    () => profiles.filter((profile) => profile.status === 'active' && profile.capabilities.includes('image_embedding')),
    [profiles],
  );
  const [file, setFile] = useState<File>();
  const [profileId, setProfileId] = useState<string>();
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<KnowledgeVisualSearchResultRecord[]>([]);
  const [preview, setPreview] = useState<KnowledgeAssetPreview>();
  const [previewOpen, setPreviewOpen] = useState(false);
  const selectedProfileId = profileId ?? imageProfiles[0]?.id;

  const selectFile = (nextFile: File) => {
    if (!nextFile.type.startsWith('image/')) {
      message.error('请选择图片文件');
      return;
    }
    if (nextFile.size > 10 * 1024 * 1024) {
      message.error('图片不能超过 10 MB');
      return;
    }
    setFile(nextFile);
    setResults([]);
  };

  const handlePaste = (event: ClipboardEvent<HTMLDivElement>) => {
    const image = Array.from(event.clipboardData.files).find((candidate) => candidate.type.startsWith('image/'));
    if (!image) return;
    event.preventDefault();
    selectFile(image);
  };

  const search = async () => {
    if (!file || !selectedProfileId) {
      message.warning(file ? '请选择支持图片向量的处理 Profile' : '请选择或粘贴一张图片');
      return;
    }
    setLoading(true);
    try {
      const response = await searchKnowledgeVisuallyWithFile(file, selectedProfileId);
      setResults(response.items);
    } catch (error) {
      message.error(error instanceof Error ? error.message : '图片检索失败');
    } finally {
      setLoading(false);
    }
  };

  const openPreview = async (assetId?: string) => {
    if (!assetId) {
      message.info('该结果没有可预览的原始图片资产');
      return;
    }
    try {
      const nextPreview = await fetchKnowledgeAssetPreview(assetId);
      setPreview(nextPreview);
      setPreviewOpen(true);
    } catch (error) {
      message.error(error instanceof Error ? error.message : '加载资产预览失败');
    }
  };

  return (
    <section aria-label="图片检索" className="knowledge-visual-search-panel" onPaste={handlePaste}>
      <div className="knowledge-panel-header">
        <div>
          <Text strong>图片检索</Text>
          <Text type="secondary">上传或粘贴图片，按多模态 Profile 生成向量后检索可访问的图片资产。</Text>
        </div>
      </div>
      <Space wrap>
        <Select
          aria-label="图片向量 Profile"
          disabled={!imageProfiles.length}
          onChange={setProfileId}
          options={imageProfiles.map((profile) => ({ label: profile.name, value: profile.id }))}
          placeholder="选择图片向量 Profile"
          style={{ minWidth: 240 }}
          value={selectedProfileId}
        />
        <Upload accept="image/*" beforeUpload={(nextFile) => { selectFile(nextFile); return false; }} maxCount={1} showUploadList={false}>
          <Button icon={<UploadOutlined />}>选择图片</Button>
        </Upload>
        <Button disabled={!imageProfiles.length} icon={<SearchOutlined />} loading={loading} onClick={() => void search()} type="primary">开始检索</Button>
      </Space>
      <div className="knowledge-visual-dropzone" tabIndex={0}>
        <PictureOutlined aria-hidden="true" />
        <span>{file ? `已选择：${file.name}` : '点击“选择图片”，或在此处粘贴截图'}</span>
        {!imageProfiles.length ? <Tag color="gold">尚未配置图片向量 Profile</Tag> : null}
      </div>
      <Table<KnowledgeVisualSearchResultRecord>
        columns={[
          { dataIndex: 'documentId', title: '命中文档', ellipsis: true, width: 210 },
          { dataIndex: 'pageNumber', title: '页码', width: 72, render: (value) => value ?? '-' },
          { dataIndex: 'boundingBox', title: '区域', ellipsis: true, width: 200, render: (value) => Array.isArray(value) ? value.join(', ') : '-' },
          { dataIndex: 'score', title: '相似度', width: 100, render: (value) => `${Math.round(value * 100)}%` },
          { dataIndex: 'assetId', title: '操作', width: 92, render: (value) => <Button icon={<EyeOutlined />} onClick={() => void openPreview(value)} size="small" type="link">预览</Button> },
        ]}
        dataSource={results}
        locale={{ emptyText: loading ? '正在检索图片' : <Empty description="暂无图片检索结果" image={Empty.PRESENTED_IMAGE_SIMPLE} /> }}
        pagination={false}
        rowKey={(row) => `${row.documentId}-${row.assetId ?? ''}-${row.pageNumber ?? ''}-${row.score}`}
        scroll={{ x: 652 }}
        size="small"
      />
      <Modal footer={null} onCancel={() => setPreviewOpen(false)} open={previewOpen} title={preview?.asset.filename ?? '图片资产预览'} width={840}>
        {preview?.previewType === 'image' && preview.contentBase64 ? (
          <Image alt={preview.asset.filename} preview={false} src={`data:${preview.asset.mimeType ?? 'image/png'};base64,${preview.contentBase64}`} style={{ maxHeight: '65vh', objectFit: 'contain', width: '100%' }} />
        ) : <Text type="secondary">当前资产不是可直接预览的图片。</Text>}
      </Modal>
    </section>
  );
}
