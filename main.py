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

# Load the default config
if not os.path.exists("config.toml"):
    shutil.copy("default.toml", "config.toml")

configs = toml.load("config.toml")
if configs['common']['version'] < 1.0:
    if os.path.exists("config_bak.txt"):
        os.remove("config_bak.txt")
    shutil.move("config.toml", "config_bak.txt")
    shutil.copy("default.toml", "config.toml")
    configs = toml.load("config.toml")
    open_file_async("config_bak.txt")

def save_config():
    with open('config.toml', 'w') as f:
        toml.dump(configs, f)

# initialize proxy settings
def get_proxies():
    if configs['connection']['isProxy']:
        proxy_auth = f"{configs['connection']['username']}:{configs['connection']['password']}@" if configs['connection']['username'] and configs['connection']['password'] else ""
        proxy_url = f"http://{proxy_auth}{configs['connection']['address']}:{configs['connection']['port']}"
        return {
            "http": proxy_url,
            "https": proxy_url
        }
    return None

proxies = get_proxies()

def get_domain(url):
    parsed_url = urlparse(url)
    return parsed_url.netloc

def check_accessibility():
    git_status = "Unknown"
    openai_status = "Unknown"

    # Check Git accessibility
    try:
        response = requests.get(get_domain(configs["sync"]["endPoint"]), timeout=5)
        if response.status_code == 200:
            git_status = "Accessible"
            logger.info(f"Sync: {git_status}")
        else:
            git_status = "Not Accessible"
            logger.info(f"Sync: {git_status}")
            logger.info(f"Response: {response.status_code}")
    except requests.RequestException:
        git_status = "Not Accessible"
        logger.info(f"Sync: {git_status}")
        logger.info(f"Error: {requests.RequestException}")

    # Check OpenAI accessibility
    try:
        response = requests.get(get_domain(configs["LLM"]["api"]), timeout=5)
        if response.status_code == 200:
            openai_status = "Accessible"
            logger.info(f"OpenAI: {openai_status}")
        else:
            openai_status = "Not Accessible"
            logger.info(f"OpenAI: {openai_status}")
            logger.info(f"Response: {response.status_code}")
    except requests.RequestException:
        openai_status = "Not Accessible"
        logger.info(f"OpenAI: {openai_status}")
        logger.info(f"Error: {requests.RequestException}")

    git_label.config(text=f"Git Source: {git_status}")
    openai_label.config(text=f"OpenAI: {openai_status}")

root = tk.Tk()
root.title("Timberborn mod translator")
root.geometry("1280x720")

log_frame = tk.LabelFrame(root, text="Log")
log_frame.place(x=800, y=10, width=460, height=700)

log_text = ScrolledText(log_frame, state=tk.DISABLED, wrap=tk.WORD)
log_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

# 将自定义日志处理器添加到 logger
text_handler = TextHandler(log_text)
text_handler.setLevel(logging.INFO)
text_handler.setFormatter(formatter)
logger.addHandler(text_handler)

network_frame = tk.LabelFrame(root, text="Network", padx=5, pady=5)
network_frame.place(x=10, y=10, width=200, height=300)

git_label = tk.Label(network_frame, text="Git Source: Unknown")
git_label.pack(pady=5)

openai_label = tk.Label(network_frame, text="OpenAI: Unknown")
openai_label.pack(pady=5)

check_button = tk.Button(network_frame, text="Check Accessibility", command=check_accessibility)
check_button.pack(pady=10)

root.mainloop()