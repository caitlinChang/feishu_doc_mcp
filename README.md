# 飞书文档API技术调研

## 概述

本调研详细介绍了如何通过飞书文档链接调用飞书开放平台的API来获取文档内容。

## API核心信息

### 1. 文档链接格式
- **旧版文档**: `https://{domain}.feishu.cn/docs/{doc_token}`
- **新版文档**: `https://{domain}.feishu.cn/docx/{doc_token}`

### 2. 主要API端点

#### 旧版文档API
- 获取富文本内容: `GET /open-apis/doc/v2/{doc_token}/content`
- 获取纯文本内容: `GET /open-apis/doc/v2/{doc_token}/raw_content`

#### 新版文档API (Docx)
- 获取文档块: `GET /open-apis/docx/v1/documents/{document_id}/blocks`
- 获取纯文本内容: `GET /open-apis/docx/v1/documents/{document_id}/raw_content`

## 使用流程

### 1. 准备工作
1. 在[飞书开放平台](https://open.feishu.cn/)创建应用
2. 获取应用的 `App ID` 和 `App Secret`
3. 为应用添加文档相关权限

### 2. 权限要求
应用需要具备以下权限：
- 查看、评论、编辑和管理文档
- 具体权限根据操作类型在开放平台配置

### 3. 调用步骤
1. **获取访问令牌**
   - 使用 `App ID` 和 `App Secret` 获取 `tenant_access_token`
   - 调用 `POST /auth/v3/tenant_access_token/internal/`

2. **提取文档标识**
   - 从文档链接中提取 `doc_token`

3. **调用内容API**
   - 在请求头中添加 `Authorization: Bearer {access_token}`
   - 调用相应的内容获取接口

## 代码示例

查看 `feishu_doc_api_research.py` 文件获取完整的Python实现示例。

## 注意事项

### 1. 权限控制
- 应用权限和文档权限都需要满足
- 确保应用有权限访问目标文档

### 2. 版本差异
- 旧版和新版文档使用不同的API
- 新版Docx API功能更丰富，建议优先使用

### 3. 错误处理
- 处理网络请求异常
- 检查API返回的code字段（0表示成功）
- 处理权限不足等错误情况

### 4. 频率限制
- 注意API调用频率限制
- 合理设置重试机制

## 官方文档参考

- [飞书开放平台文档](https://open.feishu.cn/document)
- [文档API详细说明](https://feishu.apifox.cn/)
- [权限管理指南](https://open.feishu.cn/document/ukTMukTMukTM/uQjN3QjL0YzN04CN2cDN)

## 依赖要求

- Python 3.6+
- requests >= 2.28.0

安装依赖：
```bash
pip install -r requirements.txt
```

## 技术支持

如遇问题，可参考：
1. 飞书开放平台官方文档
2. 飞书开发者社区
3. GitHub相关开源项目
