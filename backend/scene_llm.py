import os
from enum import Enum
from pathlib import Path

from anthropic import Anthropic
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from gtts import gTTS
from mutagen.mp3 import MP3

MODEL = "claude-opus-4-8"
load_dotenv(Path(__file__).with_name(".env"))


class VisualKind(str, Enum):
    title_card = "title_card"
    equation = "equation"
    graph = "graph"
    bullet_reveal = "bullet_reveal"


class Beat(BaseModel):
    id: str = Field(description="Sequential id, e.g. 'beat_01'.")
    title: str = Field(description="Short on-screen heading, max ~6 words.")
    narration: str = Field(description="Spoken script, 2-4 sentences of plain English. "
                                       "No symbols, no LaTeX, no markdown. Say math in words.")
    visual_kind: VisualKind = Field(description="Which visual to render.")
    visual_description: str = Field(description="Concrete description of what the animation shows "
                                                "and how it progresses, for an engineer to build in Manim.")
    equations_latex: list[str] = Field(description="LaTeX for displayed equations. Empty list if none.")
    on_screen_labels: list[str] = Field(description="Short text labels shown on screen. Empty list if none.")


class VideoPlan(BaseModel):
    paper_title: str
    one_line_summary: str
    beats: list[Beat]


class TimedBeat(BaseModel):
    beat: Beat
    audio_path: str
    duration: float


PLANNER_SYSTEM = """\
You plan short animated explainer videos in the spirit of 3Blue1Brown: intuition first, then formalize.
Given a research paper, produce a plan for a 3-4 minute video a general technical audience can follow.

- 6-9 beats, ~180-240 seconds total, one idea per beat.
- Arc: problem -> why it's hard -> the key idea -> how it works -> the result -> why it matters.
- narration is SPOKEN. Plain talk, no symbols or LaTeX. Put displayed math in equations_latex.
- Pick the visual_kind that makes each idea concrete. Be faithful to the paper; invent nothing.
- visual_description must be buildable in Manim without re-reading the paper.
"""


def plan_video(paper_text: str) -> VideoPlan:
    api_key = os.getenv("ANTHROPIC_API_KEY") 
    if not api_key:
        raise RuntimeError("Missing Anthropic API key. Set ANTHROPIC_API_KEY in backend/.env.")

    client = Anthropic(api_key=api_key)
    resp = client.messages.parse(
        model=MODEL,
        max_tokens=8000,
        system=PLANNER_SYSTEM,
        messages=[{"role": "user", "content": f"Paper:\n\n{paper_text}\n\nProduce the plan."}],
        output_format=VideoPlan,
    )
    if resp.stop_reason in ("refusal", "max_tokens"):
        raise RuntimeError(f"plan failed: {resp.stop_reason}")
    return resp.parsed_output


def voice_beats(plan: VideoPlan, out_dir: str = "audio") -> list[TimedBeat]:
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    timed = []
    for beat in plan.beats:
        path = os.path.join(out_dir, f"{beat.id}.mp3")
        gTTS(text=beat.narration).save(path)
        duration = MP3(path).info.length
        timed.append(TimedBeat(beat=beat, audio_path=path, duration=duration))
    return timed


def build(paper_text: str, out_dir: str = "audio") -> tuple[VideoPlan, list[TimedBeat]]:
    plan = plan_video(paper_text)
    timed = voice_beats(plan, out_dir)
    return plan, timed


if __name__ == "__main__":
    import sys, json
    from ingest_paper import prepare_paper

    plan, timed = build(prepare_paper(sys.argv[1]))
    print(json.dumps(plan.model_dump(), indent=2))
    for t in timed:
        print(f"{t.beat.id}: {t.duration:.1f}s -> {t.audio_path}")