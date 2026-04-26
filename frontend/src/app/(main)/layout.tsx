"use client"

import { useSession, signOut } from "next-auth/react"
import { usePathname, useRouter } from "next/navigation"
import { Layout, Menu, Avatar, Dropdown, Button } from "antd"
import {
  RobotOutlined,
  BookOutlined,
  LogoutOutlined,
  UserOutlined,
} from "@ant-design/icons"
import { useEffect } from "react"

const { Sider, Content } = Layout

const menuItems = [
  { key: "/chat", icon: <RobotOutlined />, label: "智能体问答" },
  { key: "/wiki", icon: <BookOutlined />, label: "Wiki 浏览" },
]

export default function MainLayout({ children }: { children: React.ReactNode }) {
  const { data: session, status } = useSession()
  const pathname = usePathname()
  const router = useRouter()

  useEffect(() => {
    if (status === "unauthenticated") {
      router.push("/login")
    }
  }, [status, router])

  if (status === "loading") {
    return (
      <div style={{ height: "100vh", display: "flex", alignItems: "center", justifyContent: "center" }}>
        加载中...
      </div>
    )
  }

  if (!session) {
    return null
  }

  const userMenu = {
    items: [
      {
        key: "logout",
        icon: <LogoutOutlined />,
        label: "退出登录",
        onClick: () => signOut({ callbackUrl: "/login" }),
      },
    ],
  }

  return (
    <Layout style={{ minHeight: "100vh" }}>
      <Sider
        width={220}
        style={{
          background: "#001529",
          position: "fixed",
          height: "100vh",
          left: 0,
          top: 0,
        }}
      >
        <div style={{
          height: 64,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          borderBottom: "1px solid rgba(255,255,255,0.1)",
        }}>
          <span style={{ color: "#fff", fontSize: 18, fontWeight: 600 }}>LLM Wiki</span>
        </div>

        <Menu
          mode="inline"
          selectedKeys={[pathname]}
          items={menuItems}
          style={{ background: "transparent", border: "none", marginTop: 16 }}
          onClick={({ key }) => router.push(key)}
        />

        <div style={{
          position: "absolute",
          bottom: 16,
          left: 0,
          right: 0,
          padding: "0 16px",
        }}>
          <Dropdown menu={userMenu} placement="topLeft">
            <div style={{
              display: "flex",
              alignItems: "center",
              gap: 8,
              padding: "8px 0",
              cursor: "pointer",
            }}>
              <Avatar icon={<UserOutlined />} style={{ background: "#1677ff" }} />
              <span style={{ color: "#fff", fontSize: 14 }}>
                {session.user?.name || "用户"}
              </span>
            </div>
          </Dropdown>
        </div>
      </Sider>

      <Content style={{ marginLeft: 220, minHeight: "100vh", background: "#f5f5f5" }}>
        {children}
      </Content>
    </Layout>
  )
}