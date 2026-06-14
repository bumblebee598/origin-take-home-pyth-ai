import { useEffect, useMemo, useRef, useState } from "react";
import "./App.css";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";

const ANALYZING_STEPS = [
  "Reading your paper",
  "Extracting the core ideas",
  "Identifying key equations",
  "Storyboarding the scenes",
  "Finalizing the video plan",
];

function BrandMark() {
  return (
    <div className="brand">
      <span className="brand-logo">
        Pyth<span className="brand-logo-ai">AI</span>
      </span>
      <span className="brand-tag">turn paper 2 vid</span>
    </div>
  );
}

function UploadView({ error, fileName, fileSize, isIngesting, onFileChange, onSubmit }) {
  return (
    <section className="hero-grid">
      <div className="hero-copy">
        <p className="eyebrow">Pyth AI</p>
        <h1>Turn dense research into cinematic explainers.</h1>
        <p className="description">
          Upload a paper and transform its ideas, equations, graphs, and
          findings into a clear visual story your audience can understand.
        </p>

        <div className="signal-row" aria-label="Pyth AI workflow">
          <span>Read</span>
          <span>Storyboard</span>
          <span>Animate</span>
        </div>
      </div>

      <form className="upload-card" onSubmit={onSubmit}>
        <div className="card-header">
          <span className="status-dot" />
          <p>Research paper intake</p>
        </div>

        <label className="drop-zone">
          <input accept="application/pdf" type="file" onChange={onFileChange} />
          <span className="drop-title">{fileName || "Drop in your PDF"}</span>
          <span className="drop-meta">
            {fileName
              ? `${fileSize} ready to analyze`
              : "Upload a research paper to begin creating your explainer."}
          </span>
        </label>

        <button className="primary-button" disabled={isIngesting} type="submit">
          {isIngesting ? "Analyzing paper..." : "Analyze paper"}
        </button>

        {error && <p className="message error-message">{error}</p>}
      </form>
    </section>
  );
}

function AnalyzingView({ fileName }) {
  const [stepIndex, setStepIndex] = useState(0);

  useEffect(() => {
    const id = setInterval(() => {
      setStepIndex((index) => Math.min(index + 1, ANALYZING_STEPS.length - 1));
    }, 2200);
    return () => clearInterval(id);
  }, []);

  return (
    <section className="analyzing-view">
      <div className="analyzing-orb">
        <span className="orb-ring" />
        <span className="orb-ring orb-ring-2" />
        <span className="orb-core" />
      </div>

      <p className="eyebrow">Analyzing</p>
      <h2 className="analyzing-step">{ANALYZING_STEPS[stepIndex]}…</h2>
      {fileName && <p className="analyzing-file">{fileName}</p>}

      <div className="step-track">
        {ANALYZING_STEPS.map((step, index) => (
          <span
            key={step}
            className={`step-pill ${index <= stepIndex ? "is-active" : ""}`}
          >
            {step}
          </span>
        ))}
      </div>
    </section>
  );
}

function BeatCard({ beat, index }) {
  return (
    <article className="beat-card">
      <div className="beat-kicker">
        <span>{String(index + 1).padStart(2, "0")}</span>
        <span>{beat.visual_kind?.replaceAll("_", " ")}</span>
      </div>

      <h3>{beat.title}</h3>
      <p className="beat-narration">{beat.narration}</p>

      <div className="beat-detail">
        <p className="detail-label">Visual direction</p>
        <p>{beat.visual_description}</p>
      </div>

      {beat.equations_latex?.length > 0 && (
        <div className="beat-detail">
          <p className="detail-label">Equations</p>
          <div className="equation-list">
            {beat.equations_latex.map((equation) => (
              <code key={equation}>{equation}</code>
            ))}
          </div>
        </div>
      )}

      {beat.on_screen_labels?.length > 0 && (
        <div className="label-list">
          {beat.on_screen_labels.map((label) => (
            <span key={label}>{label}</span>
          ))}
        </div>
      )}
    </article>
  );
}

function RenderProgress({ renderStatus }) {
  const completed = renderStatus?.details?.completed;
  const total = renderStatus?.details?.total;
  const hasBar = Number.isFinite(completed) && Number.isFinite(total) && total > 0;
  const percent = hasBar ? Math.round((completed / total) * 100) : null;

  return (
    <div className="render-progress">
      <div className="render-progress-head">
        <span className="render-spinner" />
        <p>{renderStatus?.message || "Rendering your video…"}</p>
      </div>
      {hasBar && (
        <>
          <div className="progress-track">
            <div className="progress-fill" style={{ width: `${percent}%` }} />
          </div>
          <p className="progress-meta">
            {completed} of {total} scenes · {percent}%
          </p>
        </>
      )}
    </div>
  );
}

function PlanView({ error, isRendering, onRender, plan, renderStatus }) {
  return (
    <section className="plan-view">
      <div className="plan-header">
        <p className="eyebrow">Video plan</p>
        <h2>{plan.paper_title}</h2>
        <p className="plan-summary">{plan.one_line_summary}</p>
      </div>

      <div className="render-panel">
        <div>
          <p className="eyebrow">Final step</p>
          <h3>Create the explainer video.</h3>
          <p>
            The storyboard is ready. Generate the animated video from this plan
            when you are ready.
          </p>
        </div>
        {!isRendering && (
          <button className="primary-button render-button" onClick={onRender} type="button">
            Render video
          </button>
        )}
      </div>

      {isRendering && <RenderProgress renderStatus={renderStatus} />}
      {error && <p className="message error-message">{error}</p>}

      <div className="beat-list">
        {plan.beats?.map((beat, index) => (
          <BeatCard beat={beat} index={index} key={beat.id} />
        ))}
      </div>
    </section>
  );
}

function VideoView({ plan, videoUrl }) {
  return (
    <section className="video-view">
      <aside className="video-sidebar">
        <p className="eyebrow">Video plan</p>
        <h3 className="sidebar-title">{plan.paper_title}</h3>
        <p className="sidebar-summary">{plan.one_line_summary}</p>

        <ol className="sidebar-beats">
          {plan.beats?.map((beat, index) => (
            <li className="sidebar-beat" key={beat.id}>
              <span className="sidebar-beat-index">
                {String(index + 1).padStart(2, "0")}
              </span>
              <div>
                <p className="sidebar-beat-title">{beat.title}</p>
                <p className="sidebar-beat-kind">
                  {beat.visual_kind?.replaceAll("_", " ")}
                </p>
              </div>
            </li>
          ))}
        </ol>
      </aside>

      <div className="video-stage">
        <p className="eyebrow">Your explainer is ready</p>
        <h2 className="video-title">{plan.paper_title}</h2>
        <div className="video-frame">
          <video controls autoPlay src={videoUrl} />
        </div>
        <a className="download-link" href={videoUrl} download>
          Download MP4
        </a>
      </div>
    </section>
  );
}

function App() {
  const [paperFile, setPaperFile] = useState(null);
  const [ingestedPaper, setIngestedPaper] = useState(null);
  const [isIngesting, setIsIngesting] = useState(false);
  const [isRendering, setIsRendering] = useState(false);
  const [renderResult, setRenderResult] = useState(null);
  const [renderStatus, setRenderStatus] = useState(null);
  const [error, setError] = useState("");
  const [view, setView] = useState("upload");
  const pollRef = useRef(false);

  const formattedFileSize = useMemo(() => {
    if (!paperFile) {
      return "";
    }
    return `${(paperFile.size / 1024 / 1024).toFixed(2)} MB`;
  }, [paperFile]);

  function resetToUpload() {
    pollRef.current = false;
    setPaperFile(null);
    setIngestedPaper(null);
    setIsRendering(false);
    setRenderResult(null);
    setRenderStatus(null);
    setError("");
    setView("upload");
  }

  function handleFileChange(event) {
    const nextFile = event.target.files?.[0] || null;
    setPaperFile(nextFile);
    setError("");
  }

  async function handleSubmit(event) {
    event.preventDefault();

    if (!paperFile) {
      setError("Choose a research paper PDF first.");
      return;
    }

    const formData = new FormData();
    formData.append("file", paperFile);

    setIsIngesting(true);
    setError("");
    setIngestedPaper(null);
    setRenderResult(null);
    setRenderStatus(null);

    try {
      const response = await fetch(`${API_BASE_URL}/papers/ingest`, {
        method: "POST",
        body: formData,
      });

      const payload = await response.json();

      if (!response.ok) {
        throw new Error(payload.detail || "Unable to ingest this paper.");
      }

      setIngestedPaper(payload);
      setView("plan");
    } catch (err) {
      setError(err.message);
    } finally {
      setIsIngesting(false);
    }
  }

  async function handleRender() {
    if (!ingestedPaper?.job_id) {
      setError("Analyze a paper before rendering.");
      return;
    }

    setIsRendering(true);
    setError("");
    setRenderResult(null);
    setRenderStatus({ status: "queued", message: "Render queued." });
    pollRef.current = true;

    try {
      const startResponse = await fetch(`${API_BASE_URL}/videos/render`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ job_id: ingestedPaper.job_id }),
      });

      const startPayload = await startResponse.json();

      if (!startResponse.ok) {
        throw new Error(startPayload.detail || "Unable to render this video.");
      }

      setRenderStatus(startPayload);

      for (let attempt = 0; attempt < 600 && pollRef.current; attempt += 1) {
        await new Promise((resolve) => {
          setTimeout(resolve, 2000);
        });

        const statusResponse = await fetch(
          `${API_BASE_URL}/videos/render/${ingestedPaper.job_id}`,
        );
        const statusPayload = await statusResponse.json();

        if (!statusResponse.ok) {
          throw new Error(statusPayload.detail || "Unable to check render progress.");
        }

        setRenderStatus(statusPayload);

        if (statusPayload.status === "completed") {
          setRenderResult({
            ...statusPayload,
            videoUrl: `${API_BASE_URL}${statusPayload.video_url}`,
          });
          setView("video");
          return;
        }

        if (statusPayload.status === "failed") {
          throw new Error(statusPayload.message || "Render failed.");
        }
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setIsRendering(false);
      pollRef.current = false;
    }
  }

  const screen = isIngesting ? "analyzing" : view;

  return (
    <main className="app-shell">
      <div className="ambient ambient-one" />
      <div className="ambient ambient-two" />

      <header className="top-bar">
        <BrandMark />
        {screen !== "upload" && screen !== "analyzing" && (
          <button className="ghost-button" onClick={resetToUpload} type="button">
            New paper
          </button>
        )}
      </header>

      {screen === "upload" && (
        <UploadView
          error={error}
          fileName={paperFile?.name || ""}
          fileSize={formattedFileSize}
          isIngesting={isIngesting}
          onFileChange={handleFileChange}
          onSubmit={handleSubmit}
        />
      )}

      {screen === "analyzing" && <AnalyzingView fileName={paperFile?.name || ""} />}

      {screen === "plan" && ingestedPaper?.video_plan && (
        <PlanView
          error={error}
          isRendering={isRendering}
          onRender={handleRender}
          plan={ingestedPaper.video_plan}
          renderStatus={renderStatus}
        />
      )}

      {screen === "video" && ingestedPaper?.video_plan && renderResult && (
        <VideoView plan={ingestedPaper.video_plan} videoUrl={renderResult.videoUrl} />
      )}
    </main>
  );
}

export default App;
