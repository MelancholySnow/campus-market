# 🏫 校园二手交易平台

大二 Python 课程结课作业 —— 基于 Flask 的校园闲置物品交易 Web 应用。

## 功能特性

- 🔐 **用户系统** — 注册（学号+密码复杂度校验）、登录、修改密码、编辑资料
- 📦 **商品管理** — 发布、分类浏览、模糊搜索、图片上传、详情查看
- 🛒 **购物车** — 加入/修改/删除，受库存限制，防超卖
- 📋 **订单系统** — 提交订单、订单列表、明细查看
- 💬 **站内消息** — 发送消息、对话列表、已读/未读标记
- ⭐ **商品收藏** — 收藏/取消收藏、收藏列表
- 🔄 **退货售后** — 买家申请退货、卖家同意/拒绝、库存自动恢复

## 技术栈

| 层次 | 技术 |
|------|------|
| 后端框架 | Python Flask |
| 数据库 | SQLite |
| 前端 | HTML + CSS + JavaScript |
| HTTP 客户端 | Axios |
| 密码哈希 | Werkzeug (pbkdf2:sha256) |
| 跨域 | Flask-CORS |

## 项目结构

```
campus_backend/
├── app.py                      # Flask 入口，注册蓝图、静态文件托管
├── config/
│   └── db_config.py            # 数据库连接与 8 张表的初始化
├── routes/
│   ├── auth.py                 # 注册、登录、修改密码、编辑资料
│   ├── goods.py                # 商品 CRUD、图片上传、搜索
│   ├── cart.py                 # 购物车、订单、退货
│   ├── collect.py              # 收藏
│   └── messages.py             # 站内消息、对话
├── front/                      # 前端页面
│   ├── index.html              # 首页（商品列表、分类、搜索）
│   ├── login.html / register.html
│   ├── detail.html             # 商品详情
│   ├── publish.html            # 发布闲置
│   ├── cart.html               # 购物车
│   ├── order.html              # 订单管理
│   ├── user.html               # 个人中心（发布/收藏/订单/消息）
│   └── common.js               # 公共 JS（API 封装、工具函数）
├── uploads/                    # 上传的图片
├── requirements.txt            # Python 依赖
└── .gitignore
```

## 数据库设计

8 张表：`users`（用户）、`goods`（商品）、`cart`（购物车）、`collect`（收藏）、`orders`（订单）、`order_items`（订单明细）、`messages`（消息）、`return_requests`（退货申请）。

订单明细通过外键关联订单主表，购物车和收藏用联合唯一约束防止重复。

## 快速开始

### 环境要求

- Python 3.8+
- pip

### 安装与运行

```bash
# 1. 安装依赖
pip install flask flask-cors werkzeug

# 2. 启动服务
python app.py

# 3. 打开浏览器访问
http://localhost:8080
```

> 前端既支持通过 `http://localhost:8080` 访问，也支持直接双击 HTML 文件通过 `file://` 协议打开（自动适配后端地址）。

## API 概览

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/register` | 用户注册 |
| POST | `/api/login` | 用户登录 |
| PUT | `/api/user/update` | 修改昵称 |
| PUT | `/api/user/changePassword` | 修改密码 |
| GET | `/api/goods/list` | 商品列表 |
| GET | `/api/goods/category` | 按分类查询 |
| GET | `/api/goods/search` | 模糊搜索 |
| GET | `/api/goods/detail` | 商品详情 |
| POST | `/api/goods/publish` | 发布商品 |
| POST | `/api/goods/upload` | 上传图片 |
| DELETE | `/api/goods/delete` | 删除商品 |
| POST | `/api/cart/add` | 加入购物车 |
| GET | `/api/cart/list` | 购物车列表 |
| PUT | `/api/cart/update` | 修改数量 |
| DELETE | `/api/cart/delete` | 删除购物车项 |
| POST | `/api/cart/submit` | 提交订单 |
| GET | `/api/cart/orders` | 订单列表 |
| POST | `/api/collect/add` | 加入收藏 |
| DELETE | `/api/collect/delete` | 取消收藏 |
| GET | `/api/collect/list` | 收藏列表 |
| GET | `/api/collect/check` | 检查收藏状态 |
| POST | `/api/messages/send` | 发送消息 |
| GET | `/api/messages/conversations` | 对话列表 |
| GET | `/api/messages/chat` | 聊天记录 |

## 改进方向

- [ ] 引入 JWT Token 认证替代明文 userId 传参
- [ ] 商品列表分页（LIMIT + OFFSET）
- [ ] 原子库存扣减防止并发超卖
- [ ] 图片上传校验文件头（magic bytes）
- [ ] 对接模拟支付流程
