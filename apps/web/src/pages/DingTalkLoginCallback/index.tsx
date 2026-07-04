import { Alert, Button, Card, Spin, Typography } from 'antd';
import { useEffect, useState } from 'react';

import {
  ApiRequestError,
  exchangeDingTalkTicket,
  fetchCurrentUser,
} from '../../services/aiBrain';
import { navigateTo } from '../../utils/navigation';

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
