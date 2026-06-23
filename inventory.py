#!/usr/bin/env python3
import os
import io
import base64
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext

import requests
from PIL import Image, ImageTk, ImageOps

try:
    import pillow_heif
    pillow_heif.register_heif_opener()
except ImportError:
    pass


DEFAULT_MODEL = "@cf/meta/llama-4-scout-17b-16e-instruct"


class WorkersAIVisionApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Cloudflare Workers AI Image Prompt GUI")
        self.root.geometry("900x760")

        self.image_path = None
        self.preview_image = None

        self.build_ui()

    def build_ui(self):
        api_frame = tk.LabelFrame(self.root, text="Cloudflare Workers AI Credentials")
        api_frame.pack(fill="x", padx=10, pady=5)

        tk.Label(api_frame, text="Account ID:").grid(row=0, column=0, sticky="w", padx=5, pady=4)
        self.account_id_var = tk.StringVar(value=os.getenv("CLOUDFLARE_ACCOUNT_ID", ""))
        self.account_id_entry = tk.Entry(api_frame, textvariable=self.account_id_var, width=60)
        self.account_id_entry.grid(row=0, column=1, sticky="ew", padx=5, pady=4)

        tk.Label(api_frame, text="API Token:").grid(row=1, column=0, sticky="w", padx=5, pady=4)
        self.api_token_var = tk.StringVar(
            value=os.getenv("CLOUDFLARE_AUTH_TOKEN", os.getenv("CLOUDFLARE_API_TOKEN", ""))
        )
        self.api_token_entry = tk.Entry(api_frame, textvariable=self.api_token_var, show="*", width=60)
        self.api_token_entry.grid(row=1, column=1, sticky="ew", padx=5, pady=4)

        api_frame.columnconfigure(1, weight=1)

        model_frame = tk.Frame(self.root)
        model_frame.pack(fill="x", padx=10, pady=5)

        tk.Label(model_frame, text="Model:").pack(side="left")
        self.model_var = tk.StringVar(value=DEFAULT_MODEL)

        self.model_menu = tk.OptionMenu(
            model_frame,
            self.model_var,
            "@cf/meta/llama-4-scout-17b-16e-instruct",
        )
        self.model_menu.pack(side="left", padx=5)

        optimization_frame = tk.LabelFrame(self.root, text="Image Send Settings")
        optimization_frame.pack(fill="x", padx=10, pady=5)

        self.resize_var = tk.BooleanVar(value=True)
        tk.Checkbutton(
            optimization_frame,
            text="Resize/compress before sending",
            variable=self.resize_var,
        ).pack(side="left", padx=5)

        tk.Label(optimization_frame, text="Max side:").pack(side="left", padx=(15, 3))
        self.max_side_var = tk.StringVar(value="2500")
        tk.Entry(optimization_frame, textvariable=self.max_side_var, width=8).pack(side="left")

        tk.Label(optimization_frame, text="JPEG quality:").pack(side="left", padx=(15, 3))
        self.jpeg_quality_var = tk.StringVar(value="94")
        tk.Entry(optimization_frame, textvariable=self.jpeg_quality_var, width=8).pack(side="left")

        image_frame = tk.Frame(self.root)
        image_frame.pack(fill="x", padx=10, pady=5)

        self.select_button = tk.Button(image_frame, text="Select Image", command=self.select_image)
        self.select_button.pack(side="left")

        self.image_label_var = tk.StringVar(value="No image selected")
        tk.Label(image_frame, textvariable=self.image_label_var, anchor="w").pack(
            side="left", padx=10, fill="x", expand=True
        )

        preview_frame = tk.LabelFrame(self.root, text="Image Preview")
        preview_frame.pack(fill="both", padx=10, pady=5)

        self.preview_label = tk.Label(preview_frame, text="No image loaded", width=60, height=20)
        self.preview_label.pack(padx=10, pady=10)

        prompt_frame = tk.LabelFrame(self.root, text="Prompt")
        prompt_frame.pack(fill="both", padx=10, pady=5)

        self.prompt_text = scrolledtext.ScrolledText(prompt_frame, height=8, wrap=tk.WORD)
        self.prompt_text.pack(fill="both", expand=True, padx=5, pady=5)
        self.prompt_text.insert(
            "1.0",
            "Count the visible IC packages. For each IC, transcribe the marking exactly as visible. "
            "If a character is unclear, write [?]. Do not guess missing letters or numbers. "
            "Then give a likely short description only when the marking is readable."
        )

        action_frame = tk.Frame(self.root)
        action_frame.pack(fill="x", padx=10, pady=5)

        self.submit_button = tk.Button(action_frame, text="Send to Workers AI", command=self.run_request)
        self.submit_button.pack(side="left")

        self.status_var = tk.StringVar(value="Ready")
        tk.Label(action_frame, textvariable=self.status_var, anchor="w").pack(side="left", padx=10)

        response_frame = tk.LabelFrame(self.root, text="Response")
        response_frame.pack(fill="both", expand=True, padx=10, pady=5)

        self.response_text = scrolledtext.ScrolledText(response_frame, wrap=tk.WORD)
        self.response_text.pack(fill="both", expand=True, padx=5, pady=5)

    def select_image(self):
        path = filedialog.askopenfilename(
            title="Select an image",
            filetypes=[
                ("Image files", "*.png *.jpg *.jpeg *.webp *.bmp *.gif *.heic *.heif"),
                ("All files", "*.*"),
            ],
        )
        if not path:
            return

        self.image_path = path
        self.image_label_var.set(path)
        self.show_preview(path)

    def show_preview(self, path):
        try:
            image = Image.open(path)
            image = ImageOps.exif_transpose(image)
            image.thumbnail((500, 350))
            self.preview_image = ImageTk.PhotoImage(image)
            self.preview_label.config(image=self.preview_image, text="")
        except Exception as e:
            self.preview_label.config(image="", text="Preview unavailable")
            messagebox.showerror("Preview Error", f"Could not load image preview:\n{e}")

    def run_request(self):
        if not self.image_path:
            messagebox.showwarning("Missing Image", "Please select an image first.")
            return

        prompt = self.prompt_text.get("1.0", tk.END).strip()
        if not prompt:
            messagebox.showwarning("Missing Prompt", "Please enter a prompt.")
            return

        account_id = self.account_id_var.get().strip()
        if not account_id:
            messagebox.showwarning(
                "Missing Account ID",
                "Please enter your Cloudflare Account ID or set CLOUDFLARE_ACCOUNT_ID.",
            )
            return

        api_token = self.api_token_var.get().strip()
        if not api_token:
            messagebox.showwarning(
                "Missing API Token",
                "Please enter your Cloudflare Workers AI API token or set CLOUDFLARE_AUTH_TOKEN.",
            )
            return

        model = self.model_var.get().strip()

        try:
            max_side = int(self.max_side_var.get().strip())
            jpeg_quality = int(self.jpeg_quality_var.get().strip())

            if max_side < 256:
                raise ValueError("Max side must be at least 256.")
            if not (1 <= jpeg_quality <= 100):
                raise ValueError("JPEG quality must be between 1 and 100.")
        except ValueError as e:
            messagebox.showwarning("Invalid Image Settings", str(e))
            return

        self.submit_button.config(state="disabled")
        self.status_var.set("Sending request...")
        self.response_text.delete("1.0", tk.END)

        thread = threading.Thread(
            target=self.send_request,
            args=(
                account_id,
                api_token,
                model,
                prompt,
                self.resize_var.get(),
                max_side,
                jpeg_quality,
            ),
            daemon=True,
        )
        thread.start()

    def prepare_image_bytes(self, path, resize_enabled=True, max_side=2500, jpeg_quality=94):
        if not resize_enabled:
            with open(path, "rb") as f:
                return f.read(), self.guess_mime_type(path)

        image = Image.open(path)
        image = ImageOps.exif_transpose(image)

        resample = getattr(Image, "Resampling", Image).LANCZOS
        image.thumbnail((max_side, max_side), resample)

        if image.mode in ("RGBA", "LA"):
            background = Image.new("RGB", image.size, (255, 255, 255))
            alpha = image.getchannel("A")
            background.paste(image, mask=alpha)
            image = background
        else:
            image = image.convert("RGB")

        buffer = io.BytesIO()
        image.save(buffer, format="JPEG", quality=jpeg_quality, optimize=True)
        return buffer.getvalue(), "image/jpeg"

    def guess_mime_type(self, path):
        ext = os.path.splitext(path.lower())[1]

        if ext in [".jpg", ".jpeg"]:
            return "image/jpeg"
        if ext == ".png":
            return "image/png"
        if ext == ".webp":
            return "image/webp"
        if ext == ".gif":
            return "image/gif"
        if ext in [".heic", ".heif"]:
            return "image/heif"

        return "application/octet-stream"

    def workers_ai_url(self, account_id, model):
        return f"https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/run/{model}"

    def send_request(self, account_id, api_token, model, prompt, resize_enabled, max_side, jpeg_quality):
        try:
            self.root.after(0, lambda: self.status_var.set("Preparing image..."))

            image_bytes, mime_type = self.prepare_image_bytes(
                self.image_path,
                resize_enabled=resize_enabled,
                max_side=max_side,
                jpeg_quality=jpeg_quality,
            )

            image_base64 = base64.b64encode(image_bytes).decode("utf-8")
            image_data_url = f"data:{mime_type};base64,{image_base64}"

            self.root.after(0, lambda: self.status_var.set("Sending to Llama 4 Scout..."))

            url = self.workers_ai_url(account_id, model)
            headers = {
                "Authorization": f"Bearer {api_token}",
                "Content-Type": "application/json",
            }

            payload = {
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "You are a careful electronics image-analysis assistant. "
                            "For IC markings, transcribe only what is visible. "
                            "Do not invent part numbers. Use [?] for unclear characters."
                        ),
                    },
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": prompt,
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": image_data_url,
                                },
                            },
                        ],
                    },
                ],
                "max_tokens": 1200,
                "temperature": 0.05,
                "top_p": 0.8,
            }

            response = requests.post(
                url,
                headers=headers,
                json=payload,
                timeout=180,
            )

            data = self.safe_json(response)

            if not response.ok or not data.get("success", False):
                raise RuntimeError(
                    f"Cloudflare Workers AI request failed.\n\n"
                    f"HTTP {response.status_code}\n"
                    f"{self.format_cloudflare_error(data, response.text)}"
                )

            result = data.get("result", {})

            if isinstance(result, dict):
                text = result.get("response")
                if not text:
                    text = str(result)
            else:
                text = str(result)

            self.root.after(0, self.show_response, text)

        except Exception as e:
            self.root.after(0, self.show_error, str(e))

    def safe_json(self, response):
        try:
            return response.json()
        except Exception:
            return {}

    def format_cloudflare_error(self, data, fallback_text):
        if not data:
            return fallback_text

        errors = data.get("errors", [])
        messages = data.get("messages", [])

        parts = []

        if errors:
            parts.append("Errors:")
            for error in errors:
                parts.append(f"- {error}")

        if messages:
            parts.append("Messages:")
            for message in messages:
                parts.append(f"- {message}")

        if not parts:
            parts.append(str(data))

        return "\n".join(parts)

    def show_response(self, text):
        self.response_text.insert("1.0", text)
        self.status_var.set("Done")
        self.submit_button.config(state="normal")

    def show_error(self, error_message):
        self.response_text.insert("1.0", f"Error:\n{error_message}")
        self.status_var.set("Failed")
        self.submit_button.config(state="normal")


def main():
    root = tk.Tk()
    app = WorkersAIVisionApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()