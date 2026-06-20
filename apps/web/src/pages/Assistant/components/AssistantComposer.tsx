import {
  CloseCircleOutlined,
  ExclamationCircleOutlined,
  PlusOutlined,
  SendOutlined,
  StopOutlined,
} from '@ant-design/icons';
import { Button, Input, Spin, Typography } from 'antd';
import { type KeyboardEvent, type ReactNode, type RefObject } from 'react';

import { type AssistantReference } from '../../../services/aiBrain';
import { referenceSummaryText } from './referencePresentation';

const { Text } = Typography;
const { TextArea } = Input;

export function AssistantComposer({
  addActionCandidates,
  activeAddActionIndex,
  addMenuRef,
  addActionQuery,
  canSend,
  inputValue,
  isAddMenuOpen,
  isLoadingAddActions,
  isSending,
  referencePicker,
  runOncePermissionHint,
  onAddActionMenuKeyDown,
  onChangeAddActionQuery,
  onChangeInput,
  onCloseAddMenu,
  onHoverAddAction,
  onKeyDown,
  onPressEnter,
  onSelectAddActionCandidate,
  onSend,
  onSetAddMenuTrigger,
  onStopSending,
  onToggleAddMenu,
}: {
  addActionCandidates: AssistantReference[];
  activeAddActionIndex: number;
  addMenuRef: RefObject<HTMLDivElement | null>;
  addActionQuery: string;
  canSend: boolean;
  inputValue: string;
  isAddMenuOpen: boolean;
  isLoadingAddActions: boolean;
  isSending: boolean;
  referencePicker?: ReactNode;
  runOncePermissionHint: boolean;
  onAddActionMenuKeyDown: (event: KeyboardEvent<HTMLInputElement>) => void;
  onChangeAddActionQuery: (value: string) => void;
  onChangeInput: (value: string) => void;
  onCloseAddMenu: () => void;
  onHoverAddAction: (index: number) => void;
  onKeyDown: (event: KeyboardEvent<HTMLTextAreaElement>) => void;
  onPressEnter: (event: KeyboardEvent<HTMLTextAreaElement>) => void;
  onSelectAddActionCandidate: (reference: AssistantReference) => void;
  onSend: () => void;
  onSetAddMenuTrigger: (node: HTMLElement | null) => void;
  onStopSending: () => void;
  onToggleAddMenu: () => void;
}) {
  return (
    <div className="assistant-composer">
      {runOncePermissionHint ? (
        <div aria-label="执行权限提示" className="assistant-composer-warning">
          <ExclamationCircleOutlined />
          <Text type="warning">
            当前账号没有执行定时作业权限，本次不会直接执行；请使用管理员账号或授予
            system.scheduled_jobs.run 后再发送。
          </Text>
        </div>
      ) : null}
      {isAddMenuOpen ? (
        <div
          aria-label="快捷添加 @ 能力"
          className="assistant-add-menu"
          id="assistant-add-menu"
          ref={addMenuRef}
        >
          <div className="assistant-add-menu-header">
            <Text strong>添加</Text>
            <Button
              aria-label="关闭快捷添加"
              icon={<CloseCircleOutlined />}
              size="small"
              type="text"
              onClick={onCloseAddMenu}
            />
          </div>
          <div className="assistant-add-menu-section-title">
            <Text type="secondary">常用 @ 能力</Text>
          </div>
          <Input
            aria-label="搜索快捷添加能力"
            className="assistant-add-menu-search"
            placeholder="搜索新建需求、定时作业、运行诊断..."
            value={addActionQuery}
            onChange={(event) => onChangeAddActionQuery(event.target.value)}
            onKeyDown={onAddActionMenuKeyDown}
          />
          {isLoadingAddActions ? (
            <div className="assistant-add-menu-loading">
              <Spin size="small" />
              <Text type="secondary">正在加载</Text>
            </div>
          ) : null}
          {!isLoadingAddActions && !addActionCandidates.length ? (
            <div className="assistant-add-menu-empty">
              <Text type="secondary">暂无可用动作</Text>
            </div>
          ) : null}
          <div className="assistant-add-menu-list">
            {addActionCandidates.map((reference, index) => (
              <Button
                className={`assistant-add-menu-item ${
                  index === activeAddActionIndex ? 'assistant-add-menu-item-active' : ''
                }`}
                icon={<PlusOutlined />}
                key={`${reference.type}:${reference.id}`}
                type="text"
                onClick={() => onSelectAddActionCandidate(reference)}
                onMouseEnter={() => onHoverAddAction(index)}
              >
                <span className="assistant-add-menu-item-main">
                  <span className="assistant-add-menu-item-title">{reference.title}</span>
                  <span className="assistant-add-menu-item-summary">
                    {referenceSummaryText(reference)}
                  </span>
                </span>
              </Button>
            ))}
          </div>
        </div>
      ) : null}
      {referencePicker}
      <TextArea
        aria-label="发送给 AI 助手"
        className="assistant-composer-input"
        onChange={(event) => onChangeInput(event.target.value)}
        onKeyDown={onKeyDown}
        onPressEnter={onPressEnter}
        placeholder="输入问题"
        rows={3}
        value={inputValue}
      />
      <div className="assistant-composer-toolbar">
        <Button
          aria-controls={isAddMenuOpen ? 'assistant-add-menu' : undefined}
          aria-expanded={isAddMenuOpen}
          aria-label="添加 @ 能力"
          className="assistant-composer-add-button"
          icon={<PlusOutlined />}
          ref={(node) => {
            onSetAddMenuTrigger(node);
          }}
          onClick={onToggleAddMenu}
        />
        <Button
          aria-label={isSending ? '停止生成' : '发送'}
          className={`assistant-composer-send ${isSending ? 'assistant-composer-stop' : ''}`}
          danger={isSending}
          disabled={!isSending && !canSend}
          icon={isSending ? <StopOutlined /> : <SendOutlined />}
          onClick={isSending ? onStopSending : onSend}
          type={isSending ? 'default' : 'primary'}
        >
          {isSending ? '停止' : '发送'}
        </Button>
      </div>
    </div>
  );
}
