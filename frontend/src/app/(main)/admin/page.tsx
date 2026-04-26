'use client';

import React from 'react';
import { Typography, Card, Table, Button } from 'antd';
import type { ColumnsType } from 'antd/es/table';

const { Title } = Typography;

interface SyncRecord {
  key: string;
  title: string;
  status: 'success' | 'failed' | 'pending';
  syncedAt: string;
}

const columns: ColumnsType<SyncRecord> = [
  { title: '文档标题', dataIndex: 'title' },
  {
    title: '状态',
    dataIndex: 'status',
    render: (status: string) => (
      <span style={{ color: status === 'success' ? '#52c41a' : '#f5222d' }}>
        {status === 'success' ? '成功' : '失败'}
      </span>
    ),
  },
  { title: '同步时间', dataIndex: 'syncedAt' },
];

const mockData: SyncRecord[] = [
  { key: '1', title: '产品介绍.md', status: 'success', syncedAt: '2026-04-26 10:00' },
  { key: '2', title: '销售流程.md', status: 'success', syncedAt: '2026-04-26 09:30' },
];

export default function AdminPage() {
  return (
    <div style={{ padding: 24 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 24 }}>
        <Title level={4}>管理后台</Title>
        <Button type="primary">手动同步</Button>
      </div>

      <Card title="同步记录" style={{ marginBottom: 24 }}>
        <Table columns={columns} dataSource={mockData} pagination={false} />
      </Card>

      <Card title="知识库统计">
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 16 }}>
          <StatCard label="总页面数" value="128" />
          <StatCard label="实体页" value="45" />
          <StatCard label="概念页" value="52" />
          <StatCard label="综合页" value="31" />
        </div>
      </Card>
    </div>
  );
}

function StatCard({ label, value }: { label: string; value: string }) {
  return (
    <Card size="small">
      <div style={{ textAlign: 'center' }}>
        <div style={{ fontSize: 24, fontWeight: 600, color: '#3B6AF8' }}>{value}</div>
        <div style={{ fontSize: 12, color: '#8F959E' }}>{label}</div>
      </div>
    </Card>
  );
}