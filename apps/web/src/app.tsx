import { ClusterOutlined, LogoutOutlined, UserOutlined } from '@ant-design/icons';
import { ConfigProvider, Dropdown, theme } from 'antd';
import type { ReactNode } from 'react';

import { CurrentUserTitle } from './components/CurrentUserTitle';
import { handleLogout, redirectToLoginIfNeeded } from './runtimeAuth';
import type { MenuTreeNode } from './services/aiBrain';
import { fetchCurrentUser, getAccessToken, getStoredCurrentUser } from './services/aiBrain';
import './global.css';

type InitialState = {
  currentUser: {
    isAuthenticated?: boolean;
    menuTree?: MenuTreeNode[];
    name: string;
    role: string;
  };
};

type MenuRoute = {
  hideInMenu?: boolean;
  path?: string;
  routes?: MenuRoute[];
  [key: string]: unknown;
};

function collectAuthorizedMenuPaths(menuTree: MenuTreeNode[] | undefined) {
  const paths = new Set<string>();
  const visit = (node: MenuTreeNode) => {
    if (node.path) {
      paths.add(node.path);
    }
    node.children?.forEach(visit);
  };
  menuTree?.forEach(visit);
  return paths;
}

function filterMenuDataByAuthorization(
  menuData: MenuRoute[],
  menuTree: MenuTreeNode[] | undefined,
  isAuthenticated?: boolean,
) {
  if (!menuTree?.length) {
    return isAuthenticated ? [] : menuData;
  }
  const authorizedPaths = collectAuthorizedMenuPaths(menuTree);
  const filterRoute = (route: MenuRoute): MenuRoute | undefined => {
    if (route.hideInMenu) {
      return route;
    }
    const children = route.routes?.map(filterRoute).filter(Boolean) as MenuRoute[] | undefined;
    const isAuthorized = route.path ? authorizedPaths.has(route.path) : false;
    if (!isAuthorized && !children?.length) {
      return undefined;
    }
    return {
      ...route,
      routes: children?.length ? children : route.routes,
    };
  };
  return menuData.map(filterRoute).filter(Boolean) as MenuRoute[];
}

export async function getInitialState(): Promise<InitialState> {
  if (getAccessToken()) {
    try {
      const currentUser = await fetchCurrentUser();
      return {
        currentUser: {
          isAuthenticated: true,
          menuTree: currentUser.menu_tree,
          name: currentUser.display_name,
          role: currentUser.roles.join(', ') || 'viewer',
        },
      };
    } catch {
      // Layout still renders a login-safe shell while route guards redirect anonymous users.
    }
  }
  const storedUser = getStoredCurrentUser();
  if (storedUser) {
    return {
      currentUser: {
        isAuthenticated: true,
        menuTree: storedUser.menu_tree,
        name: storedUser.display_name,
        role: storedUser.roles.join(', ') || 'viewer',
      },
    };
  }
  return {
    currentUser: {
      isAuthenticated: false,
      name: '未登录',
      role: 'anonymous',
    },
  };
}

export const layout = ({ initialState }: { initialState?: InitialState }) => ({
  actionsRender: () => [<span className="layout-action" key="phase">IT研发大脑</span>],
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
  menuDataRender: (menuData: MenuRoute[]) => {
    const storedUser = getStoredCurrentUser();
    return filterMenuDataByAuthorization(
      menuData,
      storedUser?.menu_tree ?? initialState?.currentUser?.menuTree,
      Boolean(storedUser) || initialState?.currentUser?.isAuthenticated,
    );
  },
  menuFooterRender: () => <span className="menu-footer">Enterprise AI Brain v1</span>,
  navTheme: 'light',
  onPageChange: () => {
    redirectToLoginIfNeeded();
  },
  siderWidth: 256,
  splitMenus: false,
  title: 'Enterprise AI Brain',
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
