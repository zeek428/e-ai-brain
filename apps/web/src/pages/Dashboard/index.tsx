import { RocketOutlined } from '@ant-design/icons';
import { PageContainer, ProCard } from '@ant-design/pro-components';
import { Typography } from 'antd';

const { Paragraph, Title } = Typography;

export default function DashboardPage() {
  return (
    <PageContainer title={false}>
      <ProCard className="welcome-panel">
        <div className="welcome-mark">
          <RocketOutlined />
        </div>
        <Title level={2}>欢迎使用 AI Brain</Title>
        <Paragraph>从左侧菜单进入任务中心、需求交付、产品资产和运营治理。</Paragraph>
      </ProCard>
    </PageContainer>
  );
}
