from flask import Blueprint, request, jsonify
from config.db_config import get_db
import re

bp = Blueprint('cart', __name__, url_prefix='/api/cart')


def _normalize_img(img):
    if not img:
        return img
    return re.sub(r'^https?://[^/]+(?::\d+)?(?=/uploads/)', '', img)


@bp.route('/add', methods=['POST'])
def add_to_cart():
    """加入购物车（重复商品自动数量+1，受库存限制）"""
    data = request.get_json(silent=True)
    if not data:
        return jsonify({'code': 400, 'msg': '请求数据格式错误，请使用JSON格式'}), 400

    user_id = data.get('userId')
    goods_id = data.get('goodsId')
    count = data.get('count', 1)

    if not user_id or not goods_id:
        return jsonify({'code': 400, 'msg': '缺少用户ID或商品ID'}), 400

    conn = get_db()
    try:
        cursor = conn.cursor()
        # 检查商品是否存在且待售，同时获取库存
        cursor.execute("SELECT id, status, stock, name FROM goods WHERE id = ?", (goods_id,))
        goods = cursor.fetchone()
        if not goods:
            return jsonify({'code': 400, 'msg': '商品不存在'}), 400
        goods = dict(goods)
        if goods['status'] != '待售':
            return jsonify({'code': 400, 'msg': '该商品已售出或下架'}), 400

        stock = goods['stock']
        if stock <= 0:
            return jsonify({'code': 400, 'msg': f'商品"{goods["name"]}"已售罄'}), 400

        # 检查购物车中是否已有该商品
        cursor.execute(
            "SELECT id, count FROM cart WHERE userId = ? AND goodsId = ?",
            (user_id, goods_id)
        )
        existing = cursor.fetchone()
        if existing:
            existing = dict(existing)
            new_count = existing['count'] + count
            if new_count > stock:
                new_count = stock
            if existing['count'] >= stock:
                return jsonify({'code': 400, 'msg': f'商品"{goods["name"]}"购物车已满（库存{stock}件）'}), 400
            cursor.execute(
                "UPDATE cart SET count = ? WHERE id = ?",
                (new_count, existing['id'])
            )
        else:
            # 首次加入也要检查库存
            if count > stock:
                count = stock
            cursor.execute(
                "INSERT INTO cart (userId, goodsId, count, createTime) VALUES (?, ?, ?, CURRENT_TIMESTAMP)",
                (user_id, goods_id, count)
            )
        conn.commit()
        return jsonify({'code': 200, 'msg': '已加入购物车'}), 200
    except Exception as e:
        conn.rollback()
        print(f"加入购物车错误: {e}")
        return jsonify({'code': 500, 'msg': '服务器错误'}), 500
    finally:
        conn.close()


@bp.route('/list', methods=['GET'])
def list_cart():
    """获取购物车列表（返回嵌套结构: {id, count, goods: {name, price, img}}）"""
    user_id = request.args.get('userId')
    if not user_id:
        return jsonify({'code': 400, 'msg': '缺少用户ID'}), 400

    conn = get_db()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT c.id, c.count, c.goodsId, c.createTime,
                   g.name, g.price, g.img, g.status, g.stock
            FROM cart c
            LEFT JOIN goods g ON c.goodsId = g.id
            WHERE c.userId = ?
            ORDER BY c.createTime DESC
        """, (user_id,))
        results = cursor.fetchall()

        # 组装为前端期望的嵌套结构
        cart_list = []
        for item in results:
            item = dict(item)
            create_time = item.get('createTime')
            if create_time:
                create_time = str(create_time)[:16]
            cart_list.append({
                'id': item['id'],
                'count': item['count'],
                'goodsId': item['goodsId'],
                'createTime': create_time,
                'goods': {
                    'name': item['name'],
                    'price': item['price'],
                    'img': _normalize_img(item['img']),
                    'status': item['status'],
                    'stock': item.get('stock', 1)
                }
            })
        return jsonify({'code': 200, 'data': cart_list}), 200
    except Exception as e:
        print(f"获取购物车列表错误: {e}")
        return jsonify({'code': 500, 'msg': '服务器错误'}), 500
    finally:
        conn.close()


@bp.route('/update', methods=['PUT'])
def update_cart():
    """修改购物车商品数量"""
    cart_id = request.args.get('id')
    count = request.args.get('count')

    if not cart_id or not count:
        return jsonify({'code': 400, 'msg': '缺少参数'}), 400

    try:
        count = int(count)
        if count < 1:
            return jsonify({'code': 400, 'msg': '数量不能小于1'}), 400
    except (ValueError, TypeError):
        return jsonify({'code': 400, 'msg': '数量格式错误'}), 400

    conn = get_db()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT c.id, c.goodsId, g.stock, g.name FROM cart c JOIN goods g ON c.goodsId = g.id WHERE c.id = ?", (cart_id,))
        cart_item = cursor.fetchone()
        if not cart_item:
            return jsonify({'code': 404, 'msg': '购物车项不存在'}), 404

        cart_item = dict(cart_item)
        if count > cart_item['stock']:
            return jsonify({'code': 400, 'msg': f'商品"{cart_item["name"]}"库存不足，最多{cart_item["stock"]}件'}), 400

        cursor.execute("UPDATE cart SET count = ? WHERE id = ?", (count, cart_id))
        conn.commit()
        return jsonify({'code': 200, 'msg': '修改成功'}), 200
    except Exception as e:
        conn.rollback()
        print(f"修改购物车数量错误: {e}")
        return jsonify({'code': 500, 'msg': '服务器错误'}), 500
    finally:
        conn.close()


@bp.route('/delete', methods=['DELETE'])
def delete_cart():
    """删除购物车项"""
    cart_id = request.args.get('id')
    if not cart_id:
        return jsonify({'code': 400, 'msg': '缺少购物车项ID'}), 400

    conn = get_db()
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM cart WHERE id = ?", (cart_id,))
        conn.commit()
        return jsonify({'code': 200, 'msg': '删除成功'}), 200
    except Exception as e:
        conn.rollback()
        print(f"删除购物车项错误: {e}")
        return jsonify({'code': 500, 'msg': '服务器错误'}), 500
    finally:
        conn.close()


@bp.route('/submit', methods=['POST'])
def submit_order():
    """提交订单：将购物车中的商品生成订单，扣减库存"""
    data = request.get_json(silent=True)
    if not data:
        return jsonify({'code': 400, 'msg': '请求数据格式错误，请使用JSON格式'}), 400

    user_id = data.get('userId')
    if not user_id:
        return jsonify({'code': 400, 'msg': '缺少用户ID'}), 400

    conn = get_db()
    try:
        cursor = conn.cursor()

        # 1. 查询购物车中的所有商品
        cursor.execute("""
            SELECT c.id AS cartId, c.goodsId, c.count,
                   g.name, g.price, g.stock, g.status, g.userId AS sellerId
            FROM cart c
            JOIN goods g ON c.goodsId = g.id
            WHERE c.userId = ?
        """, (user_id,))
        cart_items = [dict(row) for row in cursor.fetchall()]

        if not cart_items:
            return jsonify({'code': 400, 'msg': '购物车为空，无法提交订单'}), 400

        # 2. 校验：商品状态、库存是否充足、不能购买自己的商品
        insufficient = []
        for item in cart_items:
            if item['status'] != '待售':
                insufficient.append(f"「{item['name']}」已下架或售出")
            elif item['sellerId'] == int(user_id):
                insufficient.append(f"「{item['name']}」是您自己发布的商品，不能购买")
            elif item['stock'] < item['count']:
                insufficient.append(f"「{item['name']}」库存不足（剩余{item['stock']}件）")

        if insufficient:
            return jsonify({'code': 400, 'msg': '以下商品无法下单：\n' + '\n'.join(insufficient)}), 400

        # 3. 计算总价
        total_price = sum(item['price'] * item['count'] for item in cart_items)

        # 4. 生成订单号
        import time
        order_no = f"ORDER{int(time.time() * 1000)}{user_id}"

        # 5. 创建订单（默认已支付）
        cursor.execute(
            "INSERT INTO orders (orderNo, userId, totalPrice, status, createTime) VALUES (?, ?, ?, '已支付', CURRENT_TIMESTAMP)",
            (order_no, user_id, total_price)
        )
        order_id = cursor.lastrowid

        # 6. 插入订单明细 + 扣减库存
        for item in cart_items:
            cursor.execute(
                "INSERT INTO order_items (orderId, goodsId, goodsName, goodsPrice, count) VALUES (?, ?, ?, ?, ?)",
                (order_id, item['goodsId'], item['name'], item['price'], item['count'])
            )
            # 扣减库存
            new_stock = item['stock'] - item['count']
            new_status = '待售' if new_stock > 0 else '已售出'
            cursor.execute(
                "UPDATE goods SET stock = ?, status = ? WHERE id = ?",
                (new_stock, new_status, item['goodsId'])
            )

        # 7. 清空该用户的购物车
        cursor.execute("DELETE FROM cart WHERE userId = ?", (user_id,))

        conn.commit()
        return jsonify({
            'code': 200,
            'msg': '订单提交成功',
            'data': {
                'orderId': order_id,
                'orderNo': order_no,
                'totalPrice': total_price
            }
        }), 200
    except Exception as e:
        conn.rollback()
        print(f"提交订单错误: {e}")
        return jsonify({'code': 500, 'msg': f'订单提交失败: {str(e)}'}), 500
    finally:
        conn.close()


@bp.route('/orders', methods=['GET'])
def list_orders():
    """获取用户订单列表"""
    user_id = request.args.get('userId')
    if not user_id:
        return jsonify({'code': 400, 'msg': '缺少用户ID'}), 400

    conn = get_db()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, orderNo, totalPrice, status, createTime
            FROM orders
            WHERE userId = ?
            ORDER BY createTime DESC
        """, (user_id,))
        orders = [dict(row) for row in cursor.fetchall()]

        # 为每个订单查询明细
        for order in orders:
            cursor.execute("""
                SELECT goodsName, goodsPrice, count
                FROM order_items
                WHERE orderId = ?
            """, (order['id'],))
            order['items'] = [dict(row) for row in cursor.fetchall()]
            # 格式化时间
            if order.get('createTime'):
                order['createTime'] = str(order['createTime'])[:19]

        return jsonify({'code': 200, 'data': orders}), 200
    except Exception as e:
        print(f"查询订单列表错误: {e}")
        return jsonify({'code': 500, 'msg': '服务器错误'}), 500
    finally:
        conn.close()


@bp.route('/orders/return/request', methods=['POST'])
def request_return():
    """申请退货"""
    data = request.get_json(silent=True)
    if not data:
        return jsonify({'code': 400, 'msg': '请求数据格式错误'}), 400

    user_id = data.get('userId')
    order_id = data.get('orderId')
    reason = (data.get('reason') or '').strip()

    if not user_id or not order_id or not reason:
        return jsonify({'code': 400, 'msg': '缺少必要参数（userId/orderId/reason）'}), 400
    if len(reason) < 5:
        return jsonify({'code': 400, 'msg': '退货理由至少5个字'}), 400
    if len(reason) > 500:
        return jsonify({'code': 400, 'msg': '退货理由不能超过500字'}), 400

    conn = get_db()
    try:
        cursor = conn.cursor()

        # 验证订单是否存在且属于该用户
        cursor.execute("SELECT id, status FROM orders WHERE id = ? AND userId = ?", (order_id, user_id))
        order = cursor.fetchone()
        if not order:
            return jsonify({'code': 404, 'msg': '订单不存在或不属于您'}), 404

        order_status = dict(order)['status']
        if order_status != '已支付':
            return jsonify({'code': 400, 'msg': '该订单状态不允许申请退款'}), 400

        # 检查是否已有退货申请
        cursor.execute("SELECT id, status FROM return_requests WHERE orderId = ? AND userId = ?", (order_id, user_id))
        existing = cursor.fetchone()
        if existing:
            existing_status = dict(existing)['status']
            if existing_status == 'pending':
                return jsonify({'code': 400, 'msg': '已有待处理的退货申请，请耐心等待'}), 400
            elif existing_status == 'approved':
                return jsonify({'code': 400, 'msg': '该订单退货已通过'}), 400

        # 创建退货申请
        cursor.execute(
            "INSERT INTO return_requests (orderId, userId, reason, status, createTime) VALUES (?, ?, ?, 'pending', CURRENT_TIMESTAMP)",
            (order_id, user_id, reason)
        )
        conn.commit()
        return jsonify({'code': 200, 'msg': '退货申请已提交，等待卖家审核'}), 200
    except Exception as e:
        conn.rollback()
        print(f"申请退货错误: {e}")
        return jsonify({'code': 500, 'msg': '服务器错误'}), 500
    finally:
        conn.close()


@bp.route('/orders/return/list', methods=['GET'])
def list_return_requests():
    """查看退货申请列表（买家看自己的，卖家看收到自己商品的退货申请）"""
    user_id = request.args.get('userId')
    role = request.args.get('role', 'buyer')  # buyer 或 seller

    if not user_id:
        return jsonify({'code': 400, 'msg': '缺少用户ID'}), 400

    conn = get_db()
    try:
        cursor = conn.cursor()

        if role == 'seller':
            # 卖家：查看自己售出商品的退货申请
            cursor.execute("""
                SELECT DISTINCT rr.id, rr.orderId, rr.userId AS buyerId, rr.reason, rr.status, rr.sellerReply, rr.createTime,
                       u.nickname AS buyerName, o.orderNo, o.totalPrice
                FROM return_requests rr
                JOIN orders o ON rr.orderId = o.id
                JOIN order_items oi ON oi.orderId = o.id AND oi.goodsId IN (
                    SELECT id FROM goods WHERE userId = ?
                )
                JOIN users u ON rr.userId = u.id
                ORDER BY rr.createTime DESC
            """, (user_id,))
        else:
            # 买家：查看自己的退货申请
            cursor.execute("""
                SELECT rr.id, rr.orderId, rr.userId, rr.reason, rr.status, rr.sellerReply, rr.createTime,
                       o.orderNo, o.totalPrice
                FROM return_requests rr
                JOIN orders o ON rr.orderId = o.id
                WHERE rr.userId = ?
                ORDER BY rr.createTime DESC
            """, (user_id,))

        results = []
        for row in cursor.fetchall():
            item = dict(row)
            if item.get('createTime'):
                item['createTime'] = str(item['createTime'])[:19]
            results.append(item)

        return jsonify({'code': 200, 'data': results}), 200
    except Exception as e:
        print(f"查询退货列表错误: {e}")
        return jsonify({'code': 500, 'msg': '服务器错误'}), 500
    finally:
        conn.close()


@bp.route('/orders/return/handle', methods=['PUT'])
def handle_return():
    """卖家处理退货申请（同意/拒绝）"""
    data = request.get_json(silent=True)
    if not data:
        return jsonify({'code': 400, 'msg': '请求数据格式错误'}), 400

    return_id = data.get('returnId')
    action = data.get('action')  # 'approve' 或 'reject'
    seller_reply = (data.get('sellerReply') or '').strip()
    seller_id = data.get('sellerId')

    if not return_id or not action or not seller_id:
        return jsonify({'code': 400, 'msg': '缺少必要参数'}), 400
    if action not in ('approve', 'reject'):
        return jsonify({'code': 400, 'msg': '操作类型无效'}), 400

    conn = get_db()
    try:
        cursor = conn.cursor()

        # 验证退货申请存在，且卖家有权处理
        cursor.execute("""
            SELECT rr.id, rr.orderId, rr.status, o.status AS orderStatus,
                   (SELECT g2.userId FROM order_items oi2
                    JOIN goods g2 ON oi2.goodsId = g2.id
                    WHERE oi2.orderId = rr.orderId LIMIT 1) AS sellerId
            FROM return_requests rr
            JOIN orders o ON rr.orderId = o.id
            WHERE rr.id = ?
        """, (return_id,))
        req = cursor.fetchone()
        if not req:
            return jsonify({'code': 404, 'msg': '退货申请不存在'}), 404

        req = dict(req)
        if req['status'] != 'pending':
            return jsonify({'code': 400, 'msg': '该申请已处理，无法重复操作'}), 400
        if req['sellerId'] != int(seller_id):
            return jsonify({'code': 403, 'msg': '您无权处理该退货申请'}), 403

        if action == 'approve':
            new_rr_status = 'approved'
            new_order_status = '已退款'
            reply = seller_reply or '卖家已同意退款'

            # 恢复库存：将订单中商品的库存加回
            cursor.execute("""
                SELECT goodsId, count FROM order_items WHERE orderId = ?
            """, (req['orderId'],))
            for item in cursor.fetchall():
                item = dict(item)
                cursor.execute(
                    "UPDATE goods SET stock = stock + ?, status = '待售' WHERE id = ?",
                    (item['count'], item['goodsId'])
                )
        else:
            new_rr_status = 'rejected'
            new_order_status = '已支付'  # 拒绝后退回原状态
            reply = seller_reply or '卖家拒绝了您的退货申请'
            if not seller_reply:
                return jsonify({'code': 400, 'msg': '拒绝退货请填写理由'}), 400

        # 更新退货申请状态
        cursor.execute(
            "UPDATE return_requests SET status = ?, sellerReply = ? WHERE id = ?",
            (new_rr_status, reply, return_id)
        )
        # 更新订单状态
        cursor.execute(
            "UPDATE orders SET status = ? WHERE id = ?",
            (new_order_status, req['orderId'])
        )

        conn.commit()
        return jsonify({'code': 200, 'msg': '处理成功'}), 200
    except Exception as e:
        conn.rollback()
        print(f"处理退货错误: {e}")
        return jsonify({'code': 500, 'msg': '服务器错误'}), 500
    finally:
        conn.close()


@bp.route('/orders/return/check', methods=['GET'])
def check_return_status():
    """检查订单是否已有退货申请"""
    order_id = request.args.get('orderId')
    user_id = request.args.get('userId')

    if not order_id or not user_id:
        return jsonify({'code': 400, 'msg': '缺少参数'}), 400

    conn = get_db()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, status, reason, sellerReply FROM return_requests WHERE orderId = ? AND userId = ? ORDER BY createTime DESC LIMIT 1",
            (order_id, user_id)
        )
        result = cursor.fetchone()
        if result:
            return jsonify({'code': 200, 'data': dict(result)}), 200
        return jsonify({'code': 200, 'data': None}), 200
    except Exception as e:
        print(f"检查退货状态错误: {e}")
        return jsonify({'code': 500, 'msg': '服务器错误'}), 500
    finally:
        conn.close()
