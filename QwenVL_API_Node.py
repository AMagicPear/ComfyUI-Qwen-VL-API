import os
import io
import json
import requests
import torch
import dashscope
from dashscope import MultiModalConversation
from io import BytesIO
from PIL import Image, ImageChops
from datetime import datetime
import tempfile
import random
import platform
import hashlib

p = os.path.dirname(os.path.realpath(__file__))


def get_qwenvl_api_key():
    try:
        config_path = os.path.join(p, "config.json")
        with open(config_path, "r") as f:
            config = json.load(f)
        api_key = config["QWENVL_API_KEY"]
    except:
        print("出错啦 Error: API key is required")
        return ""
    return api_key


class QWenVL_API_S_Zho:

    def __init__(self):
        self.api_key = get_qwenvl_api_key()
        if self.api_key is not None:
            dashscope.api_key = self.api_key

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
                "prompt": (
                    "STRING",
                    {"default": "Describe this image", "multiline": True},
                ),
                "model_name": (["qwen-vl-plus", "qwen-vl-max"],),
                "seed": ("INT", {"default": 0, "min": 0, "max": 0xFFFFFFFFFFFFFFFF}),
            }
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("text",)
    FUNCTION = "qwen_vl_generation"

    CATEGORY = "Zho模块组/💫QWenVL"

    def tensor_to_image(self, tensor):
        # 确保张量是在CPU上
        tensor = tensor.cpu()

        # 将张量数据转换为0-255范围并转换为整数
        # 这里假设张量已经是H x W x C格式
        image_np = tensor.squeeze().mul(255).clamp(0, 255).byte().numpy()

        # 创建PIL图像
        image = Image.fromarray(image_np, mode="RGB")
        return image

    def qwen_vl_generation(self, image, prompt, model_name, seed):
        if not self.api_key:
            raise ValueError("API key is required")

        if image == None:
            raise ValueError("qwen_vl needs a image")
        else:
            # 转换图像
            pil_image = self.tensor_to_image(image)

            # 生成临时文件路径
            temp_directory = tempfile.gettempdir()
            unique_suffix = "_temp_" + "".join(
                random.choice("abcdefghijklmnopqrstuvwxyz") for _ in range(5)
            )
            filename = f"image{unique_suffix}.png"
            temp_image_path = os.path.join(temp_directory, filename)
            # temp_image_url = f"file://{temp_image_path}"

            # 根据操作系统选择正确的文件URL格式
            if platform.system() == "Windows":
                temp_image_url = f"file://{temp_image_path}"
            else:
                temp_image_url = f"file:///{temp_image_path}"

            temp_image_url = temp_image_url.replace("\\", "/")

            # 保存图像到临时路径
            pil_image.save(temp_image_path)

            messages = [
                {
                    "role": "user",
                    "content": [{"image": temp_image_url}, {"text": prompt}],
                }
            ]

            # print("temp_image_url:", temp_image_url)
            # print("prompt:", prompt)

            torch.manual_seed(seed)

            response = dashscope.MultiModalConversation.call(
                model=model_name, messages=messages, seed=seed
            )
            # print(response)

            response_json = response
            if "output" in response_json and "choices" in response_json["output"]:
                choices = response_json["output"]["choices"]
                if choices and "message" in choices[0]:
                    message_content = choices[0]["message"]["content"]
                    if message_content and "text" in message_content[0]:
                        text_output = message_content[0]["text"]
                        # print(text_output)
                    else:
                        print("No text content found.")
                else:
                    print("No message found in the first choice.")
            else:
                print("No choices found in the output.")

            os.remove(temp_image_path)
            # print("remove : done!" )

        return (text_output,)


class QWenVL_API_S_Multi_Zho:

    def __init__(self):
        self.api_key = get_qwenvl_api_key()
        self.messages = []  # 初始化对话历史为空
        self.last_image_hash = None
        if self.api_key is not None:
            dashscope.api_key = self.api_key

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
                "prompt": (
                    "STRING",
                    {"default": "Describe this image", "multiline": True},
                ),
                "model_name": (["qwen-vl-plus", "qwen-vl-max"],),
                "seed": ("INT", {"default": 0, "min": 0, "max": 0xFFFFFFFFFFFFFFFF}),
            }
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("text",)
    FUNCTION = "qwen_vl_generation"

    CATEGORY = "Zho模块组/💫QWenVL"

    def tensor_to_image(self, tensor):
        # 确保张量是在CPU上
        tensor = tensor.cpu()

        # 将张量数据转换为0-255范围并转换为整数
        # 这里假设张量已经是H x W x C格式
        image_np = tensor.squeeze().mul(255).clamp(0, 255).byte().numpy()

        # 创建PIL图像
        image = Image.fromarray(image_np, mode="RGB")
        return image

    def format_qwchat_history(self):
        formatted_history = []
        for message in self.messages:
            role = message["role"]
            contents = message["content"]
            for content in contents:
                if "text" in content:
                    text = content["text"]
                    formatted_message = f"{role}: {text}"
                    formatted_history.append(formatted_message)
            formatted_history.append("-" * 40)  # 添加分隔线
        return "\n".join(formatted_history)

    def get_image_hash(self, pil_image):
        # 将图像转换为字节
        image_bytes = pil_image.tobytes()
        # 使用哈希函数计算哈希值
        return hashlib.md5(image_bytes).hexdigest()

    def qwen_vl_generation(self, image, prompt, model_name, seed):
        if not self.api_key:
            raise ValueError("API key is required")

        if image == None:
            raise ValueError("qwen_vl needs a image")
        else:
            # 转换图像
            pil_image = self.tensor_to_image(image)

            # 在当前文件目录下创建 "qw" 文件夹（如果不存在）
            qw_folder = os.path.join(p, "qw")
            os.makedirs(qw_folder, exist_ok=True)

            # 获取当前图像的哈希值
            current_image_hash = self.get_image_hash(pil_image)

            # 构建文件名
            local_image_filename = f"image_{current_image_hash}.png"
            local_image_path = os.path.join(qw_folder, local_image_filename)

            # 根据操作系统选择正确的文件URL格式
            if platform.system() == "Windows":
                local_image_url = f"file://{local_image_path}"
            else:
                local_image_url = f"file:///{local_image_path}"

            # 保证路径中的反斜杠被替换为正斜杠
            local_image_url = local_image_url.replace("\\", "/")

            # 如果当前图像与上次的不同
            if current_image_hash != self.last_image_hash:
                pil_image.save(local_image_path)
                # 更新last_image_hash
                self.last_image_hash = current_image_hash
                print(f"Image saved as {local_image_filename}")
            else:
                print("Image not saved as it is identical to the last one.")

            self.messages.append(
                {
                    "role": "user",
                    "content": [{"image": local_image_url}, {"text": prompt}],
                }
            )

            # print("local_image_url:", local_image_url)
            # print("prompt:", prompt)

            torch.manual_seed(seed)

            response = dashscope.MultiModalConversation.call(
                model=model_name, messages=self.messages, seed=seed
            )
            # print(response)

            # 更新对话历史
            if response and response.output and response.output.choices:
                choice = response.output.choices[0]
                if choice and choice.message:
                    self.messages.append(
                        {"role": choice.message.role, "content": choice.message.content}
                    )

            response_json = response
            if "output" in response_json and "choices" in response_json["output"]:
                choices = response_json["output"]["choices"]
                if choices and "message" in choices[0]:
                    message_content = choices[0]["message"]["content"]
                    if message_content and "text" in message_content[0]:
                        text_output = message_content[0]["text"]
                        # print(text_output)
                    else:
                        print("No text content found.")
                else:
                    print("No message found in the first choice.")
            else:
                print("No choices found in the output.")

            # 获取格式化的对话历史
            chat_history = self.format_qwchat_history()

        return (chat_history,)


class QWenPlus_Chat:

    def __init__(self):
        self.api_key = get_qwenvl_api_key()
        if self.api_key is not None:
            dashscope.api_key = self.api_key

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "prompt": ("STRING", {"default": "", "multiline": True}),
                "model_name": (
                    ["qwen-turbo", "qwen-plus", "qwen-max", "llama3.1-8b-instruct"],
                ),
                "seed": ("INT", {"default": 0, "min": 0, "max": 0xFFFFFFFFFFFFFFFF}),
            }
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("text",)
    FUNCTION = "qwen_generation"

    CATEGORY = "Zho模块组/💫QWen"

    def qwen_generation(self, prompt, model_name, seed):
        if not self.api_key:
            raise ValueError("API key is required")
        messages = [
            {
                "role": "system",
                "content": "你是一个提示词翻译器，你会将接下来用户输入的文本描述翻译成英文版本的适合Stable Diffusion输入的提示词。不需要额外的描述信息，只需要回复单纯正向提示词即可。",
            },
            {
                "role": "system",
                "content": "在Stable Diffusion的正向提示词书写中，应该注重准确、清晰地传达你期望生成图像的特征。首先，描述应简洁且具体，避免模糊的词汇，可以使用具体的物体、风格、颜色、情感等词语。其次，关键词之间的顺序和组合要有逻辑性，通常将核心元素放在前面，辅以风格或细节描述，确保模型能理解并生成符合要求的图像。同时，可以使用多个逗号或分隔符来强化不同特征，但避免过多重复。正向提示词的书写要根据实际需求灵活调整，通常建议在输出中体现具体场景、氛围或某种视觉效果。",
            },
            {
                "role": "system",
                "content": "当我的回复本就是英文时，不需要再次翻译，直接回复即可。当我的回复中含有括号包含的内容时，例如`(树林:1.2)`，请在翻译后的提示词中也保留这个括号，例如`(forest:1.2)`。如果我的描述不是某个具体画面，那么请发挥你的想象力来为这段话讲述画面并回复提示词。",
            },
            {"role": "user", "content": prompt},
        ]
        torch.manual_seed(seed)

        response = dashscope.Generation.call(
            api_key=self.api_key,
            model=model_name,
            messages=messages,
            seed=seed,
            result_format="text",
        )

        return (response.output.text,)


NODE_CLASS_MAPPINGS = {
    "QWenVL_API_S_Zho": QWenVL_API_S_Zho,
    "QWenVL_API_S_Multi_Zho": QWenVL_API_S_Multi_Zho,
    "QWenPrompt_Translator": QWenPlus_Chat,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "QWenVL_API_S_Zho": "㊙️QWenVL_Zho",
    "QWenVL_API_S_Multi_Zho": "㊙️QWenVL_Chat_Zho",
    "QWenPrompt_Translator": "🍐通义千问提示词翻译",
}
