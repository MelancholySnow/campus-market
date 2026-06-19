from flask import Flask, send_from_directory, jsonify
from flask_cors import CORS
from routes import auth, cart, collect, goods, messages
from config.db_config import init_database
import os
import traceback

app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024  # 5MB上传限制

# CORS 配置
CORS(app, resources={r"/api/*": {
    "origins": "*",
    "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    "allow_headers": ["Content-Type", "Authorization"]
}})


# 全局错误处理器
@app.errorhandler(400)
def bad_request(e):
    return jsonify({'code': 400, 'msg': '请求格式错误，请检查参数'}), 400


@app.errorhandler(500)
def server_error(e):
    print(f"服务器内部错误: {e}\n{traceback.format_exc()}")
    return jsonify({'code': 500, 'msg': '服务器内部错误'}), 500

# 注册蓝图
app.register_blueprint(auth.bp)
app.register_blueprint(cart.bp)
app.register_blueprint(collect.bp)
app.register_blueprint(goods.bp)
app.register_blueprint(messages.bp)

# 上传文件目录
UPLOAD_DIR = os.path.join(os.path.dirname(__file__), 'uploads')
os.makedirs(UPLOAD_DIR, exist_ok=True)

FRONT_DIR = os.path.join(os.path.dirname(__file__), 'front')


@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    return send_from_directory(UPLOAD_DIR, filename)


@app.route('/')
def index():
    return send_from_directory(FRONT_DIR, 'index.html')


@app.route('/<path:filename>')
def serve_frontend(filename):
    """托管前端静态文件（排除API路由）"""
    file_path = os.path.join(FRONT_DIR, filename)
    if os.path.isfile(file_path):
        return send_from_directory(FRONT_DIR, filename)
    return send_from_directory(FRONT_DIR, 'index.html')


# 初始化数据库
with app.app_context():
    init_database()

if __name__ == '__main__':
    print("=" * 50)
    print("校园二手交易平台启动中...")
    print("=" * 50)
    app.run(host="0.0.0.0", port=8080, debug=True)
