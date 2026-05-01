from pydantic import BaseModel, Field


class TtsPreviewRequest(BaseModel):
    """Озвучка до создания нейродруга: голос + манера пресета должны совпадать с каталогом."""

    gender_style: str | None = Field(
        None,
        description="Как у пресета: masculine / feminine / neutral — для проверки допустимости голоса.",
    )
    tts_voice: str = Field(..., min_length=1, max_length=32)
    text: str = Field(
        default="Так звучит выбранный голос. Короткая фраза для проверки.",
        min_length=1,
        max_length=500,
    )


class TtsVoiceItem(BaseModel):
    id: str = Field(..., min_length=1, max_length=32)
    label: str = Field(..., min_length=1, max_length=500)
    gender: str = Field(..., min_length=1, max_length=32)
