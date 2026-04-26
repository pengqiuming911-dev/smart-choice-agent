'use client';

import React from 'react';
import {
  FolderOpenOutlined,
  LinkOutlined,
  CommentOutlined,
} from '@ant-design/icons';

const defaultCards = [
  {
    key: 'search',
    icon: <FolderOpenOutlined />,
    title: '知识检索',
    description: '快速找到相关文档',
  },
  {
    key: 'cite',
    icon: <LinkOutlined />,
    title: '引用追溯',
    description: '查看答案来源',
  },
  {
    key: 'multi-turn',
    icon: <CommentOutlined />,
    title: '多轮对话',
    description: '深入追问细节',
  },
];

export default function Capabilities() {
  return (
    <div style={{ width: '100%', maxWidth: 880, margin: '0 auto' }}>
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(3, 1fr)',
          gap: 12,
        }}
      >
        {defaultCards.map((card) => (
          <div
            key={card.key}
            style={{
              padding: '20px 18px',
              background: '#fff',
              border: '1px solid #EBEDF0',
              borderRadius: 10,
              textAlign: 'center',
              transition: 'all 0.15s',
            }}
          >
            <div
              style={{
                width: 40,
                height: 40,
                borderRadius: 10,
                background: '#E6EFFE',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                margin: '0 auto 12px',
                color: '#3B6AF8',
                fontSize: 18,
              }}
            >
              {card.icon}
            </div>
            <div
              style={{
                fontSize: 14,
                fontWeight: 600,
                color: '#1F2329',
                marginBottom: 4,
              }}
            >
              {card.title}
            </div>
            <div style={{ fontSize: 12, color: '#8F959E' }}>
              {card.description}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}