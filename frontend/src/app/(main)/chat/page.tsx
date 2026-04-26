'use client';

import React, { useState, useEffect } from 'react';
import MainLayout from '../layout';
import ChatPageContent from '@/components/chat/ChatPageContent';

export default function ChatPage() {
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  if (!mounted) {
    return null;
  }

  return (
    <MainLayout>
      <ChatPageContent />
    </MainLayout>
  );
}