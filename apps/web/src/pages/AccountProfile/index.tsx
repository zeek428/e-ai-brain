import {
  LinkOutlined,
  LockOutlined,
  QrcodeOutlined,
  ReloadOutlined,
  SaveOutlined,
  UserOutlined,
} from '@ant-design/icons';
import {
  Alert,
  App as AntdApp,
  Avatar,
  Button,
  Card,
  Descriptions,
  Form,
  Input,
  Popconfirm,
  Space,
  Spin,
  Tag,
  Typography,
} from 'antd';
import { useCallback, useEffect, useState } from 'react';

import {
  ApiRequestError,
  fetchAuthProfile,
  fetchAuthProviders,
  startDingTalkBind,
  unbindDingTalkAccount,
  updateAuthProfile,
  type AuthProfileResponse,
} from '../../services/aiBrain';
import { formatMutationError } from '../../utils/managementCrud';

type BasicProfileFormValues = {
  current_password?: string;
  display_name: string;
  email: string;
  mobile?: string;
};

type PasswordFormValues = {
  current_password: string;
  new_password: string;
  confirm_password: string;
};

function bindMessageFromQuery() {
  const params = new URLSearchParams(window.location.search);
  const bound = params.get('dingtalk_bound');
  const error = params.get('dingtalk_bind_error');
  if (bound === 'true') {
    return { type: 'success' as const, text: '钉钉账号已绑定' };
  }
  if (error) {
    return { type: 'error' as const, text: `钉钉绑定失败：${error}` };
  }
  return undefined;
}

function AccountProfileContent() {
  const { message } = AntdApp.useApp();
  const [basicForm] = Form.useForm<BasicProfileFormValues>();
  const [passwordForm] = Form.useForm<PasswordFormValues>();
  const [dingtalkEnabled, setDingtalkEnabled] = useState(false);
  const [error, setError] = useState<string>();
  const [isBinding, setIsBinding] = useState(false);
  const [isPasswordSaving, setIsPasswordSaving] = useState(false);
  const [isProfileSaving, setIsProfileSaving] = useState(false);
  const [isUnbinding, setIsUnbinding] = useState(false);
  const [loading, setLoading] = useState(true);
  const [profile, setProfile] = useState<AuthProfileResponse>();

  const populateProfile = useCallback((nextProfile: AuthProfileResponse) => {
    setProfile(nextProfile);
    basicForm.setFieldsValue({
      current_password: '',
      display_name: nextProfile.display_name,
      email: nextProfile.email ?? nextProfile.username,
      mobile: nextProfile.mobile ?? '',
    });
  }, [basicForm]);

  const reload = useCallback(async () => {
    setLoading(true);
    setError(undefined);
    try {
      const [nextProfile, providers] = await Promise.all([
        fetchAuthProfile(),
        fetchAuthProviders().catch(() => undefined),
      ]);
      populateProfile(nextProfile);
      setDingtalkEnabled(Boolean(providers?.dingtalk?.enabled));
    } catch (loadError) {
      if (loadError instanceof ApiRequestError) {
        setError(`${loadError.code ?? loadError.status} · ${loadError.message}`);
      } else {
        setError('个人资料加载失败，请检查后端服务状态。');
      }
    } finally {
      setLoading(false);
    }
  }, [populateProfile]);

  useEffect(() => {
    const bindMessage = bindMessageFromQuery();
    if (bindMessage?.type === 'success') {
      message.success(bindMessage.text);
    } else if (bindMessage?.type === 'error') {
      message.error(bindMessage.text);
    }
    if (bindMessage) {
      window.history.replaceState({}, '', '/account/profile');
    }
    const timer = window.setTimeout(() => {
      void reload();
    }, 0);
    return () => window.clearTimeout(timer);
  }, [message, reload]);

  const handleProfileSave = async () => {
    const values = await basicForm.validateFields();
    setIsProfileSaving(true);
    try {
      const response = await updateAuthProfile({
        current_password: values.current_password?.trim() || undefined,
        display_name: values.display_name.trim(),
        email: values.email.trim(),
        mobile: values.mobile?.trim() ?? '',
      });
      populateProfile(response.user);
      message.success('个人资料已更新');
    } catch (saveError) {
      message.error(formatMutationError(saveError));
    } finally {
      setIsProfileSaving(false);
    }
  };

  const handlePasswordSave = async () => {
    const values = await passwordForm.validateFields();
    setIsPasswordSaving(true);
    try {
      const response = await updateAuthProfile({
        current_password: values.current_password,
        new_password: values.new_password,
      });
      populateProfile(response.user);
      passwordForm.resetFields();
      message.success('登录密码已更新');
    } catch (saveError) {
      message.error(formatMutationError(saveError));
    } finally {
      setIsPasswordSaving(false);
    }
  };

  const handleDingTalkBind = async () => {
    setIsBinding(true);
    try {
      const response = await startDingTalkBind('/account/profile');
      window.location.assign(response.authorize_url);
    } catch (bindError) {
      message.error(formatMutationError(bindError));
      setIsBinding(false);
    }
  };

  const handleDingTalkUnbind = async () => {
    setIsUnbinding(true);
    try {
      await unbindDingTalkAccount();
      const nextProfile = await fetchAuthProfile();
      populateProfile(nextProfile);
      message.success('钉钉账号已解绑');
    } catch (unbindError) {
      message.error(formatMutationError(unbindError));
    } finally {
      setIsUnbinding(false);
    }
  };

  const dingtalkBinding = profile?.dingtalk_binding;

  return (
    <main className="account-profile-page">
      <section className="account-profile-header">
        <div>
          <Typography.Title level={2}>个人中心</Typography.Title>
          <Typography.Text type="secondary">{profile?.username ?? '当前登录账号'}</Typography.Text>
        </div>
        <Button icon={<ReloadOutlined />} loading={loading} onClick={() => void reload()}>
          刷新
        </Button>
      </section>
      {error ? <Alert showIcon title={error} type="error" /> : null}
      <Spin spinning={loading}>
        <section className="account-profile-grid">
          <Card className="account-profile-panel" title="账号资料">
            <Form<BasicProfileFormValues> form={basicForm} layout="vertical" requiredMark={false}>
              <Form.Item
                label="显示名称"
                name="display_name"
                rules={[{ message: '请输入显示名称', required: true }]}
              >
                <Input autoComplete="name" prefix={<UserOutlined />} />
              </Form.Item>
              <Form.Item
                label="邮箱"
                name="email"
                rules={[
                  { message: '请输入邮箱', required: true },
                  { message: '请输入有效邮箱', type: 'email' },
                ]}
              >
                <Input autoComplete="email" />
              </Form.Item>
              <Form.Item label="手机号" name="mobile">
                <Input autoComplete="tel" />
              </Form.Item>
              <Form.Item label="当前密码" name="current_password">
                <Input.Password aria-label="资料当前密码" autoComplete="current-password" />
              </Form.Item>
              <Button
                icon={<SaveOutlined />}
                loading={isProfileSaving}
                onClick={() => void handleProfileSave()}
                type="primary"
              >
                保存资料
              </Button>
            </Form>
          </Card>

          <Card className="account-profile-panel" title="登录密码">
            <Form<PasswordFormValues> form={passwordForm} layout="vertical" requiredMark={false}>
              <Form.Item
                label="当前密码"
                name="current_password"
                rules={[{ message: '请输入当前密码', required: true }]}
              >
                <Input.Password
                  aria-label="密码当前密码"
                  autoComplete="current-password"
                  prefix={<LockOutlined />}
                />
              </Form.Item>
              <Form.Item
                label="新密码"
                name="new_password"
                rules={[
                  { message: '请输入新密码', required: true },
                  { min: 8, message: '新密码至少 8 位' },
                ]}
              >
                <Input.Password autoComplete="new-password" />
              </Form.Item>
              <Form.Item
                dependencies={['new_password']}
                label="确认新密码"
                name="confirm_password"
                rules={[
                  { message: '请再次输入新密码', required: true },
                  ({ getFieldValue }) => ({
                    validator(_, value) {
                      if (!value || getFieldValue('new_password') === value) {
                        return Promise.resolve();
                      }
                      return Promise.reject(new Error('两次输入的新密码不一致'));
                    },
                  }),
                ]}
              >
                <Input.Password autoComplete="new-password" />
              </Form.Item>
              <Button
                icon={<SaveOutlined />}
                loading={isPasswordSaving}
                onClick={() => void handlePasswordSave()}
                type="primary"
              >
                更新密码
              </Button>
            </Form>
          </Card>

          <Card className="account-profile-panel account-profile-dingtalk" title="钉钉账号">
            <Space align="start" className="account-profile-binding" size={12}>
              <Avatar icon={<QrcodeOutlined />} src={dingtalkBinding?.avatar_url ?? undefined} />
              <div>
                <Space size={8} wrap>
                  <Typography.Text strong>
                    {dingtalkBinding?.bound
                      ? dingtalkBinding.display_name || dingtalkBinding.email || '已绑定'
                      : '未绑定'}
                  </Typography.Text>
                  <Tag color={dingtalkBinding?.bound ? 'green' : 'default'}>
                    {dingtalkBinding?.bound ? '已绑定' : '未绑定'}
                  </Tag>
                </Space>
                <Descriptions column={1} size="small">
                  <Descriptions.Item label="企业">{dingtalkBinding?.corp_id || '-'}</Descriptions.Item>
                  <Descriptions.Item label="邮箱">{dingtalkBinding?.email || '-'}</Descriptions.Item>
                </Descriptions>
              </div>
            </Space>
            <Space wrap>
              <Button
                disabled={!dingtalkEnabled}
                icon={<LinkOutlined />}
                loading={isBinding}
                onClick={() => void handleDingTalkBind()}
                type={dingtalkBinding?.bound ? 'default' : 'primary'}
              >
                {dingtalkBinding?.bound ? '重新绑定' : '绑定钉钉'}
              </Button>
              {dingtalkBinding?.bound ? (
                <Popconfirm
                  okText="解绑"
                  onConfirm={() => void handleDingTalkUnbind()}
                  title="解绑当前钉钉账号？"
                >
                  <Button danger loading={isUnbinding}>
                    解绑
                  </Button>
                </Popconfirm>
              ) : null}
            </Space>
          </Card>
        </section>
      </Spin>
    </main>
  );
}

export default function AccountProfilePage() {
  return (
    <AntdApp>
      <AccountProfileContent />
    </AntdApp>
  );
}
