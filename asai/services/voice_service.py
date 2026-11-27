import logging
from typing import Dict, Any, Optional

logger = logging.getLogger("asai.voice")


class VoiceService:
    """
    Handles speech-to-text transcription and text-to-speech synthesis.
    """

    @staticmethod
    def transcribe_audio(audio_path: str, language: str = "en") -> Dict[str, Any]:
        """
        Transcribe audio recording using faster-whisper or whisper if installed on host.
        """
        # Try local whisper
        try:
            from faster_whisper import WhisperModel
            model = WhisperModel("base", device="auto", compute_type="int8")
            segments, info = model.transcribe(audio_path, language=language)
            text = " ".join([segment.text for segment in segments]).strip()
            return {
                "status": "success",
                "text": text,
                "language": info.language,
                "duration": info.duration
            }
        except ImportError:
            pass

        try:
            import whisper
            model = whisper.load_model("base")
            result = model.transcribe(audio_path)
            return {
                "status": "success",
                "text": result.get("text", "").strip(),
                "language": result.get("language", language)
            }
        except ImportError:
            pass

        return {
            "status": "pending_worker",
            "text": "Audio captured successfully. Whisper worker is required for automatic offline transcription.",
            "message": "Install faster-whisper or whisper on your AI node to enable offline transcription."
        }


voice_service = VoiceService()
