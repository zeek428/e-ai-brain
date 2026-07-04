import { Alert, Button, Card, Spin, Typography } from 'antd';
import { useEffect, useState } from 'react';

import {
  ApiRequestError,
  exchangeDingTalkTicket,
  fetchCurrentUser,
} from '../../services/aiBrain';
import { navigateTo } from '../../utils/navigation';

const DINGTALK_LOGIN_ERROR_MESSAGES: Record<string, string> = {
  DINGTALK_ACCOUNT_INACTIVE: '绑定的 AI Brain 账号不可用，请联系管理员确认账号状态。',
  DINGTALK_ACCOUNT_NOT_BOUND: '该钉钉账号尚未绑定 AI Brain 用户，请先使用账号密码登录后到个人中心绑定。',
  DINGTALK_ACCOUNT_PENDING_APPROVAL: '钉钉登录申请正在等待管理员审批。',
  DINGTALK_AUTH_DENIED: '你取消了钉钉授权，请重新发起登录。',
  DINGTALK_CODE_MISSING: '钉钉没有返回授权码，请重新发起登录。',
  DINGTALK_CORP_NOT_ALLOWED: '当前钉钉企业不在 AI Brain 允许登录范围内。',
  DINGTALK_PROFILE_INCOMPLETE: '钉钉账号信息不完整，请联系管理员检查应用授权范围。',
  DINGTALK_STATE_INVALID: '登录会话已过期，请重新点击钉钉登录。',
  DINGTALK_TICKET_INVALID: '登录票据已过期或已使用，请重新点击钉钉登录。',
  DINGTALK_UPSTREAM_ERROR: '钉钉服务暂时不可用，请稍后重试。',
};

function safeRedirectPath(value: string | null) {
  if (
    value &&
    value.startsWith('/') &&
    !value.startsWith('//') &&
    value !== '/login' &&
    !value.startsWith('/login/dingtalk/callback')
  ) {
    return value;
  }
  return '/welcome';
}

function callbackErrorMessage(params: URLSearchParams) {
  const code = params.get('error');
  const message = params.get('message');
  if (code && DINGTALK_LOGIN_ERROR_MESSAGES[code]) {
    return DINGTALK_LOGIN_ERROR_MESSAGES[code];
  }
  if (code && message) {
    return `${code} · ${message}`;
  }
  if (code) {
    return code;
  }
  return '钉钉登录失败，请重新发起登录。';
}

export default function DingTalkLoginCallbackPage() {
  const [error, setError] = useState<string>();

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const redirect = safeRedirectPath(params.get('redirect'));
    const ticket = params.get('ticket');

    if (!ticket) {
      const timer = window.setTimeout(() => {
        setError(callbackErrorMessage(params));
      }, 0);
      return () => window.clearTimeout(timer);
    }

    void exchangeDingTalkTicket(ticket)
      .then(() => fetchCurrentUser())
      .then(() => {
        navigateTo(redirect);
      })
      .catch((requestError) => {
        if (requestError instanceof ApiRequestError) {
          setError(`${requestError.code ?? requestError.status} · ${requestError.message}`);
        } else {
          setError('钉钉登录失败，请检查后端服务状态。');
        }
      });
  }, []);

  return (
    <main className="login-shell">
      <Card className="login-card">
        <div className="login-heading">
          <Typography.Title level={1}>Enterprise AI Brain</Typography.Title>
          <Typography.Text>钉钉登录</Typography.Text>
        </div>
        {error ? (
          <>
            <Alert showIcon title={error} type="error" />
            <Button block onClick={() => navigateTo('/login')} type="primary">
              返回登录
            </Button>
          </>
        ) : (
          <Spin description="正在完成钉钉登录">
            <div style={{ minHeight: 72 }} />
          </Spin>
        )}
      </Card>
    </main>
  );
}
