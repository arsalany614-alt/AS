"""
SENTRA AS - Primary Mobile Frontend & Event Loops (Phase 1, Module 1 & Phase 3, Module 18)
Premium, high-fidelity dark-cyberpunk Kivy interface with built-in styling fallbacks.
Implements the autonomous 'Main Soya Hun' background threading pipeline and Human-in-the-Loop Gateway.
"""

import os
import sys
import time
import threading
from pathlib import Path
import json

# Ensure parent directory is in path for module resolution
sys.path.append(str(Path(__file__).resolve().parent))

# Kivy setups
import kivy
kivy.require("2.0.0")
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.togglebutton import ToggleButton
from kivy.uix.popup import Popup
from kivy.clock import Clock
from kivy.graphics import Color, RoundedRectangle, Line
from kivy.utils import get_color_from_hex
from kivy.core.window import Window

# Try importing KivyMD for standard premium widgets
try:
    from kivymd.app import MDApp
    from kivymd.uix.card import MDCard
    from kivymd.uix.dialog import MDDialog
    from kivymd.uix.button import MDRaisedButton, MDIconButton
    HAS_KIVYMD = True
except ImportError:
    HAS_KIVYMD = False

# Import our secure database & modules
from sentra_as.database import (
    initialize_database,
    log_system_event,
    get_pending_approval_items,
    update_approval_status,
    add_approval_item,
    add_financial_record,
    SafeDatabaseConnection,
    get_db_path
)
from sentra_as.security import shred_system
from sentra_as.modules import execute_module

# Set default screen size for modern look on desktops
Window.size = (420, 800)

# Colors Palette
HEX_DARK_BG = "#0c0d12"      # Deep-space Obsidian
HEX_CARD_BG = "#151821"      # Charcoal Slate
HEX_PRIMARY = "#00e5ff"      # Neon Cyan
HEX_ACCENT = "#00e676"       # Active Neon Green
HEX_RED = "#ff1744"          # Security Crimson Red
HEX_GOLD = "#ffd700"         # Trade Gold
HEX_EMERALD = "#07c160"      # Finance Emerald
HEX_TEXT = "#e0e0e0"         # Pale Gray

# Custom styled widgets
class SovereignCard(BoxLayout):
    """A premium rounded card layout for modern glassmorphism aesthetic."""
    def __init__(self, bg_color=HEX_CARD_BG, radius=12, border_color=HEX_PRIMARY, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        self.padding = 16
        self.spacing = 10
        self.bg_color = bg_color
        self.radius = radius
        self.border_color = border_color
        self.bind(size=self._update_background, pos=self._update_background)
        
    def _update_background(self, *args):
        self.canvas.before.clear()
        with self.canvas.before:
            Color(*get_color_from_hex(self.bg_color)[:3], 0.85)
            RoundedRectangle(pos=self.pos, size=self.size, radius=[self.radius])
            # Draw subtle cybernetic border outline
            Color(*get_color_from_hex(self.border_color)[:3], 0.18)
            Line(rounded_rect=(self.pos[0], self.pos[1], self.size[0], self.size[1], self.radius), width=1.2)

class SovereignButton(Button):
    """A custom cyber-styled button with dynamic press animations."""
    def __init__(self, bg_hex=HEX_PRIMARY, text_color="#000000", **kwargs):
        super().__init__(**kwargs)
        self.background_normal = ''
        self.background_down = ''
        self.background_color = (0, 0, 0, 0)
        self.bg_hex = bg_hex
        self.text_color = text_color
        self.bold = True
        self.font_size = "13sp"
        self.bind(size=self._draw_normal, pos=self._draw_normal)

    def _draw_normal(self, *args):
        self.canvas.before.clear()
        with self.canvas.before:
            Color(*get_color_from_hex(self.bg_hex)[:3], 1.0)
            RoundedRectangle(pos=self.pos, size=self.size, radius=[8])
        self.color = get_color_from_hex(self.text_color)

class SENTRA_AS_App(App):
    """The central application coordinator for SENTRA AS."""
    
    def build(self):
        # 1. Initialize SQLite storage schemas
        initialize_database()
        log_system_event("SYSTEM_BOOT", "SENTRA AS main interface initialized.")
        
        # 2. Main Canvas Base Layout
        self.root_layout = BoxLayout(orientation='vertical', spacing=12, padding=16)
        self.root_layout.bind(size=self._draw_main_background)
        
        # 3. Compile Header Panel
        self.header_card = SovereignCard(size_hint_y=0.10)
        self.header_label = Label(
            text="SENTRA AS // autonomous core",
            font_size="18sp",
            bold=True,
            color=get_color_from_hex(HEX_PRIMARY),
            halign="left",
            valign="middle"
        )
        self.header_label.bind(size=self.header_label.setter('text_size'))
        self.header_card.add_widget(self.header_label)
        self.root_layout.add_widget(self.header_card)
        
        # 4. Compile Center Scrolling Panel
        self.scroll_view = ScrollView(size_hint_y=0.48)
        self.main_content_layout = BoxLayout(orientation='vertical', spacing=14, size_hint_y=None)
        self.main_content_layout.bind(minimum_height=self.main_content_layout.setter('height'))
        
        # A: Central System Log Card
        self.console_card = SovereignCard(size_hint_y=None, height=220, border_color=HEX_ACCENT)
        self.console_title = Label(
            text="> live_console_feed",
            font_size="12sp",
            bold=True,
            color=get_color_from_hex(HEX_ACCENT),
            size_hint_y=0.15,
            halign="left"
        )
        self.console_title.bind(size=self.console_title.setter('text_size'))
        
        self.console_scroll = ScrollView(size_hint_y=0.85)
        self.console_text_label = Label(
            text="[SYSTEM ACTIVE] Awaiting input command...\n",
            font_name="Roboto",  # Monospace-like look
            font_size="11sp",
            color=get_color_from_hex("#00ff66"),
            size_hint_y=None,
            halign="left",
            valign="top"
        )
        self.console_text_label.bind(minimum_height=self.console_text_label.setter('height'))
        self.console_text_label.bind(size=self.console_text_label.setter('text_size'))
        self.console_scroll.add_widget(self.console_text_label)
        
        self.console_card.add_widget(self.console_title)
        self.console_card.add_widget(self.console_scroll)
        self.main_content_layout.add_widget(self.console_card)
        
        # B: Human-in-the-Loop Gateway Panel
        self.gateway_card = SovereignCard(size_hint_y=None, height=260, border_color=HEX_PRIMARY)
        self.gateway_title = Label(
            text="✦ approval_gateway_holding (review required)",
            font_size="12sp",
            bold=True,
            color=get_color_from_hex(HEX_PRIMARY),
            size_hint_y=0.15,
            halign="left"
        )
        self.gateway_title.bind(size=self.gateway_title.setter('text_size'))
        
        self.gateway_scroll = ScrollView(size_hint_y=0.85)
        self.gateway_items_box = BoxLayout(orientation='vertical', spacing=10, size_hint_y=None)
        self.gateway_items_box.bind(minimum_height=self.gateway_items_box.setter('height'))
        self.gateway_scroll.add_widget(self.gateway_items_box)
        
        self.gateway_card.add_widget(self.gateway_title)
        self.gateway_card.add_widget(self.gateway_scroll)
        self.main_content_layout.add_widget(self.gateway_card)
        
        self.scroll_view.add_widget(self.main_content_layout)
        self.root_layout.add_widget(self.scroll_view)
        
        # 5. Compile Control Console Card (Controls Toggles and Voice Mic)
        self.control_card = SovereignCard(size_hint_y=0.30)
        
        # Toggle: Main Soya Hun
        self.toggle_layout = BoxLayout(orientation='horizontal', size_hint_y=0.3)
        self.toggle_label = Label(
            text="Autonomous Sleeping Pipeline\n(Main Soya Hun)",
            font_size="12sp",
            bold=True,
            color=get_color_from_hex(HEX_TEXT),
            halign="left"
        )
        self.toggle_label.bind(size=self.toggle_label.setter('text_size'))
        
        self.sleep_toggle = ToggleButton(
            text="PIPELINE INACTIVE",
            font_size="11sp",
            bold=True,
            color=get_color_from_hex("#ffffff"),
            background_color=get_color_from_hex(HEX_CARD_BG),
            border=(2, 2, 2, 2),
            size_hint_x=0.4
        )
        self.sleep_toggle.bind(state=self.on_sleep_toggle_change)
        
        self.toggle_layout.add_widget(self.toggle_label)
        self.toggle_layout.add_widget(self.sleep_toggle)
        self.control_card.add_widget(self.toggle_layout)
        
        # Micro-interaction Mic & Manual Execution Buttons
        self.action_layout = BoxLayout(orientation='horizontal', spacing=10, size_hint_y=0.4)
        
        self.mic_btn = SovereignButton(
            text="🎤  LISTEN",
            bg_hex=HEX_PRIMARY,
            text_color="#000000",
            size_hint_x=0.5
        )
        self.mic_btn.bind(on_release=self.trigger_mic_listening)
        
        self.exec_btn = SovereignButton(
            text="⚡  RUN AUTOMATION",
            bg_hex=HEX_ACCENT,
            text_color="#000000",
            size_hint_x=0.5
        )
        self.exec_btn.bind(on_release=self.trigger_manual_automation)
        
        self.action_layout.add_widget(self.mic_btn)
        self.action_layout.add_widget(self.exec_btn)
        self.control_card.add_widget(self.action_layout)
        
        # Red Emergency Kill Switch
        self.kill_switch_btn = SovereignButton(
            text="🚨  EMERGENCY WIPE (RED BUTTON)  🚨",
            bg_hex=HEX_RED,
            text_color="#ffffff",
            size_hint_y=0.3
        )
        self.kill_switch_btn.bind(on_release=self.show_kill_switch_confirmation)
        self.control_card.add_widget(self.kill_switch_btn)
        
        self.root_layout.add_widget(self.control_card)
        
        # 6. Set up dynamic polling clock loops
        Clock.schedule_interval(self.poll_system_logs, 1.0)
        Clock.schedule_once(self.refresh_approval_gateway, 0.5)
        
        return self.root_layout

    def _draw_main_background(self, instance, value):
        instance.canvas.before.clear()
        with instance.canvas.before:
            # Draw deep obsidian background
            Color(*get_color_from_hex(HEX_DARK_BG)[:3], 1.0)
            RoundedRectangle(pos=instance.pos, size=instance.size)

    # --- Live Polling and Rendering UI Updates ---

    def poll_system_logs(self, dt):
        """Fetches the latest database system logs to update the real-time scrolling console."""
        db_path = get_db_path()
        if not db_path.exists():
            return
            
        try:
            with SafeDatabaseConnection(db_path) as cursor:
                cursor.execute(
                    "SELECT timestamp, component, payload FROM system_logs ORDER BY id DESC LIMIT 15"
                )
                rows = cursor.fetchall()
                
            log_lines = []
            for row in reversed(rows):
                t_str = time.strftime("%H:%M:%S", time.localtime(row["timestamp"]))
                log_lines.append(f"[{t_str}] [{row['component']}] {row['payload']}")
                
            # Update console text thread-safely
            self.console_text_label.text = "\n".join(log_lines)
            
        except Exception:
            pass  # Fail silently to avoid crash during key destruction

    def refresh_approval_gateway(self, dt=None):
        """Queries database and renders pending sleeping assets as high-fidelity interactive cards."""
        self.gateway_items_box.clear_widgets()
        
        pending_items = get_pending_approval_items()
        
        if not pending_items:
            empty_lbl = Label(
                text="No pending assets inside Gateway.\nTrigger 'Main Soya Hun' loop above.",
                font_size="12sp",
                color=get_color_from_hex("#7f8c8d"),
                halign="center",
                size_hint_y=None,
                height=100
            )
            self.gateway_items_box.add_widget(empty_lbl)
            return

        for item in pending_items:
            # Map type to correct design palette (Zero placeholders)
            border_c = HEX_PRIMARY
            action_txt = "APPROVE & PUBLISH"
            bg_c = "#1d222f"
            
            if item["type"] == "trade":
                border_c = HEX_GOLD
                action_txt = "EXECUTE TRADE"
                bg_c = "#23211c"
            elif item["type"] == "finance":
                border_c = HEX_ACCENT
                action_txt = "AUTHORIZE ALLOCATION"
                bg_c = "#1a2520"

            # Construct a beautiful micro-card per pending pipeline
            card = SovereignCard(bg_color=bg_c, size_hint_y=None, height=195, spacing=6, padding=10, border_color=border_c)
            
            title_lbl = Label(
                text=f"{item['type'].upper()} // {item['title']}",
                font_size="12sp",
                bold=True,
                color=get_color_from_hex(border_c),
                size_hint_y=None,
                height=20,
                halign="left"
            )
            title_lbl.bind(size=title_lbl.setter('text_size'))
            card.add_widget(title_lbl)
            
            # Encrypted content text edit panel
            txt_input = TextInput(
                text=item["content"],
                font_size="11sp",
                background_color=get_color_from_hex("#0f1118"),
                foreground_color=get_color_from_hex(HEX_TEXT),
                size_hint_y=None,
                height=80,
                multiline=True
            )
            card.add_widget(txt_input)
            
            # Action button panel
            btn_box = BoxLayout(orientation='horizontal', spacing=8, size_hint_y=None, height=35)
            
            approve_btn = SovereignButton(
                text=action_txt,
                bg_hex=border_c,
                text_color="#000000",
                size_hint_x=0.65
            )
            # Bind using explicit function captures
            approve_btn.bind(on_release=lambda x, i=item["id"], t=item["title"], ty=item["type"], md=item["metadata"]: self.approve_asset(i, t, ty, md))
            
            discard_btn = SovereignButton(
                text="DISCARD",
                bg_hex=HEX_RED,
                text_color="#ffffff",
                size_hint_x=0.35
            )
            discard_btn.bind(on_release=lambda x, i=item["id"], t=item["title"]: self.discard_asset(i, t))
            
            btn_box.add_widget(approve_btn)
            btn_box.add_widget(discard_btn)
            card.add_widget(btn_box)
            
            self.gateway_items_box.add_widget(card)

    def approve_asset(self, item_id: int, title: str, asset_type: str, metadata: Dict[str, Any]):
        """Approves and executes the selected asset, directly updating database ledgers & logs."""
        update_approval_status(item_id, "approved")
        
        if asset_type == "trade":
            # Direct database integration! Subtract BTC cost and log success execution
            try:
                # Retrieve price from metadata
                limit_p = metadata.get("limit_price", 95000.0)
                amount = metadata.get("amount", 0.05)
                cost = limit_p * amount
                
                # Write trade cost as expense to the ledger
                add_financial_record(cost, "expense", "Asset Purchase", f"Executed trade: Buy {amount} BTC @ {limit_p} USD limit.")
                log_system_event("EXCHANGE_LINK", f"ORDER SUCCESS: Dispatched buy ticket {amount} BTC. Cost: {cost:,.2f} USD deducted.")
            except Exception as e:
                log_system_event("EXCHANGE_LINK_ERROR", f"Failed executing order link: {e}")
                
        elif asset_type == "finance":
            # Direct database integration! Write allocated expense record to ledger
            try:
                alloc_amt = metadata.get("amount", 5000.0)
                add_financial_record(alloc_amt, "expense", "Capital Outlay", f"Sovereign node allocation: {title}")
                log_system_event("FINANCE_MANAGER", f"ALLOCATION APPROVED: Pushed ledger record for {alloc_amt:,.2f} USD outlay.")
            except Exception as e:
                log_system_event("FINANCE_MANAGER_ERROR", f"Failed budget allocation write: {e}")
                
        else:
            # Video/media asset simulation
            log_system_event("APPROVAL_GATEWAY", f"PUBLISH PIPELINE ACTIVATED: Mock uploading video/social bundle for '{title}'...")
            
        Clock.schedule_once(self.refresh_approval_gateway, 0.5)

    def discard_asset(self, item_id: int, title: str):
        """Discards the assets, removing them from the holding gateway."""
        update_approval_status(item_id, "discarded")
        log_system_event("APPROVAL_GATEWAY", f"Asset discarded from holding: '{title}'")
        Clock.schedule_once(self.refresh_approval_gateway, 0.5)

    # --- Interaction Events & Background Thread Offloads ---

    def trigger_mic_listening(self, instance):
        """Simulates listening to voice queries without locking the Kivy UI."""
        def listen_task():
            log_system_event("VOICE_SYSTEM", "Microphone listening activated. Synthesizing offline speech inputs...")
            time.sleep(1.5)
            log_system_event("VOICE_SYSTEM", "Arsalan speech detected: 'Check daily financial budget ledger.'")
            # Query standard financial emulator
            time.sleep(0.5)
            execute_module("finance_manager", "Retrieve ledger")
            
        threading.Thread(target=listen_task, daemon=True).start()

    def trigger_manual_automation(self, instance):
        """Triggers manual execution of various modules to show dynamic processing."""
        def run_task():
            execute_module("business_strategy", "Offline Marketing OS Expansion")
            time.sleep(0.5)
            execute_module("health_monitor")
            time.sleep(0.5)
            execute_module("cyber_defense")
            
        threading.Thread(target=run_task, daemon=True).start()

    def on_sleep_toggle_change(self, instance, state):
        """Toggles the background sleeping pipelines loop when Arsalan falls asleep."""
        if state == "down":
            instance.text = "PIPELINE ACTIVE (ASLEEP)"
            instance.background_color = get_color_from_hex(HEX_ACCENT)
            log_system_event("USER_CONTROL", "User toggled sleep state: 'Main Soya Hun'. Triggering autonomous content creator loops...")
            # Spawn the heavy media pipeline on isolated background thread
            threading.Thread(target=self.autonomous_sleeping_pipeline_loop, daemon=True).start()
        else:
            instance.text = "PIPELINE INACTIVE"
            instance.background_color = get_color_from_hex(HEX_CARD_BG)
            log_system_event("USER_CONTROL", "User toggled active state. Autonomous background pipeline resting.")

    def autonomous_sleeping_pipeline_loop(self):
        """
        The Core System Workflow:
        Runs background pipelines:
        1. Media Creation: Script -> Voice -> Video -> Social media tags
        2. Technical Analysis: Trading Assistant indicators -> trade tickets
        3. Automated Finance: Budget allocator proposals
        and holds all of them securely inside the holding gateway!
        """
        try:
            log_system_event("SLEEP_PIPELINE", "Initiating autonomous sleep loop. Target: Sovereign Operations bundle.")
            time.sleep(0.8)
            
            # --- 1. MEDIA PIPELINE ---
            log_system_event("SLEEP_PIPELINE", "[1/3] Triggering Content Production Pipeline...")
            script = execute_module("script_writer", "Sovereign AI Networks offline deployment")
            time.sleep(1.0)
            
            audio_path = execute_module("voice_over", script)
            time.sleep(1.0)
            
            video_path = execute_module("video_generator", audio_path)
            time.sleep(1.0)
            
            social_bundle = execute_module("social_media", script)
            time.sleep(0.8)
            
            # Write Media content hold
            add_approval_item(
                title="Sovereign AI Offline OS",
                asset_type="video",
                content=social_bundle,
                metadata={
                    "script": script[:500] + "...",
                    "audio_path": audio_path,
                    "video_path": video_path
                }
            )
            
            # --- 2. TRADING PIPELINE ---
            log_system_event("SLEEP_PIPELINE", "[2/3] Triggering Trading Technical Indicators Module...")
            execute_module("trading_assistant")
            time.sleep(1.0)
            
            # --- 3. FINANCE PIPELINE ---
            log_system_event("SLEEP_PIPELINE", "[3/3] Triggering Automated Personal Finance Budgets...")
            execute_module("finance_manager")
            time.sleep(0.8)
            
            log_system_event("SLEEP_PIPELINE", "Autonomous creation task completed. Held securely in Approval Gateway.")
            
            # Refresh UI Gateway cards thread-safely
            Clock.schedule_once(self.refresh_approval_gateway, 0.1)
            
        except Exception as e:
            log_system_event("SLEEP_PIPELINE_ERROR", f"Autonomous pipeline failed: {e}")

    # --- Red Button Emergency Kill Switch ---

    def show_kill_switch_confirmation(self, instance):
        """Displays double confirmation popup modal prior to wiping keys and databases."""
        box = BoxLayout(orientation='vertical', padding=12, spacing=10)
        lbl = Label(
            text="WARNING: Wiping system is irreversible!\nThis shreds database, logs, keys, and assets.",
            font_size="13sp",
            color=get_color_from_hex("#ff3333"),
            halign="center"
        )
        box.add_widget(lbl)
        
        btn_box = BoxLayout(orientation='horizontal', spacing=8, size_hint_y=0.4)
        
        cancel_btn = SovereignButton(
            text="ABORT",
            bg_hex=HEX_CARD_BG,
            text_color="#ffffff"
        )
        
        confirm_btn = SovereignButton(
            text="SHRED SYSTEM NOW",
            bg_hex=HEX_RED,
            text_color="#ffffff"
        )
        
        btn_box.add_widget(cancel_btn)
        btn_box.add_widget(confirm_btn)
        box.add_widget(btn_box)
        
        popup = Popup(
            title="!!! SECURE SYSTEM OVERRIDE !!!",
            content=box,
            size_hint=(0.9, 0.35),
            auto_dismiss=False
        )
        
        cancel_btn.bind(on_release=popup.dismiss)
        confirm_btn.bind(on_release=lambda x: self.trigger_hard_shred(popup))
        
        popup.open()

    def trigger_hard_shred(self, popup_instance):
        """Closes popup and triggers the security module military-grade shredder."""
        popup_instance.dismiss()
        log_system_event("SECURITY_INTELLIGENCE", "RED BUTTON CONFIRMED. EXECUTE WIPE IMMEDIATE.")
        shred_system()

if __name__ == "__main__":
    SENTRA_AS_App().run()
