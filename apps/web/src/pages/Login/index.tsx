import {
  LockOutlined,
  QrcodeOutlined,
  ReloadOutlined,
  SafetyCertificateOutlined,
  UserOutlined,
} from '@ant-design/icons';
import { Alert, Button, Card, Divider, Form, Input, Space, Typography } from 'antd';
import { useCallback, useEffect, useState } from 'react';

import {
  ApiRequestError,
  buildDingTalkStartUrl,
  fetchAuthProviders,
  fetchCurrentUser,
  fetchLoginChallenge,
  getAccessToken,
  login,
  type LoginChallengeResponse,
} from '../../services/aiBrain';
import { navigateTo } from '../../utils/navigation';

type LoginFormValues = {
  challenge_answer?: string;
  password: string;
  username: string;
};

function getRedirectPath() {
  const params = new URLSearchParams(window.location.search);
  const redirect = params.get('redirect');
  if (redirect && redirect.startsWith('/') && !redirect.startsWith('//') && redirect !== '/login') {
    return redirect;
  }
  return '/welcome';
}

function formatLoginError(error: ApiRequestError) {
  if (error.code === 'LOGIN_CHALLENGE_REQUIRED') {
    return '请输入安全校验答案后再登录。';
  }
  if (error.code === 'LOGIN_CHALLENGE_INVALID') {
    return '安全校验答案错误或已过期，请重新填写。';
  }
  if (error.code === 'LOGIN_CHALLENGE_UNAVAILABLE') {
    return '安全校验暂时不可用，请稍后重试或联系管理员。';
  }
  if (error.code === 'INVALID_CREDENTIALS') {
    return '账号或密码错误，请重新输入。';
  }
  return `${error.code ?? error.status} · ${error.message}`;
}

export default function LoginPage() {
  const [dingtalkLoginEnabled, setDingtalkLoginEnabled] = useState(false);
  const [error, setError] = useState<string>();
  const [form] = Form.useForm<LoginFormValues>();
  const [loginChallenge, setLoginChallenge] = useState<LoginChallengeResponse | null>(null);
  const [loginChallengeLoading, setLoginChallengeLoading] = useState(false);
  const [loginChallengeRequired, setLoginChallengeRequired] = useState(false);
  const [loading, setLoading] = useState(false);
  const [providerLoading, setProviderLoading] = useState(true);

  const refreshLoginChallenge = useCallback(async () => {
    setLoginChallengeLoading(true);
    try {
      const challenge = await fetchLoginChallenge();
      setLoginChallenge(challenge);
      form.setFieldsValue({ challenge_answer: undefined });
      return challenge;
    } catch {
      setLoginChallenge(null);
      setError('安全校验生成失败，请检查后端服务状态。');
      return null;
    } finally {
      setLoginChallengeLoading(false);
    }
  }, [form]);

  useEffect(() => {
    if (!getAccessToken()) {
      void fetchAuthProviders()
        .then((providers) => {
          setDingtalkLoginEnabled(Boolean(providers.dingtalk?.enabled));
          const challengeRequired = Boolean(providers.local?.challenge_required);
          setLoginChallengeRequired(challengeRequired);
          if (challengeRequired) {
            return refreshLoginChallenge();
          }
          return undefined;
        })
        .catch(() => {
          setDingtalkLoginEnabled(false);
        })
        .finally(() => {
          setProviderLoading(false);
        });
      return;
    }
    void Promise.resolve().then(() => {
      setProviderLoading(false);
      return fetchCurrentUser()
        .then(() => {
          navigateTo(getRedirectPath());
        })
        .catch(() => {
          // Invalid stored tokens are cleared by the shared API request layer.
        });
    });
  }, [refreshLoginChallenge]);

  const handleDingTalkLogin = () => {
    window.location.assign(buildDingTalkStartUrl(getRedirectPath()));
  };

  const handleFinish = async (values: LoginFormValues) => {
    setError(undefined);
    setLoading(true);
    try {
      let challengeForLogin = loginChallenge;
      if (loginChallengeRequired && !challengeForLogin) {
        challengeForLogin = await refreshLoginChallenge();
        if (!challengeForLogin) {
          return;
        }
      }
      await login(
        values.username,
        values.password,
        loginChallengeRequired && challengeForLogin
          ? {
              challengeAnswer: values.challenge_answer ?? '',
              challengeId: challengeForLogin.challenge_id,
            }
          : undefined,
      );
      await fetchCurrentUser();
      navigateTo(getRedirectPath());
    } catch (requestError) {
      if (requestError instanceof ApiRequestError) {
        setError(formatLoginError(requestError));
      } else {
        setError('登录失败，请检查后端服务状态。');
      }
      if (loginChallengeRequired) {
        form.setFieldsValue({ challenge_answer: undefined });
        void refreshLoginChallenge();
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="login-shell">
      <Card className="login-card">
        <div className="login-heading">
          <Typography.Title level={1}>Enterprise AI Brain</Typography.Title>
        </div>
        {error ? <Alert showIcon title={error} type="error" /> : null}
        <Form<LoginFormValues>
          form={form}
          layout="vertical"
          onFinish={handleFinish}
          requiredMark={false}
        >
          <Form.Item
            label="账号"
            name="username"
            rules={[{ message: '请输入账号', required: true }]}
          >
            <Input autoComplete="username" prefix={<UserOutlined />} />
          </Form.Item>
          <Form.Item
            label="密码"
            name="password"
            rules={[{ message: '请输入密码', required: true }]}
          >
            <Input.Password autoComplete="current-password" prefix={<LockOutlined />} />
          </Form.Item>
          {loginChallengeRequired ? (
            <>
              <Form.Item label="安全校验" required>
                <Space.Compact block>
                  <Input
                    disabled
                    prefix={<SafetyCertificateOutlined />}
                    value={loginChallenge?.question ?? '正在生成校验题'}
                  />
                  <Button
                    aria-label="刷新安全校验"
                    icon={<ReloadOutlined />}
                    loading={loginChallengeLoading}
                    onClick={() => void refreshLoginChallenge()}
                  />
                </Space.Compact>
              </Form.Item>
              <Form.Item
                name="challenge_answer"
                rules={[{ message: '请输入安全校验答案', required: true }]}
              >
                <Input
                  autoComplete="off"
                  inputMode="numeric"
                  placeholder="请输入计算结果"
                  prefix={<SafetyCertificateOutlined />}
                />
              </Form.Item>
            </>
          ) : null}
          <Button block htmlType="submit" loading={loading} type="primary">
            登录
          </Button>
        </Form>
        {dingtalkLoginEnabled ? (
          <>
            <Divider plain>或</Divider>
            <Button
              block
              icon={<QrcodeOutlined />}
              loading={providerLoading}
              onClick={handleDingTalkLogin}
            >
              钉钉登录
            </Button>
          </>
        ) : null}
      </Card>
    </main>
  );
}
