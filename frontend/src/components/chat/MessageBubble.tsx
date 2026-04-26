'use client';

import React from 'react';
import type { Message } from '@/types';
import { Badge, Tooltip } from 'antd';

interface MessageBubbleProps {
  message: Message;
}

export default function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === 'user';

  return (
    <div
      style={{
        display: 'flex',
        justifyContent: isUser ? 'flex-end' : 'flex-start',
        marginBottom: 16,
      }}
    >
      <div
        style={{
          maxWidth: '70%',
          padding: '12px 16px',
          borderRadius: 12,
          background: isUser ? '#3B6AF8' : '#F7F8FA',
          color: isUser ? '#fff' : '#1F2329',
          fontSize: 14,
          lineHeight: 1.6,
          whiteSpace: 'pre-wrap',
        }}
      >
        {message.content}

        {/* Sources for assistant messages */}
        {!isUser && message.sources && message.sources.length > 0 && (
          <div
            style={{
              marginTop: 12,
              paddingTop: 8,
              borderTop: '1px solid rgba(0,0,0,0.06)',
            }}
          >
            <div style={{ fontSize: 12, color: '#8F959E', marginBottom: 6 }}>
              引用来源
            </div>
            {message.sources.map((source, idx) => (
              <Tooltip key={idx} title={source.url}>
                <div
                  style={{
                    fontSize: 12,
                    color: '#3B6AF8',
                    cursor: 'pointer',
                    marginBottom: 2,
                  }}
                  onClick={() => window.open(source.url, '_blank')}
                >
                  📄 {source.title}
                </div>
              </Tooltip>
            ))}
          </div>
        )}

        {/* Confidence badge */}
        {!isUser && message.confidence && (
          <div style={{ marginTop: 8 }}>
            <Badge
              count={message.confidence}
              style={{
                backgroundColor:
                  message.confidence === 'high'
                    ? '#52c41a'
                    : message.confidence === 'medium'
                    ? '#faad14'
                    : '#f5222d',
                fontSize: 10,
              }}
            />
          </div>
        )}
      </div>
    </div>
  );
}