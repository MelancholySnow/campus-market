from flask import Blueprint, request, jsonify
from config.db_config import get_db

bp = Blueprint('messages', __name__, url_prefix='/api/messages')


@bp.route('/send', methods=['POST'])
def send_message():
    """发送消息（支持关联商品）"""
    data = request.get_json(silent=True)
    required = ['fromUserId', 'toUserId', 'content']
    if not data or not all(k in data for k in required):
        return jsonify({'code': 400, 'msg': '参数缺失'}), 400

    conn = get_db()
    try:
        cursor = conn.cursor()
        # 检查接收者是否存在
        cursor.execute("SELECT 1 FROM users WHERE id = ?", (data['toUserId'],))
        if not cursor.fetchone():
            return jsonify({'code': 400, 'msg': '接收者不存在'}), 400

        # 检查关联商品是否可交易
        if data.get('goodsId'):
            cursor.execute("SELECT status FROM goods WHERE id = ?", (data['goodsId'],))
            goods = cursor.fetchone()
            if not goods or dict(goods)['status'] != '待售':
                return jsonify({'code': 400, 'msg': '商品不可交易'}), 400

        # 插入消息
        cursor.execute(
            """INSERT INTO messages (fromUserId, toUserId, goodsId, content, isRead)
            VALUES (?, ?, ?, ?, 0)""",
            (data['fromUserId'], data['toUserId'], data.get('goodsId'), data['content'])
        )
        conn.commit()
        return jsonify({'code': 200, 'msg': '消息发送成功'}), 200
    except Exception as e:
        conn.rollback()
        return jsonify({'code': 500, 'msg': f'消息发送失败: {str(e)}'}), 500
    finally:
        conn.close()


@bp.route('/list', methods=['GET'])
def get_messages():
    """获取用户消息列表（按时间倒序）"""
    user_id = request.args.get('userId')
    if not user_id:
        return jsonify({'code': 400, 'msg': '缺少userId参数'}), 400

    conn = get_db()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT m.id, m.fromUserId, m.toUserId, m.goodsId,
                   m.content, m.createTime, m.isRead,
                   u.nickname AS senderName,
                   g.name AS goodsName
            FROM messages m
            JOIN users u ON m.fromUserId = u.id
            LEFT JOIN goods g ON m.goodsId = g.id
            WHERE m.toUserId = ?
            ORDER BY m.createTime DESC
        """, (user_id,))
        results = [dict(row) for row in cursor.fetchall()]
        return jsonify({'code': 200, 'data': results}), 200
    except Exception as e:
        print(f"查询消息列表错误: {e}")
        return jsonify({'code': 500, 'msg': '服务器错误'}), 500
    finally:
        conn.close()


@bp.route('/conversations', methods=['GET'])
def get_conversations():
    """获取用户的所有对话列表（包含发送和接收的消息，按对话对象分组）"""
    user_id = request.args.get('userId')
    if not user_id:
        return jsonify({'code': 400, 'msg': '缺少userId参数'}), 400

    conn = get_db()
    try:
        cursor = conn.cursor()
        # 查询所有与该用户相关的消息，按对话对象分组，取最新一条
        cursor.execute("""
            SELECT
                partner.id AS partnerId,
                partner.nickname AS partnerName,
                latest.content AS lastContent,
                latest.createTime AS lastTime,
                latest.isRead AS lastIsRead,
                latest.fromUserId AS lastFromUserId,
                CASE WHEN latest.fromUserId = ? THEN '我' ELSE partner.nickname END AS lastSender,
                unread_count.cnt AS unreadCount,
                latest.goodsId AS goodsId,
                g.name AS goodsName
            FROM (
                -- 找出每个对话对象的最新消息ID
                SELECT
                    CASE WHEN fromUserId = ? THEN toUserId ELSE fromUserId END AS partnerId,
                    MAX(id) AS maxMsgId
                FROM messages
                WHERE fromUserId = ? OR toUserId = ?
                GROUP BY partnerId
            ) grouped
            JOIN messages latest ON latest.id = grouped.maxMsgId
            JOIN users partner ON partner.id = grouped.partnerId
            LEFT JOIN goods g ON latest.goodsId = g.id
            LEFT JOIN (
                -- 未读消息计数（仅统计对方发来且未读的）
                SELECT fromUserId AS partnerId, COUNT(*) AS cnt
                FROM messages
                WHERE toUserId = ? AND isRead = 0
                GROUP BY fromUserId
            ) unread_count ON unread_count.partnerId = grouped.partnerId
            ORDER BY latest.createTime DESC
        """, (user_id, user_id, user_id, user_id, user_id))
        results = [dict(row) for row in cursor.fetchall()]
        return jsonify({'code': 200, 'data': results}), 200
    except Exception as e:
        print(f"查询对话列表错误: {e}")
        return jsonify({'code': 500, 'msg': '服务器错误'}), 500
    finally:
        conn.close()


@bp.route('/chat', methods=['GET'])
def get_chat_history():
    """获取与指定用户的所有聊天记录"""
    user_id = request.args.get('userId')
    partner_id = request.args.get('partnerId')
    if not user_id or not partner_id:
        return jsonify({'code': 400, 'msg': '缺少userId或partnerId参数'}), 400

    conn = get_db()
    try:
        cursor = conn.cursor()
        # 获取两人之间的所有消息
        cursor.execute("""
            SELECT m.id, m.fromUserId, m.toUserId, m.goodsId,
                   m.content, m.createTime, m.isRead,
                   fu.nickname AS fromUserName,
                   tu.nickname AS toUserName,
                   g.name AS goodsName
            FROM messages m
            JOIN users fu ON m.fromUserId = fu.id
            JOIN users tu ON m.toUserId = tu.id
            LEFT JOIN goods g ON m.goodsId = g.id
            WHERE (m.fromUserId = ? AND m.toUserId = ?)
               OR (m.fromUserId = ? AND m.toUserId = ?)
            ORDER BY m.createTime ASC
        """, (user_id, partner_id, partner_id, user_id))

        results = [dict(row) for row in cursor.fetchall()]

        # 将对方发来的未读消息标记为已读
        cursor.execute("""
            UPDATE messages SET isRead = 1
            WHERE fromUserId = ? AND toUserId = ? AND isRead = 0
        """, (partner_id, user_id))
        conn.commit()

        return jsonify({'code': 200, 'data': results}), 200
    except Exception as e:
        print(f"查询聊天记录错误: {e}")
        return jsonify({'code': 500, 'msg': '服务器错误'}), 500
    finally:
        conn.close()
