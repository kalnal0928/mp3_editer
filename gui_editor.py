import customtkinter as ctk
from tkinter import filedialog, messagebox
from PIL import Image
import os
import io
import pygame
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, TIT2, TPE1, TALB, TCON, TRCK, APIC
from pydub import AudioSegment

# --- Core Logic Functions ---

def parse_time(time_str):
    try:
        if ':' in time_str:
            parts = list(map(int, time_str.split(':')))
            if len(parts) == 2:
                mins, secs = parts
                return (mins * 60 + secs) * 1000
        return int(time_str) * 1000
    except (ValueError, TypeError):
        return None

def format_time(ms):
    if ms is None:
        return "00:00"
    seconds = int(ms / 1000)
    mins, secs = divmod(seconds, 60)
    return f"{mins:02d}:{secs:02d}"

# --- GUI Application ---

class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        # --- Font Definition ---
        self.main_font = ctk.CTkFont(family="Malgun Gothic", size=12)
        self.bold_font = ctk.CTkFont(family="Malgun Gothic", size=13, weight="bold")

        self.title("MP3 편집기")
        self.geometry("550x700")
        self.resizable(False, False)

        pygame.mixer.init()
        self.playback_active = False
        self.paused = False
        self.song_length_ms = 0

        ctk.set_appearance_mode("System")
        ctk.set_default_color_theme("blue")

        self.tab_view = ctk.CTkTabview(self, width=500)
        self.tab_view.pack(padx=20, pady=10, fill="both", expand=True)
        self.tab_view.add("태그 편집기")
        self.tab_view.add("오디오 편집기")

        self.setup_tag_editor_tab(self.tab_view.tab("태그 편집기"))
        self.setup_audio_editor_tab(self.tab_view.tab("오디오 편집기"))

        self.status_label = ctk.CTkLabel(self, text="준비 완료.", anchor="w", font=self.main_font)
        self.status_label.pack(side="bottom", fill="x", padx=10, pady=5)
        
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def on_closing(self):
        pygame.mixer.quit()
        self.destroy()

    # --- Tab 1: Tag Editor ---
    def setup_tag_editor_tab(self, tab):
        self.tag_file_path = ""
        tab.grid_columnconfigure(1, weight=1)
        ctk.CTkButton(tab, text="MP3 파일 열기", font=self.main_font, command=self.open_tag_file).grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        self.tag_file_label = ctk.CTkLabel(tab, text="선택된 파일 없음", anchor="w", font=self.main_font)
        self.tag_file_label.grid(row=0, column=1, padx=10, pady=10, sticky="ew")
        self.entries = {}
        tags = ["제목", "아티스트", "앨범", "장르", "트랙 번호"]
        for i, tag in enumerate(tags):
            ctk.CTkLabel(tab, text=tag, font=self.main_font).grid(row=i+1, column=0, padx=10, pady=5, sticky="w")
            entry = ctk.CTkEntry(tab, width=300, font=self.main_font)
            entry.grid(row=i+1, column=1, padx=10, pady=5, sticky="ew")
            self.entries[tag] = entry
        ctk.CTkLabel(tab, text="앨범 아트", font=self.main_font).grid(row=6, column=0, padx=10, pady=10, sticky="w")
        self.art_image_label = ctk.CTkLabel(tab, text="", width=100, height=100)
        self.art_image_label.grid(row=7, column=1, padx=10, pady=10, sticky="w")
        ctk.CTkButton(tab, text="이미지 변경", font=self.main_font, command=self.change_album_art).grid(row=7, column=0, padx=10, pady=10)
        self.new_art_path = ""
        ctk.CTkButton(tab, text="태그 저장", font=self.main_font, height=40, command=self.save_tags).grid(row=8, column=0, columnspan=2, padx=10, pady=20, sticky="ew")

    # --- Tab 2: Audio Editor ---
    def setup_audio_editor_tab(self, tab):
        self.player_file_path = ""
        tab.grid_columnconfigure(0, weight=1)

        cutter_frame = ctk.CTkFrame(tab)
        cutter_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        cutter_frame.grid_columnconfigure((0, 1, 2, 3), weight=1)

        ctk.CTkLabel(cutter_frame, text="오디오 커터", font=self.bold_font).grid(row=0, column=0, columnspan=4, padx=10, pady=10)

        ctk.CTkButton(cutter_frame, text="MP3 파일 선택", font=self.main_font, command=self.open_player_file).grid(row=1, column=0, columnspan=4, padx=10, pady=5, sticky="ew")
        self.player_file_label = ctk.CTkLabel(cutter_frame, text="선택된 파일 없음", font=self.main_font)
        self.player_file_label.grid(row=2, column=0, columnspan=4, padx=10, pady=(0, 10))

        self.time_label = ctk.CTkLabel(cutter_frame, text="00:00 / 00:00", font=self.main_font)
        self.time_label.grid(row=3, column=0, columnspan=4, pady=5)

        self.progress_slider = ctk.CTkSlider(cutter_frame, from_=0, to=100, command=self.seek_audio)
        self.progress_slider.grid(row=4, column=0, columnspan=4, padx=10, pady=10, sticky="ew")
        self.progress_slider.set(0)

        controls_frame = ctk.CTkFrame(cutter_frame, fg_color="transparent")
        controls_frame.grid(row=5, column=0, columnspan=4, pady=5)
        self.play_button = ctk.CTkButton(controls_frame, text="▶", width=50, font=self.main_font, command=self.play_audio).pack(side="left", padx=5)
        self.pause_button = ctk.CTkButton(controls_frame, text="⏸", width=50, font=self.main_font, command=self.pause_audio).pack(side="left", padx=5)
        self.stop_button = ctk.CTkButton(controls_frame, text="⏹", width=50, font=self.main_font, command=self.stop_audio).pack(side="left", padx=5)

        time_set_frame = ctk.CTkFrame(cutter_frame)
        time_set_frame.grid(row=6, column=0, columnspan=4, padx=10, pady=10, sticky="ew")
        time_set_frame.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(time_set_frame, text="시작:", font=self.main_font).grid(row=0, column=0, padx=(10,0))
        self.start_time_entry = ctk.CTkEntry(time_set_frame, font=self.main_font)
        self.start_time_entry.grid(row=0, column=1, padx=5, sticky="ew")
        ctk.CTkButton(time_set_frame, text="설정", width=50, font=self.main_font, command=lambda: self.set_time_from_player('start')).grid(row=0, column=2, padx=(0,10))
        ctk.CTkLabel(time_set_frame, text="종료:", font=self.main_font).grid(row=1, column=0, padx=(10,0), pady=5)
        self.end_time_entry = ctk.CTkEntry(time_set_frame, font=self.main_font)
        self.end_time_entry.grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        ctk.CTkButton(time_set_frame, text="설정", width=50, font=self.main_font, command=lambda: self.set_time_from_player('end')).grid(row=1, column=2, padx=(0,10), pady=5)

        fade_frame = ctk.CTkFrame(cutter_frame, fg_color="transparent")
        fade_frame.grid(row=7, column=0, columnspan=4, pady=5)
        self.fade_in_var = ctk.StringVar(value="off")
        self.fade_out_var = ctk.StringVar(value="off")
        ctk.CTkCheckBox(fade_frame, text="페이드 인 (0.5초)", font=self.main_font, variable=self.fade_in_var, onvalue="on", offvalue="off").pack(side="left", padx=10)
        ctk.CTkCheckBox(fade_frame, text="페이드 아웃 (0.5초)", font=self.main_font, variable=self.fade_out_var, onvalue="on", offvalue="off").pack(side="left", padx=10)

        ctk.CTkButton(cutter_frame, text="자르기 & 저장", height=40, font=self.main_font, command=self.cut_audio).grid(row=8, column=0, columnspan=4, padx=10, pady=10, sticky="ew")

        merge_frame = ctk.CTkFrame(tab)
        merge_frame.grid(row=1, column=0, padx=10, pady=20, sticky="ew")
        merge_frame.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(merge_frame, text="MP3 붙이기", font=self.bold_font).grid(row=0, column=0, columnspan=2, pady=10)
        self.merge_file1_path = ""
        self.merge_file2_path = ""
        ctk.CTkButton(merge_frame, text="첫 번째 파일", font=self.main_font, command=self.open_merge_file1).grid(row=1, column=0, padx=10, pady=5)
        self.merge_file1_label = ctk.CTkLabel(merge_frame, text="파일 없음", font=self.main_font)
        self.merge_file1_label.grid(row=1, column=1, padx=10, pady=5, sticky="w")
        ctk.CTkButton(merge_frame, text="두 번째 파일", font=self.main_font, command=self.open_merge_file2).grid(row=2, column=0, padx=10, pady=5)
        self.merge_file2_label = ctk.CTkLabel(merge_frame, text="파일 없음", font=self.main_font)
        self.merge_file2_label.grid(row=2, column=1, padx=10, pady=5, sticky="w")
        ctk.CTkButton(merge_frame, text="붙이기 & 저장", font=self.main_font, command=self.merge_audio).grid(row=3, column=0, columnspan=2, padx=10, pady=10, sticky="ew")

    def open_tag_file(self):
        self.tag_file_path = filedialog.askopenfilename(filetypes=[("MP3 files", "*.mp3")])
        if self.tag_file_path:
            self.tag_file_label.configure(text=os.path.basename(self.tag_file_path))
            self.load_tags()

    def load_tags(self):
        try:
            audio = MP3(self.tag_file_path, ID3=ID3)
            if audio.tags is None: audio.add_tags()
            for entry in self.entries.values(): entry.delete(0, "end")
            self.entries["제목"].insert(0, audio.tags.get('TIT2', [''])[0])
            self.entries["아티스트"].insert(0, audio.tags.get('TPE1', [''])[0])
            self.entries["앨범"].insert(0, audio.tags.get('TALB', [''])[0])
            self.entries["장르"].insert(0, audio.tags.get('TCON', [''])[0])
            self.entries["트랙 번호"].insert(0, audio.tags.get('TRCK', [''])[0])
            if 'APIC:' in audio.tags:
                img = Image.open(io.BytesIO(audio.tags['APIC:'].data))
                self.art_image_label.configure(image=ctk.CTkImage(light_image=img, dark_image=img, size=(100, 100)), text="")
            else:
                self.art_image_label.configure(image=None, text="아트 없음")
        except Exception as e:
            messagebox.showerror("오류", f"태그 로딩 오류: {e}")

    def change_album_art(self):
        path = filedialog.askopenfilename(filetypes=[("Image files", "*.jpg *.jpeg *.png")])
        if path:
            self.new_art_path = path
            img = Image.open(self.new_art_path)
            self.art_image_label.configure(image=ctk.CTkImage(light_image=img, dark_image=img, size=(100, 100)))

    def save_tags(self):
        if not self.tag_file_path: return messagebox.showwarning("경고", "MP3 파일을 먼저 열어주세요.")
        try:
            audio = MP3(self.tag_file_path, ID3=ID3)
            if audio.tags is None: audio.add_tags()
            audio.tags['TIT2'] = TIT2(encoding=3, text=self.entries["제목"].get())
            audio.tags['TPE1'] = TPE1(encoding=3, text=self.entries["아티스트"].get())
            audio.tags['TALB'] = TALB(encoding=3, text=self.entries["앨범"].get())
            audio.tags['TCON'] = TCON(encoding=3, text=self.entries["장르"].get())
            audio.tags['TRCK'] = TRCK(encoding=3, text=self.entries["트랙 번호"].get())
            if self.new_art_path:
                with open(self.new_art_path, 'rb') as f:
                    audio.tags.delall('APIC')
                    audio.tags.add(APIC(encoding=3, mime='image/jpeg', type=3, desc='Cover', data=f.read()))
            audio.save()
            messagebox.showinfo("성공", "태그를 저장했습니다.")
        except Exception as e:
            messagebox.showerror("오류", f"태그 저장 오류: {e}")

    def open_player_file(self):
        path = filedialog.askopenfilename(filetypes=[("MP3 files", "*.mp3")])
        if not path: return
        self.player_file_path = path
        self.player_file_label.configure(text=os.path.basename(path))
        try:
            self.stop_audio()
            pygame.mixer.music.load(self.player_file_path)
            audio_info = MP3(self.player_file_path)
            self.song_length_ms = audio_info.info.length * 1000
            self.progress_slider.configure(to=self.song_length_ms)
            self.time_label.configure(text=f"00:00 / {format_time(self.song_length_ms)}")
            self.status_label.configure(text=f"로드됨: {os.path.basename(path)}")
        except Exception as e:
            messagebox.showerror("오류", f"플레이어 파일 로딩 오류: {e}")

    def play_audio(self):
        if not self.player_file_path: return messagebox.showwarning("경고", "먼저 파일을 선택하세요.")
        if not self.playback_active:
            pygame.mixer.music.play(start=self.progress_slider.get() / 1000)
            self.playback_active = True
        elif self.paused:
            pygame.mixer.music.unpause()
        self.paused = False
        self.update_progress()

    def pause_audio(self):
        if self.playback_active and not self.paused:
            pygame.mixer.music.pause()
            self.paused = True

    def stop_audio(self):
        pygame.mixer.music.stop()
        self.playback_active = False
        self.progress_slider.set(0)
        self.time_label.configure(text=f"00:00 / {format_time(self.song_length_ms)}")

    def seek_audio(self, value):
        if pygame.mixer.music.get_busy():
            self.stop_audio()
            self.progress_slider.set(float(value))
            self.play_audio()

    def update_progress(self):
        if pygame.mixer.music.get_busy() and not self.paused:
            current_pos = pygame.mixer.music.get_pos() + self.progress_slider.get()
            if current_pos >= self.song_length_ms:
                self.stop_audio()
            else:
                self.time_label.configure(text=f"{format_time(current_pos)} / {format_time(self.song_length_ms)}")
                self.progress_slider.set(current_pos)
                self.after(250, self.update_progress)
        elif not pygame.mixer.music.get_busy() and self.playback_active:
             self.stop_audio()

    def set_time_from_player(self, target):
        current_time_ms = self.progress_slider.get()
        formatted_time = format_time(current_time_ms)
        entry = self.start_time_entry if target == 'start' else self.end_time_entry
        entry.delete(0, "end")
        entry.insert(0, formatted_time)

    def cut_audio(self):
        if not self.player_file_path: return messagebox.showwarning("경고", "먼저 파일을 선택하세요.")
        start_ms = parse_time(self.start_time_entry.get())
        end_ms = parse_time(self.end_time_entry.get())
        if start_ms is None or end_ms is None or start_ms >= end_ms:
            return messagebox.showerror("오류", "시간을 올바르게 입력하세요 (예: 1:25 또는 85).")
        output_path = filedialog.asksaveasfilename(defaultextension=".mp3", filetypes=[("MP3 files", "*.mp3")])
        if not output_path: return
        try:
            self.status_label.configure(text="오디오 자르는 중...")
            self.update_idletasks()
            audio = AudioSegment.from_mp3(self.player_file_path)
            cut_audio = audio[start_ms:end_ms]
            if self.fade_in_var.get() == "on":
                cut_audio = cut_audio.fade_in(500)
            if self.fade_out_var.get() == "on":
                cut_audio = cut_audio.fade_out(500)
            cut_audio.export(output_path, format="mp3")
            messagebox.showinfo("성공", f"파일이 저장되었습니다: {output_path}")
            self.status_label.configure(text="자르기 완료.")
        except Exception as e:
            messagebox.showerror("오류", f"자르기 오류: {e}")
            self.status_label.configure(text="오류: 자르기 실패.")

    def open_merge_file1(self):
        path = filedialog.askopenfilename(filetypes=[("MP3 files", "*.mp3")])
        if path:
            self.merge_file1_path = path
            self.merge_file1_label.configure(text=os.path.basename(path))

    def open_merge_file2(self):
        path = filedialog.askopenfilename(filetypes=[("MP3 files", "*.mp3")])
        if path:
            self.merge_file2_path = path
            self.merge_file2_label.configure(text=os.path.basename(path))

    def merge_audio(self):
        if not self.merge_file1_path or not self.merge_file2_path: return messagebox.showwarning("경고", "두 파일을 모두 선택하세요.")
        output_path = filedialog.asksaveasfilename(defaultextension=".mp3", filetypes=[("MP3 files", "*.mp3")])
        if not output_path: return
        try:
            self.status_label.configure(text="오디오 붙이는 중...")
            self.update_idletasks()
            audio1 = AudioSegment.from_mp3(self.merge_file1_path)
            audio2 = AudioSegment.from_mp3(self.merge_file2_path)
            merged_audio = audio1 + audio2
            merged_audio.export(output_path, format="mp3")
            messagebox.showinfo("성공", f"파일이 저장되었습니다: {output_path}")
            self.status_label.configure(text="붙이기 완료.")
        except Exception as e:
            messagebox.showerror("오류", f"붙이기 오류: {e}")
            self.status_label.configure(text="오류: 붙이기 실패.")

if __name__ == "__main__":
    app = App()
    app.mainloop()