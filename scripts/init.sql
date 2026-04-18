-- 文档元数据表
CREATE TABLE IF NOT EXISTS documents (
    id SERIAL PRIMARY KEY,
    document_id VARCHAR(64) UNIQUE NOT NULL,  -- 飞书 document_id / node_token
    space_id VARCHAR(64),                      -- 飞书知识空间ID
    obj_type VARCHAR(32) NOT NULL,             -- docx / sheet / bitable / wiki
    title TEXT,
    path TEXT,                                  -- 在知识空间里的路径
    content_md TEXT,                           -- 转换后的Markdown全文
    owner_id VARCHAR(64),                      -- 文档所有者 open_id
    last_edit_time TIMESTAMP,
    synced_at TIMESTAMP DEFAULT NOW(),
    chunk_count INT DEFAULT 0,
    status VARCHAR(16) DEFAULT 'active'        -- active / deleted
);
CREATE INDEX idx_documents_space ON documents(space_id);
CREATE INDEX idx_documents_status ON documents(status);

-- 文档权限表 (简化版:记录哪些用户/部门可以访问某文档)
CREATE TABLE IF NOT EXISTS document_permissions (
    id SERIAL PRIMARY KEY,
    document_id VARCHAR(64) NOT NULL,
    principal_type VARCHAR(16) NOT NULL,       -- user / department / tenant
    principal_id VARCHAR(64) NOT NULL,
    perm VARCHAR(16) DEFAULT 'read',           -- read / edit
    UNIQUE(document_id, principal_type, principal_id)
);
CREATE INDEX idx_perm_doc ON document_permissions(document_id);
CREATE INDEX idx_perm_principal ON document_permissions(principal_type, principal_id);

-- 对话审计表 (金融合规要求)
CREATE TABLE IF NOT EXISTS chat_logs (
    id BIGSERIAL PRIMARY KEY,
    session_id VARCHAR(64),
    user_open_id VARCHAR(64) NOT NULL,
    user_name VARCHAR(128),
    question TEXT NOT NULL,
    answer TEXT,
    retrieved_chunks JSONB,                    -- 检索到的chunk信息(用于追溯)
    citations JSONB,                           -- 引用的文档列表
    latency_ms INT,
    llm_model VARCHAR(64),
    created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX idx_chat_user ON chat_logs(user_open_id);
CREATE INDEX idx_chat_time ON chat_logs(created_at);

-- 合格投资者白名单 (私募场景核心合规表)
CREATE TABLE IF NOT EXISTS qualified_investors (
    user_open_id VARCHAR(64) PRIMARY KEY,
    name VARCHAR(128),
    verified_at TIMESTAMP,
    expire_at TIMESTAMP,
    level VARCHAR(16) DEFAULT 'standard'       -- standard / professional
);