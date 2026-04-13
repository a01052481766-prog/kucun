"""
打包入口：双击 exe 时自动启动服务并打开浏览器
"""
import sys
import os
import socket
import threading
import webbrowser

# ── 打包路径处理（PyInstaller）────────────────────────────
if hasattr(sys, '_MEIPASS'):
    os.environ['FLASK_TEMPLATE_FOLDER'] = os.path.join(sys._MEIPASS, 'templates')
    os.environ['FLASK_STATIC_FOLDER']   = os.path.join(sys._MEIPASS, 'static')
    # 数据库存放在 exe 同目录，方便备份
    data_dir = os.path.dirname(sys.executable)
    os.environ.setdefault('DATABASE_URL',
                          'sqlite:///' + os.path.join(data_dir, 'kucun.db'))

from app import app  # noqa: E402（需在路径设置之后导入）

PORT = 5000


def port_in_use(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('127.0.0.1', port)) == 0


if __name__ == '__main__':
    url = f'http://127.0.0.1:{PORT}'

    if port_in_use(PORT):
        # 已有实例在运行，直接打开浏览器
        print(f'系统已在运行，打开浏览器: {url}')
        webbrowser.open(url)
        sys.exit(0)

    # 延迟 1.5 秒再开浏览器，等 Flask 启动完毕
    threading.Timer(1.5, lambda: webbrowser.open(url)).start()

    print('=' * 45)
    print('  仓库库存管理系统')
    print(f'  访问地址: {url}')
    print('  关闭此窗口即可停止系统')
    print('=' * 45)

    app.run(debug=False, host='127.0.0.1', port=PORT, use_reloader=False)
