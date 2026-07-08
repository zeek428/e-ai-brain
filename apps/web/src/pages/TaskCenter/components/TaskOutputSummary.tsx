import { Tag, Typography } from 'antd';
import type { ReactNode } from 'react';

const { Text } = Typography;

type TaskOutputSummaryProps = {
  compact?: boolean;
  summary: string;
};

type SummaryLine =
  | { kind: 'bullet'; indent: number; text: string }
  | { kind: 'codeBlock'; language?: string; text: string }
  | { kind: 'heading'; text: string }
  | { kind: 'paragraph'; text: string }
  | { kind: 'status'; label: string; value: string };

function normalizeCompactSummary(value: string) {
  let text = value.replace(/\r\n/g, '\n').trim();
  const lineBreakCount = (text.match(/\n/g) ?? []).length;
  if (lineBreakCount < 2) {
    text = text
      .replace(/\s+(\*\*[^*]+?\*\*)/g, '\n\n$1')
      .replace(/\s+-\s+/g, '\n- ');
  }
  return text;
}

function stripMarkdownStrong(value: string) {
  return value.replace(/^\*\*/, '').replace(/\*\*$/, '').trim();
}

function parsePlainSummaryLine(line: string): SummaryLine {
  const bullet = line.match(/^(\s*)-\s+(.+)$/);
  if (bullet) {
    return {
      indent: bullet[1].length > 0 ? 1 : 0,
      kind: 'bullet',
      text: bullet[2].trim(),
    };
  }

  const strongHeading = line.match(/^\*\*(.+?)\*\*$/);
  const plainText = stripMarkdownStrong(line);
  const status = plainText.match(/^(整改状态|执行状态|处理状态)[：:]\s*(.+)$/);
  if (status) {
    return { kind: 'status', label: status[1], value: status[2].trim() };
  }
  if (strongHeading) {
    return { kind: 'heading', text: strongHeading[1].trim() };
  }
  return { kind: 'paragraph', text: plainText };
}

function parseSummaryLines(summary: string): SummaryLine[] {
  const lines: SummaryLine[] = [];
  let codeBlockLanguage: string | undefined;
  let codeBlockLines: string[] = [];

  normalizeCompactSummary(summary)
    .split('\n')
    .map((line) => line.trimEnd())
    .forEach((line) => {
      const fence = line.trim().match(/^```([a-zA-Z0-9_-]+)?$/);
      if (fence && codeBlockLanguage !== undefined) {
        lines.push({
          kind: 'codeBlock',
          language: codeBlockLanguage,
          text: codeBlockLines.join('\n').trim(),
        });
        codeBlockLanguage = undefined;
        codeBlockLines = [];
        return;
      }
      if (codeBlockLanguage !== undefined) {
        codeBlockLines.push(line);
        return;
      }
      if (fence) {
        codeBlockLanguage = fence[1] ?? '';
        codeBlockLines = [];
        return;
      }

      if (line.trim()) {
        lines.push(parsePlainSummaryLine(line));
      }
    });

  if (codeBlockLanguage !== undefined) {
    lines.push({
      kind: 'codeBlock',
      language: codeBlockLanguage,
      text: codeBlockLines.join('\n').trim(),
    });
  }
  return lines;
}

function renderInlineMarkdown(text: string) {
  const nodes: ReactNode[] = [];
  const tokenPattern = /(\[[^\]]+]\([^)]+\)|`[^`]+`|\*\*[^*]+\*\*)/g;
  let cursor = 0;
  let match: RegExpExecArray | null;
  while ((match = tokenPattern.exec(text)) !== null) {
    if (match.index > cursor) {
      nodes.push(text.slice(cursor, match.index));
    }
    const token = match[0];
    const link = token.match(/^\[([^\]]+)]\(([^)]+)\)$/);
    if (link) {
      const href = link[2];
      nodes.push(
        <a
          href={href}
          key={`${token}-${match.index}`}
          rel={href.startsWith('http') ? 'noreferrer' : undefined}
          target={href.startsWith('http') ? '_blank' : undefined}
          title={href}
        >
          {link[1]}
        </a>,
      );
    } else if (token.startsWith('`')) {
      nodes.push(<code key={`${token}-${match.index}`}>{token.slice(1, -1)}</code>);
    } else {
      nodes.push(
        <Text key={`${token}-${match.index}`} strong>
          {token.slice(2, -2)}
        </Text>,
      );
    }
    cursor = match.index + token.length;
  }
  if (cursor < text.length) {
    nodes.push(text.slice(cursor));
  }
  return nodes;
}

function statusColor(value: string) {
  if (/失败|异常|拒绝/.test(value)) {
    return 'error';
  }
  if (/完成|通过|修复|成功/.test(value)) {
    return 'success';
  }
  return 'processing';
}

export function TaskOutputSummary({ compact = false, summary }: TaskOutputSummaryProps) {
  const text = summary.trim();
  if (!text || text === '-') {
    return <Text type="secondary">-</Text>;
  }
  const lines = parseSummaryLines(text);
  return (
    <div
      className={compact ? 'task-output-summary-card task-output-summary-card-compact' : 'task-output-summary-card'}
      data-testid={compact ? 'task-output-summary-preview' : 'task-output-summary-report'}
    >
      {lines.map((line, index) => {
        if (line.kind === 'status') {
          return (
            <div className="task-output-summary-status" key={`${line.kind}-${index}`}>
              <Text type="secondary">{line.label}</Text>
              <Tag color={statusColor(line.value)}>{line.value}</Tag>
            </div>
          );
        }
        if (line.kind === 'heading') {
          return (
            <div className="task-output-summary-heading" key={`${line.kind}-${index}`}>
              {renderInlineMarkdown(line.text)}
            </div>
          );
        }
        if (line.kind === 'bullet') {
          return (
            <div
              className={`task-output-summary-line task-output-summary-bullet${
                line.indent ? ' task-output-summary-bullet-nested' : ''
              }`}
              key={`${line.kind}-${index}`}
            >
              <span>{renderInlineMarkdown(line.text)}</span>
            </div>
          );
        }
        if (line.kind === 'codeBlock') {
          return (
            <pre className="task-output-summary-code-block" key={`${line.kind}-${index}`}>
              <code>{line.text || line.language || '-'}</code>
            </pre>
          );
        }
        return (
          <div className="task-output-summary-line" key={`${line.kind}-${index}`}>
            {renderInlineMarkdown(line.text)}
          </div>
        );
      })}
    </div>
  );
}
