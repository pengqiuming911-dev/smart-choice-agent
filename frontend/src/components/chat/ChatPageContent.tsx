'use client';

import React, { useState } from 'react';
import ChatHeader from '@/components/chat/ChatHeader';
import Welcome from '@/components/chat/Welcome';
import Suggestions from '@/components/chat/Suggestions';
import Capabilities from '@/components/chat/Capabilities';
import ChatInput from '@/components/chat/ChatInput';
import MessageBubble from '@/components/chat/MessageBubble';
import type { Conversation, SuggestionItem, Message } from '@/types';
import { queryWiki } from '@/lib/api/client';

const mockConversations: Conversation[] = [
  {
    id: '1',
    title: '关于产品功能的讨论',
    group: '今天',
    updatedAt: '2026-04-26',
  },
];

const mockSuggestions: SuggestionItem[] = [
  {
    key: 's1',
    title: '这个产品的核心优势是什么?',
    category: '产品·销售',
  },
  {
    key: 's2',
    title: '如何联系销售团队?',
    category: '产品·销售',
  },
  {
    key: 's3',
    title: '公司报销流程是什么?',
    category: '行政·流程',
  },
  {
    key: 's4',
    title: '如何申请年假?',
    category: '行政·流程',
  },
];

export default function ChatPageContent() {
  const [conversations] = useState<Conversation[]>(mockConversations);
  const [currentId] = useState<string>('1');
  const [inputValue, setInputValue] = useState('');
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  const currentConv = conversations.find((c) => c.id === currentId);

  const handleSend = async () => {
    if (!inputValue.trim() || isLoading) return;

    const userMessage: Message = {
      id: String(Date.now()),
      role: 'user',
      content: inputValue.trim(),
      createdAt: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInputValue('');
    setIsLoading(true);

    try {
      const response = await queryWiki(userMessage.content);

      const assistantMessage: Message = {
        id: String(Date.now() + 1),
        role: 'assistant',
        content: response.answer,
        sources: response.raw_sources.map((s) => ({
          title: s.title,
          url: s.path,
          type: 'wiki' as const,
        })),
        confidence: response.confidence,
        createdAt: new Date().toISOString(),
      };

      setMessages((prev) => [...prev, assistantMessage]);
    } catch (error) {
      console.error('Query failed:', error);
      const errorMessage: Message = {
        id: String(Date.now() + 1),
        role: 'assistant',
        content: '抱歉，查询知识库时出现了问题，请稍后重试。',
        createdAt: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSelectSuggestion = (item: SuggestionItem) => {
    setInputValue(item.title);
  };

  const handleNewConversation = () => {
    setMessages([]);
  };

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        height: '100vh',
        background: '#fff',
        fontFamily:
          '-apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif',
      }}
    >
      <ChatHeader
        title={currentConv?.title || '智能体问答'}
        badge="开发模式"
        modelName="MiniMax"
        indexedCount={128}
        onNewChat={handleNewConversation}
      />

      <div
        style={{
          flex: 1,
          overflowY: 'auto',
          padding: '0 24px',
          display: 'flex',
          flexDirection: 'column',
        }}
      >
        {messages.length === 0 ? (
          <>
            <Welcome
              greeting="你好,我是知识库助手"
              description="我可以帮你查找团队文档、回答产品问题、解释流程规范"
            />

            <div style={{ marginBottom: 24 }}>
              <Suggestions
                items={mockSuggestions}
                onSelect={handleSelectSuggestion}
              />
            </div>

            <div
              style={{
                maxWidth: 880,
                margin: '8px auto 24px',
                width: '100%',
                height: 1,
                background: '#EBEDF0',
              }}
            />

            <div style={{ marginBottom: 24 }}>
              <Capabilities />
            </div>
          </>
        ) : (
          <div style={{ maxWidth: 880, margin: '0 auto', width: '100%', padding: '24px 0' }}>
            {messages.map((msg) => (
              <MessageBubble key={msg.id} message={msg} />
            ))}
          </div>
        )}
      </div>

      <ChatInput
        value={inputValue}
        onChange={setInputValue}
        onSend={handleSend}
        disabled={isLoading}
      />
    </div>
  );
}