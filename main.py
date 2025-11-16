from downloader import download_audio
from beatmap import generate_beatmap
from game import RhythmGame
from menu import MainMenu
import sys
import pygame
import threading

def main():
    menu = None
    
    while True:
        # Show main menu (reuse if it exists)
        if menu is None:
            menu = MainMenu()
        
        menu_choice = menu.run()
        
        if menu_choice == "quit" or menu_choice is None:
            print("Thanks for playing!")
            pygame.quit()
            sys.exit(0)
        
        if isinstance(menu_choice, tuple) and menu_choice[0] == "play":
            # Get URL from menu choice
            url = menu_choice[1]
            
            print("\n" + "="*50)
            print(f"YouTube URL: {url}")
            
            if not url.strip():
                print("No URL provided. Returning to menu...")
                continue
            
            # Shared variables for threading
            audio = None
            beatmap = None
            error = None
            download_complete = False
            beatmap_complete = False
            
            def download_task():
                nonlocal audio, error, download_complete
                try:
                    print("Downloading audio...")
                    audio = download_audio(url, "audio.mp3")
                except Exception as e:
                    error = f"Error downloading audio: {e}"
                finally:
                    download_complete = True
            
            def beatmap_task():
                nonlocal beatmap, error, beatmap_complete
                try:
                    print("Generating beatmap...")
                    beatmap = generate_beatmap(audio)
                except Exception as e:
                    error = f"Error generating beatmap: {e}"
                finally:
                    beatmap_complete = True
            
            # Start download in background thread
            download_thread = threading.Thread(target=download_task, daemon=True)
            download_thread.start()
            
            # Update loading screen while downloading
            menu.update_loading_loop("Downloading audio...", lambda: download_complete)
            
            if error:
                print(error)
                print("Returning to menu...")
                # Reset menu state
                menu.showing_loading = False
                menu.showing_url_input = False
                menu.url_input_text = ""
                menu.search_results = []
                menu.selected_video_index = -1
                continue
            
            # Start beatmap generation in background thread
            beatmap_thread = threading.Thread(target=beatmap_task, daemon=True)
            beatmap_thread.start()
            
            # Update loading screen while generating beatmap
            menu.update_loading_loop("Generating beatmap...", lambda: beatmap_complete)
            
            if error:
                print(error)
                print("Returning to menu...")
                # Reset menu state
                menu.showing_loading = False
                menu.showing_url_input = False
                menu.url_input_text = ""
                menu.search_results = []
                menu.selected_video_index = -1
                continue
            
            # Game loop for retries
            while True:
                print("Starting game...")
                game = RhythmGame(beatmap, audio)
                result = game.run()
                
                if result == "retry":
                    print("Retrying...")
                    continue
                else:
                    # User chose quit or closed the window, return to main menu
                    print("Returning to main menu...")
                    # Reset menu state for next time
                    menu.showing_loading = False
                    menu.showing_url_input = False
                    menu.url_input_text = ""
                    menu.search_results = []
                    menu.selected_video_index = -1
                    break

if __name__ == "__main__":
    main()
