import sys
import json
import random
import re
import threading
import logging
from datetime import datetime

# Setup logging
logging.basicConfig(
    filename='chat_overlay_debug.log',
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QLabel, QLineEdit, 
                             QSlider, QCheckBox, QScrollArea, QFrame, QSizeGrip, 
                             QMessageBox, QComboBox, QColorDialog, QGraphicsOpacityEffect, QMenu,
                             QSystemTrayIcon, QAction, QTextEdit, QRadioButton, QButtonGroup, QInputDialog, QDialog)
from PyQt5.QtCore import (Qt, QTimer, QPoint, QSize, QPropertyAnimation, 
                          QEasingCurve, pyqtSignal, QRect, QThread, QWaitCondition, QMutex)
from PyQt5.QtGui import QFont, QColor, QPalette, QIcon, QCursor, QPixmap, QPainter

try:
    import requests
    from bs4 import BeautifulSoup
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

except ImportError:
    REQUESTS_AVAILABLE = False

try:
    from gtts import gTTS
    import pygame
    import os
    import time
    from mtranslate import translate as google_translate
    TTS_AVAILABLE = True


except ImportError:
    TTS_AVAILABLE = False



    print("Warning: requests or beautifulsoup4 not installed. Channel auto-detect disabled.")
    print("Install with: pip install requests beautifulsoup4")

try:
    import pytchat
    PYTCHAT_AVAILABLE = True
except ImportError:
    PYTCHAT_AVAILABLE = False
    print("Warning: pytchat not installed. Only demo mode available.")
    print("Install with: pip install pytchat")

class TTSThread(QThread):
    """Thread xử lý Text-to-Speech dùng Google Translate (Online)"""
    def __init__(self):
        super().__init__()
        self.queue = []
        self.running = True
        self.cond = QWaitCondition()
        self.mutex = QMutex()
        self.volume = 1.0
        self.enabled = False
        self.translate_enabled = False
        self.translate_to_vi = True # True: En->Vi, False: Vi->En
        self.slang_dict = {}
        self.load_slang()

    def load_slang(self):
        try:
            with open('slang.json', 'r', encoding='utf-8') as f:
                self.slang_dict = json.load(f)
        except Exception as e:
            print(f"Error loading slang.json: {e}")
            # Fallback empty or hardcoded if needed
            self.slang_dict = {}

    def expand_slang(self, text):
        """Mở rộng các từ lóng internet và gaming common"""
        processed_text = text.lower()
        if not self.slang_dict:
             return processed_text
             
        for pattern, replacement in self.slang_dict.items():
            # Dùng regex sub để thay thế chính xác từ (word boundary)
            try:
                processed_text = re.sub(pattern, replacement, processed_text)
            except:
                pass
        return processed_text

    def run(self):
        if not TTS_AVAILABLE:
            print("gTTS or pygame not installed")
            return
            
        try:
            logging.info("TTS Thread Started")
        except Exception as e:
            logging.error(f"TTS Thread Error: {e}")
            return





        while self.running:
            self.mutex.lock()
            if not self.queue:
                self.cond.wait(self.mutex)
            
            if not self.queue:
                self.mutex.unlock()
                continue
                
            text = self.queue.pop(0)
            self.mutex.unlock()
            
            if self.enabled and text:
                try:
                    text_to_speak = text
                    
                    # Xử lý dịch thuật nếu được bật
                    if self.translate_enabled:
                        try:
                            # 1. Expand Slang trước (quan trọng!)
                            preprocessed_text = self.expand_slang(text)
                            if preprocessed_text != text.lower():
                                logging.debug(f"Slang expanded: '{text}' -> '{preprocessed_text}'")

                            # 2. Dịch bằng mtranslate
                            dest_lang = 'vi' if self.translate_to_vi else 'en'
                            translated_text = google_translate(preprocessed_text, dest_lang, 'auto')
                            logging.debug(f"Translated: '{text}' -> '{translated_text}'")
                            print(f"DEBUG: Translated '{preprocessed_text}' -> '{translated_text}'")
                            
                            if translated_text:
                                text_to_speak = translated_text
                                
                        except Exception as te:
                            logging.error(f"Translation Error: {te}")
                            print(f"Translation Error: {te}")
                            # Fallback: đọc nguyên bản

                    # Tạo tên file unique theo timestamp để tránh lỗi file đang busy
                    filename = f"tts_{int(time.time()*1000)}.mp3"

                    filename = os.path.abspath(filename)
                    
                    print(f"Generating TTS for: {text_to_speak}")
                    lang_code = 'vi' if (self.translate_enabled and self.translate_to_vi) else 'en'
                    # Nếu disable translate thì có thể cần detect lang, nhưng tạm thời mặc định
                    # Logic cũ: translate enabled -> vi. 
                    # Logic mới: translate enabled -> vi or en.
                    # Nếu không translate thì đọc nguyên bản (thường là tiếng Việt nếu stream Việt?)
                    # Để đơn giản: nếu translate=off, mặc định đọc tiếng Việt (gTTS support auto detect kém)
                    # Hoặc ta cứ để 'vi' nếu ko translate, user nói tiếng anh thì nó đọc hơi dở.
                    
                    tts = gTTS(text=text_to_speak, lang=lang_code, slow=False)
                    tts.save(filename)
                    
                    # Play sound
                    pygame.mixer.music.load(filename)
                    # Set volume (0.0 to 1.0)
                    pygame.mixer.music.set_volume(self.volume)
                    pygame.mixer.music.play()
                    
                    # Wait for playback to finish
                    while pygame.mixer.music.get_busy():
                        pygame.time.Clock().tick(10)
                        if not self.running:
                            pygame.mixer.music.stop()
                            break
                    
                    # Unload to delete
                    pygame.mixer.music.unload()
                    
                    # Delete temp file
                    try:
                        os.remove(filename)
                    except:
                        pass
                        
                except Exception as e:
                    print(f"TTS Error: {e}")
                    import traceback
                    traceback.print_exc()
    
    def add_text(self, text):
        if not self.enabled:
            return
        self.mutex.lock()
        self.queue.append(text)
        self.cond.wakeOne()
        self.mutex.unlock()

    def stop(self):
        self.running = False
        self.cond.wakeOne()
        self.wait()



class ChatMessage(QWidget):
    """Widget cho một tin nhắn chat với animation"""
    def __init__(self, author, message, timestamp, config, is_member=False, is_superchat=False, sc_amount=""):

        super().__init__()
        
        # Main layout - horizontal để text chạy liền mạch
        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(12, 8, 12, 8)
        main_layout.setSpacing(6)
        
        # Determine styles based on type
        msg_bg = config.get('msg_bg_color', 'rgba(255, 255, 255, 10)')
        border_color = config.get('accent_color', '#6366f1')
        author_color = config.get('author_color', '#6366f1')
        
        if is_superchat:
            msg_bg = 'rgba(218, 165, 32, 40)' # Golden background
            border_color = '#FFD700' # Gold border
            author_color = '#FFD700'
        elif is_member:
            author_color = '#34D399' # Emerald Green for members
            border_color = '#34D399'

        # Tạo text liền mạch
        full_text = ""
        if config.get('show_timestamp', True):
            full_text += f"<span style='color: {config.get('time_color', '#888888')};'>{timestamp}</span> "
        
        # Prefix for Member/SC
        prefix = ""
        if is_superchat:
            prefix = f"<span style='color: #FFD700; font-weight: bold;'>[SC {sc_amount}] </span>"
        elif is_member:
            prefix = "<span style='color: #34D399; font-weight: bold;'>[Member] </span>"
            
        if config.get('show_author', True):
            full_text += f"{prefix}<span style='color: {author_color}; font-weight: 600;'>{author}:</span> "
        else:
             full_text += f"{prefix}"

        full_text += f"<span style='color: {config.get('message_color', '#ffffff')};'>{message}</span>"
        
        # Label với rich text
        self.message_label = QLabel(full_text)
        self.message_label.setWordWrap(True)
        self.message_label.setTextFormat(Qt.RichText)
        self.message_label.setStyleSheet(f"""
            QLabel {{
                font-size: {config.get('font_size', 14)}px;
                padding: 6px 10px;
                background-color: {msg_bg};
                border-radius: {config.get('border_radius', 6)}px;
                border-left: 3px solid {border_color};
            }}
        """)
        
        main_layout.addWidget(self.message_label)
        self.setLayout(main_layout)
        
        # Animation - slide in from left
        self.setMaximumHeight(0)
        self.animation = QPropertyAnimation(self, b"maximumHeight")
        self.animation.setDuration(config.get('animation_speed', 300))
        self.animation.setStartValue(0)
        self.animation.setEndValue(100)
        self.animation.setEasingCurve(QEasingCurve.OutCubic)
        
        
        # Opacity animation
        self.opacity_effect = QGraphicsOpacityEffect(self)
        self.opacity_effect.setOpacity(1.0)
        self.setGraphicsEffect(self.opacity_effect)
        
        # Timeout timer
        self.timeout_timer = None
        timeout = config.get('message_timeout', 0)
        if timeout > 0:
            self.timeout_timer = QTimer()
            self.timeout_timer.setSingleShot(True)
            self.timeout_timer.timeout.connect(self.start_fade_out)
            self.timeout_timer.start(timeout * 1000)
            
    def start_fade_out(self):
        """Start fade out animation then close"""
        self.anim_opacity = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.anim_opacity.setDuration(1000) # 1 second fade out
        self.anim_opacity.setStartValue(1.0)
        self.anim_opacity.setEndValue(0.0)
        self.anim_opacity.finished.connect(self.deleteLater)
        self.anim_opacity.start()
        
    def show_animated(self):
        """Show with animation"""
        self.animation.start()
        
    def enterEvent(self, event):
        """Pause timeout on hover"""
        if self.timeout_timer and self.timeout_timer.isActive():
            self.timeout_timer.stop()
        super().enterEvent(event)
        
    def leaveEvent(self, event):
        """Resume timeout on leave"""
        if self.timeout_timer:
            self.timeout_timer.start() # Restart full duration
        super().leaveEvent(event)


class SettingsPanel(QWidget):
    """Panel cài đặt nâng cao"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.Popup)
        self.setStyleSheet("""
            QWidget {
                background-color: rgba(10, 10, 15, 250);
                border-radius: 12px;
                border: 1px solid rgba(99, 102, 241, 50);
            }
            QLabel {
                color: white;
                font-size: 12px;
                font-weight: 500;
            }
            QLineEdit {
                background-color: rgba(255, 255, 255, 15);
                border: 1px solid rgba(255, 255, 255, 30);
                border-radius: 6px;
                padding: 8px;
                color: white;
                font-size: 12px;
            }
            QLineEdit:focus {
                border: 1px solid #6366f1;
                background-color: rgba(255, 255, 255, 20);
            }
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #6366f1, stop:1 #4f46e5);
                border: none;
                border-radius: 6px;
                padding: 8px;
                color: white;
                font-size: 12px;
                font-weight: 600;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #4f46e5, stop:1 #4338ca);
            }
            QCheckBox {
                color: white;
                font-size: 12px;
                spacing: 6px;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                border-radius: 3px;
                border: 2px solid rgba(255, 255, 255, 50);
                background-color: rgba(255, 255, 255, 20);
            }
            QCheckBox::indicator:checked {
                background-color: #6366f1;
                border-color: #6366f1;
            }
            QSlider::groove:horizontal {
                height: 4px;
                background: rgba(255, 255, 255, 30);
                border-radius: 2px;
            }
            QSlider::handle:horizontal {
                background: #6366f1;
                width: 14px;
                height: 14px;
                margin: -5px 0;
                border-radius: 7px;
            }
            QComboBox {
                background-color: rgba(255, 255, 255, 15);
                border: 1px solid rgba(255, 255, 255, 30);
                border-radius: 6px;
                padding: 6px;
                color: white;
                font-size: 12px;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox QAbstractItemView {
                background-color: rgba(20, 20, 30, 250);
                color: white;
                selection-background-color: #6366f1;
            }
        """)
        
        self.setFixedWidth(360)
        self.setMaximumHeight(700)
        
        # Scroll area for settings
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        
        content_widget = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)
        
        # --- TAB LAYOUT (OPTIONAL) - BUT KEEP SIMPLE WITH SECTIONS ---

        
        # Title
        title = QLabel("⚙️ Cài đặt nâng cao")
        title.setStyleSheet("font-size: 16px; font-weight: 700; margin-bottom: 8px; color: #6366f1;")
        layout.addWidget(title)
        
        # === CONNECTION SECTION ===
        section1 = QLabel("📡 Kết nối")
        section1.setStyleSheet("font-size: 13px; font-weight: 600; margin-top: 8px; color: #8b5cf6;")
        layout.addWidget(section1)
        
        layout.addWidget(QLabel("URL Channel hoặc Video YouTube:"))
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("https://www.youtube.com/@channel hoặc /watch?v=...")
        layout.addWidget(self.url_input)
        
        # Auto-detect live button
        self.detect_live_btn = QPushButton("🔍 Tự động tìm Live Stream")
        self.detect_live_btn.setStyleSheet("""
            QPushButton {
                padding: 10px;
                font-size: 12px;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #8b5cf6, stop:1 #6366f1);
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #7c3aed, stop:1 #4f46e5);
            }
        """)
        layout.addWidget(self.detect_live_btn)

        
        # === APPEARANCE SECTION ===
        section2 = QLabel("🎨 Giao diện")
        section2.setStyleSheet("font-size: 13px; font-weight: 600; margin-top: 12px; color: #8b5cf6;")
        layout.addWidget(section2)
        
        # Background opacity
        opacity_layout = QHBoxLayout()
        opacity_layout.addWidget(QLabel("Độ mờ nền:"))
        self.opacity_value = QLabel("0%")
        opacity_layout.addWidget(self.opacity_value)
        layout.addLayout(opacity_layout)
        
        self.opacity_slider = QSlider(Qt.Horizontal)
        self.opacity_slider.setMinimum(0)
        self.opacity_slider.setMaximum(100)
        self.opacity_slider.setValue(0)
        self.opacity_slider.valueChanged.connect(self.update_opacity_label)
        layout.addWidget(self.opacity_slider)
        
        # Font size
        font_layout = QHBoxLayout()
        font_layout.addWidget(QLabel("Kích thước chữ:"))
        self.font_value = QLabel("14px")
        font_layout.addWidget(self.font_value)
        layout.addLayout(font_layout)
        
        self.font_slider = QSlider(Qt.Horizontal)
        self.font_slider.setMinimum(10)
        self.font_slider.setMaximum(28)
        self.font_slider.setValue(14)
        self.font_slider.valueChanged.connect(self.update_font_label)
        layout.addWidget(self.font_slider)
        
        # Border radius
        radius_layout = QHBoxLayout()
        radius_layout.addWidget(QLabel("Bo góc tin nhắn:"))
        self.radius_value = QLabel("6px")
        radius_layout.addWidget(self.radius_value)
        layout.addLayout(radius_layout)
        
        self.radius_slider = QSlider(Qt.Horizontal)
        self.radius_slider.setMinimum(0)
        self.radius_slider.setMaximum(20)
        self.radius_slider.setValue(6)
        self.radius_slider.valueChanged.connect(self.update_radius_label)
        layout.addWidget(self.radius_slider)
        
        # Message Timeout
        timeout_layout = QHBoxLayout()
        timeout_layout.addWidget(QLabel("Tin nhắn biến mất sau:"))
        self.timeout_value = QLabel("Không")
        timeout_layout.addWidget(self.timeout_value)
        layout.addLayout(timeout_layout)
        
        self.timeout_slider = QSlider(Qt.Horizontal)
        self.timeout_slider.setMinimum(0)
        self.timeout_slider.setMaximum(60)
        self.timeout_slider.setValue(0)
        self.timeout_slider.valueChanged.connect(self.update_timeout_label)
        layout.addWidget(self.timeout_slider)
        
        # Animation speed
        anim_layout = QHBoxLayout()
        anim_layout.addWidget(QLabel("Tốc độ animation:"))
        self.anim_value = QLabel("300ms")
        anim_layout.addWidget(self.anim_value)
        layout.addLayout(anim_layout)
        
        self.anim_slider = QSlider(Qt.Horizontal)
        self.anim_slider.setMinimum(100)
        self.anim_slider.setMaximum(1000)
        self.anim_slider.setValue(300)
        self.anim_slider.valueChanged.connect(self.update_anim_label)
        layout.addWidget(self.anim_slider)
        
        # === COLOR SECTION ===
        section3 = QLabel("🌈 Màu sắc")
        section3.setStyleSheet("font-size: 13px; font-weight: 600; margin-top: 12px; color: #8b5cf6;")
        layout.addWidget(section3)
        
        # Color buttons
        self.author_color_btn = self.create_color_button("Màu tên:", "#6366f1")
        layout.addLayout(self.author_color_btn[0])
        
        self.time_color_btn = self.create_color_button("Màu thời gian:", "#888888")
        layout.addLayout(self.time_color_btn[0])
        
        self.message_color_btn = self.create_color_button("Màu tin nhắn:", "#ffffff")
        layout.addLayout(self.message_color_btn[0])
        
        self.accent_color_btn = self.create_color_button("Màu viền:", "#6366f1")
        layout.addLayout(self.accent_color_btn[0])
        
        # === DISPLAY OPTIONS ===
        section4 = QLabel("👁️ Hiển thị")
        section4.setStyleSheet("font-size: 13px; font-weight: 600; margin-top: 12px; color: #8b5cf6;")
        layout.addWidget(section4)
        
        self.show_author_cb = QCheckBox("Hiển thị tên người gửi")
        self.show_author_cb.setChecked(True)
        layout.addWidget(self.show_author_cb)
        
        self.show_timestamp_cb = QCheckBox("Hiển thị thời gian")
        self.show_timestamp_cb.setChecked(True)
        layout.addWidget(self.show_timestamp_cb)
        
        self.autohide_header_cb = QCheckBox("Tự động ẩn header (Hover để hiện)")
        self.autohide_header_cb.setChecked(False)
        layout.addWidget(self.autohide_header_cb)

        # === TTS SECTION ===
        section5 = QLabel("🔊 Đọc tin nhắn (Chị Google)")
        section5.setStyleSheet("font-size: 13px; font-weight: 600; margin-top: 12px; color: #8b5cf6;")
        layout.addWidget(section5)
        
        self.tts_cb = QCheckBox("Bật đọc tin nhắn")
        self.tts_cb.setChecked(False)
        layout.addWidget(self.tts_cb)
        
        self.translate_cb = QCheckBox("🌐 Chế độ dịch (Translate)")
        self.translate_cb.setStyleSheet("color: #8b5cf6; margin-left: 20px;")
        self.translate_cb.setChecked(False)
        layout.addWidget(self.translate_cb)
        
        # Translate Options
        trans_layout = QHBoxLayout()
        trans_layout.setContentsMargins(20, 0, 0, 0)
        
        self.trans_group = QButtonGroup(self)
        self.rb_en_vi = QRadioButton("Anh -> Việt")
        self.rb_en_vi.setChecked(True)
        self.rb_en_vi.setStyleSheet("color: white;")
        self.rb_vi_en = QRadioButton("Việt -> Anh")
        self.rb_vi_en.setStyleSheet("color: white;")
        
        self.trans_group.addButton(self.rb_en_vi)
        self.trans_group.addButton(self.rb_vi_en)
        
        trans_layout.addWidget(self.rb_en_vi)
        trans_layout.addWidget(self.rb_vi_en)
        layout.addLayout(trans_layout)
        
        # Toggle translation options visibility
        self.translate_cb.toggled.connect(lambda c: self.rb_en_vi.setVisible(c) or self.rb_vi_en.setVisible(c))
        self.rb_en_vi.setVisible(False)
        self.rb_vi_en.setVisible(False)

        
        vol_layout = QHBoxLayout()

        vol_layout.addWidget(QLabel("Âm lượng:"))
        self.tts_vol_slider = QSlider(Qt.Horizontal)
        self.tts_vol_slider.setRange(0, 100)
        self.tts_vol_slider.setValue(100)
        self.tts_vol_value = QLabel("100%")
        self.tts_vol_slider.valueChanged.connect(
            lambda v: self.tts_vol_value.setText(f"{v}%")
        )
        vol_layout.addWidget(self.tts_vol_slider)
        vol_layout.addWidget(self.tts_vol_value)
        vol_layout.addWidget(self.tts_vol_value)
        layout.addLayout(vol_layout)
        
        # === FILTER SECTION ===
        section6 = QLabel("🛡️ Bộ lọc từ cấm (Blacklist)")
        section6.setStyleSheet("font-size: 13px; font-weight: 600; margin-top: 12px; color: #8b5cf6;")
        layout.addWidget(section6)
        
        layout.addWidget(QLabel("Nhập từ cấm (mỗi dòng 1 từ):"))
        self.blacklist_edit = QTextEdit()
        self.blacklist_edit.setPlaceholderText("bot\nspam\n... (lưu ý: sẽ ẩn tin nhắn chứa các từ này)")
        self.blacklist_edit.setFixedHeight(80)
        self.blacklist_edit.setStyleSheet("""
            QTextEdit {
                background-color: rgba(255, 255, 255, 15);
                border: 1px solid rgba(255, 255, 255, 30);
                border-radius: 6px;
                padding: 8px;
                color: white;
                font-size: 12px;
            }
        """)
        layout.addWidget(self.blacklist_edit)

        
        # Test voice button
        self.test_voice_btn = QPushButton("🔊 Test Giọng Đọc")
        self.test_voice_btn.setStyleSheet("""
            QPushButton {
                 background-color: rgba(99, 102, 241, 50);
                 border: 1px solid rgba(99, 102, 241, 100);
                 color: white;
                 border-radius: 4px;
                 padding: 4px;
            }
            QPushButton:hover { background-color: rgba(99, 102, 241, 80); }
        """)
        layout.addWidget(self.test_voice_btn)
        
        # Apply button
        self.apply_btn = QPushButton("✓ Áp dụng")
        self.apply_btn.setStyleSheet("""
            QPushButton {
                padding: 12px;
                font-size: 14px;
                margin-top: 12px;
            }
        """)
        layout.addWidget(self.apply_btn)
        
        layout.addStretch()
        content_widget.setLayout(layout)
        scroll.setWidget(content_widget)
        
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(scroll)
        self.setLayout(main_layout)
        
        # Store color values
        self.colors = {
            'author': '#6366f1',
            'time': '#888888',
            'message': '#ffffff',
            'accent': '#6366f1'
        }
    
    def create_color_button(self, label, default_color):
        """Create color picker button"""
        layout = QHBoxLayout()
        layout.addWidget(QLabel(label))
        
        btn = QPushButton("  ")
        btn.setFixedSize(60, 24)
        btn.setStyleSheet(f"background-color: {default_color}; border-radius: 4px;")
        btn.clicked.connect(lambda: self.pick_color(btn, label.split()[1].rstrip(':')))
        layout.addWidget(btn)
        layout.addStretch()
        
        return (layout, btn, default_color)
    
    def pick_color(self, button, color_type):
        """Open color picker"""
        color = QColorDialog.getColor()
        if color.isValid():
            color_hex = color.name()
            button.setStyleSheet(f"background-color: {color_hex}; border-radius: 4px;")
            self.colors[color_type] = color_hex
    
    def update_opacity_label(self, value):
        self.opacity_value.setText(f"{value}%")
    
    def update_font_label(self, value):
        self.font_value.setText(f"{value}px")
    
    def update_radius_label(self, value):
        self.radius_value.setText(f"{value}px")
    
    def update_timeout_label(self, value):
        if value == 0:
            self.timeout_value.setText("Không")
        else:
            self.timeout_value.setText(f"{value}s")
            
    def update_anim_label(self, value):
        self.anim_value.setText(f"{value}ms")



class ConnectDialog(QDialog):
    """Dialog nhập URL custom đẹp hơn"""
    def __init__(self, parent=None, current_url=""):
        super().__init__(parent)
        self.setWindowTitle("Kết nối YouTube Chat")
        self.setFixedSize(420, 200) # Increased size
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Main container with style
        container = QWidget()
        container.setStyleSheet("""
            QWidget {
                background-color: rgba(15, 15, 25, 250);
                border: 1px solid rgba(99, 102, 241, 80);
                border-radius: 12px;
            }
            QLabel {
                color: white;
                background: transparent;
                border: none;
            }
            QLineEdit {
                background-color: rgba(255, 255, 255, 10);
                border: 1px solid rgba(255, 255, 255, 20);
                border-radius: 6px;
                padding: 10px;
                color: white;
                font-size: 13px;
                min-height: 20px;
            }
            QLineEdit:focus {
                border: 1px solid #6366f1;
                background-color: rgba(255, 255, 255, 15);
            }
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #6366f1, stop:1 #4f46e5);
                border: none;
                border-radius: 6px;
                padding: 8px 16px; 
                min-height: 25px;
                color: white;
                font-weight: 600;
                font-size: 13px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #4f46e5, stop:1 #4338ca);
            }
            QPushButton#cancel {
                background: transparent;
                border: 1px solid rgba(255, 255, 255, 30);
            }
            QPushButton#cancel:hover {
                background: rgba(255, 255, 255, 10);
            }
        """)
        
        inner_layout = QVBoxLayout(container)
        inner_layout.setContentsMargins(20, 20, 20, 20)
        inner_layout.setSpacing(15)
        
        # Title
        title = QLabel("🔗 Kết nối Livestream")
        title.setStyleSheet("font-size: 16px; font-weight: 700; color: #8b5cf6;")
        inner_layout.addWidget(title)
        
        # Label instruction
        lbl = QLabel("Nhập Link Video hoặc Kênh YouTube:")
        lbl.setStyleSheet("color: #cccccc; font-size: 12px;")
        inner_layout.addWidget(lbl)
        
        # Input
        self.url_input = QLineEdit()
        self.url_input.setText(current_url)
        self.url_input.setPlaceholderText("https://youtube.com/...")
        self.url_input.setFocus()
        inner_layout.addWidget(self.url_input)
        
        # Buttons
        btn_layout = QHBoxLayout()
        self.btn_cancel = QPushButton("Bỏ qua")
        self.btn_cancel.setObjectName("cancel")
        self.btn_cancel.clicked.connect(self.reject)
        
        self.btn_ok = QPushButton("Kết nối ngay")
        self.btn_ok.clicked.connect(self.accept)
        # Default button
        self.btn_ok.setDefault(True)
        
        btn_layout.addWidget(self.btn_cancel)
        btn_layout.addWidget(self.btn_ok)
        inner_layout.addLayout(btn_layout)
        
        layout.addWidget(container)
        self.setLayout(layout)
        
    def get_url(self):
        return self.url_input.text().strip()

class YouTubeChatOverlay(QMainWindow):
    """Main window cho YouTube Chat Overlay"""
    """Main window cho YouTube Chat Overlay"""
    new_message_signal = pyqtSignal(str, str, bool, bool, str) # author, message, is_member, is_sc, sc_amount
    connect_request_signal = pyqtSignal(str) # Signal để yêu cầu kết nối từ thread khác

    
    def __init__(self):
        super().__init__()
        self.messages = []
        self.youtube_chat = None
        self.chat_thread = None
        self.is_connected = False
        self.config = {
            'font_size': 14,
            'show_author': True,
            'show_timestamp': True,
            'author_color': '#6366f1',
            'time_color': '#888888',
            'message_color': '#ffffff',
            'accent_color': '#6366f1',
            'msg_bg_color': 'rgba(255, 255, 255, 10)',
            'border_radius': 6,
            'animation_speed': 300,
            'message_timeout': 0,
            'message_timeout': 0,
            'autohide_header': False,
            'tts_enabled': False,
            'tts_translate': False,
            'translate_to_vi': True,
            'tts_volume': 1.0
        }
        
        self.blacklist = []
        self.load_blacklist()

        
        # Init TTS
        self.tts_thread = TTSThread()
        self.tts_thread.start()
        
        # Init Audio Mixer ở Main Thread để OBS nhận diện ngay
        if TTS_AVAILABLE:
            try:
                # 48kHz, 16bit, stereo, 1024 buffer
                pygame.mixer.init(frequency=48000, size=-16, channels=2, buffer=1024)
                # Hack: Stop ngay để active mixer mà không phát tiếng
                pygame.mixer.stop()
            except Exception as e:
                print(f"Audio Init Error: {e}")

        
        self.init_ui()
        self.create_tray_icon()
        self.load_settings()
        self.load_settings()
        self.new_message_signal.connect(self.add_message)
        self.connect_request_signal.connect(self.connect_to_youtube)
        
        # Tự động kết nối sau khi khởi động
        # Dùng QTimer singleShot để đảm bảo UI đã load xong mới hiện Popup
        QTimer.singleShot(100, self.startup_auto_connect)

    
    def init_ui(self):
        """Khởi tạo giao diện"""
        self.setWindowTitle("YouTube Live Chat Overlay")
        self.setGeometry(100, 100, 450, 650)
        
        # Frameless, transparent, always on top
        self.setWindowFlags(
            Qt.FramelessWindowHint | 
            Qt.WindowStaysOnTopHint |
            Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        # Main widget - NỀN ĐEN
        main_widget = QWidget()
        main_widget.setStyleSheet("""
            QWidget {
                background-color: rgba(0, 0, 0, 0);
                border-radius: 12px;
            }
        """)
        self.setCentralWidget(main_widget)
        
        # Main layout
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Header
        self.create_header(main_layout)
        
        # Chat area
        self.create_chat_area(main_layout)
        
        # Resize grip
        self.size_grip = QSizeGrip(main_widget)
        self.size_grip.setStyleSheet("""
            QSizeGrip {
                width: 16px;
                height: 16px;
                background-color: rgba(99, 102, 241, 100);
                border-radius: 4px;
            }
        """)
        grip_layout = QHBoxLayout()
        grip_layout.addStretch()
        grip_layout.addWidget(self.size_grip)
        main_layout.addLayout(grip_layout)
        
        main_widget.setLayout(main_layout)
        
        # Settings panel
        self.settings_panel = SettingsPanel(self)
        self.settings_panel.apply_btn.clicked.connect(self.apply_settings)
        self.settings_panel.detect_live_btn.clicked.connect(self.on_detect_live_clicked)
        self.settings_panel.test_voice_btn.clicked.connect(self.test_voice)
        self.settings_panel.hide()

        
        # For dragging
        self.drag_position = QPoint()
        
        # Initial state for autohide
        self.update_header_visibility()
    
    def create_header(self, parent_layout):
        """Tạo header với controls"""
        header = QWidget()
        # Enable mouse tracking for hover
        header.setAttribute(Qt.WA_Hover)
        header.setStyleSheet("""
            QWidget {
                background-color: rgba(0, 0, 0, 200);
                border-top-left-radius: 12px;
                border-top-right-radius: 12px;
                border-bottom: 1px solid rgba(99, 102, 241, 50);
            }
            QPushButton {
                background-color: rgba(99, 102, 241, 30);
                border: none;
                border-radius: 6px;
                padding: 6px;
                color: white;
            }
            QPushButton:hover {
                background-color: rgba(99, 102, 241, 60);
            }
        """)
        header.setFixedHeight(45)
        
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(12, 6, 12, 6)
        
        # Drag handle
        drag_label = QLabel("⋮⋮")
        drag_label.setStyleSheet("color: rgba(99, 102, 241, 150); font-size: 18px;")
        header_layout.addWidget(drag_label)
        
        # Title
        title_label = QLabel("YouTube Chat")
        title_label.setStyleSheet("color: rgba(255, 255, 255, 200); font-size: 12px; font-weight: 600;")
        header_layout.addWidget(title_label)
        
        header_layout.addStretch()
        
        # Control buttons
        self.settings_btn = QPushButton("⚙️")
        self.settings_btn.setFixedSize(28, 28)
        self.settings_btn.clicked.connect(self.toggle_settings)
        header_layout.addWidget(self.settings_btn)
        
        self.opacity_btn = QPushButton("🌓")
        self.opacity_btn.setFixedSize(28, 28)
        self.opacity_btn.clicked.connect(self.toggle_opacity)
        header_layout.addWidget(self.opacity_btn)
        
        self.minimize_btn = QPushButton("➖")
        self.minimize_btn.setFixedSize(28, 28)
        self.minimize_btn.clicked.connect(self.showMinimized)
        header_layout.addWidget(self.minimize_btn)
        
        self.close_btn = QPushButton("✕")
        self.close_btn.setFixedSize(28, 28)
        self.close_btn.clicked.connect(self.close)
        header_layout.addWidget(self.close_btn)
        
        header.setLayout(header_layout)
        parent_layout.addWidget(header)
        self.header = header
    
    def create_chat_area(self, parent_layout):
        """Tạo khu vực chat"""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QScrollBar:vertical {
                width: 6px;
                background: rgba(255, 255, 255, 5);
                border-radius: 3px;
            }
            QScrollBar::handle:vertical {
                background: rgba(99, 102, 241, 100);
                border-radius: 3px;
            }
            QScrollBar::handle:vertical:hover {
                background: rgba(99, 102, 241, 150);
            }
        """)
        
        self.chat_widget = QWidget()
        self.chat_widget.setStyleSheet("background-color: transparent;")
        self.chat_layout = QVBoxLayout()
        self.chat_layout.setContentsMargins(8, 8, 8, 8)
        self.chat_layout.setSpacing(4)
        self.chat_layout.addStretch()
        
        self.chat_widget.setLayout(self.chat_layout)
        scroll.setWidget(self.chat_widget)
        
        parent_layout.addWidget(scroll)
        self.scroll_area = scroll
    
    def load_blacklist(self):
        """Load blacklist từ file"""
        self.blacklist = []
        try:
            if os.path.exists('blacklist.txt'):
                with open('blacklist.txt', 'r', encoding='utf-8') as f:
                    self.blacklist = [line.strip().lower() for line in f if line.strip()]
        except Exception as e:
            print(f"Error loading blacklist: {e}")

    def save_blacklist(self):
        """Save blacklist to file"""
        try:
            content = self.settings_panel.blacklist_edit.toPlainText()
            self.blacklist = [line.strip().lower() for line in content.split('\n') if line.strip()]
            with open('blacklist.txt', 'w', encoding='utf-8') as f:
                f.write(content)
        except Exception as e:
            print(f"Error saving blacklist: {e}")

    def add_message(self, author, message, is_member=False, is_superchat=False, sc_amount=""):
        """Thêm tin nhắn mới với animation"""
        
        # CHECK BLACKLIST
        msg_lower = message.lower()
        if any(bad_word in msg_lower for bad_word in self.blacklist):
            print(f"Blocked message containing bad word: {message}")
            return # Skip bad messages
            
        timestamp = datetime.now().strftime("%H:%M")
        
        msg_widget = ChatMessage(author, message, timestamp, self.config, is_member, is_superchat, sc_amount)
        
        # Insert before stretch
        self.chat_layout.insertWidget(self.chat_layout.count() - 1, msg_widget)
        self.messages.append(msg_widget)
        
        # Animate
        msg_widget.show_animated()
        
        # Limit messages
        if len(self.messages) > 50:
            old_msg = self.messages.pop(0)
            old_msg.deleteLater()
        
        # Auto scroll
        QTimer.singleShot(50, lambda: self.scroll_area.verticalScrollBar().setValue(
            self.scroll_area.verticalScrollBar().maximum()
        ))
        
        # TTS - Chỉ đọc tin nhắn không phải System
        if author != "System":
            # Chỉ đọc nội dung tin nhắn
            text_to_read = message
            self.tts_thread.add_text(text_to_read)

    
    def startup_auto_connect(self):
        """Hiển thị popup custom nhập URL khi khởi động"""
        # Lấy URL cũ từ input (đã load từ settings)
        current_url = self.settings_panel.url_input.text().strip()
        
        # Sử dụng Custom Dialog
        dialog = ConnectDialog(self, current_url)
        if dialog.exec_() == QDialog.Accepted:
            url = dialog.get_url()
            if url:
                # Update lại vào settings panel (nhưng không save ngay để tránh ghi đè rác)
                self.settings_panel.url_input.setText(url)
                
                # Start connection thread
                threading.Thread(target=self._startup_connect_thread, args=(url,), daemon=True).start()
        else:
            pass

    def _startup_connect_thread(self, url):
        """Thread thực hiện tìm kiếm và kết nối"""
        # Kiểm tra xem có phải channel không
        is_channel = any(x in url for x in ['/@', '/channel/', '/c/', '/user/'])
        
        target_url = url
        
        if is_channel:
            # Thêm tin nhắn thông báo đang tìm
            self.new_message_signal.emit("System", "Đang tìm livestream trên kênh...", False, False, "")
            
            # Tìm live stream
            live_url = self.find_live_stream_from_channel(url, silent=True)
            if live_url:
                target_url = live_url
                self.new_message_signal.emit("System", "Đã tìm thấy livestream! Đang kết nối...", False, False, "")
            else:
                self.new_message_signal.emit("System", "Kênh hiện không có livestream.", False, False, "")
                return
        else:
            self.new_message_signal.emit("System", "Đang kết nối tới video...", False, False, "")

        # Sử dụng signal để trigger kết nối trên main thread an toàn hơn lambda
        self.connect_request_signal.emit(target_url)

    
    def toggle_settings(self):
        """Hiện/ẩn settings panel"""
        if self.settings_panel.isVisible():
            self.settings_panel.hide()
        else:
            btn_pos = self.settings_btn.mapToGlobal(QPoint(0, 0))
            self.settings_panel.move(
                btn_pos.x() - self.settings_panel.width() + self.settings_btn.width(),
                btn_pos.y() + self.settings_btn.height() + 8
            )
            self.settings_panel.show()
    
    def toggle_opacity(self):
        """Toggle độ mờ nhanh"""
        current = self.settings_panel.opacity_slider.value()
        new_value = 0 if current > 0 else 50
        self.settings_panel.opacity_slider.setValue(new_value)
        self.apply_settings()
    
    def apply_settings(self):
        """Áp dụng cài đặt"""
        opacity = self.settings_panel.opacity_slider.value()
        
        # Update config
        self.config.update({
            'font_size': self.settings_panel.font_slider.value(),
            'show_author': self.settings_panel.show_author_cb.isChecked(),
            'show_timestamp': self.settings_panel.show_timestamp_cb.isChecked(),
            'author_color': self.settings_panel.colors.get('author', '#6366f1'),
            'time_color': self.settings_panel.colors.get('time', '#888888'),
            'message_color': self.settings_panel.colors.get('message', '#ffffff'),
            'accent_color': self.settings_panel.colors.get('accent', '#6366f1'),
            'border_radius': self.settings_panel.radius_slider.value(),
            'animation_speed': self.settings_panel.anim_slider.value(),
            'message_timeout': self.settings_panel.timeout_slider.value(),
            'autohide_header': self.settings_panel.autohide_header_cb.isChecked(),
            'tts_enabled': self.settings_panel.tts_cb.isChecked(),
            'tts_translate': self.settings_panel.translate_cb.isChecked(),
            'translate_to_vi': self.settings_panel.rb_en_vi.isChecked()
        })
        
        # Update TTS settings
        self.tts_thread.enabled = self.config['tts_enabled']
        self.tts_thread.translate_enabled = self.config['tts_translate']
        self.tts_thread.translate_to_vi = self.config['translate_to_vi']
        self.tts_thread.volume = self.settings_panel.tts_vol_slider.value() / 100.0
        
        # Save Blacklist
        self.save_blacklist()

        
        # Update background opacity
        self.centralWidget().setStyleSheet(f"""
            QWidget {{
                background-color: rgba(0, 0, 0, {int(opacity * 2.55)});
                border-radius: 12px;
            }}
        """)
        
        self.update_header_visibility()
        
        # Check if URL changed
        url = self.settings_panel.url_input.text().strip()
        if url:
            self.connect_to_youtube(url)
        
        self.save_settings()
        self.settings_panel.hide()
    
    def on_detect_live_clicked(self):
        """Xử lý khi nhấn nút tự động tìm live stream"""
        url = self.settings_panel.url_input.text().strip()
        
        if not url:
            QMessageBox.warning(self, "Lỗi", "Vui lòng nhập URL channel hoặc video!")
            return
        
        # Kiểm tra xem có phải là channel URL không
        is_channel = any(x in url for x in ['/@', '/channel/', '/c/', '/user/'])
        
        if is_channel:
            # Tìm live stream từ channel
            QMessageBox.information(self, "Đang tìm kiếm", 
                "Đang tìm live stream trên channel...\nVui lòng đợi.")
            
            live_url = self.find_live_stream_from_channel(url)
            
            if live_url:
                self.settings_panel.url_input.setText(live_url)
                QMessageBox.information(self, "Thành công", 
                    f"Đã tìm thấy live stream!\n\nNhấn 'Áp dụng' để kết nối.")
        else:
            # Đã là video URL, chỉ cần kết nối
            QMessageBox.information(self, "Thông báo", 
                "Đây là URL video. Nhấn 'Áp dụng' để kết nối.")
        

    def update_header_visibility(self):
        """Update header visibility based on settings"""
        if self.config['autohide_header']:
            self.header.hide()
        else:
            self.header.show()
            
    def enterEvent(self, event):
        """Show header on hover if autohide is enabled"""
        if self.config['autohide_header']:
            self.header.show()
        super().enterEvent(event)
        
    def leaveEvent(self, event):
        """Hide header on leave if autohide is enabled"""
        # Kiểm tra xem chuột có thực sự rời khỏi widget không
        # (tránh trường hợp rời khỏi main nhưng vào header con)
        if self.config['autohide_header']:
            # Chỉ ẩn nếu không đang kéo thả hoặc tương tác menu
            if not self.settings_panel.isVisible():
                if not self.geometry().contains(QCursor.pos()):
                    self.header.hide()
        super().leaveEvent(event)
    
    def contextMenuEvent(self, event):
        """Right click context menu"""
        menu = QMenu(self)
        
        settings_action = menu.addAction("⚙️ Cài đặt")
        settings_action.triggered.connect(self.toggle_settings)
        
        toggle_header_action = menu.addAction("👁️ Ẩn/Hiện Header")
        toggle_header_action.triggered.connect(self.toggle_header_manual)
        
        close_action = menu.addAction("✕ Thoát")
        close_action.triggered.connect(self.close)
        
        menu.exec_(event.globalPos())
        
    def toggle_header_manual(self):
        if self.header.isVisible():
            self.header.hide()
        else:
            self.header.show()
    
    def extract_video_id(self, url):
        """Extract video ID from YouTube URL"""
        patterns = [
            r'(?:youtube\.com\/watch\?v=)([\w-]+)',
            r'(?:youtu\.be\/)([\w-]+)',
            r'(?:youtube\.com\/live\/)([\w-]+)',
        ]
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None
    
    def connect_to_youtube(self, url):
        """Connect to YouTube live chat"""
        if not PYTCHAT_AVAILABLE:
            QMessageBox.warning(self, "Lỗi", 
                "pytchat chưa được cài đặt!\n\nCài đặt bằng lệnh:\npip install pytchat")
            return
        
        # Clean URL
        url = url.strip()
        if '?' in url and 'watch?v=' not in url:
             url = url.split('?')[0]

        video_id = self.extract_video_id(url)
        
        # Nếu không phải link video trực tiếp, kiểm tra xem có phải link kênh không
        if not video_id:
            is_channel = any(x in url for x in ['/@', '/channel/', '/c/', '/user/'])
            if is_channel:
                self.new_message_signal.emit("System", "Đang tìm livestream từ link kênh...", False, False, "")
                # Tìm kiếm (chạy đồng bộ ở đây vì đang trong event click nút Apply)
                # Tuy nhiên find_live_stream_from_channel có thể hơi lâu, 
                # nhưng chấp nhận được trong trường hợp bấm nút.
                found_url = self.find_live_stream_from_channel(url, silent=True)
                
                if found_url:
                    video_id = self.extract_video_id(found_url)
                    # Cập nhật lại UI để người dùng thấy link thật (tùy chọn)
                    # self.settings_panel.url_input.setText(found_url) 
                else:
                    QMessageBox.warning(self, "Lỗi", "Kênh này hiện không có livestream để kết nối!")
                    return
        
        if not video_id:
            QMessageBox.warning(self, "Lỗi", "URL YouTube không hợp lệ!\nVui lòng nhập Link Video hoặc Link Channel.")
            return
        
        # Stop demo mode & cleanup
        if hasattr(self, 'chat_timer'):
            self.chat_timer.stop()
        
        # Disconnect existing chat
        self.disconnect_youtube()
        
        # Clear messages
        for msg in self.messages:
            msg.deleteLater()
        self.messages.clear()
        
        # Start connection in background thread
        self.new_message_signal.emit("System", f"Video ID: {video_id}", False, False, "")
        self.new_message_signal.emit("System", "Đang khởi tạo kết nối (Background)...", False, False, "")
        
        threading.Thread(target=self._connect_thread_worker, args=(video_id,), daemon=True).start()
            
    def _connect_thread_worker(self, video_id):
        """Worker thread để khởi tạo pytchat mà không block UI"""
        try:
            self.new_message_signal.emit("System", f"Đang kết nối tới ID: {video_id}...", False, False, "")
            print(f"DEBUG: Calling pytchat.create for {video_id}")
            
            # Thêm tham số logger để debug nếu cần, và thử tắt topchat_only
            # seek_time=0 để đảm bảo bắt đầu từ hiện tại
            chat = pytchat.create(
                video_id=video_id,
                topchat_only=False, # Lấy tất cả tin nhắn
                interruptable=False
            )
            
            print("DEBUG: pytchat.create returned")
            
            if not chat.is_alive():
                 print("DEBUG: chat.is_alive() is False immediately")
                 self.new_message_signal.emit("System", "⚠️ Lỗi: Chat stream chưa sẵn sàng hoặc Video ID không hỗ trợ chat.", False, False, "")
                 # Vẫn thử return object để xem có may mắn không
                 # return

            # Gán vào biến member sau khi khởi tạo thành công
            self.youtube_chat = chat
            self.is_connected = True
            
            # Start fetch thread
            self.chat_thread = threading.Thread(target=self.fetch_youtube_chat, daemon=True)
            self.chat_thread.start()
            
            print(f"Connected to YouTube chat: {video_id}")
            self.new_message_signal.emit("System", "✅ Đã kết nối! Đang lấy tin nhắn...", False, False, "")
            
        except Exception as e:
            self.new_message_signal.emit("System", f"❌ Lỗi Pytchat: {str(e)}", False, False, "")
            print(f"Error connecting: {e}")
            import traceback
            traceback.print_exc()

    
    def fetch_youtube_chat(self):
        """Fetch messages from YouTube chat (runs in thread)"""
        try:
            # Chờ một chút trước khi loop
            import time
            time.sleep(1)
            
            self.new_message_signal.emit("System", "🔄 Bắt đầu lấy tin nhắn...", False, False, "")
            
            while self.youtube_chat and self.youtube_chat.is_alive() and self.is_connected:
                for chat in self.youtube_chat.get().sync_items():
                    author = chat.author.name
                    message = chat.message
                    
                    # Extract Metadata
                    is_member = chat.author.isChatSponsor
                    amount = chat.amountString # Not empty if superchat
                    is_superchat = bool(amount)
                    
                    self.new_message_signal.emit(author, message, is_member, is_superchat, amount)
                    
                # Sleep một chút để giảm tải CPU
                time.sleep(0.5)
                
        except Exception as e:
            print(f"Error fetching chat: {e}")
            self.new_message_signal.emit("System", f"⚠️ Mất kết nối chat: {str(e)}", False, False, "")
            self.is_connected = False
    
    def disconnect_youtube(self):
        """Disconnect from YouTube chat"""
        self.is_connected = False
        if self.youtube_chat:
            try:
                self.youtube_chat.terminate()
            except:
                pass
            self.youtube_chat = None
        if self.chat_thread:
            self.chat_thread = None
    
    def create_tray_icon(self):
        """Tạo system tray icon"""
        # Tạo icon
        icon_pixmap = self.create_app_icon()
        
        self.tray_icon = QSystemTrayIcon(QIcon(icon_pixmap), self)
        
        # Tạo menu
        tray_menu = QMenu()
        
        show_action = QAction("📺 Hiện/Ẩn", self)
        show_action.triggered.connect(self.toggle_window)
        tray_menu.addAction(show_action)
        
        settings_action = QAction("⚙️ Cài đặt", self)
        settings_action.triggered.connect(self.toggle_settings)
        tray_menu.addAction(settings_action)
        
        tray_menu.addSeparator()
        
        quit_action = QAction("✕ Thoát", self)
        quit_action.triggered.connect(self.quit_app)
        tray_menu.addAction(quit_action)
        
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self.on_tray_icon_activated)
        self.tray_icon.show()
        
        # Tooltip
        self.tray_icon.setToolTip("YouTube Chat Overlay")
    
    def create_app_icon(self):
        """Tạo icon cho app"""
        pixmap = QPixmap(64, 64)
        pixmap.fill(Qt.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Vẽ background gradient
        from PyQt5.QtGui import QLinearGradient, QBrush
        gradient = QLinearGradient(0, 0, 64, 64)
        gradient.setColorAt(0, QColor("#6366f1"))
        gradient.setColorAt(1, QColor("#8b5cf6"))
        
        painter.setBrush(QBrush(gradient))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(4, 4, 56, 56, 12, 12)
        
        # Vẽ chat bubble icon
        painter.setBrush(QBrush(QColor("white")))
        painter.drawRoundedRect(16, 20, 32, 20, 4, 4)
        
        # Vẽ tail của bubble
        from PyQt5.QtGui import QPolygon
        points = QPolygon([
            QPoint(20, 40),
            QPoint(16, 44),
            QPoint(24, 40)
        ])
        painter.drawPolygon(points)
        
        painter.end()
        return pixmap
    
    def on_tray_icon_activated(self, reason):
        """Xử lý khi click vào tray icon"""
        if reason == QSystemTrayIcon.Trigger:  # Single click
            self.toggle_window()
    
    def toggle_window(self):
        """Toggle hiện/ẩn cửa sổ"""
        if self.isVisible():
            self.hide()
        else:
            self.show()
            self.activateWindow()
    
    def quit_app(self):
        """Thoát ứng dụng"""
        self.save_settings()
        self.disconnect_youtube()
        self.tray_icon.hide()
        QApplication.quit()
    
    def find_live_stream_from_channel(self, channel_url, silent=False):
        """Tìm live stream từ channel URL"""
        if not REQUESTS_AVAILABLE:
            if not silent:
                QMessageBox.warning(self, "Lỗi", 
                    "Cần cài đặt requests và beautifulsoup4!\n\nCài đặt bằng lệnh:\npip install requests beautifulsoup4")
            return None
        
        try:
            # 1. Làm sạch URL (bỏ query params như ?si=...)
            if '?' in channel_url:
                channel_url = channel_url.split('?')[0]
                
            # Lấy channel page
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept-Language': 'en-US,en;q=0.9',
            }
            
            # Xử lý các dạng URL channel khác nhau
            if '@' in channel_url:
                # Format: youtube.com/@channelname
                live_url = channel_url.rstrip('/') + '/live'
            elif '/channel/' in channel_url:
                # Format: youtube.com/channel/UCxxxxx
                live_url = channel_url.rstrip('/') + '/live'
            elif '/c/' in channel_url:
                # Format: youtube.com/c/channelname
                live_url = channel_url.rstrip('/').replace('/c/', '/@') + '/live'
            else:
                live_url = channel_url.rstrip('/') + '/live'
            
            # Log lên UI nếu đang chạy ngầm
            if silent:
                self.new_message_signal.emit("System", f"Đang truy cập: {live_url}", False, False, "")
            
            print(f"Fetching: {live_url}")
            response = requests.get(live_url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                content = response.text
                
                # Check link canonical trước (thường chính xác nhất)
                # <link rel="canonical" href="https://www.youtube.com/watch?v=VIDEO_ID">
                canonical_match = re.search(r'<link rel="canonical" href="https://www.youtube.com/watch\?v=([a-zA-Z0-9_-]{11})">', content)
                if canonical_match:
                    video_id = canonical_match.group(1)
                    if silent:
                        self.new_message_signal.emit("System", f"Đã tìm thấy Video ID (Canonical): {video_id}", False, False, "")
                    return f"https://www.youtube.com/watch?v={video_id}"
                
                # Pattern dự phòng để tìm video ID
                patterns = [
                    r'"videoId":"([a-zA-Z0-9_-]{11})"',
                    r'watch\?v=([a-zA-Z0-9_-]{11})',
                ]
                
                for pattern in patterns:
                    match = re.search(pattern, content)
                    if match:
                        video_id = match.group(1)
                        if silent:
                            self.new_message_signal.emit("System", f"Đã tìm thấy Video ID (Regex): {video_id}", False, False, "")
                        return f"https://www.youtube.com/watch?v={video_id}"
                
                if not silent:
                    QMessageBox.information(self, "Thông báo", 
                        "Không tìm thấy live stream đang diễn ra trên channel này.")
                else:
                    self.new_message_signal.emit("System", "Không tìm thấy Video ID trong trang /live", False, False, "")
                return None
            else:
                msg = f"Lỗi truy cập channel (Status: {response.status_code})"
                if not silent:
                    QMessageBox.warning(self, "Lỗi", msg)
                else:
                    self.new_message_signal.emit("System", msg, False, False, "")
                return None
                
        except Exception as e:
            msg = f"Lỗi khi tìm live stream: {str(e)}"
            if not silent:
                QMessageBox.critical(self, "Lỗi", msg)
            else:
                 self.new_message_signal.emit("System", msg, False, False, "")
            return None
    
    def closeEvent(self, event):
        """Handle window close"""
        # Minimize to tray instead of closing
        if self.tray_icon.isVisible():
            event.ignore()
            self.hide()
            self.tray_icon.showMessage(
                "YouTube Chat Overlay",
                "Ứng dụng đang chạy ở system tray",
                QSystemTrayIcon.Information,
                2000
            )
        else:
            self.save_settings()
            self.disconnect_youtube()
            event.accept()

    
    def save_settings(self):
        """Lưu cài đặt"""
        settings = {
            'opacity': self.settings_panel.opacity_slider.value(),
            'font_size': self.settings_panel.font_slider.value(),
            'show_author': self.settings_panel.show_author_cb.isChecked(),
            'show_timestamp': self.settings_panel.show_timestamp_cb.isChecked(),
            'url': self.settings_panel.url_input.text(),
            'colors': self.settings_panel.colors,
            'border_radius': self.settings_panel.radius_slider.value(),
            'animation_speed': self.settings_panel.anim_slider.value(),
            'message_timeout': self.settings_panel.timeout_slider.value(),
            'autohide_header': self.settings_panel.autohide_header_cb.isChecked(),
            'tts_enabled': self.settings_panel.tts_cb.isChecked(),
            'tts_translate': self.settings_panel.translate_cb.isChecked(),
            'translate_to_vi': self.settings_panel.rb_en_vi.isChecked(),
            'tts_volume': self.settings_panel.tts_vol_slider.value(),
            # Lưu vị trí và kích thước cửa sổ

            'window_x': self.x(),

            'window_y': self.y(),
            'window_width': self.width(),
            'window_height': self.height()
        }
        try:
            with open('chat_settings.json', 'w', encoding='utf-8') as f:
                json.dump(settings, f, ensure_ascii=False, indent=2)
        except:
            pass
    
    def load_settings(self):
        """Load cài đặt"""
        try:
            with open('chat_settings.json', 'r', encoding='utf-8') as f:
                settings = json.load(f)
                self.settings_panel.opacity_slider.setValue(settings.get('opacity', 0))
                self.settings_panel.font_slider.setValue(settings.get('font_size', 14))
                self.settings_panel.show_author_cb.setChecked(settings.get('show_author', True))
                self.settings_panel.show_timestamp_cb.setChecked(settings.get('show_timestamp', True))
                self.settings_panel.url_input.setText(settings.get('url', ''))
                
                if 'colors' in settings:
                    self.settings_panel.colors.update(settings['colors'])
                
                if 'border_radius' in settings:
                    self.settings_panel.radius_slider.setValue(settings['border_radius'])
                
                if 'animation_speed' in settings:
                    self.settings_panel.anim_slider.setValue(settings['animation_speed'])
                    
                if 'message_timeout' in settings:
                    self.settings_panel.timeout_slider.setValue(settings['message_timeout'])
                    self.settings_panel.update_timeout_label(settings['message_timeout'])
                    
                if 'autohide_header' in settings:
                    self.settings_panel.autohide_header_cb.setChecked(settings['autohide_header'])
                
                if 'tts_enabled' in settings:
                    self.settings_panel.tts_cb.setChecked(settings['tts_enabled'])
                    self.tts_thread.enabled = settings['tts_enabled']

                if 'tts_translate' in settings:
                    self.settings_panel.translate_cb.setChecked(settings['tts_translate'])
                    self.tts_thread.translate_enabled = settings['tts_translate']
                    
                if 'translate_to_vi' in settings:
                    to_vi = settings['translate_to_vi']
                    self.settings_panel.rb_en_vi.setChecked(to_vi)
                    self.settings_panel.rb_vi_en.setChecked(not to_vi)
                    self.tts_thread.translate_to_vi = to_vi
                    
                    # Update visible state
                    self.settings_panel.rb_en_vi.setVisible(settings['tts_translate'])
                    self.settings_panel.rb_vi_en.setVisible(settings['tts_translate'])
                
                # Load blacklist to UI
                if hasattr(self, 'blacklist') and self.blacklist:
                    self.settings_panel.blacklist_edit.setText('\n'.join(self.blacklist))
                
                if 'tts_volume' in settings:

                    vol = settings['tts_volume']
                    self.settings_panel.tts_vol_slider.setValue(vol)
                    self.settings_panel.tts_vol_value.setText(f"{vol}%")
                    self.tts_thread.volume = vol / 100.0

                
                # Load window geometry
                if 'window_x' in settings and 'window_y' in settings:
                    self.move(settings['window_x'], settings['window_y'])
                
                if 'window_width' in settings and 'window_height' in settings:
                    self.resize(settings['window_width'], settings['window_height'])
        except:
            pass
    
    def mousePressEvent(self, event):
        """Bắt đầu kéo cửa sổ"""
        if event.button() == Qt.LeftButton and self.header.geometry().contains(event.pos()):
            self.drag_position = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()
    
    def mouseMoveEvent(self, event):
        """Kéo cửa sổ"""
        if event.buttons() == Qt.LeftButton and self.drag_position:
            self.move(event.globalPos() - self.drag_position)
            event.accept()


    def test_voice(self):
        """Test giọng đọc"""
        self.tts_thread.enabled = True # Force enable for test
        self.tts_thread.add_text("Xin chào, đây là giọng đọc thử nghiệm!")
        QMessageBox.information(self, "Test", "Đã gửi lệnh đọc. Bạn có nghe thấy gì không?")

def main():
    app = QApplication(sys.argv)
    app.setFont(QFont("Segoe UI", 10))
    
    overlay = YouTubeChatOverlay()
    overlay.show()
    
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
