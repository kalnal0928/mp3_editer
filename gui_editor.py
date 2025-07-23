

import customtkinter as ctk
from tkinter import filedialog, messagebox
from PIL import Image
import os
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, TIT2, TPE1, TALB, TCON, TRCK, APIC
from pydub import AudioSegment

# --- Core Logic Functions (from previous version) ---

def parse_time(time_str):
    try:
        if ':' in time_str:
            mins, secs = map(int, time_str.split(':'))
            return (mins * 60 + secs) * 1000
        else:
            return int(time_str) * 1000
    except ValueError:
        return None

# --- GUI Application ---

class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("MP3 편집기")
        self.geometry("550x650")
        self.resizable(False, False)

        ctk.set_appearance_mode("System")  # or "Dark", "Light"
        ctk.set_default_color_theme("blue")

        # --- Main Tab View ---
        self.tab_view = ctk.CTkTabview(self, width=500)
        self.tab_view.pack(padx=20, pady=10, fill="both", expand=True)

        self.tab_view.add("태그 편집기")
        self.tab_view.add("오디오 편집기")

        self.setup_tag_editor_tab(self.tab_view.tab("태그 편집기"))
        self.setup_audio_editor_tab(self.tab_view.tab("오디오 편집기"))

        # --- Status Bar ---
        self.status_label = ctk.CTkLabel(self, text="준비 완료.", anchor="w")
        self.status_label.pack(side="bottom", fill="x", padx=10, pady=5)

    # --- Tab 1: Tag Editor ---
    def setup_tag_editor_tab(self, tab):
        self.tag_file_path = ""

        # File Selection
        tab.grid_columnconfigure(1, weight=1)
        self.tag_file_button = ctk.CTkButton(tab, text="MP3 파일 열기", command=self.open_tag_file)
        self.tag_file_button.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        self.tag_file_label = ctk.CTkLabel(tab, text="선택된 파일 없음", anchor="w")
        self.tag_file_label.grid(row=0, column=1, padx=10, pady=10, sticky="ew")

        # Tag Entries
        self.entries = {}
        tags = ["제목", "아티스트", "앨범", "장르", "트랙 번호"]
        for i, tag in enumerate(tags):
            label = ctk.CTkLabel(tab, text=tag)
            label.grid(row=i+1, column=0, padx=10, pady=5, sticky="w")
            entry = ctk.CTkEntry(tab, width=300)
            entry.grid(row=i+1, column=1, padx=10, pady=5, sticky="ew")
            self.entries[tag] = entry

        # Album Art
        self.art_label = ctk.CTkLabel(tab, text="앨범 아트")
        self.art_label.grid(row=6, column=0, padx=10, pady=10, sticky="w")
        self.art_image_label = ctk.CTkLabel(tab, text="", width=100, height=100)
        self.art_image_label.grid(row=7, column=1, padx=10, pady=10, sticky="w")
        self.art_button = ctk.CTkButton(tab, text="이미지 변경", command=self.change_album_art)
        self.art_button.grid(row=7, column=0, padx=10, pady=10)
        self.new_art_path = ""

        # Save Button
        self.save_button = ctk.CTkButton(tab, text="태그 저장", command=self.save_tags, height=40)
        self.save_button.grid(row=8, column=0, columnspan=2, padx=10, pady=20, sticky="ew")

    def open_tag_file(self):
        self.tag_file_path = filedialog.askopenfilename(filetypes=[("MP3 files", "*.mp3")])
        if not self.tag_file_path:
            return
        self.tag_file_label.configure(text=os.path.basename(self.tag_file_path))
        self.load_tags()

    def load_tags(self):
        try:
            audio = MP3(self.tag_file_path, ID3=ID3)
            if audio.tags is None: audio.add_tags()

            # Clear previous entries
            for entry in self.entries.values(): entry.delete(0, "end")

            self.entries["제목"].insert(0, audio.tags.get('TIT2', [''])[0])
            self.entries["아티스트"].insert(0, audio.tags.get('TPE1', [''])[0])
            self.entries["앨범"].insert(0, audio.tags.get('TALB', [''])[0])
            self.entries["장르"].insert(0, audio.tags.get('TCON', [''])[0])
            self.entries["트랙 번호"].insert(0, audio.tags.get('TRCK', [''])[0])

            # Load album art
            self.new_art_path = ""
            if 'APIC:' in audio.tags:
                album_art = audio.tags['APIC:'].data
                img = Image.open(io.BytesIO(album_art))
                ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(100, 100))
                self.art_image_label.configure(image=ctk_img)
            else:
                self.art_image_label.configure(image=None, text="아트 없음")
            self.status_label.configure(text="태그를 성공적으로 불러왔습니다.")
        except Exception as e:
            messagebox.showerror("오류", f"태그를 불러오는 중 오류 발생: {e}")
            self.status_label.configure(text="오류: 태그를 불러올 수 없습니다.")

    def change_album_art(self):
        self.new_art_path = filedialog.askopenfilename(filetypes=[("Image files", "*.jpg *.jpeg *.png")])
        if not self.new_art_path:
            return
        img = Image.open(self.new_art_path)
        ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(100, 100))
        self.art_image_label.configure(image=ctk_img)
        self.status_label.configure(text=f"새 앨범 아트 선택: {os.path.basename(self.new_art_path)}")

    def save_tags(self):
        if not self.tag_file_path:
            messagebox.showwarning("경고", "먼저 MP3 파일을 열어주세요.")
            return
        try:
            audio = MP3(self.tag_file_path, ID3=ID3)
            if audio.tags is None: audio.add_tags()

            audio.tags['TIT2'] = TIT2(encoding=3, text=self.entries["제목"].get())
            audio.tags['TPE1'] = TPE1(encoding=3, text=self.entries["아티스트"].get())
            audio.tags['TALB'] = TALB(encoding=3, text=self.entries["앨범"].get())
            audio.tags['TCON'] = TCON(encoding=3, text=self.entries["장르"].get())
            audio.tags['TRCK'] = TRCK(encoding=3, text=self.entries["트랙 번호"].get())

            if self.new_art_path:
                with open(self.new_art_path, 'rb') as art_file:
                    audio.tags.delall('APIC')
                    audio.tags.add(APIC(encoding=3, mime='image/jpeg', type=3, desc='Cover', data=art_file.read()))

            audio.save()
            messagebox.showinfo("성공", "태그를 성공적으로 저장했습니다.")
            self.status_label.configure(text="태그를 성공적으로 저장했습니다.")
        except Exception as e:
            messagebox.showerror("오류", f"태그 저장 중 오류 발생: {e}")
            self.status_label.configure(text="오류: 태그를 저장할 수 없습니다.")

    # --- Tab 2: Audio Editor ---
    def setup_audio_editor_tab(self, tab):
        tab.grid_columnconfigure(0, weight=1)

        # --- Cutting Frame ---
        cut_frame = ctk.CTkFrame(tab)
        cut_frame.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        cut_frame.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(cut_frame, text="MP3 자르기", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, columnspan=3, pady=10)

        self.cut_file_path = ""
        ctk.CTkButton(cut_frame, text="파일 선택", command=self.open_cut_file).grid(row=1, column=0, padx=10, pady=5)
        self.cut_file_label = ctk.CTkLabel(cut_frame, text="파일 없음")
        self.cut_file_label.grid(row=1, column=1, columnspan=2, padx=10, pady=5, sticky="w")

        ctk.CTkLabel(cut_frame, text="시작 시간 (MM:SS 또는 초):").grid(row=2, column=0, padx=10, pady=5, sticky="w")
        self.start_time_entry = ctk.CTkEntry(cut_frame)
        self.start_time_entry.grid(row=2, column=1, padx=10, pady=5, sticky="ew")

        ctk.CTkLabel(cut_frame, text="종료 시간 (MM:SS 또는 초):").grid(row=3, column=0, padx=10, pady=5, sticky="w")
        self.end_time_entry = ctk.CTkEntry(cut_frame)
        self.end_time_entry.grid(row=3, column=1, padx=10, pady=5, sticky="ew")

        ctk.CTkButton(cut_frame, text="자르기 & 저장", command=self.cut_audio).grid(row=4, column=0, columnspan=2, padx=10, pady=10, sticky="ew")

        # --- Merging Frame ---
        merge_frame = ctk.CTkFrame(tab)
        merge_frame.grid(row=1, column=0, padx=10, pady=20, sticky="ew")
        merge_frame.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(merge_frame, text="MP3 붙이기", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, columnspan=3, pady=10)

        self.merge_file1_path = ""
        self.merge_file2_path = ""
        ctk.CTkButton(merge_frame, text="첫 번째 파일", command=self.open_merge_file1).grid(row=1, column=0, padx=10, pady=5)
        self.merge_file1_label = ctk.CTkLabel(merge_frame, text="파일 없음")
        self.merge_file1_label.grid(row=1, column=1, padx=10, pady=5, sticky="w")

        ctk.CTkButton(merge_frame, text="두 번째 파일", command=self.open_merge_file2).grid(row=2, column=0, padx=10, pady=5)
        self.merge_file2_label = ctk.CTkLabel(merge_frame, text="파일 없음")
        self.merge_file2_label.grid(row=2, column=1, padx=10, pady=5, sticky="w")

        ctk.CTkButton(merge_frame, text="붙이기 & 저장", command=self.merge_audio).grid(row=3, column=0, columnspan=2, padx=10, pady=10, sticky="ew")

    def open_cut_file(self):
        self.cut_file_path = filedialog.askopenfilename(filetypes=[("MP3 files", "*.mp3")])
        if self.cut_file_path:
            self.cut_file_label.configure(text=os.path.basename(self.cut_file_path))

    def open_merge_file1(self):
        self.merge_file1_path = filedialog.askopenfilename(filetypes=[("MP3 files", "*.mp3")])
        if self.merge_file1_path:
            self.merge_file1_label.configure(text=os.path.basename(self.merge_file1_path))

    def open_merge_file2(self):
        self.merge_file2_path = filedialog.askopenfilename(filetypes=[("MP3 files", "*.mp3")])
        if self.merge_file2_path:
            self.merge_file2_label.configure(text=os.path.basename(self.merge_file2_path))

    def cut_audio(self):
        if not self.cut_file_path:
            messagebox.showwarning("경고", "자를 파일을 선택해주세요.")
            return

        start_ms = parse_time(self.start_time_entry.get())
        end_ms = parse_time(self.end_time_entry.get())

        if start_ms is None or end_ms is None or start_ms >= end_ms:
            messagebox.showerror("오류", "시간을 올바르게 입력해주세요 (예: 1:25 또는 85).")
            return

        output_path = filedialog.asksaveasfilename(defaultextension=".mp3", filetypes=[("MP3 files", "*.mp3")])
        if not output_path:
            return

        try:
            self.status_label.configure(text="오디오 자르는 중...")
            self.update()
            audio = AudioSegment.from_mp3(self.cut_file_path)
            cut_audio = audio[start_ms:end_ms]
            cut_audio.export(output_path, format="mp3")
            messagebox.showinfo("성공", f"파일이 성공적으로 저장되었습니다:\n{output_path}")
            self.status_label.configure(text="자르기 완료.")
        except Exception as e:
            messagebox.showerror("오류", f"오디오 자르기 중 오류 발생: {e}")
            self.status_label.configure(text="오류: 자르기 실패.")

    def merge_audio(self):
        if not self.merge_file1_path or not self.merge_file2_path:
            messagebox.showwarning("경고", "두 개의 파일을 모두 선택해주세요.")
            return

        output_path = filedialog.asksaveasfilename(defaultextension=".mp3", filetypes=[("MP3 files", "*.mp3")])
        if not output_path:
            return

        try:
            self.status_label.configure(text="오디오 붙이는 중...")
            self.update()
            audio1 = AudioSegment.from_mp3(self.merge_file1_path)
            audio2 = AudioSegment.from_mp3(self.merge_file2_path)
            merged_audio = audio1 + audio2
            merged_audio.export(output_path, format="mp3")
            messagebox.showinfo("성공", f"파일이 성공적으로 저장되었습니다:\n{output_path}")
            self.status_label.configure(text="붙이기 완료.")
        except Exception as e:
            messagebox.showerror("오류", f"오디오 붙이기 중 오류 발생: {e}")
            self.status_label.configure(text="오류: 붙이기 실패.")

if __name__ == "__main__":
    import io
    app = App()
    app.mainloop()
