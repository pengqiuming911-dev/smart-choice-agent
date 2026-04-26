'use client';

import React from 'react';
import { Card, List, Input, Tag, Typography } from 'antd';
import { BookOutlined, SearchOutlined } from '@ant-design/icons';
import type { WikiPage } from '@/types';

const { Search } = Input;
const { Title, Text } = Typography;

// Mock data
const mockPages: WikiPage[] = [
  { title: '产品介绍', path: 'wiki/entities/product-intro.md', type: 'entity', access: 'public' },
  { title: '销售流程', path: 'wiki/concepts/sales-process.md', type: 'concept', access: 'public' },
  { title: 'Q3销售业绩', path: 'wiki/overviews/q3-sales.md', type: 'overview', access: 'dept-sales' },
];

export default function WikiPage() {
  return (
    <div style={{ padding: 24 }}>
      <div style={{ marginBottom: 24 }}>
        <Title level={4} style={{ marginBottom: 16 }}>知识库</Title>
        <Search
          placeholder="搜索 wiki 页面..."
          prefix={<SearchOutlined />}
          style={{ maxWidth: 400 }}
        />
      </div>

      <List
        dataSource={mockPages}
        renderItem={(page) => (
          <List.Item
            style={{
              padding: 16,
              borderRadius: 8,
              marginBottom: 8,
              border: '1px solid #EBEDF0',
              cursor: 'pointer',
            }}
          >
            <List.Item.Meta
              avatar={<BookOutlined style={{ fontSize: 24, color: '#3B6AF8' }} />}
              title={
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <span>{page.title}</span>
                  <Tag color={page.type === 'entity' ? 'blue' : page.type === 'concept' ? 'green' : 'purple'}>
                    {page.type}
                  </Tag>
                </div>
              }
              description={
                <Text type="secondary">{page.path}</Text>
              }
            />
          </List.Item>
        )}
      />
    </div>
  );
}