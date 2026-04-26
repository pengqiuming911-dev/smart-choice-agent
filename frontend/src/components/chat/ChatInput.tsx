'use client';

import React from 'react';
import { Input, Button } from 'antd';
import { SendOutlined } from '@ant-design/icons';

const { TextArea } = Input;

interface ChatInputProps {
  value: string;
  onChange: (value: string) => void;
  onSend: () => void;
  disabled?: boolean;
}

export default function ChatInput({ value, onChange, onSend, disabled }: ChatInputProps) {
  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if (value.trim() && !disabled) {
        onSend();
      }
    }
  };

  return (
    <div
      style={{
        padding: '16px 24px 20px',
        borderTop: '1px solid #EBEDF0',
        background: '#fff',
      }}
    >
      <div style={{ maxWidth: 880, margin: '0 auto' }}>
        <div
          style={{
            border: '1px solid #EBEDF0',
            borderRadius: 12,
            padding: '12px 14px',
            background: '#fff',
            transition: 'border-color 0.15s',
          }}
          onFocus={(e) => {
            e.currentTarget.style.borderColor = '#3B6AF8';
          }}
          onBlur={(e) => {
            e.currentTarget.style.borderColor = '#EBEDF0';
          }}
        >
          <TextArea
            value={value}
            onChange={(e) => onChange(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="输入问题,按 Enter 发送,Shift+Enter 换行"
            autoSize={{ minRows: 1, maxRows: 6 }}
            variant="borderless"
            style={{
              fontSize: 14,
              resize: 'none',
              padding: '4px 0',
            }}
          />

          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              marginTop: 10,
              paddingTop: 8,
            }}
          >
            <Button
              type="primary"
              icon={<SendOutlined />}
              onClick={onSend}
              disabled={!value.trim() || disabled}
              style={{
                height: 32,
                width: 32,
                padding: 0,
                borderRadius: 8,
                background: value.trim() && !disabled ? '#3B6AF8' : '#D1D5DB',
                border: 'none',
                marginLeft: 'auto',
              }}
            />
          </div>
        </div>

        <div
          style={{
            textAlign: 'center',
            fontSize: 12,
            color: '#8F959E',
            marginTop: 10,
          }}
        >
          回答由 AI 生成,仅供参考
        </div>
      </div>
    </div>
  );
}