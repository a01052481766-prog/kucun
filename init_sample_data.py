"""
示例数据生成脚本
运行此脚本可以为系统生成测试数据
用途：方便测试和演示系统功能
"""

import sys
sys.path.insert(0, '.')

from app import app, db, Material, InventoryOperation
from datetime import datetime, timedelta
import random

def init_sample_data():
    """初始化示例数据"""
    with app.app_context():
        # 清空现有数据（可选）
        # db.drop_all()
        
        # 检查是否已有数据
        if Material.query.first():
            print("⚠️  数据库已有数据，跳过初始化")
            return
        
        print("开始生成示例数据...")
        
        # 示例物料数据
        materials_data = [
            {
                'code': '001-A',
                'name': '螺丝 M3*10',
                'unit': '个',
                'category': '五金配件',
                'initial_quantity': 1000,
                'min_quantity': 100,
                'max_quantity': 5000,
                'remarks': '日常常用'
            },
            {
                'code': '002-B',
                'name': '螺帽 M3',
                'unit': '个',
                'category': '五金配件',
                'initial_quantity': 800,
                'min_quantity': 80,
                'max_quantity': 4000,
                'remarks': '配合螺丝使用'
            },
            {
                'code': '003-C',
                'name': '垫圈 M3',
                'unit': '个',
                'category': '五金配件',
                'initial_quantity': 500,
                'min_quantity': 50,
                'max_quantity': 2000,
                'remarks': ''
            },
            {
                'code': '004-D',
                'name': 'LED灯珠 红色',
                'unit': '个',
                'category': '电子元件',
                'initial_quantity': 200,
                'min_quantity': 20,
                'max_quantity': 1000,
                'remarks': '5mm 普通亮度'
            },
            {
                'code': '005-E',
                'name': 'LED灯珠 绿色',
                'unit': '个',
                'category': '电子元件',
                'initial_quantity': 150,
                'min_quantity': 15,
                'max_quantity': 800,
                'remarks': '5mm 普通亮度'
            },
            {
                'code': '006-F',
                'name': '铜管 Φ6',
                'unit': 'm',
                'category': '管材料',
                'initial_quantity': 100,
                'min_quantity': 10,
                'max_quantity': 500,
                'remarks': '外径6mm'
            },
            {
                'code': '007-G',
                'name': '铝型材 2020',
                'unit': 'm',
                'category': '型材',
                'initial_quantity': 50,
                'min_quantity': 5,
                'max_quantity': 200,
                'remarks': '工业用'
            },
            {
                'code': '008-H',
                'name': '钢板 10mm',
                'unit': 'kg',
                'category': '钢铁材料',
                'initial_quantity': 500,
                'min_quantity': 50,
                'max_quantity': 2000,
                'remarks': '冷轧钢板'
            },
        ]
        
        # 创建物料
        materials = []
        for data in materials_data:
            material = Material(
                code=data['code'],
                name=data['name'],
                unit=data['unit'],
                category=data['category'],
                initial_quantity=data['initial_quantity'],
                current_quantity=data['initial_quantity'],
                min_quantity=data['min_quantity'],
                max_quantity=data['max_quantity'],
                remarks=data['remarks']
            )
            db.session.add(material)
            materials.append(material)
            print(f"  ✓ {data['code']} - {data['name']}")
        
        db.session.commit()
        print(f"\n✓ 已创建 {len(materials)} 种物料")
        
        # 生成示例操作记录
        print("\n生成示例操作记录...")
        
        operations_data = [
            ('入库', 50, '李明', '新采购'),
            ('出库', 20, '王芳', '产线使用'),
            ('入库', 100, '李明', '补货'),
            ('出库', 30, '张三', '产线使用'),
            ('入库', 80, '李明', '返工件'),
            ('出库', 15, '王芳', '产线使用'),
        ]
        
        # 为每个物料生成随机操作记录
        for material in materials:
            for _ in range(random.randint(2, 5)):
                op_type, qty, operator, remarks = random.choice(operations_data)
                
                # 计算随机时间（近7天内）
                days_ago = random.randint(0, 7)
                created_time = datetime.now() - timedelta(days=days_ago, hours=random.randint(0, 23))
                
                operation = InventoryOperation(
                    material_id=material.id,
                    operation_type='in' if op_type == '入库' else 'out',
                    quantity=qty,
                    operator=operator,
                    remarks=remarks,
                    created_at=created_time
                )
                
                # 更新物料数量
                if op_type == '入库':
                    material.current_quantity += qty
                else:
                    if material.current_quantity >= qty:
                        material.current_quantity -= qty
                    else:
                        material.current_quantity = 0
                
                db.session.add(operation)
                print(f"  ✓ {material.name}: {op_type} {qty}{material.unit}")
        
        db.session.commit()
        print("\n✅ 示例数据生成完成！")
        print("\n📊 数据统计:")
        print(f"  物料总数: {len(materials)}")
        print(f"  操作记录: {InventoryOperation.query.count()}")

if __name__ == '__main__':
    try:
        init_sample_data()
    except Exception as e:
        print(f"❌ 错误: {str(e)}")
        import traceback
        traceback.print_exc()
