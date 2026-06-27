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
  fetchLifecycleFullChain,
  fetchRequirementFullChain,
  type RequirementFullChainRecord,
} from '../../services/aiBrain';

type FullChainTarget = {
  breadcrumbTitle: string;
  subjectId: string;
  subjectType: string;
};

const subjectTypeTitles: Record<string, string> = {
  ai_task: 'AI 任务',
  audit_event: '审计事件',
  bug: 'Bug',
  code_inspection_report: '代码巡检',
  code_review_report: '代码评审',
  gitlab_mr_snapshot: 'PR/MR 快照',
  human_review: '人工确认',
  knowledge_deposit: '知识沉淀',
  product_version: '迭代版本',
  requirement: '需求',
};

function parseFullChainTarget(pathname: string, search: string): FullChainTarget | null {
  const match = pathname.match(/^\/delivery\/requirements\/([^/]+)\/full-chain\/?$/);
  if (match?.[1]) {
    const requirementId = decodeURIComponent(match[1]);
    return {
      breadcrumbTitle: requirementId,
      subjectId: requirementId,
      subjectType: 'requirement',
    };
  }
  if (pathname.replace(/\/$/, '') !== '/delivery/full-chain') {
    return null;
  }
  const params = new URLSearchParams(search);
  const subjectType = params.get('subject_type')?.trim();
  const subjectId = params.get('subject_id')?.trim();
  if (!subjectType || !subjectId) {
    return null;
  }
  return {
    breadcrumbTitle: `${subjectTypeTitles[subjectType] ?? subjectType} · ${subjectId}`,
    subjectId,
    subjectType,
  };
}

export default function RequirementFullChainPage() {
  const target = useMemo(
    () => parseFullChainTarget(window.location.pathname, window.location.search),
    [],
  );
  const [chain, setChain] = useState<RequirementFullChainRecord | null>(null);
  const [error, setError] = useState<RemoteRowsError>();
  const [isLoading, setIsLoading] = useState(Boolean(target));
  const [versionRequirements, setVersionRequirements] = useState<RequirementRecord[]>([]);

  useEffect(() => {
    if (!target) {
      return undefined;
    }
    let isActive = true;
    const loadChain =
      target.subjectType === 'requirement'
        ? fetchRequirementFullChain(target.subjectId)
        : fetchLifecycleFullChain(target.subjectType, target.subjectId);
    void loadChain
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
  }, [target]);

  const visibleError = target ? error : { message: '缺少全链路主体参数' };

  return (
    <PageContainer
      breadcrumb={{
        items: [
          { title: '需求交付' },
          { title: '需求管理' },
          { title: target?.breadcrumbTitle || '需求全链路' },
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
