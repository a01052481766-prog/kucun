"""
仓库库存管理系统
支持物料管理、入库出库、库存统计等功能
"""

import sys
if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

from flask import Flask, render_template, request, jsonify, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os

app = Flask(
    __name__,
    template_folder=os.environ.get('FLASK_TEMPLATE_FOLDER', 'templates'),
    static_folder=os.environ.get('FLASK_STATIC_FOLDER', 'static')
)

# 配置
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'kucun-dev-secret-2024')

# 本地用 SQLite，云端自动切换到 PostgreSQL（通过环境变量 DATABASE_URL）
_db_url = os.environ.get('DATABASE_URL', 'sqlite:///kucun.db')
if _db_url.startswith('postgres://'):
    _db_url = _db_url.replace('postgres://', 'postgresql+psycopg2://', 1)
elif _db_url.startswith('postgresql://') and '+psycopg2' not in _db_url:
    _db_url = _db_url.replace('postgresql://', 'postgresql+psycopg2://', 1)

app.config['SQLALCHEMY_DATABASE_URI'] = _db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JSON_AS_ASCII'] = False

db = SQLAlchemy(app)

# 登录管理
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message = '请先登录后再访问'


# ===== 数据库模型 =====

class User(db.Model, UserMixin):
    """用户表"""
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.now)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Material(db.Model):
    """物料表"""
    __tablename__ = 'materials'

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(50), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    unit = db.Column(db.String(20), default='个')
    category = db.Column(db.String(50))
    initial_quantity = db.Column(db.Float, default=0)
    current_quantity = db.Column(db.Float, default=0)
    min_quantity = db.Column(db.Float, default=0)
    max_quantity = db.Column(db.Float, default=0)
    remarks = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)

    inventory_operations = db.relationship('InventoryOperation', backref='material', lazy=True, cascade='all, delete-orphan')


class InventoryOperation(db.Model):
    """库存操作表（入库、出库）"""
    __tablename__ = 'inventory_operations'

    id = db.Column(db.Integer, primary_key=True)
    material_id = db.Column(db.Integer, db.ForeignKey('materials.id'), nullable=False)
    operation_type = db.Column(db.String(10), nullable=False)  # 'in' 入库, 'out' 出库
    quantity = db.Column(db.Float, nullable=False)
    operator = db.Column(db.String(50))
    remarks = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.now)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# 初始化数据库，首次运行创建默认管理员
with app.app_context():
    db.create_all()
    if not User.query.first():
        admin = User(username='admin', is_admin=True)
        admin.set_password('admin123')
        db.session.add(admin)
        db.session.commit()
        print("✓ 默认管理员账号已创建: admin / admin123")


# ===== 登录 / 登出 =====

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    error = None
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user, remember=True)
            return redirect(url_for('index'))
        error = '用户名或密码错误'
    return render_template('login.html', error=error)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))


# ===== 前端路由 =====

@app.route('/')
@login_required
def index():
    return render_template('index.html')


@app.route('/materials')
@login_required
def materials_page():
    return render_template('materials.html')


@app.route('/inventory')
@login_required
def inventory_page():
    return render_template('inventory.html')


@app.route('/report')
@login_required
def report_page():
    return render_template('report.html')


@app.route('/users')
@login_required
def users_page():
    if not current_user.is_admin:
        return redirect(url_for('index'))
    return render_template('users.html')


# ===== 用户管理 API（仅管理员）=====

@app.route('/api/users', methods=['GET'])
@login_required
def get_users():
    if not current_user.is_admin:
        return jsonify({'success': False, 'message': '无权限'}), 403
    users = User.query.order_by(User.created_at).all()
    return jsonify([{
        'id': u.id,
        'username': u.username,
        'is_admin': u.is_admin,
        'created_at': u.created_at.strftime('%Y-%m-%d %H:%M')
    } for u in users])


@app.route('/api/users', methods=['POST'])
@login_required
def create_user():
    if not current_user.is_admin:
        return jsonify({'success': False, 'message': '无权限'}), 403
    data = request.json
    username = data.get('username', '').strip()
    password = data.get('password', '')
    is_admin = data.get('is_admin', False)

    if not username or not password:
        return jsonify({'success': False, 'message': '用户名和密码不能为空'}), 400
    if User.query.filter_by(username=username).first():
        return jsonify({'success': False, 'message': '用户名已存在'}), 400

    user = User(username=username, is_admin=is_admin)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    return jsonify({'success': True, 'message': f'用户 {username} 创建成功'}), 201


@app.route('/api/users/<int:id>', methods=['DELETE'])
@login_required
def delete_user(id):
    if not current_user.is_admin:
        return jsonify({'success': False, 'message': '无权限'}), 403
    if id == current_user.id:
        return jsonify({'success': False, 'message': '不能删除自己'}), 400
    user = User.query.get(id)
    if not user:
        return jsonify({'success': False, 'message': '用户不存在'}), 404
    db.session.delete(user)
    db.session.commit()
    return jsonify({'success': True, 'message': f'用户 {user.username} 已删除'})


@app.route('/api/users/<int:id>/password', methods=['PUT'])
@login_required
def change_password(id):
    if id != current_user.id and not current_user.is_admin:
        return jsonify({'success': False, 'message': '无权限'}), 403
    user = User.query.get(id)
    if not user:
        return jsonify({'success': False, 'message': '用户不存在'}), 404
    new_password = request.json.get('password', '')
    if not new_password:
        return jsonify({'success': False, 'message': '密码不能为空'}), 400
    user.set_password(new_password)
    db.session.commit()
    return jsonify({'success': True, 'message': '密码修改成功'})


# ===== 物料相关 API =====

@app.route('/api/materials', methods=['GET'])
@login_required
def get_materials():
    materials = Material.query.all()
    return jsonify([{
        'id': m.id,
        'code': m.code,
        'name': m.name,
        'unit': m.unit,
        'category': m.category,
        'current_quantity': m.current_quantity,
        'min_quantity': m.min_quantity,
        'max_quantity': m.max_quantity,
        'remarks': m.remarks
    } for m in materials])


@app.route('/api/materials', methods=['POST'])
@login_required
def create_material():
    data = request.json
    if Material.query.filter_by(code=data['code']).first():
        return jsonify({'success': False, 'message': '物料编码已存在'}), 400

    material = Material(
        code=data['code'],
        name=data['name'],
        unit=data.get('unit', '个'),
        category=data.get('category', ''),
        initial_quantity=data.get('initial_quantity', 0),
        current_quantity=data.get('initial_quantity', 0),
        min_quantity=data.get('min_quantity', 0),
        max_quantity=data.get('max_quantity', 0),
        remarks=data.get('remarks', '')
    )
    db.session.add(material)
    db.session.commit()
    return jsonify({'success': True, 'message': '物料创建成功', 'id': material.id}), 201


@app.route('/api/materials/<int:id>', methods=['PUT'])
@login_required
def update_material(id):
    material = Material.query.get(id)
    if not material:
        return jsonify({'success': False, 'message': '物料不存在'}), 404
    data = request.json
    material.name = data.get('name', material.name)
    material.unit = data.get('unit', material.unit)
    material.category = data.get('category', material.category)
    material.min_quantity = data.get('min_quantity', material.min_quantity)
    material.max_quantity = data.get('max_quantity', material.max_quantity)
    material.remarks = data.get('remarks', material.remarks)
    material.updated_at = datetime.now()
    db.session.commit()
    return jsonify({'success': True, 'message': '物料更新成功'})


@app.route('/api/materials/<int:id>', methods=['DELETE'])
@login_required
def delete_material(id):
    material = Material.query.get(id)
    if not material:
        return jsonify({'success': False, 'message': '物料不存在'}), 404
    db.session.delete(material)
    db.session.commit()
    return jsonify({'success': True, 'message': '物料删除成功'})


# ===== 库存操作 API =====

@app.route('/api/inventory/in', methods=['POST'])
@login_required
def inventory_in():
    data = request.json
    material_id = data.get('material_id')
    quantity = data.get('quantity')
    remarks = data.get('remarks', '')

    material = Material.query.get(material_id)
    if not material:
        return jsonify({'success': False, 'message': '物料不存在'}), 404

    operation = InventoryOperation(
        material_id=material_id,
        operation_type='in',
        quantity=quantity,
        operator=current_user.username,
        remarks=remarks
    )
    material.current_quantity += quantity
    material.updated_at = datetime.now()
    db.session.add(operation)
    db.session.commit()
    return jsonify({
        'success': True,
        'message': f'入库成功，当前库存：{material.current_quantity}',
        'current_quantity': material.current_quantity
    })


@app.route('/api/inventory/out', methods=['POST'])
@login_required
def inventory_out():
    data = request.json
    material_id = data.get('material_id')
    quantity = data.get('quantity')
    remarks = data.get('remarks', '')

    material = Material.query.get(material_id)
    if not material:
        return jsonify({'success': False, 'message': '物料不存在'}), 404
    if material.current_quantity < quantity:
        return jsonify({'success': False, 'message': '库存不足'}), 400

    operation = InventoryOperation(
        material_id=material_id,
        operation_type='out',
        quantity=quantity,
        operator=current_user.username,
        remarks=remarks
    )
    material.current_quantity -= quantity
    material.updated_at = datetime.now()
    db.session.add(operation)
    db.session.commit()
    return jsonify({
        'success': True,
        'message': f'出库成功，当前库存：{material.current_quantity}',
        'current_quantity': material.current_quantity
    })


@app.route('/api/inventory/operations', methods=['GET'])
@login_required
def get_operations():
    material_id = request.args.get('material_id')
    operation_type = request.args.get('type')
    query = InventoryOperation.query
    if material_id:
        query = query.filter_by(material_id=material_id)
    if operation_type:
        query = query.filter_by(operation_type=operation_type)
    operations = query.order_by(InventoryOperation.created_at.desc()).all()
    return jsonify([{
        'id': op.id,
        'material_id': op.material_id,
        'material_name': op.material.name,
        'material_code': op.material.code,
        'operation_type': '入库' if op.operation_type == 'in' else '出库',
        'quantity': op.quantity,
        'operator': op.operator,
        'remarks': op.remarks,
        'created_at': op.created_at.strftime('%Y-%m-%d %H:%M:%S')
    } for op in operations])


# ===== 统计报表 API =====

@app.route('/api/report/summary')
@login_required
def get_summary():
    materials = Material.query.all()
    total_quantity = sum(m.current_quantity for m in materials)
    low_stock = [m for m in materials if m.min_quantity > 0 and m.current_quantity <= m.min_quantity]
    return jsonify({
        'total_materials': len(materials),
        'total_quantity': total_quantity,
        'low_stock_count': len(low_stock),
        'low_stock_items': [{
            'id': m.id,
            'name': m.name,
            'code': m.code,
            'current': m.current_quantity,
            'min': m.min_quantity
        } for m in low_stock]
    })


@app.route('/api/report/materials')
@login_required
def get_materials_report():
    materials = Material.query.all()
    report = []
    for m in materials:
        in_qty = db.session.query(db.func.sum(InventoryOperation.quantity)).filter(
            InventoryOperation.material_id == m.id,
            InventoryOperation.operation_type == 'in'
        ).scalar() or 0
        out_qty = db.session.query(db.func.sum(InventoryOperation.quantity)).filter(
            InventoryOperation.material_id == m.id,
            InventoryOperation.operation_type == 'out'
        ).scalar() or 0
        report.append({
            'id': m.id,
            'code': m.code,
            'name': m.name,
            'unit': m.unit,
            'initial_quantity': m.initial_quantity,
            'in_quantity': in_qty,
            'out_quantity': out_qty,
            'current_quantity': m.current_quantity,
            'surplus': m.current_quantity - m.initial_quantity
        })
    return jsonify(report)


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=False, host='0.0.0.0', port=5000)
