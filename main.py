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
log_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

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
    elif len(text) < configs["common"]["minlength"]:
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

    git_label.config(text=f"Git Source: {git_status}")
    LLM_label.config(text=f"LLM: {openai_status}")
    steam_label.config(text=f"Steam: {steam_status}")




# normal tkinter widgets
network_frame = tk.LabelFrame(root, text="Network", padx=5, pady=5)
network_frame.place(x=10, y=500, width=200, height=180)

git_label = tk.Label(network_frame, text="Git Source: Unknown")
git_label.pack(pady=5)

LLM_label = tk.Label(network_frame, text="LLM: Unknown")
LLM_label.pack(pady=5)

steam_label = tk.Label(network_frame, text="Steam: Unknown")
steam_label.pack(pady=5)

check_button = tk.Button(network_frame, text="Try Again", command=check_accessibility)
check_button.pack(pady=10)
check_accessibility()


root.mainloop()