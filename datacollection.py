import os
import random
import tkinter as tk
from tkinter import ttk, messagebox
import pygame
import pandas as pd
from datetime import datetime
from pylsl import StreamInfo, StreamOutlet

# Initialize the music player
pygame.mixer.init()

class MusicPlayerApp:
    def __init__(self, root, music_dir):
        self.root = root
        self.music_dir = music_dir
        self.songs = [f for f in os.listdir(music_dir) if f.endswith(('.mp3', '.wav'))]
        random.shuffle(self.songs)  # Shuffle the songs for random order
        self.played_songs = []  # Track played songs
        self.current_song = None
        self.start_time = None
        self.ratings = []
        self.mood_coords = None
        self.mood_marker = None
        self.mood_submitted = False
        self.timer_seconds = 60  # Countdown timer starts at 60 seconds
        self.timer_running = False  # Tracks if the timer is active
        self.timer_id = None  # To store the `after` ID for canceling the timer

        # LSL Outlet Initialization
        self.lsl_info = StreamInfo(name='Music_markers', type='Markers', channel_count=1, nominal_srate=0, channel_format='string', source_id='psy_marker')
        self.lsl_outlet = StreamOutlet(self.lsl_info)

        self.setup_gui()

    def setup_gui(self):
        self.root.title("Music Player with Mood Map and Timer")
        self.root.geometry("1000x600")  # Adjusted window size for side-by-side layout

        # Main container for side-by-side layout
        main_frame = tk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Left panel for mood map
        left_panel = tk.Frame(main_frame)
        left_panel.pack(side=tk.LEFT, padx=10, pady=10, fill=tk.BOTH)

        # Mood Map
        self.mood_label = tk.Label(left_panel, text="Select your mood:")
        self.mood_label.pack(pady=5)
        self.mood_canvas = tk.Canvas(left_panel, width=400, height=400, bg="white")
        self.mood_canvas.pack()

        # Draw axes
        self.mood_canvas.create_line(200, 50, 200, 350, fill="black", width=2)  # Y-axis
        self.mood_canvas.create_line(50, 200, 350, 200, fill="black", width=2)  # X-axis

        # Axis labels outside the mood map
        self.mood_canvas.create_text(200, 10, text="High Arousal", font=("Arial", 10), fill="black")
        self.mood_canvas.create_text(200, 390, text="Low Arousal", font=("Arial", 10), fill="black")
        self.mood_canvas.create_text(380, 210, text="Positive", font=("Arial", 10), fill="black")
        self.mood_canvas.create_text(25, 210, text="Negative", font=("Arial", 10), fill="black")

        # Add mood descriptions
        moods = {
            (300, 100): "Excited", (300, 300): "Relaxed", (365, 200): "Happy",
            (100, 100): "Angry", (50, 200): "Sad", (85, 300): "Depressed",
            (200, 350): "Bored", (200, 50): "Alarmed"
        }
        for coords, text in moods.items():
            self.mood_canvas.create_text(coords[0], coords[1], text=text, font=("Arial", 10), fill="black")

        # Click listener for mood map
        self.mood_canvas.bind("<Button-1>", self.record_mood)

        # Selected mood label
        self.mood_display = tk.Label(left_panel, text="Mood: (0, 0)", font=("Arial", 10))
        self.mood_display.pack()

        # Submit Mood Button
        self.submit_mood_button = ttk.Button(left_panel, text="Submit Mood", command=self.submit_mood)
        self.submit_mood_button.pack(pady=5)

        # Right panel for song controls
        right_panel = tk.Frame(main_frame)
        right_panel.pack(side=tk.RIGHT, padx=10, pady=10, fill=tk.BOTH)

        # Song Label
        self.song_label = tk.Label(right_panel, text="No song playing", font=("Arial", 12), wraplength=400)
        self.song_label.pack(pady=10)

        # Start/Stop Button
        self.play_button = ttk.Button(right_panel, text="Start", command=self.toggle_playback)
        self.play_button.pack(pady=10)

        # Rating Slider
        self.rating_label = tk.Label(right_panel, text="Rate this song (1-5):")
        self.rating_label.pack()
        self.rating_value = tk.IntVar(value=3)  # Default rating value
        self.rating_slider = ttk.Scale(right_panel, from_=1, to=5, orient="horizontal", command=self.update_rating_label)
        self.rating_slider.pack(pady=5)
        self.rating_slider.bind("<ButtonRelease-1>", self.snap_rating_slider)  # Make slider discrete
        self.rating_display = tk.Label(right_panel, text="Rating: 3", font=("Arial", 10))
        self.rating_display.pack()

        # Timer Label
        self.timer_label = tk.Label(right_panel, text="Time Remaining: 1:00", font=("Arial", 12), fg="red")
        self.timer_label.pack(pady=10)

        # Submit Rating Button
        self.submit_button = ttk.Button(right_panel, text="Submit Rating", command=self.submit_rating)
        self.submit_button.pack(pady=10)

        # Exit Button
        self.exit_button = ttk.Button(right_panel, text="Exit", command=self.exit_app)
        self.exit_button.pack(pady=10)

    def update_timer(self):
        """Update the timer countdown."""
        if self.timer_seconds > 0:
            mins, secs = divmod(self.timer_seconds, 60)
            self.timer_label.config(text=f"Time Remaining: {mins}:{secs:02}")
            self.timer_seconds -= 1
            self.timer_id = self.root.after(1000, self.update_timer)  # Schedule next update
        else:
            self.timer_label.config(text="Time Remaining: 0:00")
            self.timer_running = False

    def start_timer(self):
        """Start the countdown timer."""
        self.stop_timer()  # Stop any existing timer
        self.timer_seconds = 60
        self.timer_running = True
        self.update_timer()

    def stop_timer(self):
        """Stop the countdown timer."""
        if self.timer_id:
            self.root.after_cancel(self.timer_id)
            self.timer_id = None
        self.timer_running = False

    def play_random_song(self):
        if not self.mood_submitted:
            messagebox.showwarning("Mood Not Submitted", "Please select and submit your mood before playing a song!")
            return

        if not self.songs:
            self.songs = self.played_songs[:]
            random.shuffle(self.songs)
            self.played_songs = []

        self.current_song = self.songs.pop()
        self.played_songs.append(self.current_song)

        song_path = os.path.join(self.music_dir, self.current_song)
        pygame.mixer.music.load(song_path)
        pygame.mixer.music.play()
        self.start_time = datetime.now()
        self.song_label.config(text=f"Now Playing: {self.current_song}")

        # Start the countdown timer
        self.start_timer()

        # Send LSL marker for music start
        self.lsl_outlet.push_sample([f"Music Started: {self.current_song}"])

    def toggle_playback(self):
        if pygame.mixer.music.get_busy():
            self.stop_song()
            self.play_button.config(text="Start")
        else:
            self.play_random_song()
            self.play_button.config(text="Stop")

    def stop_song(self):
        if self.current_song:
            pygame.mixer.music.stop()
            self.song_label.config(text="No song playing")
            self.stop_timer()  # Stop the countdown timer

            # Send LSL marker for music stop
            self.lsl_outlet.push_sample([f"Music Stopped: {self.current_song}"])

    def update_rating_label(self, value):
        rating = int(float(value))  # Convert slider value to integer
        self.rating_display.config(text=f"Rating: {rating}")
        self.rating_value.set(rating)  # Update the rating value

    def snap_rating_slider(self, event):
        value = self.rating_slider.get()
        snapped_value = round(value)
        self.rating_slider.set(snapped_value)
        self.update_rating_label(snapped_value)

    def record_mood(self, event):

        """Record the mood coordinates based on user click on the mood map."""
        x, y = event.x - 200, 200 - event.y  # Translate to center-based coordinates
        self.mood_coords = (x, y)
        self.mood_display.config(text=f"Mood: ({x}, {y})")

        # Remove previous marker if it exists
        if self.mood_marker:
            self.mood_canvas.delete(self.mood_marker)

        # Draw a new marker
        self.mood_marker = self.mood_canvas.create_oval(
            event.x - 5, event.y - 5, event.x + 5, event.y + 5, fill="red"
        )

    def submit_mood(self):
        if not self.mood_coords:
            messagebox.showwarning("Mood Not Selected", "Please select a mood by clicking on the mood map!")
            return
        self.mood_submitted = True
        messagebox.showinfo("Mood Submitted", f"Mood ({self.mood_coords}) submitted successfully!")

    def submit_rating(self):
        if not self.current_song:
            messagebox.showwarning("Warning", "No song is currently playing!")
            return

        rating = self.rating_value.get()
        duration_played = (datetime.now() - self.start_time).total_seconds()

        self.ratings.append({
            "Song": self.current_song,
            "Rating": rating,
            "Duration Played (s)": duration_played,
            "Mood X": self.mood_coords[0],
            "Mood Y": self.mood_coords[1]
        })

        messagebox.showinfo("Rating Submitted", 
                            f"Rating: {rating}\nMood: {self.mood_coords}\nDuration: {duration_played:.2f} seconds\nSubmitted for {self.current_song}.")
        self.start_time = None

    def exit_app(self):
        pygame.mixer.music.stop()
        self.stop_timer()  # Stop the countdown timer
        self.save_ratings()
        self.root.destroy()

    def save_ratings(self):
        if not self.ratings:
            return

        df = pd.DataFrame(self.ratings)
        ratings_file = "song_ratings_with_mood.csv"
        df.to_csv(ratings_file, index=False)
        print(f"Ratings saved to {ratings_file}")


# Directory containing songs
music_directory = "" #path to music directory

# Create the GUI
root = tk.Tk()
app = MusicPlayerApp(root, music_directory)
root.mainloop()
