import { PageContainer, ProCard } from '@ant-design/pro-components';
import { Tag, Typography } from 'antd';

import { pagePanels, type PagePanelKey } from '../../data/workbench';

const { Paragraph, Title } = Typography;

type ModuleOverviewProps = {
  panelKey: PagePanelKey;
};

export function ModuleOverview({ panelKey }: ModuleOverviewProps) {
  const panel = pagePanels[panelKey];

  return (
    <PageContainer title={false}>
      <ProCard className="capability-list" gutter={[0, 12]} ghost>
        {panel.items.map((item) => (
          <div className="capability-row" key={item.label}>
            <div>
              <Title level={3}>{item.label}</Title>
              <Paragraph>{item.detail}</Paragraph>
            </div>
            <Tag color={item.value === '可用' ? 'green' : 'default'}>{item.value}</Tag>
          </div>
        ))}
      </ProCard>
    </PageContainer>
  );
}
