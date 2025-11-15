from __future__ import annotations
import os
import shutil
import tempfile
from pathlib import Path
import yt_dlp

def _check_ffmpeg_exists() -> bool:
    """Return True if ffmpeg is available on PATH (yt-dlp needs it for conversion)."""
    return shutil.which("ffmpeg") is not None

def download_audio(url: str, output_path: str = "audio.mp3") -> str:
    """
    Download audio from YouTube and convert to MP3 using yt-dlp + ffmpeg.
    - url: YouTube watch/share URL
    - output_path: final path (default "audio.mp3")
    Returns: final path as string.
    Raises: RuntimeError on failure with helpful message.
    """
    if not url or not isinstance(url, str):
        raise ValueError("A valid YouTube URL (string) must be provided.")

    # Ensure ffmpeg exists (yt-dlp uses it for postprocessing to mp3)
    if not _check_ffmpeg_exists():
        raise RuntimeError(
            "ffmpeg not found on PATH. Install ffmpeg (e.g. `sudo apt install ffmpeg` "
            "or `brew install ffmpeg`) before running this script."
        )

    out_path = Path(output_path).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    tmpdir = Path(tempfile.mkdtemp(prefix="yt_audio_"))
    try:
        # Temporary template ensures we don't accidentally overwrite files in project root
        out_template = str(tmpdir / "download.%(ext)s")

        ydl_opts = {
            # best available audio
            "format": "bestaudio/best",

            # write to temporary dir; yt-dlp will create download.<ext>
            "outtmpl": out_template,

            # convert to mp3 via ffmpeg after download
            "postprocessors": [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",  # kbps, change if you want different quality
                }
            ],

            "noplaylist": True,
            "quiet": True,       # set False if you want verbose output
            "no_warnings": True,
            # "restrictfilenames": True,  # uncomment if you need safe filenames
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # will raise on failure
            ydl.download([url])

        # After successful download+conversion, find the mp3 in tmpdir
        mp3_files = list(tmpdir.glob("download*.mp3")) + list(tmpdir.glob("*.mp3"))
        if not mp3_files:
            # if postprocessor changed name, try any file in tmpdir
            candidates = list(tmpdir.iterdir())
            if not candidates:
                raise RuntimeError("yt-dlp finished but no output file was found in temporary directory.")
            # prefer an mp3-like file even if extension missing
            mp3_files = [p for p in candidates if p.suffix.lower() == ".mp3"]
            if not mp3_files:
                # fallback: take first candidate
                mp3_files = [candidates[0]]

        downloaded_mp3 = mp3_files[0]
        # Move to desired final path (overwrite if exists)
        if out_path.exists():
            out_path.unlink()
        shutil.move(str(downloaded_mp3), str(out_path))

        return str(out_path)
    except yt_dlp.utils.DownloadError as e:
        raise RuntimeError(f"yt-dlp failed to download the video: {e}") from e
    except Exception as e:
        raise RuntimeError(f"Failed to download/convert audio: {e}") from e
    finally:
        # cleanup any remaining files/dir
        try:
            if tmpdir.exists():
                shutil.rmtree(tmpdir)
        except Exception:
            pass

if __name__ == "__main__":
    url = input("YouTube URL: ").strip()
    try:
        result = download_audio(url, output_path="audio.mp3")
        print(result)
    except Exception as exc:
        print("Error:", exc)
        # small friendly hint
        print("\nHints: make sure the URL is a valid YouTube watch/share link and ffmpeg is installed.")
