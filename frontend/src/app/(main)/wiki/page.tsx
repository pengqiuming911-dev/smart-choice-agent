"use client"

import { useEffect, useState } from "react"
import { Card, List, Typography, Tag, Spin, Empty } from "antd"
import { BookOutlined, FileTextOutlined } from "@ant-design/icons"
import { useRouter } from "next/navigation"
import { getWikiList } from "@/lib/wiki-api"
import type { WikiListResponse, WikiPageItem } from "@/types"

const { Title, Text } = Typography

const typeColors: Record<string, string> = {
  entity: "blue",
  concept: "purple",
  overview: "orange",
}

const accessColors: Record<string, string> = {
  public: "green",
  "dept-sales": "orange",
  "dept-tech": "blue",
  admin: "red",
}

export default function WikiPage() {
  const [pages, setPages] = useState<WikiPageItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const router = useRouter()

  useEffect(() => {
    async function fetchWiki() {
      try {
        const data = await getWikiList()
        setPages(data.pages || [])
      } catch (err) {
        setError(err instanceof Error ? err.message : "加载失败")
      } finally {
        setLoading(false)
      }
    }
    fetchWiki()
  }, [])

  if (loading) {
    return (
      <div style={{ padding: 24 }}>
        <Title level={3}><BookOutlined /> Wiki 浏览</Title>
        <div style={{ textAlign: "center", marginTop: 100 }}>
          <Spin size="large" />
          <Text type="secondary" style={{ display: "block", marginTop: 16 }}>加载中...</Text>
        </div>
      </div>
    )
  }

  return (
    <div style={{ padding: 24 }}>
      <Title level={3} style={{ marginBottom: 24 }}>
        <BookOutlined /> Wiki 浏览
      </Title>

      {error ? (
        <Card>
          <Text type="danger">{error}</Text>
        </Card>
      ) : pages.length === 0 ? (
        <Card>
          <Empty description="暂无 Wiki 页面，请先同步飞书文档" />
        </Card>
      ) : (
        <List
          grid={{ gutter: 16, xs: 1, sm: 2, md: 3, lg: 3, xl: 4, xxl: 4 }}
          dataSource={pages}
          renderItem={(page: WikiPageItem) => (
            <List.Item>
              <Card
                hoverable
                onClick={() => router.push(`/wiki/${encodeURIComponent(page.path)}`)}
                style={{ cursor: "pointer" }}
              >
                <div style={{ display: "flex", alignItems: "flex-start", gap: 8 }}>
                  <FileTextOutlined style={{ fontSize: 24, color: "#1890ff", marginTop: 4 }} />
                  <div style={{ flex: 1 }}>
                    <Text strong style={{ display: "block", fontSize: 15, marginBottom: 8 }}>
                      {page.title}
                    </Text>
                    <div style={{ display: "flex", gap: 4, flexWrap: "wrap" }}>
                      <Tag color={typeColors[page.type] || "default"}>
                        {page.type || "page"}
                      </Tag>
                      <Tag color={accessColors[page.access] || "default"}>
                        {page.access || "public"}
                      </Tag>
                    </div>
                  </div>
                </div>
              </Card>
            </List.Item>
          )}
        />
      )}
    </div>
  )
}