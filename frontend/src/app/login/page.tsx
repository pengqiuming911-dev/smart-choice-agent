"use client"

import { signIn } from "next-auth/react"
import { Button, Space, Typography, Card } from "antd"

const { Title, Text } = Typography

export default function LoginPage() {
  return (
    <div style={{
      minHeight: "100vh",
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      background: "linear-gradient(135deg, #667eea 0%, #764ba2 100%)",
    }}>
      <Card style={{ width: 400, textAlign: "center", borderRadius: 16 }}>
        <Space orientation="vertical" size="large" style={{ width: "100%" }}>
          <div>
            <Title level={2}>LLM Wiki</Title>
            <Text type="secondary">团队智能知识库</Text>
          </div>

          <Button
            type="primary"
            size="large"
            block
            onClick={() => signIn("feishu", { callbackUrl: "/chat" })}
            style={{
              height: 48,
              fontSize: 16,
              background: "#3370ff",
              borderColor: "#3370ff",
            }}
          >
            飞书授权登录
          </Button>

          <Text type="secondary" style={{ fontSize: 12 }}>
            登录即表示同意服务条款和隐私政策
          </Text>
        </Space>
      </Card>
    </div>
  )
}