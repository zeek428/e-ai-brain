import { Alert, Descriptions, Tag } from 'antd';

import type { ProductVersionRecord } from '../../data/management';

type Props = {
  version?: ProductVersionRecord | null;
};

export function RequirementGroupingPanel({ version }: Props) {
  if (!version) {
    return null;
  }
  const planning = version.status === 'planning';
  return (
    <>
      <Alert
        showIcon
        title={planning
          ? '自动归组优先选择兼容的规划版本；只有没有合适版本时才新建版本。并列候选与高风险新建版本会等待人工决策。'
          : '当前不是规划中版本，不能作为自动归组目标。'}
        type={planning ? 'info' : 'warning'}
      />
      <Descriptions bordered column={1} size="small" style={{ marginTop: 12 }}>
        <Descriptions.Item label="候选版本">{version.code} · {version.name}</Descriptions.Item>
        <Descriptions.Item label="归组资格">
          <Tag color={planning ? 'green' : 'default'}>{planning ? '可作为兼容候选' : '不可自动归组'}</Tag>
        </Descriptions.Item>
        <Descriptions.Item label="人工关卡">候选评分并列、范围冲突或高风险新增版本</Descriptions.Item>
      </Descriptions>
    </>
  );
}
