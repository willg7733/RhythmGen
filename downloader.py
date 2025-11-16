from __future__ import annotations
import shutil
import tempfile
from pathlib import Path
from typing import Any, Dict, TypedDict

import yt_dlp
from yt_dlp.utils import DownloadError
import soundfile as sf
import numpy as np

INTRO_SILENCE_DURATION = 2.0


class DownloadedMedia(TypedDict):
    audio_path: str
    video_path: str
    intro_silence: float


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


def _download_audio_file(url: str, tmpdir: Path) -> Path:
    out_template = str(tmpdir / "audio.%(ext)s")

    ydl_opts: Dict[str, Any] = {
        "format": "bestaudio/best",
        "outtmpl": out_template,
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "wav",
            }
        ],
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:  # type: ignore[arg-type]
        ydl.download([url])

    wav_files = list(tmpdir.glob("audio*.wav")) + list(tmpdir.glob("*.wav"))
    if not wav_files:
        candidates = list(tmpdir.iterdir())
        if not candidates:
            raise RuntimeError("yt-dlp finished but no audio output file was found in temporary directory.")
        wav_files = [p for p in candidates if p.suffix.lower() == ".wav"] or [candidates[0]]

    return wav_files[0]


def _download_video_file(url: str, tmpdir: Path) -> Path:
    out_template = str(tmpdir / "video.%(ext)s")

    avc_preferred = (
        "bestvideo[ext=mp4][height<=720][vcodec^=avc1]+bestaudio[ext=m4a]"
    )
    h264_fallback = (
        "bestvideo[ext=mp4][height<=720][vcodec~='.(264|h264)']+bestaudio[ext=m4a]"
    )
    generic_mp4 = "bestvideo[ext=mp4][height<=720]+bestaudio[ext=m4a]"
    direct_best = "best[ext=mp4][height<=720]/best[ext=mp4]/best"

    ydl_opts: Dict[str, Any] = {
        "format": f"{avc_preferred}/{h264_fallback}/{generic_mp4}/{direct_best}",
        "merge_output_format": "mp4",
        "outtmpl": out_template,
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:  # type: ignore[arg-type]
        ydl.download([url])

    video_files = list(tmpdir.glob("video*.mp4")) + list(tmpdir.glob("*.mp4"))
    if not video_files:
        candidates = list(tmpdir.iterdir())
        if not candidates:
            raise RuntimeError("yt-dlp finished but no video output file was found in temporary directory.")
        video_files = [p for p in candidates if p.suffix.lower() in (".mp4", ".mkv", ".webm")]
        if not video_files:
            video_files = [candidates[0]]

    return video_files[0]


def download_media(
    url: str,
    audio_output_path: str = "audio.wav",
    video_output_path: str = "video.mp4",
) -> DownloadedMedia:
    """Download the song audio (with intro silence) plus the accompanying video."""

    if not url or not isinstance(url, str):
        raise ValueError("A valid YouTube URL (string) must be provided.")

    if not _check_ffmpeg_exists():
        raise RuntimeError(
            "ffmpeg not found on PATH. Install ffmpeg (e.g. `sudo apt install ffmpeg` "
            "or `brew install ffmpeg`) before running this script."
        )

    audio_out_path = Path(audio_output_path).resolve()
    video_out_path = Path(video_output_path).resolve()
    audio_out_path.parent.mkdir(parents=True, exist_ok=True)
    video_out_path.parent.mkdir(parents=True, exist_ok=True)

    tmpdir = Path(tempfile.mkdtemp(prefix="yt_media_"))
    try:
        downloaded_wav = _download_audio_file(url, tmpdir)

        if audio_out_path.exists():
            audio_out_path.unlink()
        shutil.move(str(downloaded_wav), str(audio_out_path))

        _add_silence_to_start(str(audio_out_path), silence_duration=INTRO_SILENCE_DURATION)

        downloaded_video = _download_video_file(url, tmpdir)

        if video_out_path.exists():
            video_out_path.unlink()
        shutil.move(str(downloaded_video), str(video_out_path))

        return {
            "audio_path": str(audio_out_path),
            "video_path": str(video_out_path),
            "intro_silence": INTRO_SILENCE_DURATION,
        }
    except DownloadError as e:
        raise RuntimeError(f"yt-dlp failed to download the media: {e}") from e
    except Exception as e:
        raise RuntimeError(f"Failed to download/convert media: {e}") from e
    finally:
        try:
            if tmpdir.exists():
                shutil.rmtree(tmpdir)
        except Exception:
            pass


def download_audio(url: str, output_path: str = "audio.wav") -> str:
    """Backward-compatible helper that returns only the audio path."""
    result = download_media(url, audio_output_path=output_path)
    return result["audio_path"]

if __name__ == "__main__":
    url = input("YouTube URL: ").strip()
    try:
        result = download_media(url, audio_output_path="audio.wav", video_output_path="video.mp4")
        print("Successfully downloaded media:")
        print(f"  Audio: {result['audio_path']}")
        print(f"  Video: {result['video_path']}")
    except Exception as exc:
        print("Error:", exc)
        print("\nHints: make sure the URL is a valid YouTube watch/share link and ffmpeg is installed.")