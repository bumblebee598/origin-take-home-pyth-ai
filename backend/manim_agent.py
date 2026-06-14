import os
import json
import time
import asyncio
import subprocess
from pathlib import Path
from typing import Callable

from claude_agent_sdk import query, ClaudeAgentOptions
from dotenv import load_dotenv

from scene_llm import TimedBeat, VideoPlan, voice_beats

AGENT_MODEL = "claude-opus-4-8"
BACKEND_DIR = Path(__file__).resolve().parent
load_dotenv(Path(__file__).with_name(".env"))
ProgressCallback = Callable[[str, dict | None], None]

MANIM_SYSTEM = """\
You render ONE beat of an explainer video into a silent Manim mp4.
You may consult the `manimce-best-practices` skill for ManimCE rules and visual style,
but be efficient: skim at most one or two rule files. Do NOT read every rule or example
file. Prioritize writing scene.py and rendering quickly.

1. Work only in the beat directory provided by the user.
2. Improve the starter scene.py there as a class BeatScene(Scene).
3. Render from that beat directory: `manim -ql scene.py BeatScene` with Bash.
4. Read any traceback, fix scene.py, and re-render until an mp4 exists under media/.
5. Time the scene to about the target duration.
Stop as soon as the render succeeds. Do not keep polishing after an mp4 exists.
"""


def _beat_prompt(tb: TimedBeat) -> str:
    return (
        "Render one beat.\n\n"
        "Beat directory:\n"
        f"{Path(tb.audio_path).resolve().parents[1] / tb.beat.id}\n\n"
        f"Beat spec:\n{tb.beat.model_dump_json(indent=2)}\n\n"
        f"Target duration: {tb.duration:.2f} seconds.\n\n"
        "A starter scene.py already exists in the beat directory. Replace it with a richer Manim scene, "
        "then run Manim from that directory until media/videos contains an mp4."
    )


def _summarize(message):
    out = {"type": type(message).__name__}
    content = getattr(message, "content", None)
    if isinstance(content, list):
        blocks = []
        for b in content:
            entry = {"block": type(b).__name__}
            if hasattr(b, "text"):
                entry["text"] = b.text
            if hasattr(b, "name"):
                entry["tool"] = b.name
                entry["input"] = getattr(b, "input", None)
            if hasattr(b, "content"):
                entry["result"] = str(getattr(b, "content", ""))[:2000]
            blocks.append(entry)
        out["blocks"] = blocks
    if hasattr(message, "result"):
        out["result"] = message.result
    return out


def _ensure_anthropic_env() -> str:
    api_key = os.getenv("anthropic_api_key")
    if not api_key:
        raise RuntimeError("Missing Anthropic API key. Set ANTHROPIC_API_KEY in backend/.env.")

    # Claude Agent SDK reads the standard Anthropic environment variable.
    os.environ["ANTHROPIC_API_KEY"] = api_key
    return api_key


def _write_seed_scene(tb: TimedBeat, workdir: Path) -> None:
    title = json.dumps(tb.beat.title)
    labels = json.dumps(tb.beat.on_screen_labels[:4])
    narration = json.dumps(tb.beat.narration[:220])
    scene = f'''from manim import *


class BeatScene(Scene):
    def construct(self):
        self.camera.background_color = "#111111"
        title = Text({title}, font_size=48, weight=BOLD).to_edge(UP)
        summary = Text({narration}, font_size=24, line_spacing=0.8).scale_to_fit_width(11).next_to(title, DOWN, buff=0.6)
        labels = VGroup(*[
            Text(label, font_size=26).set_color(YELLOW)
            for label in {labels}
        ]).arrange(DOWN, aligned_edge=LEFT, buff=0.28).next_to(summary, DOWN, buff=0.6)

        self.play(Write(title))
        self.play(FadeIn(summary, shift=UP * 0.2))
        if len(labels) > 0:
            self.play(LaggedStart(*[FadeIn(label, shift=RIGHT * 0.2) for label in labels], lag_ratio=0.2))
        self.wait(1)
'''
    (workdir / "scene.py").write_text(scene)


async def render_beat(
    tb: TimedBeat,
    workdir: str,
    progress: ProgressCallback | None = None,
) -> str:
    api_key = _ensure_anthropic_env()
    workdir_path = Path(workdir).resolve()
    workdir_path.mkdir(parents=True, exist_ok=True)
    _write_seed_scene(tb, workdir_path)
    if progress:
        progress(
            f"Rendering {tb.beat.id}: {tb.beat.title}",
            {"beat_id": tb.beat.id, "workdir": str(workdir_path), "scene": str(workdir_path / "scene.py")},
        )
    options = ClaudeAgentOptions(
        system_prompt=MANIM_SYSTEM,
        allowed_tools=["Read", "Write", "Edit", "Bash", "Skill"],
        setting_sources=["user"],
        skills=["manimce-best-practices"],
        permission_mode="bypassPermissions",
        cwd=BACKEND_DIR,
        add_dirs=[workdir_path],
        env={"ANTHROPIC_API_KEY": api_key},
        max_turns=25,
        model=AGENT_MODEL,
    )

    trace = []
    async for message in query(prompt=_beat_prompt(tb), options=options):
        trace.append(_summarize(message))
        Path(workdir_path, "trace.json").write_text(json.dumps(trace, indent=2, default=str))

    mp4 = next(workdir_path.glob("media/videos/**/*.mp4"), None)
    if mp4 is None:
        raise RuntimeError(f"{tb.beat.id}: agent produced no mp4")
    if progress:
        progress(f"Finished {tb.beat.id}", {"beat_id": tb.beat.id, "mp4": str(mp4)})
    return str(mp4)


def _duration(path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
        check=True, capture_output=True, text=True,
    )
    return float(out.stdout.strip())


# Tail of frozen frame kept after narration ends, so the voice is never clipped.
_TAIL_PADDING = 0.4


def _mux(video, audio, out):
    # Match clip length to the longer of animation/narration so the voice is
    # never cut off when the animation finishes first. The last video frame is
    # frozen to cover any remaining narration, and audio is padded with silence
    # if the animation runs longer than the voice-over.
    target = max(_duration(video), _duration(audio)) + _TAIL_PADDING
    subprocess.run(
        ["ffmpeg", "-y", "-i", video, "-i", audio,
         "-filter_complex",
         f"[0:v]tpad=stop_mode=clone:stop_duration={target:.3f}[v];[1:a]apad[a]",
         "-map", "[v]", "-map", "[a]",
         "-t", f"{target:.3f}",
         "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac",
         out],
        check=True, capture_output=True,
    )


def _concat(clips, out):
    listfile = Path(out).with_suffix(".txt")
    listfile.write_text("".join(f"file '{os.path.abspath(c)}'\n" for c in clips))
    subprocess.run(
        ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(listfile), "-c", "copy", out],
        check=True, capture_output=True,
    )


async def render_video_plan(
    plan: VideoPlan | dict,
    workroot: str = "work",
    concurrency: int = 2,
    progress: ProgressCallback | None = None,
) -> str:
    if isinstance(plan, dict):
        plan = VideoPlan.model_validate(plan)

    Path(workroot).mkdir(parents=True, exist_ok=True)
    Path(workroot, "plan.json").write_text(json.dumps(plan.model_dump(), indent=2))
    if progress:
        progress("Generating narration audio", {"beat_count": len(plan.beats)})
    timed = voice_beats(plan, out_dir=os.path.join(workroot, "audio"))

    sem = asyncio.Semaphore(concurrency)
    total = len(timed)
    completed = 0
    progress_lock = asyncio.Lock()
    timings: dict[str, float] = {}
    beat_timeout = float(os.getenv("BEAT_TIMEOUT_SECONDS", "900"))
    overall_start = time.perf_counter()

    def _persist_timings() -> None:
        Path(workroot, "timings.json").write_text(json.dumps(timings, indent=2))

    async def one(tb: TimedBeat) -> str:
        nonlocal completed
        start = time.perf_counter()
        async with sem:
            try:
                silent = await asyncio.wait_for(
                    render_beat(tb, os.path.join(workroot, tb.beat.id), progress),
                    timeout=beat_timeout,
                )
            except asyncio.TimeoutError as exc:
                raise RuntimeError(
                    f"{tb.beat.id}: render timed out after {beat_timeout:.0f}s"
                ) from exc
        elapsed = time.perf_counter() - start
        async with progress_lock:
            completed += 1
            timings[tb.beat.id] = round(elapsed, 1)
            _persist_timings()
            if progress:
                progress(
                    f"Rendered {completed} of {total} scenes — {tb.beat.id} took {elapsed:.1f}s",
                    {
                        "completed": completed,
                        "total": total,
                        "beat_id": tb.beat.id,
                        "seconds": round(elapsed, 1),
                    },
                )
        return silent

    if progress:
        progress(
            f"Rendering {total} scenes in parallel",
            {"beat_count": total, "concurrency": concurrency},
        )
    silents = await asyncio.gather(*(one(tb) for tb in timed))

    clips = []
    for tb, silent in zip(timed, silents):
        av = os.path.join(workroot, f"{tb.beat.id}_av.mp4")
        if progress:
            progress(f"Adding narration to {tb.beat.id}", {"beat_id": tb.beat.id})
        _mux(silent, tb.audio_path, av)
        clips.append(av)

    final = os.path.join(workroot, "final.mp4")
    if progress:
        progress("Combining final video", {"clip_count": len(clips)})
    _concat(clips, final)

    timings["_total"] = round(time.perf_counter() - overall_start, 1)
    _persist_timings()
    if progress:
        progress(
            f"Render complete in {timings['_total']:.1f}s",
            {"video_path": final, "timings": timings},
        )
    return final


if __name__ == "__main__":
    import sys
    plan_path = Path(sys.argv[1])
    print("done:", asyncio.run(render_video_plan(json.loads(plan_path.read_text()))))