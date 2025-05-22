import json
import os
from PIL import Image, ImageOps
import imageio.v2 as imageio_v2

SUPPORTED_IMAGE_FORMATS = {'.png', '.jpg', '.jpeg', '.bmp', '.tif', '.tiff'}
SUPPORTED_VIDEO_FORMATS = {'.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv'}

def parse_layout(json_path):
    with open(json_path, 'r') as f:
        return json.load(f)

class StaticImageLoader:
    def __init__(self, path):
        self.path = path
        self.img = Image.open(path).convert('RGBA')
    def get_frame(self, idx=None, total=None):
        return self.img.copy()
    def num_frames(self):
        return 1

class GifLoader:
    def __init__(self, path):
        self.path = path
        self._frames = []
        with Image.open(path) as im:
            try:
                while True:
                    self._frames.append(im.convert('RGBA').copy())
                    im.seek(im.tell() + 1)
            except EOFError:
                pass
        self.length = len(self._frames)
    def get_frame(self, idx, total):
        if self.length == 0:
            return Image.new('RGBA', (1, 1), (0,0,0,0))
        frame_idx = idx % self.length
        return self._frames[frame_idx].copy()
    def num_frames(self):
        return self.length

class VideoLoader:
    def __init__(self, path):
        self.path = path
        self.reader = imageio_v2.get_reader(path, 'ffmpeg')
        try:
            self.length = self.reader.count_frames()
        except Exception:
            self.length = 1
    def get_frame(self, idx, total):
        frame_idx = idx % self.length
        try:
            frame = self.reader.get_data(frame_idx)
        except Exception:
            frame = self.reader.get_data(0)
        img = Image.fromarray(frame)
        return img.convert('RGBA')
    def num_frames(self):
        return self.length

# FIX: Add get_loader definition (was missing)
def get_loader(item):
    path = item['path']
    ext = os.path.splitext(path)[1].lower()
    if item['type'] == 'gif' or ext == '.gif':
        return GifLoader(path)
    elif item['type'] == 'video' or ext in SUPPORTED_VIDEO_FORMATS:
        return VideoLoader(path)
    elif item['type'] == 'image' or ext in SUPPORTED_IMAGE_FORMATS:
        return StaticImageLoader(path)
    else:
        raise ValueError(f"Unsupported file type for {path}")

def compute_content_bounding_box(layout_items):
    min_x = float('inf')
    min_y = float('inf')
    max_x = float('-inf')
    max_y = float('-inf')
    for item in layout_items:
        x, y = item['x'], item['y']
        w, h = item['width'], item['height']
        angle = item.get('rotation_degrees', 0)
        if angle:
            from math import radians, cos, sin
            theta = radians(angle)
            corners = [
                (0, 0), (w, 0), (w, h), (0, h)
            ]
            rotated = [
                (
                    x + c[0]*cos(theta) - c[1]*sin(theta),
                    y + c[0]*sin(theta) + c[1]*cos(theta)
                ) for c in corners
            ]
            xs = [cx for cx, cy in rotated]
            ys = [cy for cx, cy in rotated]
            min_x = min(min_x, min(xs))
            min_y = min(min_y, min(ys))
            max_x = max(max_x, max(xs))
            max_y = max(max_y, max(ys))
        else:
            min_x = min(min_x, x)
            min_y = min(min_y, y)
            max_x = max(max_x, x + w)
            max_y = max(max_y, y + h)
    min_x, min_y = int(min_x), int(min_y)
    max_x, max_y = int(max_x), int(max_y)
    return min_x, min_y, max_x, max_y

def composite_frame(layout_items, loaders, frame_idx, total_frames, min_x, min_y, canvas_size):
    canvas = Image.new('RGBA', canvas_size, (255,255,255,0))
    ordered = sorted(zip(layout_items, loaders), key=lambda x: x[0]['order'])
    for item, loader in ordered:
        img = loader.get_frame(frame_idx, total_frames)
        w, h = item['width'], item['height']
        angle = item.get('rotation_degrees', 0)
        img = img.resize((w, h), resample=Image.LANCZOS)
        if angle:
            img = img.rotate(-angle, expand=True, resample=Image.BICUBIC)
        x, y = item['x'], item['y']
        paste_x, paste_y = int(x - min_x), int(y - min_y)
        canvas.alpha_composite(img, (paste_x, paste_y))
    return canvas

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Render layout JSON as image sequence, cropped to content.")
    parser.add_argument('layout_json', help="Path to exported layout JSON file.")
    parser.add_argument('output_folder', help="Folder to write frame images into (created if doesn't exist).")
    parser.add_argument('--frames', type=int, default=None, help="Number of frames (default=max over all media)")
    args = parser.parse_args()

    layout = parse_layout(args.layout_json)
    loaders = [get_loader(item) for item in layout]
    if args.frames:
        total_frames = args.frames
    else:
        total_frames = max((ldr.num_frames() for ldr in loaders), default=1)
    min_x, min_y, max_x, max_y = compute_content_bounding_box(layout)
    canvas_size = (max_x - min_x, max_y - min_y)
    os.makedirs(args.output_folder, exist_ok=True)
    for idx in range(total_frames):
        frame = composite_frame(layout, loaders, idx, total_frames, min_x, min_y, canvas_size)
        outpath = os.path.join(args.output_folder, f"frame_{idx:03d}.png")
        frame.save(outpath)
        print(f"Saved {outpath}")

if __name__ == '__main__':
    main()
