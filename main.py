from downloader import download_audio
from beatmap import generate_beatmap
from game import RhythmGame

def main():
    url = input("Paste YouTube link: ")
    audio = download_audio(url, "audio.mp3")

    print("Generating beatmap...")
    beatmap = generate_beatmap(audio)

    print("Starting game...")
    game = RhythmGame(beatmap, audio)
    game.run()

if __name__ == "__main__":
    main()

