'use client';

import React from 'react';
import { useRouter } from 'next/navigation';
import { Form, Input, Button, Card, Typography } from 'antd';

const { Title, Text } = Typography;

export default function LoginPage() {
  const router = useRouter();
  const [form] = Form.useForm();

  const handleFeishuLogin = () => {
    // In production: initiate Feishu OAuth flow
    // For now, simulate login and redirect
    router.push('/chat');
  };

  return (
    <div
      style={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: '#F7F8FA',
      }}
    >
      <Card
        style={{
          width: 400,
          borderRadius: 16,
          boxShadow: '0 4px 24px rgba(0,0,0,0.08)',
        }}
        bodyStyle={{ padding: 40 }}
      >
        <div style={{ textAlign: 'center', marginBottom: 32 }}>
          <div
            style={{
              width: 56,
              height: 56,
              borderRadius: 16,
              background: '#3B6AF8',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              margin: '0 auto 16px',
            }}
          >
            <span style={{ fontSize: 28, color: '#fff' }}>📖</span>
          </div>
          <Title level={3} style={{ marginBottom: 8 }}>LLM Wiki</Title>
          <Text type="secondary">智能知识库问答系统</Text>
        </div>

        <Form form={form} layout="vertical" onFinish={handleFeishuLogin}>
          <Form.Item>
            <Button
              type="primary"
              htmlType="submit"
              block
              size="large"
              style={{
                height: 48,
                borderRadius: 8,
                fontSize: 16,
              }}
            >
              飞书登录
            </Button>
          </Form.Item>
        </Form>

        <Text type="secondary" style={{ fontSize: 12, display: 'block', textAlign: 'center', marginTop: 16 }}>
          使用飞书账号登录，统一认证管理
        </Text>
      </Card>
    </div>
  );
}