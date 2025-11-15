from pytube import YouTube
import os

def download_audio(url, output_path="audio.mp3"):
    yt = YouTube(url)
    stream = yt.streams.filter(only_audio=True).first()
    temp_file = stream.download(filename="temp_audio")
    os.rename(temp_file, output_path)
    return output_path

if __name__ == "__main__":
    print(download_audio(input("YouTube URL: ")))

