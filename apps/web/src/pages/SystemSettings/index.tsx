import { ReloadOutlined, SaveOutlined } from '@ant-design/icons';
import { PageContainer } from '@ant-design/pro-components';
import { Alert, Button, Form, Input, Skeleton, Space, Tag, Typography, message } from 'antd';
import { useCallback, useEffect, useState } from 'react';

import {
  fetchSystemSettings,
  updateSystemSettings,
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
};

export default function SystemSettingsPage() {
  const [form] = Form.useForm<SystemSettingsFormValues>();
  const [settings, setSettings] = useState<SystemSettingsRecord>({});
  const [error, setError] = useState<RemoteRowsError>();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  const loadSettings = useCallback(async () => {
    setLoading(true);
    setError(undefined);
    try {
      const loaded = await fetchSystemSettings();
      setSettings(loaded);
      form.setFieldsValue({ admin_email: loaded.admin_email ?? '' });
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

  const saveSettings = async () => {
    const values = await form.validateFields();
    setSaving(true);
    setError(undefined);
    try {
      const updated = await updateSystemSettings({
        admin_email: values.admin_email?.trim() || null,
      });
      setSettings(updated);
      form.setFieldsValue({ admin_email: updated.admin_email ?? '' });
      message.success('系统设置已保存');
    } catch (saveError) {
      const normalized = normalizeRemoteRowsError(saveError);
      setError(normalized);
      message.error(normalized.message);
    } finally {
      setSaving(false);
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
            <Tag color={settings.admin_email_configured ? 'green' : 'default'}>
              {settings.admin_email_configured ? '已配置' : '未配置'}
            </Tag>
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
                  extra="用于发送 AI Brain 相关系统邮件。"
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
                  <Button icon={<ReloadOutlined />} onClick={() => void loadSettings()}>
                    刷新
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
