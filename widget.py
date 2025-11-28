import flet as ft
import json
import os
import subprocess
import platform
import webbrowser
import base64
import urllib.request
import threading

DATA_FILE = os.path.join("data", "reading_list.json")
WEBHOOK_URL = "http://localhost:5678/webhook/refresh"

# --- TRIGGER LOGIC ---
def trigger_n8n_update():
    """Pings n8n with detailed error reporting."""
    print(f"Attempting to connect to: {WEBHOOK_URL}")
    try:
        with urllib.request.urlopen(WEBHOOK_URL, timeout=1) as response:
            print(f"Trigger sent! Server code: {response.getcode()}")
    except Exception as e:
        print(f"Trigger silent fail (normal if n8n busy): {e}")

# --- BROWSER & IMAGE LOGIC ---
def open_brave_private(url):
    if not url: return
    system_name = platform.system()
    try:
        if system_name == "Darwin": 
            subprocess.run(["open", "-a", "Brave Browser", "--args", "--incognito", url])  
        elif system_name == "Windows":
            paths = [
                r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe",
                r"C:\Program Files (x86)\BraveSoftware\Brave-Browser\Application\brave.exe",
                os.path.expanduser(r"~\AppData\Local\BraveSoftware\Brave-Browser\Application\brave.exe")
            ]
            for path in paths:
                if os.path.exists(path):
                    subprocess.Popen([path, "--incognito", url])
                    return
            raise FileNotFoundError("Brave not found")
        else: 
            subprocess.Popen(["brave-browser", "--incognito", url])
    except Exception as e:
        webbrowser.open(url)

def get_image_base64(url):
    if not url or "http" not in url: return None
    try:
        req = urllib.request.Request(
            url, 
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
        )
        with urllib.request.urlopen(req) as response:
            return base64.b64encode(response.read()).decode("utf-8")
    except Exception as e:
        return None

# --- MAIN APP ---
def main(page: ft.Page):
    # 1. TRIGGER UPDATE ON STARTUP
    threading.Thread(target=trigger_n8n_update, daemon=True).start()

    page.title = "Manga Dashboard"
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 0
    
    # Window Config
    page.window_width = 1800
    page.window_height = 1600
    page.window_frameless = True 
    page.window_title_bar_hidden = True 
    page.window_resizable = False 
    page.window_always_on_top = False 
    page.window_skip_task_bar = True
    
    page.window_left = 50  
    page.window_top = 50
    page.bgcolor = ft.Colors.BLACK 

    # --- GRID CONFIGURATION ---
    manga_grid_view = ft.GridView(
        expand=True,
        runs_count=3,
        max_extent=600,
        child_aspect_ratio=2.2,
        spacing=20,
        run_spacing=20,
        padding=20,
    )

    def load_data():
        if not os.path.exists(DATA_FILE): return []
        try:
            with open(DATA_FILE, "r") as f:
                data = json.load(f)
                if isinstance(data, list): return data
                return []
        except: return []

    def save_data(data):
        with open(DATA_FILE, "w") as f: json.dump(data, f, indent=2)

    def mark_as_read(e, item_id, latest_chap):
        data = load_data()
        for item in data:
            if item.get("id") == item_id:
                item["last_read"] = latest_chap
                item["hype_message"] = "Caught up!"
        save_data(data)
        refresh_ui()

    def create_card(item):
        title = item.get("title", "Unknown Series")
        item_id = item.get("id", "unknown")
        url = item.get("url", "")
        img_src = item.get("thumbnail", "")
        latest = item.get("latest_available", 0)
        last = item.get("last_read", 0)
        
        has_update = latest > last
        
        if has_update:
            diff = latest - last
            status_text = f"🔥 {diff} New Chapters"
            status_color = ft.Colors.ORANGE_400
            btn_text = f"Read Ch. {latest}"
            btn_bg = ft.Colors.BLUE_700
            border_color = ft.Colors.BLUE_900
        else:
            status_text = "Caught up"
            status_color = ft.Colors.GREEN_400
            btn_text = "Open"
            btn_bg = ft.Colors.GREY_800
            border_color = ft.Colors.GREY_900

        img_h = 250 
        img_w = 170 
        b64_img = get_image_base64(img_src)
        left_radius = ft.border_radius.only(top_left=12, bottom_left=12)

        if b64_img:
            image_control = ft.Image(
                src_base64=b64_img, 
                width=img_w, height=img_h, 
                fit=ft.ImageFit.COVER, 
                border_radius=left_radius
            )
        else:
            image_control = ft.Container(
                width=img_w, height=img_h, 
                bgcolor=ft.Colors.GREY_800, 
                border_radius=left_radius,
                content=ft.Icon(ft.Icons.BROKEN_IMAGE, color=ft.Colors.GREY_500, size=40)
            )

        return ft.Container(
            content=ft.Row([
                image_control,
                ft.Container(
                    content=ft.Column([
                        ft.Text(title, size=16, weight=ft.FontWeight.BOLD, max_lines=3, overflow=ft.TextOverflow.ELLIPSIS),
                        ft.Row([
                            ft.Icon(ft.Icons.CIRCLE, size=10, color=status_color),
                            ft.Text(status_text, size=13, color=status_color, weight=ft.FontWeight.W_500),
                        ], spacing=5),
                        ft.Text(f"Last Read: {last}", size=12, color=ft.Colors.GREY_500),
                        ft.Container(expand=True),
                        ft.Row([
                            ft.Container(expand=True), 
                            ft.ElevatedButton(
                                text=btn_text,
                                icon=ft.Icons.LAUNCH,
                                icon_color=ft.Colors.WHITE,
                                color=ft.Colors.WHITE,
                                bgcolor=btn_bg,
                                style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8)),
                                height=40,
                                width=140,
                                on_click=lambda _: (open_brave_private(url), mark_as_read(None, item_id, latest) if has_update else None)
                            )
                        ])
                    ]),
                    padding=15,
                    height=img_h, 
                    expand=True
                )
            ], spacing=0),
            bgcolor=ft.Colors.GREY_900,
            border_radius=12,
            border=ft.border.all(1, border_color),
        )

    def refresh_ui(e=None):
        manga_grid_view.controls.clear()
        data = load_data()
        
        if not data:
            manga_grid_view.controls.append(ft.Text("No Data", color=ft.Colors.RED))
        else:
            # --- SORTING LOGIC ---
            # 1. Updates First (False < True, so 'not has_update' puts updates first)
            # 2. Then Alphabetical by Title
            data.sort(key=lambda x: (
                not (x.get("latest_available", 0) > x.get("last_read", 0)), 
                x.get("title", "")
            ))

            for item in data:
                if not item.get("id"): continue
                manga_grid_view.controls.append(create_card(item))
        
        manga_grid_view.update()

    header = ft.Container(
        content=ft.Row([
            ft.Row([
                 ft.Icon(ft.Icons.DASHBOARD, color=ft.Colors.BLUE_400, size=20), 
                 ft.Text("Manga Dashboard", size=16, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE), 
            ], spacing=10),
            ft.IconButton(ft.Icons.REFRESH, icon_size=20, on_click=refresh_ui, tooltip="Reload") 
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
        padding=10, 
        bgcolor=ft.Colors.GREY_900,
        border=ft.border.only(bottom=ft.border.BorderSide(1, ft.Colors.GREY_800)) 
    )

    page.add(ft.Column([header, manga_grid_view], expand=True, spacing=0))
    refresh_ui()

ft.app(target=main)
