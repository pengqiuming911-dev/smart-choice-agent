"use client"

import { useState, useRef } from "react"
import { useSession } from "next-auth/react"
import { Input, Card, List, Typography, Tag, Spin, Empty, Space, Avatar, Button } from "antd"
import { RobotOutlined, UserOutlined, FileTextOutlined, LinkOutlined } from "@ant-design/icons"
import { queryWiki } from "@/lib/wiki-api"
import type { ChatMessage, WikiPage, RawSource } from "@/types"

const { TextArea } = Input
const { Title, Paragraph, Text } = Typography

function generateId() {
  return Math.random().toString(36).substring(2, 15) + Date.now().toString(36)
}

export default function ChatPage() {
  const { data: session } = useSession()
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState("")
  const [loading, setLoading] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }

  const handleSend = async () => {
    if (!input.trim() || loading) return

    const userMessage: ChatMessage = {
      id: generateId(),
      role: "user",
      content: input.trim(),
    }

    setMessages(prev => [...prev, userMessage])
    setInput("")
    setLoading(true)

    try {
      const userId = (session?.user as any)?.union_id || session?.user?.email

      const result = await queryWiki({
        question: userMessage.content,
        user_id: userId,
      })

      const assistantMessage: ChatMessage = {
        id: generateId(),
        role: "assistant",
        content: result.answer,
        wiki_pages: result.wiki_pages,
        raw_sources: result.raw_sources,
        confidence: result.confidence,
      }

      setMessages(prev => [...prev, assistantMessage])
    } catch (err) {
      const errorMessage: ChatMessage = {
        id: generateId(),
        role: "assistant",
        content: `抱歉，发生了错误：${err instanceof Error ? err.message : "未知错误"}`,
      }
      setMessages(prev => [...prev, errorMessage])
    } finally {
      setLoading(false)
      setTimeout(scrollToBottom, 100)
    }
  }

  const confidenceColor = (c?: string) => {
    if (c === "high") return "green"
    if (c === "medium") return "orange"
    return "red"
  }

  return (
    <div style={{ height: "100vh", display: "flex", flexDirection: "column", padding: 24 }}>
      <Title level={3} style={{ marginBottom: 16 }}>
        <RobotOutlined /> 智能体问答
      </Title>

      <Card
        style={{
          flex: 1,
          display: "flex",
          flexDirection: "column",
          overflow: "hidden",
        }}
        bodyStyle={{
          flex: 1,
          display: "flex",
          flexDirection: "column",
          padding: 0,
        }}
      >
        <div style={{ flex: 1, overflow: "auto", padding: 24 }}>
          {messages.length === 0 ? (
            <Empty
              description="输入问题，向知识库提问"
              style={{ marginTop: "30%" }}
            />
          ) : (
            <List
              dataSource={messages}
              renderItem={(msg) => (
                <List.Item style={{ display: "block", border: "none", padding: "12px 0" }}>
                  <div style={{ display: "flex", gap: 12, alignItems: "flex-start" }}>
                    <Avatar
                      icon={msg.role === "user" ? <UserOutlined /> : <RobotOutlined />}
                      style={{ background: msg.role === "user" ? "#1677ff" : "#52c41a" }}
                    />
                    <div style={{ flex: 1 }}>
                      <Space>
                        <Text strong>{msg.role === "user" ? "你" : "助手"}</Text>
                        {msg.confidence && msg.role === "assistant" && (
                          <Tag color={confidenceColor(msg.confidence)}>
                            置信度: {msg.confidence}
                          </Tag>
                        )}
                      </Space>

                      <Paragraph style={{ marginTop: 4, marginBottom: 8, whiteSpace: "pre-wrap" }}>
                        {msg.content}
                      </Paragraph>

                      {msg.wiki_pages && msg.wiki_pages.length > 0 && (
                        <div style={{ marginBottom: 8 }}>
                          <Text type="secondary" style={{ fontSize: 12 }}>
                            <LinkOutlined /> 引用 Wiki 页面：
                          </Text>
                          <div style={{ marginTop: 4 }}>
                            {msg.wiki_pages.map((page: WikiPage, i: number) => (
                              <Tag key={i} color="blue" style={{ marginBottom: 4 }}>
                                {page.title}
                              </Tag>
                            ))}
                          </div>
                        </div>
                      )}

                      {msg.raw_sources && msg.raw_sources.length > 0 && (
                        <div>
                          <Text type="secondary" style={{ fontSize: 12 }}>
                            <FileTextOutlined /> 原始来源：
                          </Text>
                          <div style={{ marginTop: 4 }}>
                            {msg.raw_sources.map((source: RawSource, i: number) => (
                              <Tag key={i} color="default" style={{ marginBottom: 4 }}>
                                {source.title}
                              </Tag>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                </List.Item>
              )}
            />
          )}
          <div ref={messagesEndRef} />
        </div>

        <div style={{
          borderTop: "1px solid #f0f0f0",
          padding: 16,
          display: "flex",
          gap: 12,
          background: "#fff",
        }}>
          <TextArea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onPressEnter={(e) => {
              if (!e.shiftKey) {
                e.preventDefault()
                handleSend()
              }
            }}
            placeholder="输入问题，按 Enter 发送，Shift+Enter 换行"
            autoSize={{ minRows: 1, maxRows: 4 }}
            style={{ flex: 1 }}
            disabled={loading}
          />
          <Button
            type="primary"
            onClick={handleSend}
            loading={loading}
            disabled={!input.trim()}
            style={{ alignSelf: "flex-end" }}
          >
            发送
          </Button>
        </div>
      </Card>

      {loading && (
        <div style={{ textAlign: "center", padding: 8, color: "#999" }}>
          <Spin size="small" /> AI 思考中...
        </div>
      )}
    </div>
  )
}