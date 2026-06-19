from flask import Blueprint, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from config.db_config import get_db
import re

bp = Blueprint('auth', __name__, url_prefix='/api')

# 敏感词列表（可扩展）
SENSITIVE_WORDS = ['admin', '管理员', '官方', '客服', '系统', 'test', '测试账号',
    'fuck', 'shit', '操', '傻逼', 'sb', '妈的', '滚', '死', '杀']


def validate_password(password):
    """密码复杂度校验：8-32位，至少含大写/小写/数字/特殊字符中的三类"""
    if len(password) < 8 or len(password) > 32:
        return False, '密码长度需为8-32位'
    categories = 0
    if re.search(r'[A-Z]', password): categories += 1
    if re.search(r'[a-z]', password): categories += 1
    if re.search(r'[0-9]', password): categories += 1
    if re.search(r'[^A-Za-z0-9]', password): categories += 1
    if categories < 3:
        return False, '密码需包含大写字母、小写字母、数字、特殊字符中的至少三类'
    return True, ''


def validate_nickname(nickname):
    """昵称敏感词校验"""
    if not nickname or len(nickname.strip()) == 0:
        return False, '昵称不能为空'
    if len(nickname) > 20:
        return False, '昵称不能超过20个字符'
    lower = nickname.lower()
    for word in SENSITIVE_WORDS:
        if word.lower() in lower:
            return False, f'昵称包含不当词汇，请修改'
    return True, ''


def validate_student_id(username):
    """学号格式校验：纯数字，6-15位"""
    if not username or not re.match(r'^\d{6,15}$', username):
        return False, '学号需为6-15位纯数字'
    return True, ''


@bp.route('/register', methods=['POST'])
def register():
    """用户注册"""
    data = request.get_json(silent=True)
    if not data:
        return jsonify({'code': 400, 'msg': '请求数据格式错误，请使用JSON格式'}), 400

    username = (data.get('username') or '').strip()
    password = (data.get('password') or '').strip()
    nickname = (data.get('nickname') or '').strip()

    if not username or not password:
        return jsonify({'code': 400, 'msg': '用户名和密码不能为空'}), 400

    # 学号格式校验
    valid, msg = validate_student_id(username)
    if not valid:
        return jsonify({'code': 400, 'msg': msg}), 400

    # 密码复杂度校验
    valid, msg = validate_password(password)
    if not valid:
        return jsonify({'code': 400, 'msg': msg}), 400

    # 昵称敏感词校验
    if nickname:
        valid, msg = validate_nickname(nickname)
        if not valid:
            return jsonify({'code': 400, 'msg': msg}), 400

    conn = get_db()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
        if cursor.fetchone():
            return jsonify({'code': 400, 'msg': '用户名已存在'}), 400

        hashed_pw = generate_password_hash(password)
        cursor.execute(
            "INSERT INTO users (username, password, nickname) VALUES (?, ?, ?)",
            (username, hashed_pw, nickname)
        )
        conn.commit()
        return jsonify({'code': 200, 'msg': '注册成功'}), 200
    except Exception as e:
        conn.rollback()
        print(f"注册错误: {e}")
        return jsonify({'code': 500, 'msg': '服务器错误'}), 500
    finally:
        conn.close()


@bp.route('/login', methods=['POST'])
def login():
    """用户登录"""
    data = request.get_json(silent=True)
    if not data:
        return jsonify({'code': 400, 'msg': '请求数据格式错误，请使用JSON格式'}), 400

    username = (data.get('username') or '').strip()
    password = (data.get('password') or '').strip()

    if not username or not password:
        return jsonify({'code': 400, 'msg': '参数缺失'}), 400

    conn = get_db()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        user = cursor.fetchone()

        if user and check_password_hash(dict(user)['password'], password):
            user_dict = dict(user)
            return jsonify({
                'code': 200,
                'msg': '登录成功',
                'data': {
                    'id': user_dict['id'],
                    'username': user_dict['username'],
                    'nickname': user_dict['nickname']
                }
            }), 200
        else:
            return jsonify({'code': 400, 'msg': '用户名或密码错误'}), 400
    except Exception as e:
        print(f"登录错误: {e}")
        return jsonify({'code': 500, 'msg': '服务器错误'}), 500
    finally:
        conn.close()


@bp.route('/user/update', methods=['PUT'])
def update_profile():
    """编辑个人资料（昵称）"""
    data = request.get_json(silent=True)
    if not data:
        return jsonify({'code': 400, 'msg': '请求数据格式错误，请使用JSON格式'}), 400

    user_id = data.get('userId')
    nickname = data.get('nickname')

    if not user_id:
        return jsonify({'code': 400, 'msg': '缺少用户ID'}), 400

    # 昵称敏感词校验
    if nickname:
        valid, msg = validate_nickname(nickname)
        if not valid:
            return jsonify({'code': 400, 'msg': msg}), 400

    conn = get_db()
    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET nickname = ? WHERE id = ?", (nickname, user_id))
        if cursor.rowcount == 0:
            return jsonify({'code': 404, 'msg': '用户不存在'}), 404
        conn.commit()
        # 返回更新后的用户信息
        cursor.execute("SELECT id, username, nickname FROM users WHERE id = ?", (user_id,))
        user = dict(cursor.fetchone())
        return jsonify({'code': 200, 'msg': '修改成功', 'data': user}), 200
    except Exception as e:
        conn.rollback()
        return jsonify({'code': 500, 'msg': str(e)}), 500
    finally:
        conn.close()


@bp.route('/user/changePassword', methods=['PUT'])
def change_password():
    """修改密码"""
    data = request.get_json(silent=True)
    if not data:
        return jsonify({'code': 400, 'msg': '请求数据格式错误，请使用JSON格式'}), 400

    user_id = data.get('userId')
    old_password = (data.get('oldPassword') or '').strip()
    new_password = (data.get('newPassword') or '').strip()

    if not user_id or not old_password or not new_password:
        return jsonify({'code': 400, 'msg': '缺少必要参数（userId/oldPassword/newPassword）'}), 400

    if old_password == new_password:
        return jsonify({'code': 400, 'msg': '新密码不能与旧密码相同'}), 400

    # 新密码复杂度校验
    valid, msg = validate_password(new_password)
    if not valid:
        return jsonify({'code': 400, 'msg': msg}), 400

    conn = get_db()
    try:
        cursor = conn.cursor()
        # 查询用户
        cursor.execute("SELECT password FROM users WHERE id = ?", (user_id,))
        user = cursor.fetchone()
        if not user:
            return jsonify({'code': 404, 'msg': '用户不存在'}), 404

        # 验证旧密码
        if not check_password_hash(dict(user)['password'], old_password):
            return jsonify({'code': 400, 'msg': '旧密码错误'}), 400

        # 更新密码
        hashed_pw = generate_password_hash(new_password)
        cursor.execute("UPDATE users SET password = ? WHERE id = ?", (hashed_pw, user_id))
        conn.commit()
        return jsonify({'code': 200, 'msg': '密码修改成功'}), 200
    except Exception as e:
        conn.rollback()
        return jsonify({'code': 500, 'msg': str(e)}), 500
    finally:
        conn.close()
