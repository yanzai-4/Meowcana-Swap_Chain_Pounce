"""Minimal PixelLab v2 client (stdlib only). Token comes from the PIXELLAB_API_KEY env var."""

import base64
import json
import os
import time
import urllib.error
import urllib.request

BASE = "https://api.pixellab.ai/v2"


class PixelLab:
    def __init__(self, token=None):
        self.token = token or os.environ.get("PIXELLAB_API_KEY")
        if not self.token:
            raise SystemExit("Set PIXELLAB_API_KEY (see arcade/README.md, Asset pipeline).")
        self.spent = 0.0

    def _request(self, method, path, body=None, timeout=300):
        data = json.dumps(body).encode() if body is not None else None
        request = urllib.request.Request(BASE + path, data=data, method=method, headers={
            "Authorization": f"Bearer {self.token}", "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(request, timeout=timeout) as reply:
                payload = json.loads(reply.read())
        except urllib.error.HTTPError as error:
            raise RuntimeError(f"{method} {path}: HTTP {error.code} {error.read()[:300]!r}") from None
        usage = payload.get("usage") or {}
        if usage.get("type") == "usd":
            self.spent += usage.get("usd") or 0
        return payload

    def balance(self):
        return self._request("GET", "/balance", timeout=30)

    def wait(self, job_id, poll=4, limit=600):
        deadline = time.monotonic() + limit
        while time.monotonic() < deadline:
            job = self._request("GET", f"/background-jobs/{job_id}", timeout=30)
            if job.get("status") == "completed":
                return job.get("last_response") or {}
            if job.get("status") == "failed":
                raise RuntimeError(f"job {job_id} failed: {json.dumps(job.get('last_response'))[:300]}")
            time.sleep(poll)
        raise TimeoutError(f"job {job_id} still running after {limit}s")

    def create_image_pixen(self, **body):
        return png_bytes(self._request("POST", "/create-image-pixen", body)["image"])

    def animate_with_text_v3(self, first_frame_png, action, frame_count, seed=0):
        job = self._request("POST", "/animate-with-text-v3", {
            "first_frame": {"type": "base64", "base64": base64.b64encode(first_frame_png).decode(),
                            "format": "png"},
            "action": action, "frame_count": frame_count, "seed": seed, "no_background": True})
        return [png_bytes(image) for image in self.wait(job["background_job_id"])["images"]]

    def edit_image_pixen(self, image_png, description, seed=None):
        """Edit an existing sprite with a text instruction; pose and pixel style are kept."""
        body = {"image": {"type": "base64", "base64": base64.b64encode(image_png).decode(), "format": "png"},
                "description": description, "no_background": True}
        if seed is not None:
            body["seed"] = seed
        job = self._request("POST", "/edit-image-pixen", body)
        result = self.wait(job["background_job_id"])
        return png_bytes(result["image"] if "image" in result else result["images"][0])


def png_bytes(image):
    data = image["base64"]
    return base64.b64decode(data.split(",", 1)[1] if data.startswith("data:") else data)
