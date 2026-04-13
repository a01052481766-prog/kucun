"""
仓库库存管理系统
支持物料管理、入库出库、库存统计等功能
"""

import sys
if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

from flask import Flask, render_template, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os
from functools import wraps

app = Flask(__name__)

# 本地用 SQLite，云端自动切换到 PostgreSQL（通过环境变量 DATABASE_URL）
_db_url = os.environ.get('DATABASE_URL', 'sqlite:///kucun.db')
if _db_url.startswith('postgres://'):
    _db_url = _db_url.replace('postgres://', 'postgresql+psycopg2://', 1)
elif _db_url.startswith('postgresql://') and '+psycopg2' not in _db_url:
    _db_url = _db_url.replace('postgresql://', 'postgresql+psycopg2://', 1)

app.config['SQLALCHEMY_DATABASE_URI'] = _db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JSON_AS_ASCII'] = False  # 支持中文

db = SQLAlchemy(app)

# 数据库模型
class Material(db.Model):
    """物料表"""
    __tablename__ = 'materials'
    
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(50), unique=True, nullable=False)  # 物料编码
    name = db.Column(db.String(100), nullable=False)  # 物料名称
    unit = db.Column(db.String(20), default='个')  # 单位
    category = db.Column(db.String(50))  # 分类
    initial_quantity = db.Column(db.Float, default=0)  # 初始数量
    current_quantity = db.Column(db.Float, default=0)  # 当前数量
    min_quantity = db.Column(db.Float, default=0)  # 最低库存
    max_quantity = db.Column(db.Float, default=0)  # 最高库存
    remarks = db.Column(db.Text)  # 备注
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    
    inventory_operations = db.relationship('InventoryOperation', backref='material', lazy=True, cascade='all, delete-orphan')


class InventoryOperation(db.Model):
    """库存操作表（入库、出库）"""
    __tablename__ = 'inventory_operations'
    
    id = db.Column(db.Integer, primary_key=True)
    material_id = db.Column(db.Integer, db.ForeignKey('materials.id'), nullable=False)
    operation_type = db.Column(db.String(10), nullable=False)  # 'in' 入库, 'out' 出库
    quantity = db.Column(db.Float, nullable=False)  # 操作数量
    operator = db.Column(db.String(50))  # 操作人员
    remarks = db.Column(db.Text)  # 备注
    created_at = db.Column(db.DateTime, default=datetime.now)


# 初始化数据库
def init_db():
    with app.app_context():
        db.create_all()
        print("✓ 数据库初始化成功")

# gunicorn 启动时也需要自动建表
with app.app_context():
    db.create_all()


# 前端路由
@app.route('/')
def index():
    """首页"""
    return render_template('index.html')


@app.route('/materials')
def materials_page():
    """物料管理页面"""
    return render_template('materials.html')


@app.route('/inventory')
def inventory_page():
    """库存操作页面"""
    return render_template('inventory.html')


@app.route('/report')
def report_page():
    """报表统计页面"""
    return render_template('report.html')


# API 端点

# ===== 物料相关 API =====
@app.route('/api/materials', methods=['GET'])
def get_materials():
    """获取所有物料"""
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
def create_material():
    """创建新物料"""
    data = request.json
    
    # 检查编码是否已存在
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
def update_material(id):
    """更新物料"""
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
def delete_material(id):
    """删除物料"""
    material = Material.query.get(id)
    if not material:
        return jsonify({'success': False, 'message': '物料不存在'}), 404
    
    db.session.delete(material)
    db.session.commit()
    return jsonify({'success': True, 'message': '物料删除成功'})


# ===== 库存操作 API =====
@app.route('/api/inventory/in', methods=['POST'])
def inventory_in():
    """入库操作"""
    data = request.json
    material_id = data.get('material_id')
    quantity = data.get('quantity')
    operator = data.get('operator', '未知')
    remarks = data.get('remarks', '')
    
    material = Material.query.get(material_id)
    if not material:
        return jsonify({'success': False, 'message': '物料不存在'}), 404
    
    # 记录操作
    operation = InventoryOperation(
        material_id=material_id,
        operation_type='in',
        quantity=quantity,
        operator=operator,
        remarks=remarks
    )
    
    # 更新库存
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
def inventory_out():
    """出库操作"""
    data = request.json
    material_id = data.get('material_id')
    quantity = data.get('quantity')
    operator = data.get('operator', '未知')
    remarks = data.get('remarks', '')
    
    material = Material.query.get(material_id)
    if not material:
        return jsonify({'success': False, 'message': '物料不存在'}), 404
    
    if material.current_quantity < quantity:
        return jsonify({'success': False, 'message': '库存不足'}), 400
    
    # 记录操作
    operation = InventoryOperation(
        material_id=material_id,
        operation_type='out',
        quantity=quantity,
        operator=operator,
        remarks=remarks
    )
    
    # 更新库存
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
def get_operations():
    """获取库存操作日志"""
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
def get_summary():
    """获取库存汇总信息"""
    materials = Material.query.all()
    
    total_quantity = sum(m.current_quantity for m in materials)
    total_value = len(materials)
    
    # 库存预警
    low_stock = [m for m in materials if m.min_quantity > 0 and m.current_quantity <= m.min_quantity]
    
    return jsonify({
        'total_materials': total_value,
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
def get_materials_report():
    """获取物料详细统计"""
    materials = Material.query.all()
    
    report = []
    for m in materials:
        # 计算进出账
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
    init_db()
    app.run(debug=False, host='0.0.0.0', port=5000)
