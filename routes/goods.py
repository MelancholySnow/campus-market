from flask import Blueprint, request, jsonify, current_app
from config.db_config import get_db
from werkzeug.utils import secure_filename
import os
import uuid

bp = Blueprint('goods', __name__, url_prefix='/api/goods')

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def normalize_img_url(img):
    """将图片URL转为相对路径，兼容 localhost 和局域网 IP 访问"""
    if not img:
        return img
    # 将 http://localhost:8080/uploads/xxx 或 http://127.0.0.1:8080/uploads/xxx 转为 /uploads/xxx
    import re
    return re.sub(r'^https?://[^/]+(?::\d+)?(?=/uploads/)', '', img)


@bp.route('/list', methods=['GET'])
def list_goods():
    """获取全部待售商品列表"""
    conn = get_db()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, name, price, category, img, status, author
            FROM goods
            WHERE status = '待售'
            ORDER BY createTime DESC
        """)
        # 转换为普通字典列表，并修正图片路径
        results = [dict(row) for row in cursor.fetchall()]
        for r in results:
            r['img'] = normalize_img_url(r.get('img', ''))
        return jsonify({'code': 200, 'data': results}), 200
    except Exception as e:
        print(f"查询商品列表错误: {e}")
        return jsonify({'code': 500, 'msg': '服务器错误'}), 500
    finally:
        conn.close()


@bp.route('/category', methods=['GET'])
def get_goods_by_category():
    """按分类获取商品"""
    category = request.args.get('category')
    conn = get_db()
    try:
        cursor = conn.cursor()
        if category == '全部' or not category:
            cursor.execute("""
                SELECT id, name, price, img, author, category
                FROM goods
                WHERE status = '待售'
                ORDER BY createTime DESC
            """)
        else:
            cursor.execute("""
                SELECT id, name, price, img, author, category
                FROM goods
                WHERE status = '待售' AND category = ?
                ORDER BY createTime DESC
            """, (category,))
        results = [dict(row) for row in cursor.fetchall()]
        for r in results:
            r['img'] = normalize_img_url(r.get('img', ''))
        return jsonify({'code': 200, 'data': results}), 200
    except Exception as e:
        print(f"查询分类错误: {e}")
        return jsonify({'code': 500, 'msg': '服务器错误'}), 500
    finally:
        conn.close()


@bp.route('/detail', methods=['GET'])
def get_detail():
    """获取商品详情"""
    goods_id = request.args.get('id')
    if not goods_id:
        return jsonify({'code': 400, 'msg': '缺少商品ID'})

    conn = get_db()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, name, price, category, img, description,
                   author, userId, stock, status, createTime
            FROM goods WHERE id = ?
        """, (goods_id,))
        result = cursor.fetchone()
        if result:
            result = dict(result)
            result['img'] = normalize_img_url(result.get('img', ''))
            # SQLite 时间是字符串格式：YYYY-MM-DD HH:MM:SS
            time_obj = result.get('createTime')
            if time_obj:
                # 已经是字符串，直接截取前19位
                result['createTime'] = str(time_obj)[:19]
            else:
                result['createTime'] = '未知时间'
            return jsonify({'code': 200, 'data': result})
        else:
            return jsonify({'code': 404, 'msg': '商品不存在'})
    except Exception as e:
        print(f"查询详情错误: {e}")
        return jsonify({'code': 500, 'msg': '服务器错误'}), 500
    finally:
        conn.close()


@bp.route('/upload', methods=['POST'])
def upload_image():
    """上传商品图片"""
    if 'file' not in request.files:
        return jsonify({'code': 400, 'msg': '未选择文件'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'code': 400, 'msg': '未选择文件'}), 400
    if not allowed_file(file.filename):
        return jsonify({'code': 400, 'msg': '仅支持 png/jpg/jpeg/gif/webp 格式'}), 400

    # 检查文件大小
    file.seek(0, os.SEEK_END)
    size = file.tell()
    file.seek(0)
    if size > MAX_FILE_SIZE:
        return jsonify({'code': 400, 'msg': '图片大小不能超过5MB'}), 400

    # 生成唯一文件名
    ext = file.filename.rsplit('.', 1)[1].lower()
    filename = f"{uuid.uuid4().hex}.{ext}"

    # 保存到 uploads 目录
    upload_dir = os.path.join(current_app.root_path, 'uploads')
    os.makedirs(upload_dir, exist_ok=True)
    file.save(os.path.join(upload_dir, filename))

    # 返回可访问的URL（相对路径，兼容 localhost 和局域网 IP 访问）
    url = f"/uploads/{filename}"
    return jsonify({'code': 200, 'msg': '上传成功', 'data': {'url': url}}), 200


@bp.route('/publish', methods=['POST'])
def publish():
    """发布新商品"""
    data = request.get_json(silent=True)

    required = ['name', 'price', 'category', 'userId', 'author']
    if not data or not all(k in data for k in required):
        return jsonify({'code': 400, 'msg': '缺少必要参数'}), 400

    # 价格校验：必须为正数（支持小数）
    try:
        price = float(data['price'])
        if price <= 0:
            return jsonify({'code': 400, 'msg': '价格必须大于0'}), 400
        # 保留两位小数
        price = round(price, 2)
    except (ValueError, TypeError):
        return jsonify({'code': 400, 'msg': '价格格式错误'}), 400

    # 库存校验
    stock = data.get('stock', 1)
    try:
        stock = int(stock)
        if stock < 1 or stock > 9999:
            stock = 1
    except (ValueError, TypeError):
        stock = 1

    conn = get_db()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO goods
            (name, price, category, img, description, userId, author, status, stock, createTime)
            VALUES (?, ?, ?, ?, ?, ?, ?, '待售', ?, CURRENT_TIMESTAMP)""",
            (
                data['name'], price, data['category'],
                data.get('img', ''), data.get('description', ''),
                data['userId'], data['author'], stock
            )
        )
        conn.commit()
        return jsonify({'code': 200, 'msg': '发布成功'}), 200
    except Exception as e:
        conn.rollback()
        return jsonify({'code': 500, 'msg': f'发布失败: {str(e)}'}), 500
    finally:
        conn.close()


@bp.route('/myPublish', methods=['GET'])
def get_my_publish():
    """获取指定用户发布的商品列表"""
    user_id = request.args.get('userId')
    if not user_id:
        return jsonify({'code': 400, 'msg': '缺少用户ID'}), 400

    conn = get_db()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, name, price, img, description, stock, status, createTime
            FROM goods
            WHERE userId = ?
            ORDER BY createTime DESC
        """, (user_id,))
        results = [dict(row) for row in cursor.fetchall()]
        # 格式化时间：YYYY-MM-DD HH:MM:SS -> MM-DD HH:MM
        for item in results:
            item['img'] = normalize_img_url(item.get('img', ''))
            if item.get('createTime'):
                item['createTime'] = str(item['createTime'])[5:16]  # MM-DD HH:MM
        return jsonify({'code': 200, 'data': results}), 200
    except Exception as e:
        print(f"查询我的发布错误: {e}")
        return jsonify({'code': 500, 'msg': '服务器错误'}), 500
    finally:
        conn.close()


@bp.route('/search', methods=['GET'])
def search_goods():
    """模糊搜索商品（按名称和描述）"""
    keyword = request.args.get('keyword', '').strip()
    if not keyword:
        return jsonify({'code': 400, 'msg': '请输入搜索关键词'}), 400

    conn = get_db()
    try:
        cursor = conn.cursor()
        like_pattern = f'%{keyword}%'
        cursor.execute("""
            SELECT id, name, price, category, img, description, author, stock, status, createTime
            FROM goods
            WHERE status = '待售' AND (name LIKE ? OR description LIKE ? OR category LIKE ?)
            ORDER BY createTime DESC
        """, (like_pattern, like_pattern, like_pattern))
        results = [dict(row) for row in cursor.fetchall()]
        for r in results:
            r['img'] = normalize_img_url(r.get('img', ''))
        return jsonify({'code': 200, 'data': results, 'keyword': keyword}), 200
    except Exception as e:
        print(f"搜索商品错误: {e}")
        return jsonify({'code': 500, 'msg': '服务器错误'}), 500
    finally:
        conn.close()


@bp.route('/delete', methods=['DELETE'])
def delete_goods():
    """删除商品（需验证所有权，级联删除购物车和收藏记录）"""
    goods_id = request.args.get('id')
    user_id = request.args.get('userId')  # 新增：验证当前用户
    if not goods_id or not user_id:
        return jsonify({'code': 400, 'msg': '缺少商品ID或用户ID'}), 400

    conn = get_db()
    try:
        cursor = conn.cursor()
        # 检查商品是否存在并验证所有权
        cursor.execute("SELECT id, userId FROM goods WHERE id = ?", (goods_id,))
        goods = cursor.fetchone()
        if not goods:
            return jsonify({'code': 404, 'msg': '商品不存在'}), 404
        if dict(goods)['userId'] != int(user_id):
            return jsonify({'code': 403, 'msg': '无权删除该商品'}), 403

        # 级联删除关联数据
        cursor.execute("DELETE FROM cart WHERE goodsId = ?", (goods_id,))
        cursor.execute("DELETE FROM collect WHERE goodsId = ?", (goods_id,))
        cursor.execute("DELETE FROM goods WHERE id = ?", (goods_id,))
        conn.commit()
        return jsonify({'code': 200, 'msg': '删除成功，已同步清除关联数据'}), 200
    except Exception as e:
        conn.rollback()
        print(f"删除商品错误: {e}")
        return jsonify({'code': 500, 'msg': '服务器错误'}), 500
    finally:
        conn.close()
