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
  | { kind: 'status'; label: string; value: string }
  | { headers: string[]; kind: 'table'; rows: string[][] };

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

function markdownTableCells(line: string) {
  const normalized = line.trim();
  if (!normalized.startsWith('|')) {
    return undefined;
  }
  const body = normalized.replace(/^\|/, '').replace(/\|$/, '');
  const cells = body.split('|').map((cell) => cell.trim());
  return cells.length ? cells : undefined;
}

function isMarkdownTableDivider(line: string) {
  const cells = markdownTableCells(line);
  return Boolean(cells?.length && cells.every((cell) => /^:?-{3,}:?$/.test(cell)));
}

function parseSummaryLines(summary: string): SummaryLine[] {
  const lines: SummaryLine[] = [];
  let codeBlockLanguage: string | undefined;
  let codeBlockLines: string[] = [];
  const sourceLines = normalizeCompactSummary(summary)
    .split('\n')
    .map((line) => line.trimEnd());

  let index = 0;
  while (index < sourceLines.length) {
    const line = sourceLines[index];
    const fence = line.trim().match(/^```([a-zA-Z0-9_-]+)?$/);
    if (fence && codeBlockLanguage !== undefined) {
      lines.push({
        kind: 'codeBlock',
        language: codeBlockLanguage,
        text: codeBlockLines.join('\n').trim(),
      });
      codeBlockLanguage = undefined;
      codeBlockLines = [];
      index += 1;
      continue;
    }
    if (codeBlockLanguage !== undefined) {
      codeBlockLines.push(line);
      index += 1;
      continue;
    }
    if (fence) {
      codeBlockLanguage = fence[1] ?? '';
      codeBlockLines = [];
      index += 1;
      continue;
    }

    const headers = markdownTableCells(line);
    if (headers && isMarkdownTableDivider(sourceLines[index + 1] ?? '')) {
      const rows: string[][] = [];
      index += 2;
      while (index < sourceLines.length) {
        const cells = markdownTableCells(sourceLines[index]);
        if (!cells) {
          break;
        }
        rows.push(headers.map((_, cellIndex) => cells[cellIndex] ?? ''));
        index += 1;
      }
      lines.push({ kind: 'table', headers, rows });
      continue;
    }

    if (line.trim()) {
      lines.push(parsePlainSummaryLine(line));
    }
    index += 1;
  }

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
        if (line.kind === 'table') {
          return (
            <div className="task-output-summary-table-scroll" key={`${line.kind}-${index}`}>
              <table className="task-output-summary-table">
                <thead>
                  <tr>
                    {line.headers.map((header, headerIndex) => (
                      <th key={`header-${headerIndex}`} scope="col">
                        {renderInlineMarkdown(header)}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {line.rows.map((row, rowIndex) => (
                    <tr key={`row-${rowIndex}`}>
                      {row.map((cell, cellIndex) => (
                        <td key={`cell-${rowIndex}-${cellIndex}`}>{renderInlineMarkdown(cell)}</td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
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
