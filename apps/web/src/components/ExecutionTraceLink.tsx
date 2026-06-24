import { Button, Typography } from 'antd';
import type { CSSProperties, ReactNode } from 'react';

type ExecutionTraceLinkProps = {
  asButton?: boolean;
  children?: ReactNode;
  fallback?: ReactNode;
  sourceId?: string | null;
  sourceType: string;
  style?: CSSProperties;
  title?: string;
};

function executionTraceHref(sourceId?: string | null, sourceType?: string | null) {
  const normalizedSourceId = String(sourceId ?? '').trim();
  const normalizedSourceType = String(sourceType ?? '').trim();
  if (!normalizedSourceId || !normalizedSourceType) {
    return undefined;
  }
  const params = new URLSearchParams();
  params.set('source_id', normalizedSourceId);
  params.set('source_type', normalizedSourceType);
  return `/governance/execution-traces?${params.toString()}`;
}

export function ExecutionTraceLink({
  asButton = false,
  children,
  fallback = '-',
  sourceId,
  sourceType,
  style,
  title,
}: ExecutionTraceLinkProps) {
  const href = executionTraceHref(sourceId, sourceType);
  if (!href) {
    return <>{fallback}</>;
  }
  const label = children ?? sourceId;
  if (asButton) {
    return (
      <Button href={href} type="link">
        {label}
      </Button>
    );
  }
  return (
    <Typography.Link href={href} style={style} title={title ?? String(sourceId ?? '')}>
      {label}
    </Typography.Link>
  );
}
