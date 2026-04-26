// Zustand store for chat state

import { create } from 'zustand';
import type { Message, Conversation } from '@/types';

interface ChatState {
  conversations: Conversation[];
  currentConversationId: string | null;
  messages: Message[];
  isLoading: boolean;
  inputValue: string;

  // Actions
  setConversations: (conversations: Conversation[]) => void;
  setCurrentConversation: (id: string) => void;
  addMessage: (message: Message) => void;
  clearMessages: () => void;
  setIsLoading: (loading: boolean) => void;
  setInputValue: (value: string) => void;
  createConversation: () => Conversation;
  deleteConversation: (id: string) => void;
}

export const useChatStore = create<ChatState>((set, get) => ({
  conversations: [],
  currentConversationId: null,
  messages: [],
  isLoading: false,
  inputValue: '',

  setConversations: (conversations) => set({ conversations }),

  setCurrentConversation: (id) => set({ currentConversationId: id, messages: [] }),

  addMessage: (message) =>
    set((state) => ({ messages: [...state.messages, message] })),

  clearMessages: () => set({ messages: [] }),

  setIsLoading: (loading) => set({ isLoading: loading }),

  setInputValue: (value) => set({ inputValue: value }),

  createConversation: () => {
    const newConv: Conversation = {
      id: String(Date.now()),
      title: '新会话',
      group: '今天',
      updatedAt: new Date().toISOString(),
    };
    set((state) => ({
      conversations: [newConv, ...state.conversations],
      currentConversationId: newConv.id,
      messages: [],
    }));
    return newConv;
  },

  deleteConversation: (id) =>
    set((state) => {
      const remaining = state.conversations.filter((c) => c.id !== id);
      return {
        conversations: remaining,
        currentConversationId:
          state.currentConversationId === id ? remaining[0]?.id || null : state.currentConversationId,
      };
    }),
}));