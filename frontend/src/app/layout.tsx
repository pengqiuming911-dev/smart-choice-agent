import type { Metadata } from "next"
import "./globals.css"
import { Providers } from "@/providers/Providers"
import { AntdRegistry } from '@ant-design/nextjs-registry'

export const metadata: Metadata = {
  title: "LLM Wiki 智能知识库",
  description: "团队智能知识库问答系统",
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="zh-CN">
      <body>
        <Providers>
          <AntdRegistry>
            {children}
          </AntdRegistry>
        </Providers>
      </body>
    </html>
  )
}