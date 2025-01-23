import configparser
import os
import subprocess
import shutil
import requests
import csv
import json
import toml
import logging
from cryptography.fernet import Fernet
from urllib.parse import urlparse
import tkinter as tk
from tkinter.scrolledtext import ScrolledText

def open_file_async(file_path):
    if os.name == 'nt':  # Windows
        os.startfile(file_path)
    elif os.name == 'posix':  # macOS, Linux
        subprocess.Popen(['open', file_path])
    else:
        subprocess.Popen(['xdg-open', file_path])

# initialize logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

file_handler = logging.FileHandler('log.txt')
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(formatter)

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)
console_handler.setFormatter(formatter)

logger.addHandler(file_handler)
logger.addHandler(console_handler)

class TextHandler(logging.Handler):
    def __init__(self, text_widget):
        logging.Handler.__init__(self)
        self.text_widget = text_widget

    def emit(self, record):
        msg = self.format(record)
        self.text_widget.config(state=tk.NORMAL)
        self.text_widget.insert(tk.END, msg + '\n')
        self.text_widget.config(state=tk.DISABLED)
        self.text_widget.yview(tk.END)

# initialize tkinter and log frame
root = tk.Tk()
root.title("Timberborn mod translator")
root.geometry("1280x720")
root.resizable(False, False)
root.tk.call('wm', 'iconphoto', root._w, tk.PhotoImage(file='logo.png')) 

log_frame = tk.LabelFrame(root, text="Log")
log_frame.place(x=800, y=10, width=460, height=700)

log_text = ScrolledText(log_frame, state=tk.DISABLED, wrap=tk.WORD)
log_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

text_handler = TextHandler(log_text)
text_handler.setLevel(logging.INFO)
text_handler.setFormatter(formatter)
logger.addHandler(text_handler)

# Load the default config
if not os.path.exists("config.toml"):
    shutil.copy("default.toml", "config.toml")

configs = toml.load("config.toml")
if configs['common']['version'] < 0.2:
    if os.path.exists("config_bak.txt"):
        os.remove("config_bak.txt")
    shutil.move("config.toml", "config_bak.txt")
    shutil.copy("default.toml", "config.toml")
    configs = toml.load("config.toml")
    open_file_async("config_bak.txt")


def save_config():
    with open('config.toml', 'w') as f:
        toml.dump(configs, f)

def update_config(var, config_path):
    keys = config_path.split(".")
    config_section = configs
    for key in keys[:-1]:
        config_section = config_section[key]
    config_section[keys[-1]] = var.get()
    save_config()

# initialize proxy settings
proxies = None
def get_proxies() -> None:
    global proxies
    if configs['connection']['isProxy']:
        proxy_auth = f"{configs['connection']['username']}:{configs['connection']['password']}@" if configs['connection']['username'] and configs['connection']['password'] else ""
        proxy_url = f"socks5://{proxy_auth}{configs['connection']['address']}:{configs['connection']['port']}"
        proxies = {
            "http": proxy_url,
            "https": proxy_url
        }
    return None

get_proxies()

def get_domain(url) -> str:
    parsed_url = urlparse(url)
    return parsed_url.netloc

def get_prompt() -> str:
    prompt = configs["LLM"]["prompt"].replace("{lang}", configs["LLM"]["lang"])
    if configs["LLM"]["isParallelProcessing"]:
        prompt += configs["LLM"]["promptParallelProcessing"].replace("{signParallelProcessing}", configs["LLM"]["signParallelProcessing"])
    return prompt

prompt = get_prompt()

promptTokens, completionTokens = 0, 0

def requestLLM(text="",prompt = prompt) -> dict["text": str, "code": int]:
    if text == "":
        logger.warning("Empty text")
        return ""
    elif len(text) < configs["LLM"]["minlength"]:
        logger.warning("Text too short")
        return text

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {configs["LLM"]["token"]}"
    }

    data = {
        "model": configs["LLM"]["model"],
        "messages": [
            {
                "role": "system",
                "content": prompt
            },
            {
                "role": "user",
                "content": text
            }
        ]
    }

    global promptTokens, completionTokens
    try:
        response = requests.post(configs["LLM"]["API"], headers=headers, data=json.dumps(data), proxies=proxies)
        response_data = response.json()
        if 'usage' in response_data:
            promptTokens += response_data['usage']['prompt_tokens']
            completionTokens += response_data['usage']['completion_tokens']
            logger.debug(f"Prompt tokens: {promptTokens}, Completion tokens: {completionTokens}")
        else:
            logger.warning('No usage data found')

        if response.status_code == 200:
            openai_result = response_data['choices'][0]['message']['content']
            logger.info(f'{text} -> {openai_result}')
            return {"text": openai_result, "code": response.status_code}
        else:
            logger.error(f"Request failed, status code: {response.status_code}")
            logger.error(headers)
            logger.error(data)
            logger.error(response.text)
            return {"text": "Unexpected", "code": response.status_code}
    except requests.RequestException as e:
        logger.error(f"Request failed: {e}")
        return {"text": "Failed", "code": -1}

def check_accessibility():
    git_status = "Unknown"
    openai_status = "Unknown"
    steam_status = "Unknown"
    logger.info("Checking accessibility...")
    gitDomain = get_domain(configs["sync"]["API"])
    openaiDomain = get_domain(configs["LLM"]["API"])
    logger.debug(f"Git Source: {gitDomain}")
    logger.debug(f"OpenAI: {openaiDomain}")
    logger.debug(f"Steam: store.steampowered.com")

    # Check Git accessibility
    try:
        response = requests.get(f"https://{gitDomain}", timeout=5, proxies=proxies)
        if response.status_code == 200:
            git_status = "Accessible"
            logger.info(f"Sync: {git_status}")
        else:
            git_status = "Not Accessible"
            logger.info(f"Sync: {git_status}")
            logger.info(f"Response: {response}")
    except requests.RequestException as e:
        git_status = "Not Accessible"
        logger.info(f"Sync: {git_status}")
        logger.info(f"Error: {e}")

    # Check LLM accessibility
    LLMStatus = requestLLM(text="Hello", prompt="Reply me \"Hi\"")
    if LLMStatus["code"] == 200:
        openai_status = "Accessible"
        logger.info(f"LLM: {openai_status}")
    else:
        openai_status = "Not Accessible"
        logger.info(f"LLM: {openai_status}")
        logger.info(f"Response: {LLMStatus}")

    # Check Steam accessibility
    try:
        response = requests.get(f"https://store.steampowered.com", timeout=5, proxies=proxies)
        if response.status_code == 200:
            steam_status = "Accessible"
            logger.info(f"Steam: {steam_status}")
        else:
            steam_status = "Not Accessible"
            logger.info(f"Steam: {steam_status}")
            logger.info(f"Response: {response}")
    except requests.RequestException as e:
        steam_status = "Not Accessible"
        logger.info(f"Steam: {steam_status}")
        logger.info(f"Error: {e}")

    git_label.config(text=f"Sync: {git_status}")
    LLM_label.config(text=f"LLM: {openai_status}")
    steam_label.config(text=f"Steam: {steam_status}")


# settings frame
settings_frame = tk.LabelFrame(root, text="Settings", padx=5, pady=0)
settings_frame.place(x=10, y=10, width=780, height=360)


# data sync settings
sync_settings_frame = tk.LabelFrame(settings_frame, text="Sync Settings")
sync_settings_frame.place(x=0, y=0, width=380, height=100)

sync_tip = tk.Label(sync_settings_frame, text="Sync Git URL:")
sync_tip.place(x=10, y=10)

api_sync = tk.StringVar(value=configs["sync"]["API"])
api_sync.trace_add("write", lambda *args: update_config(api_sync, "sync.API"))
tk.Entry(sync_settings_frame, textvariable=api_sync, width=50).place(x=10, y=40)

enabled_sync = tk.BooleanVar(value=configs["sync"]["enabled"])
enabled_sync.trace_add("write", lambda *args: update_config(enabled_sync, "sync.enabled"))
tk.Checkbutton(sync_settings_frame, text="Enabled", variable=enabled_sync).place(x=150, y=10)

write_sync = tk.BooleanVar(value=configs["sync"]["writePermission"])
write_sync.trace_add("write", lambda *args: update_config(write_sync, "sync.writePermission"))
tk.Checkbutton(sync_settings_frame, text="Write Permission", variable=write_sync).place(x=250, y=10)


# Proxy settings
proxy_settings_frame = tk.LabelFrame(settings_frame, text="Proxy Settings")
proxy_settings_frame.place(x=0, y=110, width=380, height=150)

is_proxy = tk.BooleanVar(value=configs["connection"]["isProxy"])
is_proxy.trace_add("write", lambda *args: update_config(is_proxy, "connection.isProxy"))
tk.Checkbutton(proxy_settings_frame, text="Use Proxy", variable=is_proxy).place(x=250, y=10)

proxy_address_tip = tk.Label(proxy_settings_frame, text="Proxy Address:")
proxy_address_tip.place(x=10, y=10)
proxy_address = tk.StringVar(value=configs["connection"]["address"])
proxy_address.trace_add("write", lambda *args: update_config(proxy_address, "connection.address"))
tk.Entry(proxy_settings_frame, textvariable=proxy_address, width=50).place(x=10, y=40)

proxy_username_tip = tk.Label(proxy_settings_frame, text="Username:")
proxy_username_tip.place(x=10, y=70)
proxy_username = tk.StringVar(value=configs["connection"]["username"])
proxy_username.trace_add("write", lambda *args: update_config(proxy_username, "connection.username"))
tk.Entry(proxy_settings_frame, textvariable=proxy_username, width=12).place(x=80, y=70)

proxy_password_tip = tk.Label(proxy_settings_frame, text="Password:")
proxy_password_tip.place(x=180, y=70)
proxy_password = tk.StringVar(value=configs["connection"]["password"])
proxy_password.trace_add("write", lambda *args: update_config(proxy_password, "connection.password"))
tk.Entry(proxy_settings_frame, textvariable=proxy_password, width=12).place(x=260, y=70)

proxy_port_tip = tk.Label(proxy_settings_frame, text="Proxy Port:")
proxy_port_tip.place(x=10, y=100)
proxy_port = tk.StringVar(value=configs["connection"]["port"])
proxy_port.trace_add("write", lambda *args: update_config(proxy_port, "connection.port"))
tk.Entry(proxy_settings_frame, textvariable=proxy_port, width=10).place(x=80, y=100)

apply_proxy_button = tk.Button(proxy_settings_frame, text="Apply", command=get_proxies, width=10, height=1)
apply_proxy_button.place(x=250, y=95)

# normal tkinter widgets
network_frame = tk.LabelFrame(root, text="API Access", padx=5, pady=5)
network_frame.place(x=10, y=500, width=200, height=180)

git_label = tk.Label(network_frame, text="Sync: Unknown")
git_label.pack(pady=5)

LLM_label = tk.Label(network_frame, text="LLM: Unknown")
LLM_label.pack(pady=5)

steam_label = tk.Label(network_frame, text="Steam: Unknown")
steam_label.pack(pady=5)

check_button = tk.Button(network_frame, text="Try Again", command=check_accessibility)
check_button.pack(pady=10)
check_accessibility()


root.mainloop()