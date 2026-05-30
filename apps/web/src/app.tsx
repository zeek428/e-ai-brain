import { ClusterOutlined, UserOutlined } from '@ant-design/icons';
import { ConfigProvider, theme } from 'antd';
import type { ReactNode } from 'react';

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

export const layout = ({ initialState }: { initialState?: InitialState }) => ({
  actionsRender: () => [<span className="layout-action" key="phase">研发大脑 MVP</span>],
  avatarProps: {
    icon: <UserOutlined />,
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
