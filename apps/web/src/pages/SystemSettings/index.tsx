import { MailOutlined, ReloadOutlined, SaveOutlined, SendOutlined } from '@ant-design/icons';
import { PageContainer } from '@ant-design/pro-components';
import {
  Alert,
  Button,
  Divider,
  Form,
  Input,
  InputNumber,
  Select,
  Skeleton,
  Space,
  Switch,
  Tag,
  Typography,
  message,
} from 'antd';
import { useCallback, useEffect, useState } from 'react';

import {
  fetchSystemSettings,
  testSystemEmailDelivery,
  updateSystemSettings,
  type SystemEmailDeliverySettings,
  type SystemSettingsRecord,
} from '../../services/aiBrain';
import { formatDisplayDateTime } from '../../utils/dateTime';
import {
  formatRemoteRowsError,
  normalizeRemoteRowsError,
  type RemoteRowsError,
} from '../../hooks/useRemoteRows';

type SystemSettingsFormValues = {
  admin_email?: string;
  email_delivery?: SystemEmailDeliverySettings;
  test_recipient_email?: string;
};

const DEFAULT_EMAIL_DELIVERY: SystemEmailDeliverySettings = {
  enabled: false,
  smtp_tls: 'starttls',
};

const normalizeEmailDeliveryFormValues = (
  settings?: SystemEmailDeliverySettings | null,
): SystemEmailDeliverySettings => ({
  ...DEFAULT_EMAIL_DELIVERY,
  ...(settings ?? {}),
  smtp_password: '',
  smtp_tls: settings?.smtp_tls || DEFAULT_EMAIL_DELIVERY.smtp_tls,
});

const buildEmailDeliveryPayload = (
  values?: SystemEmailDeliverySettings,
): SystemEmailDeliverySettings => {
  const smtpPassword = values?.smtp_password?.trim();
  const smtpPort = values?.smtp_port === null || values?.smtp_port === undefined
    ? undefined
    : Number(values.smtp_port);
  return {
    default_from: values?.default_from?.trim() || null,
    enabled: Boolean(values?.enabled),
    reply_to: values?.reply_to?.trim() || null,
    sender_email: values?.sender_email?.trim() || null,
    smtp_host: values?.smtp_host?.trim() || null,
    ...(smtpPassword ? { smtp_password: smtpPassword } : {}),
    smtp_port: Number.isFinite(smtpPort) ? smtpPort : null,
    smtp_tls: values?.smtp_tls || 'starttls',
    smtp_username: values?.smtp_username?.trim() || null,
  };
};

const formatEmailDeliveryTestError = (error: RemoteRowsError) => {
  if (error.code !== 'EMAIL_DELIVERY_TEST_FAILED') {
    return error.message;
  }
  const errorType = String(error.detail?.error_type ?? '');
  if (errorType === 'SMTPAuthenticationError') {
    return '邮件发送测试失败：SMTP 认证失败，请检查 SMTP 用户名、密码/授权码，阿里企业邮箱可能需要客户端授权码。';
  }
  if (errorType === 'ConnectionResetError') {
    return '邮件发送测试失败：SMTP 连接被重置，请检查 Host、端口、TLS/SSL 和网络访问。';
  }
  if (errorType === 'TimeoutError') {
    return '邮件发送测试失败：SMTP 连接超时，请检查服务器地址、端口和网络。';
  }
  return '邮件发送测试失败，请检查 SMTP 配置和邮箱服务状态。';
};

export default function SystemSettingsPage() {
  const [form] = Form.useForm<SystemSettingsFormValues>();
  const [settings, setSettings] = useState<SystemSettingsRecord>({});
  const [error, setError] = useState<RemoteRowsError>();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [testingEmail, setTestingEmail] = useState(false);
  const emailDelivery = Form.useWatch('email_delivery', form);
  const emailDeliveryEnabled = Boolean(emailDelivery?.enabled);

  const loadSettings = useCallback(async () => {
    setLoading(true);
    setError(undefined);
    try {
      const loaded = await fetchSystemSettings();
      setSettings(loaded);
      form.setFieldsValue({
        admin_email: loaded.admin_email ?? '',
        email_delivery: normalizeEmailDeliveryFormValues(loaded.email_delivery),
        test_recipient_email: loaded.test_recipient_email ?? '',
      });
    } catch (loadError) {
      setError(normalizeRemoteRowsError(loadError));
    } finally {
      setLoading(false);
    }
  }, [form]);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      void loadSettings();
    }, 0);
    return () => window.clearTimeout(timer);
  }, [loadSettings]);

  const persistSettingsFromForm = async () => {
    const values = await form.validateFields();
    const nextAdminEmail = values.admin_email?.trim() || null;
    const nextTestRecipientEmail = values.test_recipient_email?.trim() || null;
    const updated = await updateSystemSettings({
      admin_email: nextAdminEmail,
      email_delivery: buildEmailDeliveryPayload(values.email_delivery),
      test_recipient_email: nextTestRecipientEmail,
    });
    setSettings(updated);
    form.setFieldsValue({
      admin_email: updated.admin_email ?? '',
      email_delivery: normalizeEmailDeliveryFormValues(updated.email_delivery),
      test_recipient_email: updated.test_recipient_email ?? nextTestRecipientEmail ?? '',
    });
    return updated;
  };

  const saveSettings = async () => {
    setSaving(true);
    setError(undefined);
    try {
      await persistSettingsFromForm();
      message.success('系统设置已保存');
    } catch (saveError) {
      const normalized = normalizeRemoteRowsError(saveError);
      setError(normalized);
      message.error(normalized.message);
    } finally {
      setSaving(false);
    }
  };

  const sendTestEmail = async () => {
    setTestingEmail(true);
    setSaving(true);
    setError(undefined);
    try {
      const updated = await persistSettingsFromForm();
      const recipientEmail = updated.test_recipient_email?.trim();
      const result = await testSystemEmailDelivery({
        recipient_email: recipientEmail || null,
      });
      const subjectSuffix = result.message_subject ? `，主题：${result.message_subject}` : '';
      message.success(`测试邮件已发送至 ${result.recipient_email}${subjectSuffix}`);
    } catch (testError) {
      const normalized = normalizeRemoteRowsError(testError);
      const diagnosticMessage = formatEmailDeliveryTestError(normalized);
      setError({ ...normalized, message: diagnosticMessage });
      message.error(diagnosticMessage);
    } finally {
      setSaving(false);
      setTestingEmail(false);
    }
  };

  return (
    <PageContainer
      breadcrumb={{ items: [{ title: '系统管理' }, { title: '系统设置' }] }}
      title={false}
    >
      <div className="system-settings-page">
        {error ? (
          <Alert
            className="management-list-alert"
            showIcon
            title={formatRemoteRowsError(error)}
            type="warning"
          />
        ) : null}
        <section className="system-settings-panel">
          <Space align="center" className="system-settings-header">
            <Typography.Title level={4}>系统设置</Typography.Title>
            <Space wrap>
              <Tag color={settings.admin_email_configured ? 'green' : 'default'}>
                {settings.admin_email_configured ? '管理员邮箱已配置' : '管理员邮箱未配置'}
              </Tag>
              <Tag color={settings.email_delivery_configured ? 'green' : 'default'}>
                {settings.email_delivery_configured ? '发信已配置' : '发信未配置'}
              </Tag>
            </Space>
          </Space>
          <Form<SystemSettingsFormValues>
            form={form}
            labelCol={{ flex: '140px' }}
            layout="horizontal"
            requiredMark={false}
            wrapperCol={{ flex: 1 }}
          >
            {loading ? (
              <Skeleton active paragraph={{ rows: 4 }} />
            ) : (
              <>
                <Form.Item
                  extra="作为默认测试收件人和系统通知联系人。"
                  label="系统管理员邮箱"
                  name="admin_email"
                  rules={[
                    {
                      type: 'email',
                      message: '请输入有效邮箱',
                    },
                  ]}
                >
                  <Input
                    allowClear
                    autoComplete="email"
                    placeholder="admin@example.com"
                  />
                </Form.Item>
                <Divider plain titlePlacement="left">
                  邮件发送配置
                </Divider>
                <Form.Item
                  label="启用发信"
                  name={['email_delivery', 'enabled']}
                  valuePropName="checked"
                >
                  <Switch checkedChildren="启用" unCheckedChildren="停用" />
                </Form.Item>
                <div className="system-settings-grid">
                  <Form.Item
                    label="发件邮箱"
                    name={['email_delivery', 'sender_email']}
                    rules={[
                      {
                        type: 'email',
                        message: '请输入有效邮箱',
                      },
                    ]}
                  >
                    <Input
                      allowClear
                      autoComplete="email"
                      disabled={!emailDeliveryEnabled}
                      placeholder="noreply@example.com"
                    />
                  </Form.Item>
                  <Form.Item
                    label="默认发件人"
                    name={['email_delivery', 'default_from']}
                    rules={[
                      {
                        type: 'email',
                        message: '请输入有效邮箱',
                      },
                    ]}
                  >
                    <Input
                      allowClear
                      autoComplete="email"
                      disabled={!emailDeliveryEnabled}
                      placeholder="noreply@example.com"
                    />
                  </Form.Item>
                  <Form.Item
                    label="Reply-To"
                    name={['email_delivery', 'reply_to']}
                    rules={[
                      {
                        type: 'email',
                        message: '请输入有效邮箱',
                      },
                    ]}
                  >
                    <Input
                      allowClear
                      autoComplete="email"
                      disabled={!emailDeliveryEnabled}
                      placeholder="support@example.com"
                    />
                  </Form.Item>
                  <Form.Item label="SMTP Host" name={['email_delivery', 'smtp_host']}>
                    <Input
                      allowClear
                      disabled={!emailDeliveryEnabled}
                      placeholder="smtp.example.com"
                    />
                  </Form.Item>
                  <Form.Item label="SMTP 端口" name={['email_delivery', 'smtp_port']}>
                    <InputNumber
                      disabled={!emailDeliveryEnabled}
                      max={65535}
                      min={1}
                      placeholder="587"
                      style={{ width: '100%' }}
                    />
                  </Form.Item>
                  <Form.Item label="加密方式" name={['email_delivery', 'smtp_tls']}>
                    <Select
                      disabled={!emailDeliveryEnabled}
                      options={[
                        { label: 'STARTTLS', value: 'starttls' },
                        { label: 'SSL', value: 'ssl' },
                        { label: '不加密', value: 'none' },
                      ]}
                    />
                  </Form.Item>
                  <Form.Item label="SMTP 用户名" name={['email_delivery', 'smtp_username']}>
                    <Input
                      allowClear
                      autoComplete="username"
                      disabled={!emailDeliveryEnabled}
                      placeholder="noreply@example.com"
                    />
                  </Form.Item>
                  <Form.Item label="SMTP 密码/授权码" name={['email_delivery', 'smtp_password']}>
                    <Input.Password
                      autoComplete="new-password"
                      disabled={!emailDeliveryEnabled}
                      placeholder={
                        settings.email_delivery?.smtp_password_configured
                          ? '已配置，留空则继续沿用'
                          : '请输入 SMTP 密码或授权码'
                      }
                    />
                  </Form.Item>
                </div>
                <Divider plain titlePlacement="left">
                  测试发送
                </Divider>
                <Form.Item
                  extra="点击发送测试邮件会先保存当前页面配置；留空时使用系统管理员邮箱。"
                  label="测试收件人"
                  name="test_recipient_email"
                  rules={[
                    {
                      type: 'email',
                      message: '请输入有效邮箱',
                    },
                  ]}
                >
                  <Input
                    allowClear
                    autoComplete="email"
                    placeholder="默认使用系统管理员邮箱"
                  />
                </Form.Item>
                <Form.Item label="更新时间">
                  <Typography.Text>{formatDisplayDateTime(settings.updated_at)}</Typography.Text>
                </Form.Item>
                <Form.Item label="更新人">
                  <Typography.Text>{settings.updated_by || '-'}</Typography.Text>
                </Form.Item>
                <Form.Item label=" ">
                  <Space wrap>
                    <Button
                      icon={<SaveOutlined />}
                      loading={saving}
                      onClick={() => void saveSettings()}
                      type="primary"
                    >
                      保存
                    </Button>
                    <Button
                      icon={<SendOutlined />}
                      loading={testingEmail}
                      onClick={() => void sendTestEmail()}
                    >
                      发送测试邮件
                    </Button>
                    <Button icon={<ReloadOutlined />} onClick={() => void loadSettings()}>
                      刷新
                    </Button>
                    <Button
                      href="/system/plugins"
                      icon={<MailOutlined />}
                      type="link"
                    >
                      邮箱插件
                    </Button>
                  </Space>
                </Form.Item>
              </>
            )}
          </Form>
        </section>
      </div>
    </PageContainer>
  );
}
