'use client';

import React from 'react';
import { BulbOutlined } from '@ant-design/icons';
import type { SuggestionItem } from '@/types';

interface SuggestionsProps {
  items: SuggestionItem[];
  onSelect: (item: SuggestionItem) => void;
}

export default function Suggestions({ items, onSelect }: SuggestionsProps) {
  return (
    <div style={{ width: '100%', maxWidth: 880, margin: '0 auto' }}>
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 6,
          marginBottom: 12,
          fontSize: 14,
          fontWeight: 500,
          color: '#1F2329',
        }}
      >
        <BulbOutlined style={{ color: '#3B6AF8' }} />
        推荐问题
      </div>

      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(2, 1fr)',
          gap: 12,
        }}
      >
        {items.map((item) => (
          <SuggestionCard
            key={item.key}
            item={item}
            onClick={() => onSelect(item)}
          />
        ))}
      </div>
    </div>
  );
}

function SuggestionCard({ item, onClick }: { item: SuggestionItem; onClick: () => void }) {
  const [hover, setHover] = React.useState(false);

  return (
    <div
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
      onClick={onClick}
      style={{
        padding: '16px 18px',
        background: '#fff',
        border: `1px solid ${hover ? '#3B6AF8' : '#EBEDF0'}`,
        borderRadius: 10,
        cursor: 'pointer',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        gap: 12,
        transition: 'all 0.15s',
        boxShadow: hover ? '0 2px 8px rgba(59, 106, 248, 0.08)' : 'none',
      }}
    >
      <div
        style={{
          fontSize: 14,
          color: '#1F2329',
          fontWeight: 500,
          flex: 1,
        }}
      >
        {item.title}
      </div>
      <div
        style={{
          fontSize: 12,
          color: '#8F959E',
          background: '#F7F8FA',
          padding: '3px 8px',
          borderRadius: 4,
          flexShrink: 0,
        }}
      >
        {item.category}
      </div>
    </div>
  );
}