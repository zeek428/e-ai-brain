import { LockOutlined, UserOutlined } from '@ant-design/icons';
import { Alert, Button, Card, Form, Input, Typography } from 'antd';
import { useState } from 'react';

import { ApiRequestError, login } from '../../services/aiBrain';
import { navigateTo } from '../../utils/navigation';

type LoginFormValues = {
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

export default function LoginPage() {
  const [error, setError] = useState<string>();
  const [loading, setLoading] = useState(false);

  const handleFinish = async (values: LoginFormValues) => {
    setError(undefined);
    setLoading(true);
    try {
      await login(values.username, values.password);
      navigateTo(getRedirectPath());
    } catch (requestError) {
      if (requestError instanceof ApiRequestError) {
        setError(`${requestError.code ?? requestError.status} · ${requestError.message}`);
      } else {
        setError('登录失败，请检查后端服务状态。');
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="login-shell">
      <Card className="login-card">
        <div className="login-heading">
          <Typography.Title level={1}>AI Brain</Typography.Title>
          <Typography.Text>开发环境登录</Typography.Text>
        </div>
        {error ? <Alert message={error} showIcon type="error" /> : null}
        <Form<LoginFormValues>
          initialValues={{ password: 'admin123', username: 'admin@example.com' }}
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
          <Button block htmlType="submit" loading={loading} type="primary">
            登录
          </Button>
        </Form>
      </Card>
    </main>
  );
}
