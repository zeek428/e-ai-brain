import { PageContainer } from '@ant-design/pro-components';
import { Alert, Button, Space, Spin } from 'antd';
import { useEffect, useMemo, useState } from 'react';

import { RequirementFullChainView } from '../../components/RequirementFullChainView';
import type { RequirementRecord } from '../../data/management';
import {
  formatRemoteRowsError,
  normalizeRemoteRowsError,
  type RemoteRowsError,
} from '../../hooks/useRemoteRows';
import {
  fetchManagementRequirementList,
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
  const [isLoading, setIsLoading] = useState(Boolean(requirementId));
  const [versionRequirements, setVersionRequirements] = useState<RequirementRecord[]>([]);

  useEffect(() => {
    if (!requirementId) {
      return undefined;
    }
    let isActive = true;
    void fetchRequirementFullChain(requirementId)
      .then(async (loadedChain) => {
        if (!isActive) {
          return;
        }
        setChain(loadedChain);
        setError(undefined);
        if (!loadedChain.iterationVersion?.id) {
          setVersionRequirements([]);
          return;
        }
        try {
          const requirements = await fetchManagementRequirementList({
            page: 1,
            pageSize: 100,
            sortField: 'created_at',
            sortOrder: 'descend',
            versionId: loadedChain.iterationVersion.id,
          });
          if (isActive) {
            setVersionRequirements(requirements.rows);
          }
        } catch {
          if (isActive) {
            setVersionRequirements([]);
          }
        }
      })
      .catch((loadError: unknown) => {
        if (!isActive) {
          return;
        }
        setChain(null);
        setError(normalizeRemoteRowsError(loadError));
        setVersionRequirements([]);
      })
      .finally(() => {
        if (isActive) {
          setIsLoading(false);
        }
      });
    return () => {
      isActive = false;
    };
  }, [requirementId]);

  const visibleError = requirementId ? error : { message: '缺少需求 ID' };

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
          {visibleError ? <Alert message={formatRemoteRowsError(visibleError)} type="error" /> : null}
          {chain ? <RequirementFullChainView fullChain={chain} versionRequirements={versionRequirements} /> : null}
        </Space>
      </Spin>
    </PageContainer>
  );
}
