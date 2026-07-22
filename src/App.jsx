import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  Activity, AlertTriangle, ArrowRight, BookOpen, CheckCircle2, ChevronRight,
  Clock3, Cpu, Download, Eye, FileImage, FileJson, Film, Fingerprint, Gauge,
  HelpCircle, History, Image as ImageIcon, Info, Layers3, LockKeyhole,
  MonitorCheck, ScanLine, Server, Shield, ShieldAlert, ShieldCheck, Sparkles,
  Timer, Trash2, Upload, Video, Wand2, X, Zap,
} from 'lucide-react';
import {
  analyzeMedia, downloadJson, downloadReportCard, formatBytes, formatTime,
  getHealth, historyRecord, loadHistory, riskColor, saveHistory,
} from './lib';

const ACCEPT = {
  photo: 'image/jpeg,image/png,image/webp,image/bmp,image/tiff',
  video: 'video/mp4,video/quicktime,video/webm,video/x-matroska,video/x-msvideo,video/avi',
};
const LIMITS = { photo: 25 * 1024 * 1024, video: 150 * 1024 * 1024 };

function cx(...classes) {
  return classes.filter(Boolean).join(' ');
}

function StatusPill({ health }) {
  const online = Boolean(health?.ok);
  const modelReady = health?.model?.status === 'ready';
  return (
    <div className={cx('status-pill', online ? 'online' : 'offline')}>
      <span className="status-dot" />
      {online ? <Server size={15} /> : <ShieldAlert size={15} />}
      <span>{online ? (modelReady ? 'ML DETECTOR READY' : 'FORENSIC ENGINE READY') : 'BACKEND OFFLINE'}</span>
    </div>
  );
}

function HeroArtwork() {
  return (
    <div className="hero-art" aria-hidden="true">
      <svg viewBox="0 0 760 480" role="img">
        <defs>
          <linearGradient id="face" x1="0" x2="1">
            <stop stopColor="#c78f7f" />
            <stop offset=".48" stopColor="#765157" />
            <stop offset=".5" stopColor="#132d57" />
            <stop offset="1" stopColor="#54135f" />
          </linearGradient>
          <radialGradient id="cyanGlow">
            <stop stopColor="#22e7ff" stopOpacity=".8" />
            <stop offset="1" stopColor="#22e7ff" stopOpacity="0" />
          </radialGradient>
          <radialGradient id="pinkGlow">
            <stop stopColor="#ff2aa1" stopOpacity=".75" />
            <stop offset="1" stopColor="#ff2aa1" stopOpacity="0" />
          </radialGradient>
        </defs>
        <circle cx="365" cy="220" r="210" fill="url(#cyanGlow)" opacity=".28" />
        <circle cx="545" cy="250" r="180" fill="url(#pinkGlow)" opacity=".32" />
        <ellipse cx="385" cy="246" rx="145" ry="190" fill="url(#face)" />
        <path d="M385 56v382" stroke="#f5fbff" strokeOpacity=".7" strokeWidth="2" />
        <g fill="none" stroke="#4bedff" strokeWidth="2" opacity=".85">
          <path d="M385 92 292 170l23 112 70 98 70-98 23-112z" />
          <path d="m292 170 93 30 93-30M315 282l70-82 70 82M315 282l70 98 70-98" />
          <path d="M235 110h-80v60M535 85h105v60M540 390h120v-70" opacity=".55" />
        </g>
        <g fill="#4bedff">
          {[['315','210'],['350','185'],['385','200'],['420','185'],['455','210'],['385','258'],['340','315'],['430','315']].map(([x,y]) => <circle key={`${x}-${y}`} cx={x} cy={y} r="5" />)}
        </g>
        <g fill="#ff49bd">
          <circle cx="455" cy="210" r="7" /><circle cx="430" cy="315" r="7" /><circle cx="470" cy="265" r="5" />
        </g>
        <g transform="translate(510 120)">
          <rect width="205" height="112" rx="15" fill="#061022" stroke="#b63ee9" opacity=".9" />
          <path d="M18 78 50 49l29 15 38-37 66 48" fill="none" stroke="#ff4fbd" strokeWidth="3" />
          <text x="18" y="28" fill="#d9eaff" fontSize="13" fontFamily="monospace">FRAME ANOMALY</text>
        </g>
        <g transform="translate(60 285)">
          <rect width="225" height="125" rx="15" fill="#061022" stroke="#25dbff" opacity=".88" />
          <path d="M18 90h28l16-37 20 62 24-50 22 25h26l18-38 22 58 20-44 16 24" fill="none" stroke="#33e8ff" strokeWidth="3" />
          <text x="18" y="28" fill="#d9eaff" fontSize="13" fontFamily="monospace">TEMPORAL SIGNAL</text>
        </g>
      </svg>
      <div className="art-scanline" />
    </div>
  );
}

function Header({ health, openModal }) {
  return (
    <header className="topbar">
      <div className="brand-wrap">
        <div className="brand-mark"><Shield size={28} strokeWidth={2.4} /></div>
        <div>
          <div className="brand-title-row"><h1>VERISIGHT</h1><span>2.1</span></div>
          <p>AI, DEEPFAKE & FILTER DETECTION HUB</p>
        </div>
      </div>
      <div className="header-actions">
        <button onClick={() => openModal('guide')}><HelpCircle size={15} /> How it works</button>
        <button onClick={() => openModal('legal')}><LockKeyhole size={15} /> Privacy & terms</button>
        <StatusPill health={health} />
      </div>
    </header>
  );
}

function Hero({ onStart, openModal }) {
  const capabilities = [
    { icon: Eye, title: 'AI image detection', text: 'Model-assisted synthetic-pattern and image-forensics screening.' },
    { icon: Film, title: 'Deepfake video analysis', text: 'Adaptive frame sampling, peak timestamp and temporal instability.' },
    { icon: Layers3, title: 'Evidence heatmaps', text: 'Visual maps highlight unusual recompression and texture regions.' },
  ];
  return (
    <section className="hero">
      <div className="hero-copy">
        <span className="hero-kicker"><i /> TRUST THROUGH FORENSICS</span>
        <h2>See what the media<br /><em>may be hiding.</em></h2>
        <p>Screen photos and videos for AI generation, deepfake manipulation, heavy filters and editing artifacts—then inspect the evidence behind the score.</p>
        <div className="hero-actions">
          <button className="hero-primary" onClick={onStart}><ScanLine size={17} /> Start a real scan <ArrowRight size={16} /></button>
          <button className="hero-secondary" onClick={() => openModal('guide')}><BookOpen size={17} /> Understand results</button>
        </div>
        <div className="trust-row">
          <span><ShieldCheck size={15} /> Honest confidence labels</span>
          <span><LockKeyhole size={15} /> No permanent media library</span>
          <span><MonitorCheck size={15} /> Photo + video</span>
        </div>
      </div>
      <HeroArtwork />
      <div className="capability-strip">
        {capabilities.map(({ icon: Icon, title, text }) => (
          <article key={title}>
            <div className="cap-icon"><Icon size={20} /></div>
            <div><strong>{title}</strong><span>{text}</span></div>
          </article>
        ))}
      </div>
    </section>
  );
}

function ScanToggle({ value, onChange, disabled }) {
  return (
    <div className="scan-toggle">
      <button className={value === 'photo' ? 'active photo' : ''} onClick={() => onChange('photo')} disabled={disabled}><ImageIcon size={15} /> Photo</button>
      <button className={value === 'video' ? 'active video' : ''} onClick={() => onChange('video')} disabled={disabled}><Video size={15} /> AI video</button>
    </div>
  );
}

function Uploader({ type, setType, file, preview, onFile, onAnalyze, onClear, scanning, progress, error, online }) {
  const inputRef = useRef(null);
  const [dragging, setDragging] = useState(false);
  return (
    <section className="panel scanner-panel" id="scanner">
      <div className="panel-heading">
        <div><span className="eyebrow">ANALYSIS TERMINAL</span><h3>Upload media for a real scan</h3></div>
        <ScanToggle value={type} onChange={setType} disabled={scanning} />
      </div>
      <div
        className={cx('drop-zone', dragging && 'dragging', preview && 'has-preview')}
        onClick={() => !scanning && inputRef.current?.click()}
        onDragOver={(event) => { event.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={(event) => { event.preventDefault(); setDragging(false); onFile(event.dataTransfer.files?.[0]); }}
      >
        <input ref={inputRef} hidden type="file" accept={ACCEPT[type]} onChange={(event) => onFile(event.target.files?.[0])} />
        {preview ? (
          <div className="preview-stage">
            {type === 'photo' ? <img src={preview} alt="Selected upload" /> : <video src={preview} controls={!scanning} preload="metadata" />}
            <div className="preview-shade" />
            {scanning && <><div className="scan-beam" /><div className="scan-card"><Activity size={18} /><div><strong>{type === 'video' ? 'Sampling frames and temporal signals' : 'Running model and forensic checks'}</strong><span>{Math.round(progress)}% complete</span></div></div></>}
          </div>
        ) : (
          <div className="empty-upload">
            <div className="upload-icon"><Upload size={34} /></div>
            <h4>Drop a {type === 'video' ? 'video clip' : 'photo'} here</h4>
            <p>{type === 'video' ? 'MP4, MOV, WebM, MKV or AVI up to 150 MB' : 'JPEG, PNG, WebP, BMP or TIFF up to 25 MB'}</p>
            <button type="button"><Upload size={16} /> Choose file</button>
          </div>
        )}
      </div>
      {file && <div className="file-row"><div className="file-icon">{type === 'video' ? <Film size={19} /> : <FileImage size={19} />}</div><div><strong>{file.name}</strong><span>{formatBytes(file.size)} · processed for this request and discarded</span></div><button onClick={onClear} disabled={scanning} aria-label="Remove selected media"><X size={18} /></button></div>}
      {error && <div className="error-banner"><AlertTriangle size={17} /><span>{error}</span></div>}
      {!online && <div className="error-banner"><ShieldAlert size={17} /><span>The backend is offline. Start or deploy the API before scanning.</span></div>}
      <button className="analyze-button" onClick={onAnalyze} disabled={!file || scanning || !online}>{scanning ? <><Activity size={18} className="spin" /> Analyzing media…</> : <><Sparkles size={18} /> Run VeriSight scan</>}</button>
    </section>
  );
}

function ScoreRing({ score = 0 }) {
  const risk = 100 - score;
  return <div className="score-ring" style={{ '--score': score, '--ring': riskColor(risk) }}><div><strong>{score}%</strong><span>Authenticity</span></div></div>;
}

function ResultSummary({ result }) {
  if (!result) return <section className="panel results-empty"><div className="empty-orbit"><Fingerprint size={35} /></div><h3>Awaiting media</h3><p>Your authenticity score, detector signals, model status and evidence map will appear here.</p></section>;
  return (
    <section className="panel result-summary">
      <span className="eyebrow">DETAILED REPORT</span>
      <ScoreRing score={result.authenticity_score} />
      <div className={cx('verdict', `risk-${result.risk || 'mixed'}`)}><ShieldCheck size={19} /><div><strong>{result.verdict}</strong><span>{result.verdict_detail}</span></div></div>
      <div className="metric-grid">
        <div><span>Synthetic</span><strong>{result.synthetic_probability}%</strong></div>
        <div><span>Deepfake</span><strong>{result.deepfake_probability}%</strong></div>
        <div><span>Filters</span><strong>{result.filter_probability}%</strong></div>
        <div><span>Confidence</span><strong>{result.confidence}%</strong></div>
      </div>
      <div className="model-mode"><Cpu size={16} /><span>{result.model?.mode || 'Forensic engine'}</span><Info size={15} /></div>
      <div className="report-actions"><button onClick={() => downloadReportCard(result)}><Download size={15} /> Report card</button><button onClick={() => downloadJson(result)}><FileJson size={15} /> JSON</button></div>
    </section>
  );
}

function SignalPanel({ result }) {
  const signals = result?.signals || [];
  return (
    <section className="panel wide-panel">
      <div className="panel-heading compact"><div><span className="eyebrow">DETECTOR SIGNALS</span><h3>What shaped the result</h3></div><Gauge size={22} /></div>
      {signals.length ? <div className="signal-list">{signals.map((signal) => <div className="signal" key={signal.name}><div className="signal-head"><strong>{signal.name}</strong><span>{signal.score}%</span></div><div className="signal-track"><i style={{ width: `${signal.score}%`, background: riskColor(signal.score) }} /></div><p>{signal.detail}</p></div>)}</div> : <div className="soft-empty"><Wand2 size={24} /><p>Signal details populate after a scan.</p></div>}
    </section>
  );
}

function ExplanationPanel({ result }) {
  return (
    <section className="panel explanation-panel">
      <div className="panel-heading compact"><div><span className="eyebrow">PLAIN ENGLISH</span><h3>What this result means</h3></div><BookOpen size={21} /></div>
      {result ? <><p className="explanation-lead">{result.explanation}</p><div className="strongest"><span>Strongest indicators</span>{(result.strongest_signals || result.signals || []).slice(0, 3).map((item) => <div key={item.name}><CheckCircle2 size={16} /><p><strong>{item.name}</strong>{item.detail}</p></div>)}</div><div className="next-steps"><span>Responsible next steps</span>{(result.next_steps || []).map((step) => <p key={step}><ChevronRight size={15} />{step}</p>)}</div></> : <div className="soft-empty"><Info size={25} /><p>After a scan, VeriSight explains the score, confidence and safest next action without claiming certainty it does not have.</p></div>}
    </section>
  );
}

function EvidencePanel({ result }) {
  return (
    <section className="panel evidence-panel">
      <div className="panel-heading compact"><div><span className="eyebrow">FORENSIC EVIDENCE</span><h3>Suspicion heatmap</h3></div><Layers3 size={22} /></div>
      {result?.evidence_image ? <><div className="evidence-image"><img src={result.evidence_image} alt="Forensic evidence heatmap" /><div className="heat-scale"><span>More unusual</span><i /><span>Less</span></div></div><p className="panel-note">Bright areas show stronger local differences. They are clues, not proof of AI generation or malicious editing.</p></> : <div className="soft-empty evidence-placeholder"><ScanLine size={30} /><p>The heatmap will highlight unusual compression, texture and noise regions.</p></div>}
    </section>
  );
}

function VideoTimeline({ result }) {
  const frames = result?.video?.frames || [];
  if (!frames.length) return null;
  return (
    <section className="panel wide-panel timeline-panel">
      <div className="panel-heading compact"><div><span className="eyebrow">VIDEO TIMELINE</span><h3>Sampled frame risk</h3></div><div className="peak-time"><Timer size={16} /> Peak at {formatTime(result.video.peak_timestamp)}</div></div>
      <div className="timeline">{frames.map((frame, index) => <article key={`${frame.timestamp}-${index}`}><div className="frame-thumb">{frame.thumbnail ? <img src={frame.thumbnail} alt={`Sample at ${formatTime(frame.timestamp)}`} /> : <Film size={22} />}</div><strong style={{ color: riskColor(frame.score) }}>{frame.score}%</strong><span>{formatTime(frame.timestamp)}</span></article>)}</div>
      <p className="panel-note">VeriSight samples representative frames; it does not inspect every frame or synthetic audio.</p>
    </section>
  );
}

function PrivacyPanel() {
  return <section className="panel privacy-panel"><div className="privacy-icon"><LockKeyhole size={24} /></div><div><span className="eyebrow">PRIVACY FIRST</span><h3>No permanent media library</h3><p>Images are analyzed in memory. Videos use a temporary seekable file that is removed after the request. Scan summaries stay only in this browser unless you export them.</p></div></section>;
}

function HistoryPanel({ history, clearHistory }) {
  return (
    <section className="panel wide-panel history-panel">
      <div className="panel-heading compact"><div><span className="eyebrow">LOCAL HISTORY</span><h3>Recent scans on this device</h3></div>{history.length > 0 && <button className="clear-button" onClick={clearHistory}><Trash2 size={15} /> Clear</button>}</div>
      {history.length ? <div className="history-list">{history.map((item) => <article key={item.id}><div className="history-icon">{item.mediaType === 'video' ? <Film size={18} /> : <ImageIcon size={18} />}</div><div className="history-name"><strong>{item.filename}</strong><span><Clock3 size={12} /> {new Date(item.createdAt).toLocaleString()}</span></div><div className="history-score"><strong>{item.authenticity}%</strong><span>{item.verdict}</span></div></article>)}</div> : <div className="soft-empty"><History size={25} /><p>No scans saved on this browser yet.</p></div>}
    </section>
  );
}

function Modal({ view, onClose }) {
  if (!view) return null;
  const guide = view === 'guide';
  return <div className="modal-backdrop" onMouseDown={onClose}><section className="modal" onMouseDown={(event) => event.stopPropagation()}><button className="modal-close" onClick={onClose}><X size={20} /></button><span className="eyebrow">{guide ? 'HOW VERISIGHT WORKS' : 'PRIVACY, TERMS & RESPONSIBLE USE'}</span><h2>{guide ? 'Evidence, not a magic truth button.' : 'Use the detector responsibly.'}</h2>{guide ? <><p>VeriSight combines an optional neural classifier with visible forensic measurements. Image scores consider recompression differences, texture/noise consistency, frequency structure, smoothing, metadata context and facial-region checks. Video scans sample frames across the clip and compare score movement over time.</p><h4>How to read confidence</h4><p>Confidence estimates how strongly the available signals agree. A high-confidence result can still be wrong, especially after social-media compression, screenshots, heavy editing or with newly released generators.</p><h4>Forensic fallback</h4><p>If the optional neural model cannot load, VeriSight clearly labels the result as forensic fallback. The scan remains file-dependent, but confidence is reduced.</p></> : <><p>Uploads are processed to return a scan. The included backend does not intentionally keep a permanent media library. Temporary video files are deleted after processing, and API responses are marked no-store.</p><h4>Do not use a single score as proof</h4><p>Never accuse, punish, deny access, make hiring decisions, or take legal or safety action based only on VeriSight. Preserve originals, examine provenance, compare multiple tools and seek qualified review for high-stakes cases.</p><h4>Launch note</h4><p>Before offering public uploads, add HTTPS, rate limiting, abuse controls, malware screening, final privacy terms and counsel review appropriate to the real hosting stack.</p></>}<button className="modal-done" onClick={onClose}>Got it</button></section></div>;
}

export default function App() {
  const [health, setHealth] = useState(null);
  const [healthLoading, setHealthLoading] = useState(true);
  const [type, setType] = useState('photo');
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [result, setResult] = useState(null);
  const [scanning, setScanning] = useState(false);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState('');
  const [history, setHistory] = useState(() => loadHistory());
  const [modal, setModal] = useState(null);

  const checkHealth = useCallback(async () => {
    setHealthLoading(true);
    try { setHealth(await getHealth()); } catch { setHealth(null); } finally { setHealthLoading(false); }
  }, []);

  useEffect(() => { checkHealth(); }, [checkHealth]);
  useEffect(() => () => { if (preview) URL.revokeObjectURL(preview); }, [preview]);

  const clearMedia = useCallback(() => {
    if (preview) URL.revokeObjectURL(preview);
    setPreview(null); setFile(null); setResult(null); setError(''); setProgress(0);
  }, [preview]);

  const changeType = useCallback((next) => { clearMedia(); setType(next); }, [clearMedia]);

  const handleFile = useCallback((candidate) => {
    if (!candidate) return;
    setError(''); setResult(null);
    const expected = type === 'photo' ? candidate.type.startsWith('image/') : candidate.type.startsWith('video/');
    if (!expected) return setError(`That file is not a supported ${type === 'photo' ? 'image' : 'video'}.`);
    if (candidate.size > LIMITS[type]) return setError(`${type === 'photo' ? 'Images' : 'Videos'} must be under ${type === 'photo' ? '25' : '150'} MB.`);
    if (preview) URL.revokeObjectURL(preview);
    setFile(candidate); setPreview(URL.createObjectURL(candidate));
  }, [preview, type]);

  const runAnalysis = useCallback(async () => {
    if (!file || !health?.ok) return;
    setScanning(true); setProgress(6); setError(''); setResult(null);
    const timer = window.setInterval(() => setProgress((value) => value < 90 ? Math.min(90, value + (type === 'video' ? 1.1 : 2.6)) : value), 450);
    try {
      const data = await analyzeMedia(file, type, (next) => setProgress((value) => Math.max(value, next)));
      setResult(data);
      const updated = [historyRecord(data, file), ...history].slice(0, 20);
      setHistory(updated); saveHistory(updated);
    } catch (analysisError) {
      setError(analysisError.message || 'Analysis failed.');
    } finally {
      window.clearInterval(timer); setProgress(100); setScanning(false);
    }
  }, [file, health, history, type]);

  const modelNotice = useMemo(() => {
    if (!health?.ok) return null;
    if (health.model?.status === 'ready') return 'The neural detector is loaded and the forensic checks are active.';
    if (health.model?.status === 'failed') return 'The optional neural model could not load. VeriSight will label results as forensic fallback.';
    return 'The forensic engine is ready. The neural model loads lazily on the first scan.';
  }, [health]);

  return (
    <div className="app-shell">
      <div className="ambient-grid" />
      <Header health={health} openModal={setModal} />
      <main>
        <Hero onStart={() => document.getElementById('scanner')?.scrollIntoView({ behavior: 'smooth' })} openModal={setModal} />
        {!healthLoading && !health?.ok && <div className="offline-banner"><ShieldAlert size={17} /><span>Backend offline. The interface is ready, but scans need the API.</span><button onClick={checkHealth}>Retry</button></div>}
        {modelNotice && <div className="model-notice"><Zap size={15} /><span>{modelNotice}</span></div>}
        <div className="top-grid">
          <Uploader type={type} setType={changeType} file={file} preview={preview} onFile={handleFile} onAnalyze={runAnalysis} onClear={clearMedia} scanning={scanning} progress={progress} error={error} online={Boolean(health?.ok)} />
          <ResultSummary result={result} />
        </div>
        <div className="content-grid"><SignalPanel result={result} /><ExplanationPanel result={result} /></div>
        <div className="content-grid"><EvidencePanel result={result} /><PrivacyPanel /></div>
        <VideoTimeline result={result} />
        <HistoryPanel history={history} clearHistory={() => { setHistory([]); saveHistory([]); }} />
      </main>
      <footer><Shield size={14} /> VeriSight provides probabilistic media screening, not proof. Never use one detector score as the sole basis for accusing a person or making a high-stakes decision.</footer>
      <Modal view={modal} onClose={() => setModal(null)} />
    </div>
  );
}
