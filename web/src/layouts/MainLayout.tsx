import { useState } from 'react'
import { Outlet, useNavigate, useLocation } from 'react-router-dom'
import { Layout, Menu, Typography } from 'antd'
import type { MenuProps } from 'antd'
import {
  HomeOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  ExperimentOutlined,
} from '@ant-design/icons'
import owlAvatar from '../logo/猫头鹰.png'
import raccoonAvatar from '../logo/浣熊.png'
import hamsterAvatar from '../logo/仓鼠.png'
import squirrelAvatar from '../logo/松鼠.png'

const { Sider, Content } = Layout
const { Text } = Typography

type MenuItem = Required<MenuProps>['items'][number]

const menuItems: MenuItem[] = [
  {
    key: '/',
    icon: <HomeOutlined />,
    label: '工作台',
  },
  {
    key: '/experiment-design',
    icon: <img src={owlAvatar} alt="" style={{ width: 28, height: 28, borderRadius: 8 }} />,
    label: '实验思路设计',
  },
  {
    key: '/image-analysis',
    icon: <img src={raccoonAvatar} alt="" style={{ width: 28, height: 28, borderRadius: 8 }} />,
    label: '图像分析',
  },
  {
    key: '/grant-writing',
    icon: <img src={hamsterAvatar} alt="" style={{ width: 28, height: 28, borderRadius: 8 }} />,
    label: '标书撰写',
  },
  {
    key: '/paper-writing',
    icon: <img src={squirrelAvatar} alt="" style={{ width: 28, height: 28, borderRadius: 8 }} />,
    label: '论文撰写',
  },
]

export default function MainLayout() {
  const [collapsed, setCollapsed] = useState(false)
  const navigate = useNavigate()
  const location = useLocation()

  const selectedKey = '/' + location.pathname.split('/')[1] || '/'

  const onClick: MenuProps['onClick'] = (e) => {
    navigate(e.key)
  }

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider
        collapsible
        collapsed={collapsed}
        onCollapse={setCollapsed}
        trigger={null}
        width={220}
        style={{
          background: '#fff',
          borderRight: '1px solid #f0f0f0',
        }}
      >
        {/* Logo 区域 */}
        <div
          style={{
            height: 64,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            borderBottom: '1px solid #f0f0f0',
            padding: '0 16px',
          }}
        >
          {collapsed ? (
            <ExperimentOutlined style={{ fontSize: 24, color: '#1677ff' }} />
          ) : (
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: 16, fontWeight: 700, color: '#1677ff', lineHeight: 1.2 }}>
                🔬 科研智能助手
              </div>
              <Text type="secondary" style={{ fontSize: 11 }}>
                ScienceStudy
              </Text>
            </div>
          )}
        </div>

        {/* 导航菜单 */}
        <Menu
          mode="inline"
          selectedKeys={[selectedKey === '/' ? '/' : selectedKey]}
          items={menuItems}
          onClick={onClick}
          style={{ border: 'none', marginTop: 8 }}
        />

        {/* 底部折叠按钮 */}
        <div
          style={{
            position: 'absolute',
            bottom: 16,
            left: 0,
            right: 0,
            textAlign: 'center',
            cursor: 'pointer',
            color: '#999',
            padding: '8px 0',
          }}
          onClick={() => setCollapsed(!collapsed)}
        >
          {collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
        </div>
      </Sider>

      <Layout>
        <Content
          style={{
            background: '#fafafa',
            minHeight: '100vh',
            overflow: 'auto',
          }}
        >
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  )
}
