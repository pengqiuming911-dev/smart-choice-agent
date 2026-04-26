'use client';

import React from 'react';
import { Tag, Button } from 'antd';
import { RobotOutlined, DatabaseOutlined, PlusOutlined } from '@ant-design/icons';

interface ChatHeaderProps {
  title: string;
  badge?: string;
  modelName: string;
  indexedCount: number;
  onNewChat?: () => void;
}

export default function ChatHeader({ title, badge, modelName, indexedCount, onNewChat }: ChatHeaderProps) {
  return (
    <header
      style={{
        height: 60,
        padding: '0 24px',
        borderBottom: '1px solid #EBEDF0',
        background: '#fff',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        flexShrink: 0,
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
        {onNewChat && (
          <Button
            type="text"
            icon={<PlusOutlined />}
            onClick={onNewChat}
            style={{ marginRight: 8 }}
          >
            新建
          </Button>
        )}
        <div style={{ fontSize: 16, fontWeight: 600, color: '#1F2329' }}>
          {title}
        </div>
        {badge && (
          <Tag
            color="blue"
            style={{
              borderRadius: 4,
              fontSize: 12,
              padding: '0 8px',
              margin: 0,
              border: 'none',
              background: '#E6EFFE',
              color: '#3B6AF8',
            }}
          >
            {badge}
          </Tag>
        )}
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
        <InfoChip icon={<RobotOutlined />} text={modelName} />
        <InfoChip icon={<DatabaseOutlined />} text={`已索引 ${indexedCount}`} />
      </div>
    </header>
  );
}

function InfoChip({ icon, text }: { icon: React.ReactNode; text: string }) {
  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: 6,
        padding: '6px 12px',
        background: '#F7F8FA',
        borderRadius: 6,
        fontSize: 13,
        color: '#4E5969',
      }}
    >
      <span style={{ color: '#8F959E', fontSize: 13 }}>{icon}</span>
      {text}
    </div>
  );
}