"use client"

import { use, useEffect, useState } from "react"
import { Card, Typography, Spin, Button, Breadcrumb } from "antd"
import { BookOutlined, HomeOutlined, ArrowLeftOutlined } from "@ant-design/icons"
import { useRouter } from "next/navigation"
import { getWikiPage } from "@/lib/wiki-api"

const { Title, Text } = Typography

export default function WikiContentPage({
  params,
}: {
  params: Promise<{ path: string }>
}) {
  const { path: encodedPath } = use(params)
  const path = decodeURIComponent(encodedPath)
  const [content, setContent] = useState<string>("")
  const [title, setTitle] = useState<string>("")
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const router = useRouter()

  useEffect(() => {
    async function fetchPage() {
      try {
        const data = await getWikiPage(path)
        setContent(data.content || "")
        setTitle(data.title || path.split("/").pop()?.replace(".md", "") || "页面")
      } catch (err) {
        setError(err instanceof Error ? err.message : "加载失败")
      } finally {
        setLoading(false)
      }
    }
    if (path) fetchPage()
  }, [path])

  return (
    <div style={{ padding: 24 }}>
      <Breadcrumb
        style={{ marginBottom: 16 }}
        items={[
          { title: <HomeOutlined onClick={() => router.push("/wiki")} style={{ cursor: "pointer" }} /> },
          { title: <span onClick={() => router.push("/wiki")} style={{ cursor: "pointer" }}>Wiki 浏览</span> },
          { title: title },
        ]}
      />

      <Button
        icon={<ArrowLeftOutlined />}
        onClick={() => router.push("/wiki")}
        style={{ marginBottom: 16 }}
      >
        返回列表
      </Button>

      {loading ? (
        <div style={{ textAlign: "center", marginTop: 100 }}>
          <Spin size="large" />
          <Text type="secondary" style={{ display: "block", marginTop: 16 }}>加载中...</Text>
        </div>
      ) : error ? (
        <Card>
          <Text type="danger">{error}</Text>
        </Card>
      ) : (
        <Card
          title={<Title level={4}><BookOutlined /> {title}</Title>}
        >
          <div style={{ whiteSpace: "pre-wrap", lineHeight: 1.8 }}>
            {content}
          </div>
        </Card>
      )}
    </div>
  )
}