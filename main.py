from downloader import download_audio
from beatmap import generate_beatmap
from game import RhythmGame
from menu import MainMenu
import sys
import pygame

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
            
            # Download audio with loading screen
            menu.update_loading("Downloading audio...")
            
            print("Downloading audio...")
            try:
                audio = download_audio(url, "audio.mp3")
            except Exception as e:
                print(f"Error downloading audio: {e}")
                print("Returning to menu...")
                # Reset menu state
                menu.showing_loading = False
                menu.showing_url_input = False
                menu.url_input_text = ""
                menu.search_results = []
                menu.selected_video_index = -1
                continue
            
            # Generate beatmap with loading screen
            menu.update_loading("Generating beatmap...")
            
            print("Generating beatmap...")
            try:
                beatmap = generate_beatmap(audio)
            except Exception as e:
                print(f"Error generating beatmap: {e}")
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
