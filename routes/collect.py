from flask import Blueprint, request, jsonify
from config.db_config import get_db
import re

bp = Blueprint('collect', __name__, url_prefix='/api/collect')


def _normalize_img(img):
    if not img:
        return img
    return re.sub(r'^https?://[^/]+(?::\d+)?(?=/uploads/)', '', img)


@bp.route('/check', methods=['GET'])
def check_collect():
    """检查用户是否已收藏某商品"""
    user_id = request.args.get('userId')
    goods_id = request.args.get('goodsId')
    if not user_id or not goods_id:
        return jsonify({'code': 400, 'msg': '缺少参数'}), 400
    conn = get_db()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM collect WHERE userId = ? AND goodsId = ?", (user_id, goods_id))
        row = cursor.fetchone()
        return jsonify({'code': 200, 'data': {'collected': bool(row)}}), 200
    except Exception as e:
        print(f"检查收藏状态错误: {e}")
        return jsonify({'code': 500, 'msg': '服务器错误'}), 500
    finally:
        conn.close()


@bp.route('/add', methods=['POST'])
def add_to_collect():
    """加入收藏"""
    data = request.get_json(silent=True)
    if not data:
        return jsonify({'code': 400, 'msg': '请求数据格式错误，请使用JSON格式'}), 400

    user_id = data.get('userId')
    goods_id = data.get('goodsId')

    if not user_id or not goods_id:
        return jsonify({'code': 400, 'msg': '缺少用户ID或商品ID'}), 400

    conn = get_db()
    try:
        cursor = conn.cursor()
        # 检查商品是否存在且待售
        cursor.execute("SELECT id FROM goods WHERE id = ? AND status = '待售'", (goods_id,))
        if not cursor.fetchone():
            return jsonify({'code': 400, 'msg': '商品不存在或已售出'}), 400

        # 检查是否已收藏
        cursor.execute("SELECT id FROM collect WHERE userId = ? AND goodsId = ?", (user_id, goods_id))
        if cursor.fetchone():
            return jsonify({'code': 400, 'msg': '该商品已收藏'}), 400

        # 插入收藏记录
        cursor.execute(
            "INSERT INTO collect (userId, goodsId, createTime) VALUES (?, ?, CURRENT_TIMESTAMP)",
            (user_id, goods_id)
        )
        conn.commit()
        return jsonify({'code': 200, 'msg': '收藏成功'}), 200
    except Exception as e:
        conn.rollback()
        print(f"收藏商品错误: {e}")
        return jsonify({'code': 500, 'msg': '服务器错误'}), 500
    finally:
        conn.close()


@bp.route('/delete', methods=['DELETE'])
def cancel_collect():
    """取消收藏"""
    user_id = request.args.get('userId')
    goods_id = request.args.get('goodsId')

    if not user_id or not goods_id:
        return jsonify({'code': 400, 'msg': '缺少用户ID或商品ID'}), 400

    conn = get_db()
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM collect WHERE userId = ? AND goodsId = ?", (user_id, goods_id))
        conn.commit()
        return jsonify({'code': 200, 'msg': '取消收藏成功'}), 200
    except Exception as e:
        conn.rollback()
        print(f"取消收藏错误: {e}")
        return jsonify({'code': 500, 'msg': '服务器错误'}), 500
    finally:
        conn.close()


@bp.route('/list', methods=['GET'])
def list_collect():
    """
    获取我的收藏列表
    返回嵌套结构: [{userId, goodsId, goods: {img, name, price}}]
    """
    user_id = request.args.get('userId')
    if not user_id:
        return jsonify({'code': 400, 'msg': '缺少用户ID'}), 400

    conn = get_db()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT c.id, c.userId, c.goodsId, c.createTime,
                   g.name, g.price, g.img, g.status
            FROM collect c
            LEFT JOIN goods g ON c.goodsId = g.id
            WHERE c.userId = ?
            ORDER BY c.createTime DESC
        """, (user_id,))
        results = cursor.fetchall()

        # 组装为前端期望的嵌套结构
        collect_list = []
        for item in results:
            item = dict(item)
            create_time = item.get('createTime')
            if create_time:
                create_time = str(create_time)[:16]  # YYYY-MM-DD HH:MM
            collect_list.append({
                'id': item['id'],
                'userId': item['userId'],
                'goodsId': item['goodsId'],
                'createTime': create_time,
                'goods': {
                    'name': item['name'],
                    'price': item['price'],
                    'img': _normalize_img(item['img']),
                    'status': item['status']
                }
            })
        return jsonify({'code': 200, 'data': collect_list}), 200
    except Exception as e:
        print(f"获取收藏列表错误: {e}")
        return jsonify({'code': 500, 'msg': '服务器错误'}), 500
    finally:
        conn.close()
