'use client';

import React from 'react';
import { MessageOutlined } from '@ant-design/icons';

interface WelcomeProps {
  greeting: string;
  description: string;
}

export default function Welcome({ greeting, description }: WelcomeProps) {
  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        textAlign: 'center',
        padding: '32px 0 28px',
      }}
    >
      <div
        style={{
          width: 56,
          height: 56,
          borderRadius: 16,
          background: '#3B6AF8',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          marginBottom: 16,
          boxShadow: '0 4px 12px rgba(59, 106, 248, 0.2)',
        }}
      >
        <MessageOutlined style={{ fontSize: 28, color: '#fff' }} />
      </div>

      <div
        style={{
          fontSize: 28,
          fontWeight: 600,
          color: '#1F2329',
          marginBottom: 8,
          letterSpacing: '0.5px',
        }}
      >
        {greeting}
      </div>

      <div
        style={{
          fontSize: 14,
          color: '#8F959E',
          maxWidth: 520,
          lineHeight: 1.6,
        }}
      >
        {description}
      </div>
    </div>
  );
}