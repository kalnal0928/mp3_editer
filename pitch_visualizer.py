
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, APIC, TIT2, TPE1, TALB, TCON, TRCK
import os
from pydub import AudioSegment
import threading
import pygame
import librosa
import numpy as np
import matplotlib
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

class PitchVisualizerUI:
    def __init__(self, root):
        self.root = root
        self.root.title("MP3 Pitch Visualizer")
        self.file_path = None
        self.playing = False
        self.paused = False
        self.position = 0
        self.pitch_thread = None
        self.stop_pitch_visualization_flag = threading.Event()

        # Initialize Pygame Mixer
        pygame.mixer.init()

        # Create UI elements
        self.create_widgets()

    def create_widgets(self):
        # Frame for file operations
        file_frame = tk.Frame(self.root)
        file_frame.pack(pady=10)

        self.file_label = tk.Label(file_frame, text="No file selected", width=50)
        self.file_label.pack(side=tk.LEFT, padx=5)

        self.browse_button = tk.Button(file_frame, text="Browse", command=self.browse_file)
        self.browse_button.pack(side=tk.LEFT)

        # Frame for pitch visualization
        pitch_frame = tk.Frame(self.root)
        pitch_frame.pack(pady=10)

        self.fig, self.ax = plt.subplots(figsize=(8, 2))
        self.canvas = FigureCanvasTkAgg(self.fig, master=pitch_frame)
        self.canvas.get_tk_widget().pack()

        # Frame for controls
        control_frame = tk.Frame(self.root)
        control_frame.pack(pady=10)

        self.play_button = tk.Button(control_frame, text="Play", command=self.play_audio)
        self.play_button.pack(side=tk.LEFT, padx=5)

        self.pause_button = tk.Button(control_frame, text="Pause", command=self.pause_audio)
        self.pause_button.pack(side=tk.LEFT, padx=5)

        self.stop_button = tk.Button(control_frame, text="Stop", command=self.stop_audio)
        self.stop_button.pack(side=tk.LEFT, padx=5)

    def browse_file(self):
        self.file_path = filedialog.askopenfilename(filetypes=[("MP3 files", "*.mp3")])
        if self.file_path:
            self.file_label.config(text=os.path.basename(self.file_path))
            # Stop any previous audio and visualization
            self.stop_audio()

    def play_audio(self):
        if self.file_path:
            if not self.playing:
                pygame.mixer.music.load(self.file_path)
                pygame.mixer.music.play(start=self.position)
                self.playing = True
                self.paused = False
                self.start_pitch_visualization()
            elif self.paused:
                pygame.mixer.music.unpause()
                self.paused = False
                # Resume visualization
                self.start_pitch_visualization()

    def pause_audio(self):
        if self.playing and not self.paused:
            pygame.mixer.music.pause()
            self.paused = True
            self.position = pygame.mixer.music.get_pos() / 1000.0 + self.position
            self.stop_pitch_visualization()

    def stop_audio(self):
        if self.playing or self.paused:
            pygame.mixer.music.stop()
            self.playing = False
            self.paused = False
            self.position = 0
            self.stop_pitch_visualization()
            # Clear the plot
            self.ax.clear()
            self.ax.set_ylim(0, 1000)
            self.ax.set_ylabel('Pitch (Hz)')
            self.canvas.draw()

    def start_pitch_visualization(self):
        if self.pitch_thread is None or not self.pitch_thread.is_alive():
            self.stop_pitch_visualization_flag.clear()
            self.pitch_thread = threading.Thread(target=self.update_pitch_visualization)
            self.pitch_thread.daemon = True
            self.pitch_thread.start()

    def stop_pitch_visualization(self):
        if self.pitch_thread and self.pitch_thread.is_alive():
            self.stop_pitch_visualization_flag.set()
            self.pitch_thread.join(timeout=0.5) # Wait briefly for the thread to finish
            self.pitch_thread = None

    def update_pitch_visualization(self):
        if not self.file_path:
            return

        try:
            y, sr = librosa.load(self.file_path, sr=None)

            while self.playing and not self.paused and not self.stop_pitch_visualization_flag.is_set():
                current_pos_sec = (pygame.mixer.music.get_pos() / 1000.0) + self.position
                start_sample = int(current_pos_sec * sr)
                # Analyze a small chunk of audio
                end_sample = start_sample + int(0.2 * sr)

                if end_sample > len(y):
                    break # End of song

                y_chunk = y[start_sample:end_sample]

                # Pitch tracking
                pitches, magnitudes = librosa.piptrack(y=y_chunk, sr=sr)

                pitch_values = []
                if pitches.shape[0] > 0 and pitches.shape[1] > 0:
                    for t in range(pitches.shape[1]):
                        index = magnitudes[:, t].argmax()
                        pitch = pitches[index, t]
                        if 50 < pitch < 800: # Filter for a reasonable vocal/instrumental range
                            pitch_values.append(pitch)

                if pitch_values:
                    avg_pitch = np.mean(pitch_values)
                else:
                    avg_pitch = 0

                # Update plot on the main thread
                self.root.after(0, self.update_plot, avg_pitch)

                # Adjust sleep time to be more responsive
                plt.pause(0.1)

        except Exception as e:
            print(f"Error during pitch visualization: {e}")
        finally:
            self.playing = False

    def update_plot(self, pitch):
        self.ax.clear()
        self.ax.bar(['Pitch'], [pitch], color='c')
        self.ax.set_ylim(0, 800) # Adjusted ylim for better visualization
        self.ax.set_ylabel('Pitch (Hz)')
        self.ax.set_xticklabels([]) # Hide x-axis labels
        self.ax.set_xticks([]) # Hide x-axis ticks
        self.canvas.draw()

    def on_closing(self):
        self.stop_audio()
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = PitchVisualizerUI(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()
