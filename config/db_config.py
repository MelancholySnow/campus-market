import sqlite3
import os

# 数据库文件路径
DB_PATH = os.path.join(os.path.dirname(__file__), 'campus_market.db')


def get_db():
    """获取数据库连接"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_database():
    """初始化数据库表结构"""
    conn = get_db()
    try:
        cursor = conn.cursor()

        # 用户表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password TEXT NOT NULL,
                nickname TEXT,
                createTime TEXT DEFAULT (datetime('now', 'localtime'))
            )
        """)

        # 商品表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS goods (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                price REAL NOT NULL,
                category TEXT,
                img TEXT,
                description TEXT,
                author TEXT,
                userId INTEGER NOT NULL,
                status TEXT DEFAULT '待售',
                stock INTEGER DEFAULT 1,
                createTime TEXT DEFAULT (datetime('now', 'localtime'))
            )
        """)

        # 购物车表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS cart (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                userId INTEGER NOT NULL,
                goodsId INTEGER NOT NULL,
                count INTEGER DEFAULT 1,
                createTime TEXT DEFAULT (datetime('now', 'localtime')),
                UNIQUE(userId, goodsId)
            )
        """)

        # 收藏表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS collect (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                userId INTEGER NOT NULL,
                goodsId INTEGER NOT NULL,
                createTime TEXT DEFAULT (datetime('now', 'localtime')),
                UNIQUE(userId, goodsId)
            )
        """)

        # 订单表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                orderNo TEXT UNIQUE,
                userId INTEGER NOT NULL,
                totalPrice REAL,
                status TEXT DEFAULT '待支付',
                createTime TEXT DEFAULT (datetime('now', 'localtime'))
            )
        """)

        # 订单明细表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS order_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                orderId INTEGER NOT NULL,
                goodsId INTEGER NOT NULL,
                goodsName TEXT,
                goodsPrice REAL,
                count INTEGER DEFAULT 1,
                FOREIGN KEY (orderId) REFERENCES orders(id)
            )
        """)

        # 消息表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fromUserId INTEGER NOT NULL,
                toUserId INTEGER NOT NULL,
                goodsId INTEGER,
                content TEXT NOT NULL,
                isRead INTEGER DEFAULT 0,
                createTime TEXT DEFAULT (datetime('now', 'localtime'))
            )
        """)

        # 退货申请表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS return_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                orderId INTEGER NOT NULL,
                userId INTEGER NOT NULL,
                reason TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                sellerReply TEXT,
                createTime TEXT DEFAULT (datetime('now', 'localtime')),
                FOREIGN KEY (orderId) REFERENCES orders(id)
            )
        """)

        conn.commit()

        # 兼容旧表：尝试添加 stock 列（忽略已存在的错误）
        try:
            cursor.execute("ALTER TABLE goods ADD COLUMN stock INTEGER DEFAULT 1")
            conn.commit()
        except:
            pass

        print("✅ 数据库初始化完成")
        return True
    except Exception as e:
        print(f"❌ 初始化失败: {e}")
        return False
    finally:
        conn.close()
