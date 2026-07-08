import {
  ClusterOutlined,
  LogoutOutlined,
  ProfileOutlined,
  QuestionCircleOutlined,
  UserOutlined,
} from '@ant-design/icons';
import { ConfigProvider, Dropdown, theme } from 'antd';
import type { ReactNode } from 'react';

import { CurrentUserTitle } from './components/CurrentUserTitle';
import { handleLogout, redirectToLoginIfNeeded } from './runtimeAuth';
import type { MenuTreeNode } from './services/aiBrain';
import { fetchCurrentUser, getAccessToken, getStoredCurrentUser } from './services/aiBrain';
import { navigateTo } from './utils/navigation';
import './global.css';

type InitialState = {
  currentUser: {
    id?: string;
    isAuthenticated?: boolean;
    menuTree?: MenuTreeNode[];
    name: string;
    role: string;
    username?: string;
  };
};

type MenuRoute = {
  children?: MenuRoute[];
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

function collectMenuPathOrder(menuTree: MenuTreeNode[] | undefined) {
  const orderByPath = new Map<string, number>();
  let order = 0;
  const visit = (node: MenuTreeNode) => {
    if (node.path && !orderByPath.has(node.path)) {
      orderByPath.set(node.path, order);
      order += 1;
    }
    node.children?.forEach(visit);
  };
  menuTree?.forEach(visit);
  return orderByPath;
}

function sortRoutesByMenuTreeOrder(menuData: MenuRoute[], orderByPath: Map<string, number>) {
  return [...menuData].sort((left, right) => {
    const leftOrder = left.path ? orderByPath.get(left.path) : undefined;
    const rightOrder = right.path ? orderByPath.get(right.path) : undefined;
    const leftValue = leftOrder ?? Number.MAX_SAFE_INTEGER;
    const rightValue = rightOrder ?? Number.MAX_SAFE_INTEGER;
    return leftValue - rightValue;
  });
}

function selectCurrentMenuTree(
  initialUser: InitialState['currentUser'] | undefined,
  storedUser: Awaited<ReturnType<typeof getStoredCurrentUser>>,
) {
  if (!storedUser) {
    return initialUser?.menuTree;
  }
  if (!initialUser?.isAuthenticated) {
    return storedUser.menu_tree;
  }
  if (!initialUser.id && !initialUser.username) {
    return storedUser.menu_tree ?? initialUser.menuTree;
  }
  if (initialUser.id && storedUser.id && initialUser.id !== storedUser.id) {
    return storedUser.menu_tree;
  }
  if (initialUser.username && storedUser.username && initialUser.username !== storedUser.username) {
    return storedUser.menu_tree;
  }
  return initialUser.menuTree ?? storedUser.menu_tree;
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
  const orderByPath = collectMenuPathOrder(menuTree);
  const filterRoute = (route: MenuRoute): MenuRoute | undefined => {
    if (route.hideInMenu) {
      return route;
    }
    const sourceChildren = route.routes ?? route.children;
    const children = sourceChildren?.map(filterRoute).filter(Boolean) as MenuRoute[] | undefined;
    if (sourceChildren?.length && !children?.length) {
      return undefined;
    }
    const isAuthorized = route.path ? authorizedPaths.has(route.path) : false;
    if (!isAuthorized && !children?.length) {
      return undefined;
    }
    const sortedChildren = children?.length ? sortRoutesByMenuTreeOrder(children, orderByPath) : undefined;
    return {
      ...route,
      ...(route.children ? { children: sortedChildren ?? route.children } : {}),
      ...(route.routes ? { routes: sortedChildren ?? route.routes } : {}),
    };
  };
  return sortRoutesByMenuTreeOrder(
    menuData.map(filterRoute).filter(Boolean) as MenuRoute[],
    orderByPath,
  );
}

export async function getInitialState(): Promise<InitialState> {
  if (getAccessToken()) {
    try {
      const currentUser = await fetchCurrentUser();
      return {
        currentUser: {
          id: currentUser.id,
          isAuthenticated: true,
          menuTree: currentUser.menu_tree,
          name: currentUser.display_name,
          role: currentUser.roles.join(', ') || 'viewer',
          username: currentUser.username,
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
        id: storedUser.id,
        isAuthenticated: true,
        menuTree: storedUser.menu_tree,
        name: storedUser.display_name,
        role: storedUser.roles.join(', ') || 'viewer',
        username: storedUser.username,
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
  actionsRender: () => [
    <button
      className="layout-action layout-help-link"
      key="help"
      onClick={() => navigateTo('/help')}
      type="button"
    >
      <QuestionCircleOutlined aria-hidden="true" />
      帮助中心
    </button>,
    <span className="layout-action" key="phase">IT研发大脑</span>,
  ],
  avatarProps: {
    icon: <UserOutlined />,
    render: (_props: unknown, dom: ReactNode) => (
      <Dropdown
        menu={{
          items: [
            {
              icon: <QuestionCircleOutlined aria-hidden="true" />,
              key: 'help',
              label: '帮助中心',
            },
            {
              icon: <ProfileOutlined />,
              key: 'profile',
              label: '个人中心',
            },
            {
              icon: <LogoutOutlined />,
              key: 'logout',
              label: '退出登录',
            },
          ],
          onClick: ({ key }) => {
            if (key === 'help') {
              navigateTo('/help');
            }
            if (key === 'profile') {
              navigateTo('/account/profile');
            }
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
    const currentMenuTree = selectCurrentMenuTree(initialState?.currentUser, storedUser);
    return filterMenuDataByAuthorization(
      menuData,
      currentMenuTree,
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
