from __future__ import annotations
import shutil
import tempfile
from pathlib import Path
import yt_dlp
import soundfile as sf
import numpy as np

def _check_ffmpeg_exists() -> bool:
    """Return True if ffmpeg is available on PATH (yt-dlp needs it for conversion)."""
    return shutil.which("ffmpeg") is not None

def _add_silence_to_start(audio_path: str, silence_duration: float = 3.0) -> None:
    """
    Add silence to the start of an audio file.
    - audio_path: path to the WAV file to modify
    - silence_duration: duration of silence in seconds (default 3.0)
    Modifies the file in place.
    """
    # Read the audio file
    audio_data, sample_rate = sf.read(audio_path)
    
    # Calculate number of silent samples needed
    silence_samples = int(silence_duration * sample_rate)
    
    # Create silence array with same number of channels as audio
    if audio_data.ndim == 1:
        # Mono audio
        silence = np.zeros(silence_samples, dtype=audio_data.dtype)
    else:
        # Stereo or multi-channel audio
        silence = np.zeros((silence_samples, audio_data.shape[1]), dtype=audio_data.dtype)
    
    # Concatenate silence before audio
    audio_with_silence = np.concatenate([silence, audio_data])
    
    # Write back to the same file
    sf.write(audio_path, audio_with_silence, sample_rate)

def download_audio(url: str, output_path: str = "audio.wav") -> str: # <-- CHANGED
    """
    Download audio from YouTube and convert to WAV using yt-dlp + ffmpeg.
    - url: YouTube watch/share URL
    - output_path: final path (default "audio.wav")
    Returns: final path as string.
    Raises: RuntimeError on failure with helpful message.
    """
    if not url or not isinstance(url, str):
        raise ValueError("A valid YouTube URL (string) must be provided.")

    if not _check_ffmpeg_exists():
        raise RuntimeError(
            "ffmpeg not found on PATH. Install ffmpeg (e.g. `sudo apt install ffmpeg` "
            "or `brew install ffmpeg`) before running this script."
        )

    out_path = Path(output_path).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    tmpdir = Path(tempfile.mkdtemp(prefix="yt_audio_"))
    try:
        out_template = str(tmpdir / "download.%(ext)s")

        ydl_opts = {
            "format": "bestaudio/best",
            "outtmpl": out_template,
            "postprocessors": [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "wav",
                    # "preferredquality" removed (not needed for wav)
                }
            ],
            "noplaylist": True,
            "quiet": True,
            "no_warnings": True,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        # After successful download+conversion, find the wav in tmpdir
        wav_files = list(tmpdir.glob("download*.wav")) + list(tmpdir.glob("*.wav"))
        if not wav_files:
            candidates = list(tmpdir.iterdir())
            if not candidates:
                raise RuntimeError("yt-dlp finished but no output file was found in temporary directory.")
            # prefer a wav-like file
            wav_files = [p for p in candidates if p.suffix.lower() == ".wav"]
            if not wav_files:
                wav_files = [candidates[0]] # fallback

        downloaded_wav = wav_files[0]
        
        # Move to desired final path (overwrite if exists)
        if out_path.exists():
            out_path.unlink()
        shutil.move(str(downloaded_wav), str(out_path)) # <-- CHANGED
        
        # Add 2 seconds of silence to the start of the audio
        _add_silence_to_start(str(out_path), silence_duration=2.0)

        return str(out_path)
    except yt_dlp.utils.DownloadError as e:
        raise RuntimeError(f"yt-dlp failed to download the video: {e}") from e
    except Exception as e:
        raise RuntimeError(f"Failed to download/convert audio: {e}") from e
    finally:
        try:
            if tmpdir.exists():
                shutil.rmtree(tmpdir)
        except Exception:
            pass

if __name__ == "__main__":
    url = input("YouTube URL: ").strip()
    try:
        result = download_audio(url, output_path="audio.wav") 
        print(f"Successfully downloaded and saved to:\n{result}")
    except Exception as exc:
        print("Error:", exc)
        print("\nHints: make sure the URL is a valid YouTube watch/share link and ffmpeg is installed.")