'use client';

import React from 'react';
import { usePathname } from 'next/navigation';
import Link from 'next/link';
import { Layout, Menu, Avatar, Dropdown } from 'antd';
import type { MenuProps } from 'antd';
import {
  MessageOutlined,
  BookOutlined,
  CalendarOutlined,
  SettingOutlined,
  LogoutOutlined,
} from '@ant-design/icons';
import { useAuthStore } from '@/stores';

const { Sider, Content } = Layout;

export default function MainLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();
  const { user } = useAuthStore();

  // Use mock user if not authenticated (for development)
  const displayUser = user || {
    id: '1',
    name: '开发者',
    email: 'dev@example.com',
    department: '技术研发部',
    role: 'public' as const,
  };

  const menuItems: MenuProps['items'] = [
    {
      key: '/chat',
      icon: <MessageOutlined />,
      label: <Link href="/chat">智能问答</Link>,
    },
    {
      key: '/wiki',
      icon: <BookOutlined />,
      label: <Link href="/wiki">知识库</Link>,
    },
    {
      key: '/calendar',
      icon: <CalendarOutlined />,
      label: <Link href="/calendar">日历</Link>,
    },
  ];

  const userMenuItems: MenuProps['items'] = [
    {
      key: 'admin',
      icon: <SettingOutlined />,
      label: <Link href="/admin">管理后台</Link>,
    },
    { type: 'divider' },
    {
      key: 'logout',
      icon: <LogoutOutlined />,
      label: '退出登录',
    },
  ];

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider
        width={240}
        style={{
          background: '#F7F8FA',
          borderRight: '1px solid #EBEDF0',
        }}
      >
        {/* Logo */}
        <div
          style={{
            padding: '16px',
            display: 'flex',
            alignItems: 'center',
            gap: 10,
            borderBottom: '1px solid #EBEDF0',
          }}
        >
          <div
            style={{
              width: 36,
              height: 36,
              borderRadius: 8,
              background: '#3B6AF8',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: '#fff',
              fontSize: 16,
            }}
          >
            <MessageOutlined />
          </div>
          <div>
            <div style={{ fontSize: 15, fontWeight: 600, color: '#1F2329' }}>LLM Wiki</div>
            <div style={{ fontSize: 12, color: '#8F959E' }}>智能知识库</div>
          </div>
        </div>

        {/* Navigation */}
        <Menu
          mode="inline"
          selectedKeys={[pathname]}
          items={menuItems}
          style={{
            background: 'transparent',
            borderRight: 'none',
            padding: '8px 0',
          }}
        />

        {/* User */}
        <div
          style={{
            position: 'absolute',
            bottom: 0,
            left: 0,
            right: 0,
            padding: '12px 16px',
            borderTop: '1px solid #EBEDF0',
            display: 'flex',
            alignItems: 'center',
            gap: 10,
          }}
        >
          <Dropdown menu={{ items: userMenuItems }} placement="topLeft">
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, cursor: 'pointer', flex: 1 }}>
              <Avatar size={32} style={{ background: '#1F2329' }}>
                {displayUser.name.charAt(0)}
              </Avatar>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontSize: 13, fontWeight: 500, color: '#1F2329' }}>{displayUser.name}</div>
                <div style={{ fontSize: 11, color: '#8F959E' }}>{displayUser.department}</div>
              </div>
            </div>
          </Dropdown>
        </div>
      </Sider>

      <Content>{children}</Content>
    </Layout>
  );
}