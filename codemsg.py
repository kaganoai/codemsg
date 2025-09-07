import websocket
import json
import ssl
import time
import threading
import pyperclip
import re
from plyer import notification

# --- 配置 ---
# 请替换为你的 Gotify 服务器地址，例如 "http://localhost:8080" 或 "https://gotify.example.com"
# 注意：WebSocket URL 通常与 HTTP URL 相同，库会自动处理 ws:// 或 wss:// 的转换
GOTIFY_URL = "http://localhost:8080"

# 请替换为你的 Gotify 应用令牌 (Clients_Token)
Clients_TOKEN = "abcdefghijk"

# 如果你的 Gotify 服务器使用自签名 SSL 证书，你可能需要设置 ssl_context
# 例如，忽略证书验证 (仅用于测试！生产环境请使用有效证书)
# SSL_CONTEXT = ssl._create_unverified_context() # 仅用于测试
SSL_CONTEXT = None # 使用系统默认证书验证
# --- 配置结束 ---


def on_message(ws, message):
    """当从服务器接收到消息时调用。"""
    try:
        # Gotify Stream API 发送的是 JSON 字符串
        msg_data = json.loads(message)
        print("--- 实时收到新消息 ---")
        print(f"  ID: {msg_data.get('id')}")
        print(f"  标题: {msg_data.get('title', 'No Title')}")
        print(f"  内容: {msg_data.get('message', 'No Message Content')}")
        print(f"  优先级: {msg_data.get('priority', 0)}")
        print(f"  时间: {msg_data.get('date', 'Unknown Date')}")
        extras = msg_data.get('extras')
        if extras:
            print(f"  附加信息 (Extras): {json.dumps(extras, indent=2, ensure_ascii=False)}")
        print("-" * 25)
        full_message = msg_data.get('message', 'No Message Content')

        #匹配验证码
        pattern_numeric = r'(?<!\d)\d{4,6}(?!\d)'
        numeric_matches = re.findall(pattern_numeric, full_message)
        code = ','.join(numeric_matches)
        if code:
            pyperclip.copy(code)
            
        notification.notify(
            title="短信",
            message=full_message,
            app_name="code",
            timeout=60 # 通知显示60秒后消失
        )


    except json.JSONDecodeError as e:
        print(f"解析消息时出错: {e}, 原始消息: {message}")
    except Exception as e:
         print(f"处理消息时发生未知错误: {e}")

def on_error(ws, error):
    """当发生错误时调用。"""
    print(f"WebSocket 连接发生错误: {error}")

def on_close(ws, close_status_code, close_msg):
    """当连接关闭时调用。"""
    print("WebSocket 连接已关闭。")
    if close_status_code or close_msg:
        print(f"关闭状态码: {close_status_code}, 关闭消息: {close_msg}")

def on_open(ws):
    """当连接成功建立时调用。"""
    print("WebSocket 连接已成功建立，正在监听实时消息...")

def create_websocket_url(base_url):
    """根据基础 HTTP URL 生成 WebSocket URL。"""
    if base_url.startswith("https://"):
        return base_url.replace("https://", "wss://") + "/stream"
    elif base_url.startswith("http://"):
        return base_url.replace("http://", "ws://") + "/stream"                                             
    else:
        # 如果已经是以 ws:// 或 wss:// 开头
        if base_url.startswith("wss://") or base_url.startswith("ws://"):
             return base_url + "/stream" if not base_url.endswith("/stream") else base_url
        else:
            # 默认假设是 http
            return "ws://" + base_url + "/stream"

def main():
    """主函数，建立 WebSocket 连接并运行。"""
    # 构造 WebSocket URL
    ws_url = create_websocket_url(GOTIFY_URL)
    print(f"准备连接到 Gotify Stream API: {ws_url}")

    # 设置 WebSocket 头部，包含认证令牌
    header = {
        "Authorization": f"Bearer {Clients_TOKEN}"
        # 注意：Gotify Stream API 通常使用 Bearer Token 进行认证
        # 虽然文档有时也提及相关 Key，但 Bearer 是标准且推荐的方式
    }

    # 启用 WebSocket 调试信息 (可选)
    # websocket.enableTrace(True)

    # 创建 WebSocketApp 实例
    # sslopt 参数用于传递 SSL 上下文，处理 HTTPS/WSS 连接
    ws = websocket.WebSocketApp(ws_url,
                                header=header, # 传递头部
                                on_open=on_open,
                                on_message=on_message,
                                on_error=on_error,
                                on_close=on_close)

    # 在单独的线程中运行 WebSocket 连接，以避免阻塞主线程
    # run_forever 会一直运行直到连接被关闭
    # sslopt 传递 SSL 配置
    wst = threading.Thread(target=ws.run_forever, kwargs={'sslopt': {'cert_reqs': ssl.CERT_NONE} if SSL_CONTEXT else {}})
    wst.daemon = True # 设置为守护线程，这样主程序退出时线程也会退出
    wst.start()

    try:
        # 保持主线程运行，以便 WebSocket 线程可以持续监听
        # 你可以在这里执行其他任务，或者简单地让程序保持运行
        while True:
            time.sleep(1) # 主线程休眠，不占用 CPU
    except KeyboardInterrupt:
        print("\n收到中断信号，正在关闭连接...")
        ws.close()
        print("程序已退出。")


if __name__ == "__main__":
    main()
