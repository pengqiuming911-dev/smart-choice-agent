'use client';

import React from 'react';
import { Typography, Card } from 'antd';

const { Title, Text } = Typography;

export default function CalendarPage() {
  return (
    <div style={{ padding: 24 }}>
      <Title level={4} style={{ marginBottom: 24 }}>日历</Title>
      <Card
        style={{
          textAlign: 'center',
          padding: '60px 0',
          color: '#8F959E',
        }}
      >
        <Text type="secondary">日历模块开发中...</Text>
        <br />
        <Text type="secondary">计划接入飞书日历</Text>
      </Card>
    </div>
  );
}