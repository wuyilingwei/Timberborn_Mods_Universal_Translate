import copy
import os
import sys
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

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

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
root.tk.call('wm', 'iconphoto', root._w, tk.PhotoImage(file=resource_path("logo.png")))

log_frame = tk.LabelFrame(root, text="Log")
log_frame.place(x=800, y=10, width=460, height=700)

log_text = ScrolledText(log_frame, state=tk.DISABLED, wrap=tk.WORD)
log_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

text_handler = TextHandler(log_text)
text_handler.setLevel(logging.INFO)
text_handler.setFormatter(formatter)
logger.addHandler(text_handler)

# Load the default config
default_configs = {
    'common': {'version': 0.2, 'columns': '2,3'},
    'sync': {'enabled': True, 'API': 'https://github.com/wuyilingwei/TMT_Data.git', 'writePermission': False},
    'steam': {'mode': 'command', 'userName': '', 'installPath': ''},
    'LLM': {'API': 'https://api.openai.com/v1/chat/completions', 'token': '', 'model': 'gpt-4o-mini', 'minlength': 2, 'lang': '', 'prompt': 'You are a professional, authentic machine translation engine. Translate text to {lang}, preserving structure, codes, and markup.'},
    'connection': {'isProxy': False, 'address': '', 'port': '', 'username': '', 'password': ''}}

configs = copy.deepcopy(default_configs)
if os.path.exists('config.toml'):
    configs.update(toml.load('config.toml'))
    configs['common']['version'] = default_configs['common']['version']

def save_config():
    with open('config.toml', 'w') as f:
        toml.dump(configs, f)

save_config()

def update_config(var, config_path):
    keys = config_path.split(".")
    config_section = configs
    for key in keys[:-1]:
        config_section = config_section[key]
    config_section[keys[-1]] = var.get()
    logging.debug(f"Updated config: {config_path} -> {var.get()}")
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
    """
    if configs["LLM"]["isParallelProcessing"]:
        prompt += configs["LLM"]["promptParallelProcessing"].replace("{signParallelProcessing}", configs["LLM"]["signParallelProcessing"])
    """
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


# settings frame
settings_frame = tk.LabelFrame(root, text="Settings", padx=5, pady=0)
settings_frame.place(x=10, y=10, width=780, height=360)


# data sync settings
sync_settings_frame = tk.LabelFrame(settings_frame, text="Sync Settings")
sync_settings_frame.place(x=0, y=0, width=380, height=80)

sync_tip = tk.Label(sync_settings_frame, text="Sync Git URL:")
sync_tip.place(x=10, y=0)

api_sync = tk.StringVar(value=configs["sync"]["API"])
api_sync.trace_add("write", lambda *args: update_config(api_sync, "sync.API"))
tk.Entry(sync_settings_frame, textvariable=api_sync, width=50).place(x=10, y=30)

enabled_sync = tk.BooleanVar(value=configs["sync"]["enabled"])
enabled_sync.trace_add("write", lambda *args: update_config(enabled_sync, "sync.enabled"))
tk.Checkbutton(sync_settings_frame, text="Enabled", variable=enabled_sync).place(x=150, y=0)

write_sync = tk.BooleanVar(value=configs["sync"]["writePermission"])
write_sync.trace_add("write", lambda *args: update_config(write_sync, "sync.writePermission"))
tk.Checkbutton(sync_settings_frame, text="Write Permission", variable=write_sync).place(x=250, y=0)


# Proxy settings
proxy_settings_frame = tk.LabelFrame(settings_frame, text="Proxy Settings (socks5)")
proxy_settings_frame.place(x=0, y=90, width=380, height=150)

is_proxy = tk.BooleanVar(value=configs["connection"]["isProxy"])
is_proxy.trace_add("write", lambda *args: update_config(is_proxy, "connection.isProxy"))
tk.Checkbutton(proxy_settings_frame, text="Use Proxy", variable=is_proxy).place(x=250, y=0)

proxy_address_tip = tk.Label(proxy_settings_frame, text="Server Address:")
proxy_address_tip.place(x=10, y=0)
proxy_address = tk.StringVar(value=configs["connection"]["address"])
proxy_address.trace_add("write", lambda *args: update_config(proxy_address, "connection.address"))
tk.Entry(proxy_settings_frame, textvariable=proxy_address, width=50).place(x=10, y=30)

proxy_username_tip = tk.Label(proxy_settings_frame, text="Username:")
proxy_username_tip.place(x=10, y=60)
proxy_username = tk.StringVar(value=configs["connection"]["username"])
proxy_username.trace_add("write", lambda *args: update_config(proxy_username, "connection.username"))
tk.Entry(proxy_settings_frame, textvariable=proxy_username, width=12).place(x=80, y=60)

proxy_password_tip = tk.Label(proxy_settings_frame, text="Password:")
proxy_password_tip.place(x=180, y=60)
proxy_password = tk.StringVar(value=configs["connection"]["password"])
proxy_password.trace_add("write", lambda *args: update_config(proxy_password, "connection.password"))
tk.Entry(proxy_settings_frame, textvariable=proxy_password, width=12).place(x=260, y=60)

proxy_port_tip = tk.Label(proxy_settings_frame, text="Proxy Port:")
proxy_port_tip.place(x=10, y=100)
proxy_port = tk.StringVar(value=configs["connection"]["port"])
proxy_port.trace_add("write", lambda *args: update_config(proxy_port, "connection.port"))
tk.Entry(proxy_settings_frame, textvariable=proxy_port, width=10).place(x=80, y=100)

apply_proxy_button = tk.Button(proxy_settings_frame, text="Apply", command=get_proxies, width=10, height=1)
apply_proxy_button.place(x=250, y=95)

# steam settings
steam_settings_frame = tk.LabelFrame(settings_frame, text="Steam Settings")
steam_settings_frame.place(x=0, y=250, width=380, height=85)

steam_mode = tk.StringVar(value=configs["steam"]["mode"])
steam_mode.trace_add("write", lambda *args: update_config(steam_mode, "steam.mode"))

command_radio = tk.Radiobutton(steam_settings_frame, text="CMD", variable=steam_mode, value="command")
command_radio.place(x=10, y=0)

client_radio = tk.Radiobutton(steam_settings_frame, text="Client", variable=steam_mode, value="client")
client_radio.place(x=10, y=30)

steam_path_tip = tk.Label(steam_settings_frame, text="Username:")
steam_path_tip.place(x=80, y=2)
steam_username = tk.StringVar(value=configs["steam"]["userName"])
steam_username.trace_add("write", lambda *args: update_config(steam_username, "steam.userName"))
tk.Entry(steam_settings_frame, textvariable=steam_username, width=15).place(x=150, y=2)

def init_steam():
    return None

steam_init = tk.Button(steam_settings_frame, text="Init", command=init_steam, width=5, height=1)
steam_init.place(x=300, y=0)

steam_path_tip = tk.Label(steam_settings_frame, text="Path:")
steam_path_tip.place(x=80, y=32)
steam_path = tk.StringVar(value=configs["steam"]["installPath"])
steam_path.trace_add("write", lambda *args: update_config(steam_path, "steam.installPath"))
tk.Entry(steam_settings_frame, textvariable=steam_path, width=35).place(x=120, y=32)


# LLM settings
llm_settings_frame = tk.LabelFrame(settings_frame, text="LLM Settings")
llm_settings_frame.place(x=385, y=0, width=380, height=335)

llm_tip = tk.Label(llm_settings_frame, text="API:")
llm_tip.place(x=10, y=10)
api_llm = tk.StringVar(value=configs["LLM"]["API"])
api_llm.trace_add("write", lambda *args: update_config(api_llm, "LLM.API"))
tk.Entry(llm_settings_frame, textvariable=api_llm, width=50).place(x=10, y=40)

llm_token_tip = tk.Label(llm_settings_frame, text="Token:")
llm_token_tip.place(x=10, y=70)
api_llm_token = tk.StringVar(value=configs["LLM"]["token"])
api_llm_token.trace_add("write", lambda *args: update_config(api_llm_token, "LLM.token"))
tk.Entry(llm_settings_frame, textvariable=api_llm_token, width=50).place(x=10, y=100)

llm_model_tip = tk.Label(llm_settings_frame, text="Model:")
llm_model_tip.place(x=10, y=130)
api_llm_model = tk.StringVar(value=configs["LLM"]["model"])
api_llm_model.trace_add("write", lambda *args: update_config(api_llm_model, "LLM.model"))
tk.Entry(llm_settings_frame, textvariable=api_llm_model, width=15).place(x=60, y=130)

llm_leng_tip = tk.Label(llm_settings_frame, text="Min Length:")
llm_leng_tip.place(x=180, y=130)
api_llm_minlength = tk.StringVar(value=configs["LLM"]["minlength"])
api_llm_minlength.trace_add("write", lambda *args: update_config(api_llm_minlength, "LLM.minlength"))
tk.Entry(llm_settings_frame, textvariable=api_llm_minlength, width=15).place(x=260, y=130)

llm_lang_tip = tk.Label(llm_settings_frame, text="Language:")
llm_lang_tip.place(x=180, y=160)
api_llm_lang = tk.StringVar(value=configs["LLM"]["lang"])
api_llm_lang.trace_add("write", lambda *args: update_config(api_llm_lang, "LLM.lang"))
tk.Entry(llm_settings_frame, textvariable=api_llm_lang, width=15).place(x=260, y=160)

llm_prompt_tip = tk.Label(llm_settings_frame, text="Prompt:")
llm_prompt_tip.place(x=10, y=160)
edit_prompt_var = tk.BooleanVar(value=False)
edit_prompt_check = tk.Checkbutton(llm_settings_frame, text="Edit", variable=edit_prompt_var, command=lambda: toggle_prompt_edit(edit_prompt_var.get()))
edit_prompt_check.place(x=120, y=160)
llm_prompt_text = tk.Text(llm_settings_frame, width=50, height=8, wrap=tk.WORD)
llm_prompt_text.insert(tk.END, configs["LLM"]["prompt"])
llm_prompt_text.config(state=tk.DISABLED)
llm_prompt_text.place(x=10, y=190)
def toggle_prompt_edit(editable):
    if editable:
        llm_prompt_text.config(state=tk.NORMAL)
    else:
        llm_prompt_text.config(state=tk.DISABLED)
def update_config_text(*args):
    if edit_prompt_var.get():
        configs["LLM"]["prompt"] = llm_prompt_text.get("1.0", tk.END).strip()
        save_config()
llm_prompt_text.bind("<KeyRelease>", update_config_text)


"""
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

network_frame = tk.LabelFrame(root, text="API Access", padx=5, pady=5)
network_frame.place(x=10, y=500, width=100, height=180)

git_label = tk.Label(network_frame, text="Sync: Unknown")
git_label.pack(pady=5)

LLM_label = tk.Label(network_frame, text="LLM: Unknown")
LLM_label.pack(pady=5)

steam_label = tk.Label(network_frame, text="Steam: Unknown")
steam_label.pack(pady=5)

check_button = tk.Button(network_frame, text="Try Again", command=check_accessibility)
check_button.pack(pady=10)
"""


logger.info("Application started")
logger.debug(configs)

root.mainloop()