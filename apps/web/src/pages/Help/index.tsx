import { BookOutlined, LinkOutlined, SearchOutlined } from '@ant-design/icons';
import { PageContainer } from '@ant-design/pro-components';
import { Button, Empty, Input, Space, Tag } from 'antd';
import { useMemo, useState } from 'react';

import { navigateTo } from '../../utils/navigation';
import {
  findHelpArticle,
  getArticleSearchText,
  helpArticleByKey,
  helpArticles,
  helpGroups,
  type HelpArticle,
} from './helpContent';
import './Help.css';

function getInitialArticleKey() {
  if (typeof window === 'undefined') {
    return helpArticles[0]?.key ?? '';
  }
  return (
    findHelpArticle(new URLSearchParams(window.location.search).get('article'))?.key ??
    helpArticles[0]?.key ??
    ''
  );
}

function updateHelpArticleQuery(articleKey: string) {
  if (typeof window === 'undefined') {
    return;
  }
  const params = new URLSearchParams(window.location.search);
  params.set('article', articleKey);
  window.history.replaceState({}, '', `/help?${params.toString()}`);
}

function HelpArticleButton({
  article,
  isActive,
  onSelect,
}: {
  article: HelpArticle;
  isActive: boolean;
  onSelect: (article: HelpArticle) => void;
}) {
  return (
    <button
      aria-pressed={isActive}
      className={isActive ? 'help-article-button help-article-button-active' : 'help-article-button'}
      onClick={() => onSelect(article)}
      type="button"
    >
      <strong>{article.title}</strong>
      <span>{article.summary}</span>
    </button>
  );
}

export default function HelpPage() {
  const [query, setQuery] = useState('');
  const [selectedKey, setSelectedKey] = useState(getInitialArticleKey);

  const normalizedQuery = query.trim().toLowerCase();
  const filteredGroups = useMemo(() => {
    if (!normalizedQuery) {
      return helpGroups;
    }
    return helpGroups
      .map((group) => ({
        ...group,
        articles: group.articles.filter((article) =>
          getArticleSearchText(article).includes(normalizedQuery),
        ),
      }))
      .filter((group) => group.articles.length > 0);
  }, [normalizedQuery]);

  const visibleArticles = filteredGroups.flatMap((group) => group.articles);
  const selectedArticle =
    visibleArticles.find((article) => article.key === selectedKey) ??
    helpArticleByKey.get(selectedKey) ??
    visibleArticles[0] ??
    helpArticles[0];

  if (!selectedArticle) {
    return null;
  }

  const relatedArticles =
    selectedArticle.related
      ?.map((key) => helpArticleByKey.get(key))
      .filter((article): article is HelpArticle => Boolean(article)) ?? [];

  const handleSelectArticle = (article: HelpArticle) => {
    setSelectedKey(article.key);
    updateHelpArticleQuery(article.key);
  };

  return (
    <PageContainer title={false}>
      <main className="help-page">
        <section className="help-header" aria-labelledby="help-page-title">
          <div className="help-header-copy">
            <h1 id="help-page-title">
              <BookOutlined aria-hidden="true" /> 帮助中心
            </h1>
            <p>
              面向 AI Brain 日常使用的操作手册。可以按模块浏览，也可以搜索菜单、字段、错误码或操作关键词。
            </p>
          </div>
          <div className="help-header-tags" aria-label="帮助中心覆盖范围">
            <Tag color="blue">业务模块</Tag>
            <Tag color="green">常用操作</Tag>
            <Tag color="gold">错误处理</Tag>
          </div>
        </section>

        <section className="help-shell">
          <aside className="help-sidebar" aria-label="帮助文档目录">
            <Input.Search
              allowClear
              className="help-search"
              onChange={(event) => setQuery(event.target.value)}
              placeholder="搜索功能、字段或错误码"
              prefix={<SearchOutlined aria-hidden="true" />}
              value={query}
            />
            {filteredGroups.length > 0 ? (
              filteredGroups.map((group) => (
                <div className="help-group" key={group.key}>
                  <div className="help-group-title">{group.title}</div>
                  <div className="help-article-list">
                    {group.articles.map((article) => (
                      <HelpArticleButton
                        article={article}
                        isActive={selectedArticle.key === article.key}
                        key={article.key}
                        onSelect={handleSelectArticle}
                      />
                    ))}
                  </div>
                </div>
              ))
            ) : (
              <Empty
                className="help-empty"
                description="没有找到匹配的帮助文档"
                image={Empty.PRESENTED_IMAGE_SIMPLE}
              />
            )}
          </aside>

          <article className="help-article-panel" aria-labelledby="help-article-title">
            <div className="help-article-heading">
              <div className="help-article-title">
                <h2 id="help-article-title">{selectedArticle.title}</h2>
                <p className="help-summary">{selectedArticle.summary}</p>
                <div className="help-meta">
                  <Tag color="default">适用：{selectedArticle.role}</Tag>
                  {selectedArticle.route ? <Tag color="blue">{selectedArticle.route}</Tag> : null}
                </div>
              </div>
              {selectedArticle.route ? (
                <Button
                  icon={<LinkOutlined aria-hidden="true" />}
                  onClick={() => navigateTo(selectedArticle.route as string)}
                  type="primary"
                >
                  进入功能
                </Button>
              ) : null}
            </div>

            {selectedArticle.sections.map((section) => (
              <section className="help-section" key={section.heading}>
                <h3>{section.heading}</h3>
                {section.body.map((paragraph) => (
                  <p key={paragraph}>{paragraph}</p>
                ))}
              </section>
            ))}

            {relatedArticles.length > 0 ? (
              <div className="help-related" aria-label="相关帮助文档">
                <Space wrap>
                  <span>相关文档：</span>
                  {relatedArticles.map((article) => (
                    <Button key={article.key} onClick={() => handleSelectArticle(article)} size="small">
                      {article.title}
                    </Button>
                  ))}
                </Space>
              </div>
            ) : null}
          </article>
        </section>
      </main>
    </PageContainer>
  );
}
