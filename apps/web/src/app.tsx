import { ClusterOutlined, LogoutOutlined, UserOutlined } from '@ant-design/icons';
import { ConfigProvider, Dropdown, theme } from 'antd';
import type { ReactNode } from 'react';

import { getAccessToken, logout } from './services/aiBrain';
import { navigateTo } from './utils/navigation';
import './global.css';

type InitialState = {
  currentUser: {
    name: string;
    role: string;
  };
};

export async function getInitialState(): Promise<InitialState> {
  return {
    currentUser: {
      name: 'AI Brain Admin',
      role: 'admin',
    },
  };
}

function loginRedirectFor(pathname: string, search: string) {
  const target = `${pathname}${search}`;
  return `/login?redirect=${encodeURIComponent(target)}`;
}

export function redirectToLoginIfNeeded(pathname = window.location.pathname, search = window.location.search) {
  if (pathname === '/login' || getAccessToken()) {
    return false;
  }
  navigateTo(loginRedirectFor(pathname, search));
  return true;
}

export async function handleLogout() {
  await logout();
  navigateTo('/login');
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
    title: initialState?.currentUser?.name ?? 'admin',
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
