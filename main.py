import os
import sys
import random
import subprocess
from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton, QLabel, QComboBox, QLineEdit, QTextEdit, QMessageBox
from PySide6.QtCore import QThread, Signal

# 配置服务器信息

# 为了Minecraft联机工具的项目能够继续进行，因此服务器的地址端口密钥已被抹去，但你可自己尝试搭建一个

# 需要在你的服务器上运行 FRP server v0.42.0
SERVERS = {
    "位置": {"server_addr": "服务器地址", "server_port": 65534, "token": "密钥"},
}

# 生成远程端口号
def generate_remote_port(server):
    if "fixed_port" in server:
        return server["fixed_port"]
    common_ports = {80, 443, 3306, 8080, 25565}  # 常见端口
    while True:
        port = random.randint(10000, 65535)
        if port not in common_ports:
            return port

class FrpcThread(QThread):
    output_signal = Signal(str)
    warning_signal = Signal(str)  # 新增警告信号

    def __init__(self):
        super().__init__()
        self.process = None

    def run(self):
        self.process = subprocess.Popen(["frpc.exe", "-c", "frpc.ini"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        for line in self.process.stdout:
            self.output_signal.emit(line.strip())
            if "start proxy success" in line:
                PortMappingApp.instance.display_success()
            elif "already" in line:
                if PortMappingApp.instance.server_select.currentText() == "宿迁":
                    self.warning_signal.emit("此线路已满，请切换到别的线路尝试。")
                else:
                    self.output_signal.emit("端口已被占用，重新分配端口...")
                    PortMappingApp.instance.start_mapping()

    def stop(self):
        if self.process:
            self.process.terminate()
            self.process.wait()
            self.process = None

class PortMappingApp(QWidget):
    instance = None
    current_link = ""

    def __init__(self):
        super().__init__()
        PortMappingApp.instance = self
        self.setWindowTitle("Minecraft 端口映射")
        self.setGeometry(100, 100, 400, 400)

        self.layout = QVBoxLayout()
        self.server_select = QComboBox()
        self.server_select.addItems(SERVERS.keys())
        self.layout.addWidget(QLabel("选择线路:"))
        self.layout.addWidget(self.server_select)

        self.port_input = QLineEdit()
        self.layout.addWidget(QLabel("输入本地端口:"))
        self.layout.addWidget(self.port_input)

        self.start_button = QPushButton("启动映射")
        self.start_button.clicked.connect(self.start_mapping)
        self.layout.addWidget(self.start_button)

        self.output_console = QTextEdit()
        self.output_console.setReadOnly(True)
        self.layout.addWidget(QLabel("运行日志:"))
        self.layout.addWidget(self.output_console)

        self.link_label = QLabel("映射地址: 无")
        self.layout.addWidget(self.link_label)

        self.copy_button = QPushButton("复制链接")
        self.copy_button.setEnabled(False)
        self.copy_button.clicked.connect(self.copy_link)
        self.layout.addWidget(self.copy_button)

        self.setLayout(self.layout)
        self.frpc_thread = None

        if not os.path.exists("frpc.exe"):
            QMessageBox.critical(self, "错误", "frpc.exe 未找到，程序即将退出。")
            sys.exit(1)

        if os.path.exists("frpc.ini"):
            os.remove("frpc.ini")

    def start_mapping(self):
        if self.frpc_thread and self.frpc_thread.isRunning():
            self.output_console.append("检测到已有映射进程，正在关闭...")
            self.frpc_thread.stop()
            self.frpc_thread.wait()
            self.output_console.append("旧映射进程已终止。")

        local_port = self.port_input.text()
        if not local_port.isdigit() or not (1 <= int(local_port) <= 65535):
            QMessageBox.warning(self, "错误", "请输入有效的本地端口（1-65535）。")
            return

        selected_server = self.server_select.currentText()
        server_config = SERVERS[selected_server]
        remote_port = generate_remote_port(server_config)
        unique_id = random.randint(10000, 99999)
        section_name = f"Minecraft-{unique_id}"

        frpc_config = f"""[common]
server_addr = {server_config['server_addr']}
server_port = {server_config['server_port']}
token = {server_config['token']}

[{section_name}]
type = tcp
local_ip = 127.0.0.1
local_port = {local_port}
remote_port = {remote_port}
"""

        with open("frpc.ini", "w") as f:
            f.write(frpc_config)

        PortMappingApp.current_link = f"{server_config['server_addr']}:{remote_port}"
        self.output_console.append("frpc.ini 配置文件已生成，开始映射...")
        self.frpc_thread = FrpcThread()
        self.frpc_thread.output_signal.connect(self.output_console.append)
        self.frpc_thread.warning_signal.connect(self.display_warning)  # 连接警告信号
        self.frpc_thread.start()

    def display_success(self):
        self.link_label.setText(f"映射地址: {PortMappingApp.current_link}")
        self.copy_button.setEnabled(True)

    def display_warning(self, message):
        self.output_console.append(f"⚠️ {message}")

    def copy_link(self):
        QApplication.clipboard().setText(PortMappingApp.current_link)
        QMessageBox.information(self, "复制成功", "映射地址已复制到剪贴板！")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = PortMappingApp()
    window.show()
    sys.exit(app.exec())
