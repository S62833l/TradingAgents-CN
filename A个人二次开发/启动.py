"""
TradingAgents-CN 一键启动脚本
双击或在终端 python 启动.py 即可
"""
import subprocess
import os
import sys
import time
import socket
import webbrowser
from pathlib import Path

BASE_DIR = Path(__file__).parent

def find_exe(name, search_paths):
    """在指定路径中查找可执行文件"""
    for p in search_paths:
        exe = Path(p) / f"{name}.exe"
        if exe.exists():
            return str(exe)
    return None

def is_port_open(port, host="127.0.0.1"):
    """检查端口是否已被占用"""
    try:
        with socket.create_connection((host, port), timeout=1):
            return True
    except:
        return False

def print_banner():
    print("""
╔══════════════════════════════════════════════╗
║     TradingAgents-CN 一键启动脚本           ║
║     多智能体股票分析平台                    ║
╚══════════════════════════════════════════════╝
""")

def start_mongodb():
    """启动 MongoDB"""
    print("[1/5] 启动 MongoDB...", end=" ")

    if is_port_open(27017):
        print("✅ 已在运行")
        return None

    mongod = find_exe("mongod", [
        "C:/Program Files/MongoDB/Server/8.3/bin",
        "C:/Program Files/MongoDB/Server/8.0/bin",
        "C:/Program Files/MongoDB/Server/7.0/bin",
        "C:/Program Files/MongoDB/Server/6.0/bin",
    ])

    if not mongod:
        print("❌ 未找到 MongoDB，请先安装")
        return None

    data_dir = "C:/data/db"
    Path(data_dir).mkdir(parents=True, exist_ok=True)

    proc = subprocess.Popen(
        [mongod, "--dbpath", data_dir],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=subprocess.CREATE_NO_WINDOW
    )
    time.sleep(3)

    if is_port_open(27017):
        print("✅ 启动成功")
        return proc
    else:
        print("⚠️ 可能启动失败，继续...")
        return proc

def start_redis():
    """启动 Redis"""
    print("[2/5] 启动 Redis...", end=" ")

    if is_port_open(6379):
        print("✅ 已在运行")
        return None

    redis_server = find_exe("redis-server", [
        "C:/Program Files/Redis",
        "C:/Program Files (x86)/Redis",
    ])

    if not redis_server:
        print("⚠️ 未找到 Redis，跳过（不影响核心功能）")
        return None

    proc = subprocess.Popen(
        [redis_server],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=subprocess.CREATE_NO_WINDOW
    )
    time.sleep(1)

    if is_port_open(6379):
        print("✅ 启动成功")
    else:
        print("⚠️ 可能启动失败，继续...")
    return proc

def start_backend():
    """启动 FastAPI 后端"""
    print("[3/5] 启动后端 API 服务...", end=" ")

    if is_port_open(8000):
        print("✅ 已在运行")
        return None

    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["PATH"] = env.get("PATH", "") + ";C:/Program Files/MongoDB/Server/8.3/bin;C:/Program Files/Redis"

    venv_python = BASE_DIR.parent / ".venv" / "Scripts" / "python.exe"
    python_exe = str(venv_python) if venv_python.exists() else sys.executable

    proc = subprocess.Popen(
        [python_exe, "-m", "app"],
        cwd=str(BASE_DIR),
        env=env,
        creationflags=subprocess.CREATE_NO_WINDOW
    )

    # 等后端启动
    for i in range(30):
        time.sleep(1)
        if is_port_open(8000):
            print("✅ 启动成功")
            return proc

    print("⚠️ 启动超时，继续...")
    return proc

def start_frontend():
    """启动 Vue 前端"""
    print("[4/5] 启动前端界面...", end=" ")

    if is_port_open(3000):
        print("✅ 已在运行")
        return None

    frontend_dir = BASE_DIR / "frontend"
    if not frontend_dir.exists():
        print("⚠️ 前端目录不存在")
        return None

    # 检查 node_modules 是否存在
    if not (frontend_dir / "node_modules").exists():
        print("\n    ⚠️ 前端依赖未安装，正在安装...")
        subprocess.run(["npm", "install"], cwd=str(frontend_dir), check=False)

    npm_cmd = "npm.cmd" if sys.platform == "win32" else "npm"

    proc = subprocess.Popen(
        [npm_cmd, "run", "dev"],
        cwd=str(frontend_dir),
        creationflags=subprocess.CREATE_NO_WINDOW
    )

    # 等前端启动
    for i in range(20):
        time.sleep(1)
        if is_port_open(3000):
            print("✅ 启动成功")
            return proc

    print("⚠️ 启动超时，继续...")
    return proc

def stop_existing():
    """停止已有进程"""
    print("[0/5] 检查现有进程...")

    # 检查并提示端口占用
    occupied = []
    if is_port_open(8000):
        occupied.append("8000 (后端)")
    if is_port_open(3000):
        occupied.append("3000 (前端)")

    if occupied:
        print(f"    ⚠️ 端口已占用: {', '.join(occupied)}")
        print("    如需重启请先关闭旧进程 (或无视此提示)")

    print()

def main():
    print_banner()

    # 切换到项目目录
    os.chdir(str(BASE_DIR))

    stop_existing()

    print("正在启动所有服务...\n")

    # 按顺序启动
    procs = []

    p = start_mongodb()
    if p: procs.append(("MongoDB", p))

    p = start_redis()
    if p: procs.append(("Redis", p))

    p = start_backend()
    if p: procs.append(("后端API", p))

    p = start_frontend()
    if p: procs.append(("前端界面", p))

    print(f"\n[5/5] 打开浏览器...")
    time.sleep(2)
    webbrowser.open("http://localhost:3000")

    print("""
╔══════════════════════════════════════════════╗
║  🎉 启动完成！                             ║
║                                            ║
║  前端界面: http://localhost:3000           ║
║  后端API:  http://localhost:8000           ║
║  API文档:  http://localhost:8000/docs      ║
║                                            ║
║  用户名: admin                             ║
║  密码:   admin123                          ║
║                                            ║
║  关闭此窗口即可停止所有服务               ║
╚══════════════════════════════════════════════╝
""")

    print("按 Ctrl+C 停止所有服务...\n")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n正在停止所有服务...")
        for name, proc in reversed(procs):
            print(f"  停止 {name}...")
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except:
                proc.kill()
        # 额外清理
        import signal
        for name, proc in procs:
            try:
                proc.send_signal(signal.CTRL_BREAK_EVENT)
            except:
                pass
        print("👋 已停止，下次再见！")

if __name__ == "__main__":
    main()
