import { PageContainer } from '@ant-design/pro-components';
import { Alert, Button, Space, Spin } from 'antd';
import { useCallback, useEffect, useMemo, useState } from 'react';

import { RequirementFullChainView } from '../../components/RequirementFullChainView';
import {
  formatRemoteRowsError,
  normalizeRemoteRowsError,
  type RemoteRowsError,
} from '../../hooks/useRemoteRows';
import {
  fetchRequirementFullChain,
  type RequirementFullChainRecord,
} from '../../services/aiBrain';

function parseRequirementId(pathname: string) {
  const match = pathname.match(/^\/delivery\/requirements\/([^/]+)\/full-chain\/?$/);
  return match?.[1] ? decodeURIComponent(match[1]) : '';
}

export default function RequirementFullChainPage() {
  const requirementId = useMemo(() => parseRequirementId(window.location.pathname), []);
  const [chain, setChain] = useState<RequirementFullChainRecord | null>(null);
  const [error, setError] = useState<RemoteRowsError>();
  const [isLoading, setIsLoading] = useState(true);

  const loadFullChain = useCallback(async () => {
    if (!requirementId) {
      setChain(null);
      setError({ message: '缺少需求 ID' });
      setIsLoading(false);
      return;
    }
    setIsLoading(true);
    setError(undefined);
    try {
      const loadedChain = await fetchRequirementFullChain(requirementId);
      setChain(loadedChain);
    } catch (loadError: unknown) {
      setChain(null);
      setError(normalizeRemoteRowsError(loadError));
    } finally {
      setIsLoading(false);
    }
  }, [requirementId]);

  useEffect(() => {
    void loadFullChain();
  }, [loadFullChain]);

  return (
    <PageContainer
      breadcrumb={{
        items: [
          { title: '需求交付' },
          { title: '需求管理' },
          { title: requirementId || '需求全链路' },
        ],
      }}
      extra={<Button href="/delivery/requirements">返回需求管理</Button>}
      title="需求全链路详情"
    >
      <Spin spinning={isLoading}>
        <Space orientation="vertical" size={16} style={{ width: '100%' }}>
          {error ? <Alert message={formatRemoteRowsError(error)} type="error" /> : null}
          {chain ? <RequirementFullChainView fullChain={chain} /> : null}
        </Space>
      </Spin>
    </PageContainer>
  );
}
