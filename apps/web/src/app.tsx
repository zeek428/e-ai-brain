import { ClusterOutlined, LogoutOutlined, UserOutlined } from '@ant-design/icons';
import { ConfigProvider, Dropdown, theme } from 'antd';
import type { ReactNode } from 'react';

import { CurrentUserTitle } from './components/CurrentUserTitle';
import { handleLogout, redirectToLoginIfNeeded } from './runtimeAuth';
import { fetchCurrentUser, getStoredCurrentUser } from './services/aiBrain';
import './global.css';

type InitialState = {
  currentUser: {
    name: string;
    role: string;
  };
};

export async function getInitialState(): Promise<InitialState> {
  const storedUser = getStoredCurrentUser();
  if (storedUser) {
    return {
      currentUser: {
        name: storedUser.display_name,
        role: storedUser.roles.join(', ') || 'viewer',
      },
    };
  }
  try {
    const currentUser = await fetchCurrentUser();
    return {
      currentUser: {
        name: currentUser.display_name,
        role: currentUser.roles.join(', ') || 'viewer',
      },
    };
  } catch {
    // Layout still renders a login-safe shell while route guards redirect anonymous users.
  }
  return {
    currentUser: {
      name: '未登录',
      role: 'anonymous',
    },
  };
}

export const layout = ({ initialState }: { initialState?: InitialState }) => ({
  actionsRender: () => [<span className="layout-action" key="phase">研发大脑 MVP</span>],
  avatarProps: {
    icon: <UserOutlined />,
    render: (_props: unknown, dom: ReactNode) => (
      <Dropdown
        menu={{
          items: [
            {
              icon: <LogoutOutlined />,
              key: 'logout',
              label: '退出登录',
            },
          ],
          onClick: ({ key }) => {
            if (key === 'logout') {
              void handleLogout();
            }
          },
        }}
        placement="bottomRight"
        trigger={['click']}
      >
        <button className="avatar-menu-trigger" type="button">
          {dom}
        </button>
      </Dropdown>
    ),
    title: <CurrentUserTitle fallback={initialState?.currentUser?.name ?? '未登录'} />,
  },
  contentStyle: {
    padding: 0,
  },
  defaultOpenAll: true,
  fixSiderbar: true,
  layout: 'mix',
  logo: <ClusterOutlined />,
  menu: {
    locale: false,
  },
  menuFooterRender: () => <span className="menu-footer">AI Brain v1</span>,
  navTheme: 'light',
  onPageChange: () => {
    redirectToLoginIfNeeded();
  },
  siderWidth: 256,
  splitMenus: false,
  title: 'AI Brain',
});

export function rootContainer(container: ReactNode) {
  return (
    <ConfigProvider
      theme={{
        algorithm: theme.defaultAlgorithm,
        token: {
          borderRadius: 8,
          colorPrimary: '#2f6fed',
          fontFamily:
            'Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
        },
      }}
    >
      {container}
    </ConfigProvider>
  );
}
