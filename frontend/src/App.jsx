import { useState, useEffect, useRef } from 'react';
import { Doughnut } from 'react-chartjs-2';
import { Chart as ChartJS, ArcElement, Tooltip, Legend } from 'chart.js';
import ChatbotCopilot from './ChatbotCopilot';
import { 
  Cpu, 
  ChevronDown, 
  FilePlus, 
  FileText, 
  Trash2, 
  Play, 
  BrainCircuit, 
  Inbox, 
  Loader2,
  CheckCircle2,
  XCircle,
  Check,
  X,
  ChevronRight,
  ShieldCheck,
  AlertTriangle,
  Bot,
  Search,
  BookOpen,
  Wrench,
  Activity,
  ImageOff,
  MousePointerClick
} from 'lucide-react';

ChartJS.register(ArcElement, Tooltip, Legend);

const getBackendUrl = () => {
  if (import.meta.env.VITE_API_BASE_URL) {
    return import.meta.env.VITE_API_BASE_URL.replace(/\/+$/, "");
  }
  if (typeof window !== "undefined" && window.location.pathname.includes("/proxy/6001")) {
    const proxyPath = window.location.pathname.replace(/\/proxy\/6001.*$/, "/proxy/8001");
    return `${window.location.origin}${proxyPath}`;
  }
  if (typeof window !== "undefined" && window.location.hostname) {
    const protocol = window.location.protocol || "http:";
    return `${protocol}//${window.location.hostname}:8001`;
  }
  return "http://localhost:8001";
};

const BACKEND_URL = getBackendUrl();
const API_BASE = `${BACKEND_URL}/api`;
const STATIC_BASE = BACKEND_URL;

// ---------------------------------------------------------
// Components
// ---------------------------------------------------------

const PieChart = ({ passed, failed }) => {
  const data = {
    labels: ['Pass', 'Fail'],
    datasets: [{
      data: [passed, failed],
      backgroundColor: ['#10b981', '#f43f5e'],
      borderWidth: 0,
      hoverOffset: 4
    }]
  };

  const options = {
    cutout: '75%',
    plugins: {
      legend: { display: false },
      tooltip: {
        backgroundColor: '#ffffff',
        titleColor: '#0f172a',
        bodyColor: '#475569',
        borderColor: '#e2e8f0',
        borderWidth: 1,
        titleFont: { family: 'Inter', size: 14 },
        bodyFont: { family: 'Inter', size: 14 },
        padding: 12,
        cornerRadius: 8,
      }
    }
  };

  return (
    <div className="relative w-32 h-32">
      <Doughnut data={data} options={options} />
      <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
        <span className="text-2xl font-bold font-heading text-slate-800">{passed + failed}</span>
        <span className="text-xs text-slate-500">Total</span>
      </div>
    </div>
  );
};

// ---------------------------------------------------------
// Main App
// ---------------------------------------------------------

function App() {
  const [reportsList, setReportsList] = useState([]);
  const [selectedReportId, setSelectedReportId] = useState("");
  const [reportData, setReportData] = useState(null);
  const [loading, setLoading] = useState(false);
  
  // Upload State Machine
  const [selectedFile, setSelectedFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [uploadStatus, setUploadStatus] = useState("");
  const [taskId, setTaskId] = useState(null);

  const [activeFilter, setActiveFilter] = useState("all");
  const [selectedTc, setSelectedTc] = useState(null);
  const [zoomedImage, setZoomedImage] = useState(null);
  const fileInputRef = useRef(null);

  // Initial fetch
  useEffect(() => {
    fetchReports();
  }, []);

  // Polling for Task Status
  useEffect(() => {
    let interval;
    if (taskId && uploading) {
        interval = setInterval(async () => {
            try {
                const res = await fetch(`${API_BASE}/status`);
                if (res.ok) {
                    const statuses = await res.json();
                    const current = statuses[taskId];
                    if (current) {
                        setUploadStatus(current.message);
                        if (current.status === "complete") {
                            setUploading(false);
                            setTaskId(null);
                            setSelectedFile(null);
                            await fetchReports();
                            setSelectedReportId(current.report_id);
                        } else if (current.status === "error") {
                            setUploading(false);
                            setTaskId(null);
                            alert("Processing failed: " + current.message);
                        }
                    }
                }
            } catch (e) {
                console.error("Failed to poll status", e);
            }
        }, 1000);
    }
    return () => clearInterval(interval);
  }, [taskId, uploading]);

  useEffect(() => {
    if (selectedReportId) {
        fetchReportData(selectedReportId);
    } else {
        setReportData(null);
        setSelectedTc(null);
    }
  }, [selectedReportId]);

  const fetchReports = async () => {
    try {
        const res = await fetch(`${API_BASE}/reports`);
        if (res.ok) {
            const data = await res.json();
            if (data.reports) setReportsList(data.reports);
        }
    } catch (err) {
        console.error("Failed to fetch reports list", err);
    }
  };

  const fetchReportData = async (id) => {
    setLoading(true);
    try {
        const res = await fetch(`${API_BASE}/reports/${id}`);
        if (res.ok) {
            const data = await res.json();
            setReportData(data);
        }
    } catch (err) {
        console.error("Failed to fetch report data", err);
    }
    setLoading(false);
  };

  const handleFileSelect = (e) => {
    const file = e.target.files[0];
    if (file) {
        setSelectedFile(file);
        setSelectedReportId("");
    }
  };

  const handleRemoveFile = () => {
    setSelectedFile(null);
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  const handleStartAnalysis = async () => {
    if (!selectedFile) return;

    setUploading(true);
    setUploadStatus("Uploading file to server...");
    const formData = new FormData();
    formData.append("file", selectedFile);

    try {
        const res = await fetch(`${API_BASE}/upload_report`, {
            method: "POST",
            body: formData
        });
        if (res.ok) {
            const data = await res.json();
            if (data.task_id) {
                setTaskId(data.task_id);
            }
        } else {
            setUploadStatus("Upload failed.");
            setUploading(false);
        }
    } catch (err) {
        setUploadStatus("Network error during upload.");
        setUploading(false);
    }
  };

  const filteredTestCases = reportData?.test_cases?.filter(tc => {
    if (activeFilter === "all") return true;
    return tc.verdict === activeFilter;
  }) || [];

  return (
    <div className="min-h-screen p-6 font-sans">
      {/* Header */}
      <header className="max-w-7xl mx-auto flex justify-between items-center mb-8 animate-fade-in">
        <div className="flex items-center gap-3">
          <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-brand-accent to-blue-400 flex items-center justify-center shadow-lg shadow-brand-accent/20">
            <Cpu className="text-white w-7 h-7" />
          </div>
          <div>
            <h1 className="text-2xl font-heading font-extrabold text-slate-900 tracking-tight">NeuroNest <span className="text-brand-accent">IVN</span></h1>
            <p className="text-sm text-slate-500 font-medium">Agentic AI Test Report Analyzer</p>
          </div>
        </div>

        <div className="flex items-center gap-4">
          <div className="relative">
            <select 
              className="appearance-none glass-panel text-slate-700 text-sm font-bold rounded-xl pl-4 pr-10 py-3 outline-none focus:ring-2 focus:ring-brand-accent transition-all cursor-pointer border border-slate-200"
              value={selectedReportId}
              onChange={(e) => setSelectedReportId(e.target.value)}
              disabled={uploading || selectedFile !== null}
            >
              <option value="">-- Select a Processed Report --</option>
              {reportsList.map((r, i) => (
                <option key={i} value={r.metadata?.report_no || ""}>
                  Report #{r.metadata?.report_no || "N/A"} ({r.metadata?.project_name || "Unknown"})
                </option>
              ))}
            </select>
            <ChevronDown className="w-4 h-4 absolute right-3 top-3.5 text-slate-400 pointer-events-none" />
          </div>
          
          <input 
            type="file" 
            accept="application/pdf" 
            className="hidden" 
            ref={fileInputRef} 
            onChange={handleFileSelect} 
          />
          
          {!selectedFile && !uploading && (
            <button 
              onClick={() => fileInputRef.current.click()}
              className="flex items-center gap-2 bg-slate-900 hover:bg-slate-800 text-white px-6 py-3 rounded-xl font-bold transition-all shadow-md hover:shadow-lg"
            >
              <FilePlus className="w-5 h-5" />
              Select PDF
            </button>
          )}
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto grid grid-cols-1 lg:grid-cols-12 gap-6 relative">
        
        {/* Interactive Upload Card */}
        {selectedFile && !uploading && !selectedReportId && (
          <div className="lg:col-span-12 glass-panel rounded-2xl p-12 flex flex-col items-center justify-center text-center animate-fade-in border-slate-200 shadow-sm min-h-[600px]">
            <div className="max-w-lg w-full">
              <div className="w-24 h-24 bg-blue-50 rounded-full flex items-center justify-center mx-auto mb-8 shadow-inner border border-blue-100">
                <FileText className="w-12 h-12 text-brand-accent" />
              </div>
              <h2 className="text-3xl font-heading font-extrabold text-slate-800 mb-4">Ready to Analyze</h2>
              <p className="text-slate-500 font-medium mb-10 bg-slate-100 py-3 px-6 rounded-xl inline-block border border-slate-200 shadow-sm">
                {selectedFile.name} <span className="text-slate-400 ml-1">({(selectedFile.size / 1024 / 1024).toFixed(2)} MB)</span>
              </p>
              
              <div className="flex gap-4 justify-center">
                <button 
                  onClick={handleRemoveFile}
                  className="flex items-center gap-2 bg-white hover:bg-rose-50 text-slate-600 hover:text-rose-600 border-2 border-slate-200 hover:border-rose-200 px-6 py-3.5 rounded-xl font-bold transition-all"
                >
                  <Trash2 className="w-5 h-5" />
                  Remove
                </button>
                <button 
                  onClick={handleStartAnalysis}
                  className="flex items-center gap-2 bg-gradient-to-r from-brand-accent to-blue-500 hover:from-blue-600 hover:to-blue-500 text-white px-10 py-3.5 rounded-xl font-bold transition-all shadow-lg shadow-brand-accent/30 hover:scale-[1.02]"
                >
                  <Play className="w-5 h-5 fill-current" />
                  Start Analysis
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Status Message / Loading Screen */}
        {(uploading || (!reportData && !loading && !selectedFile)) && (
          <div className="lg:col-span-12 glass-panel rounded-2xl p-20 flex flex-col items-center justify-center text-center animate-slide-up border-dashed border-2 border-slate-300 min-h-[600px]">
            {uploading ? (
              <div className="flex flex-col items-center animate-fade-in">
                <div className="relative mb-8">
                  <div className="absolute inset-0 bg-brand-accent/20 rounded-full blur-xl animate-pulse-slow"></div>
                  <div className="w-24 h-24 bg-white rounded-full flex items-center justify-center shadow-xl border-4 border-white relative z-10">
                    <BrainCircuit className="w-12 h-12 text-brand-accent animate-pulse" />
                  </div>
                </div>
                <h2 className="text-2xl font-heading font-extrabold text-slate-800 mb-3">{uploadStatus}</h2>
                <div className="w-64 bg-slate-100 rounded-full h-2 mb-4 overflow-hidden relative">
                  <div className="absolute inset-0 bg-brand-accent/20"></div>
                  <div className="h-full bg-brand-accent animate-[pulse_1.5s_ease-in-out_infinite] w-full origin-left scale-x-75"></div>
                </div>
                <p className="text-slate-500 font-medium max-w-md">Our Agentic AI is actively extracting data and diagnosing failures in real-time. Please wait...</p>
              </div>
            ) : (
              <div className="flex flex-col items-center opacity-70 hover:opacity-100 transition-opacity">
                <div className="w-24 h-24 bg-slate-100 rounded-full flex items-center justify-center mb-6 shadow-inner">
                  <Inbox className="w-10 h-10 text-slate-400" />
                </div>
                <h2 className="text-2xl font-heading font-bold text-slate-800 mb-2">No Report Selected</h2>
                <p className="text-slate-500 font-medium max-w-sm">Click "Select PDF" above to upload a new report, or choose an existing one from the dropdown.</p>
              </div>
            )}
          </div>
        )}

        {loading && !uploading && (
          <div className="lg:col-span-12 glass-panel rounded-2xl p-20 flex flex-col items-center justify-center text-center min-h-[600px]">
            <Loader2 className="w-12 h-12 text-brand-accent animate-spin mb-4" />
            <h2 className="text-xl font-heading font-bold text-slate-800">Loading Report Data...</h2>
          </div>
        )}

        {/* Report Data UI */}
        {reportData && !loading && !selectedFile && (
          <>
            {/* Left Column: Summary & Test Cases */}
            <div className="lg:col-span-6 space-y-6 animate-slide-up">
              
              {/* Executive Summary */}
              <div className="glass-panel rounded-2xl p-6 shadow-sm border border-slate-200">
                <div className="flex justify-between items-start mb-6">
                  <div>
                    <h2 className="text-xl font-heading font-extrabold text-slate-800 mb-1">Executive Summary</h2>
                    <p className="text-sm font-bold text-slate-500">Report #{reportData.metadata?.report_no || 'N/A'} • {reportData.metadata?.project_name || 'N/A'}</p>
                  </div>
                  <div className="flex gap-4 items-center">
                    <div className="text-right">
                      <div className="text-xs text-slate-400 uppercase tracking-wider font-extrabold mb-1">Results</div>
                      <div className="flex gap-3">
                        <span className="text-brand-pass font-extrabold text-sm flex items-center gap-1"><CheckCircle2 className="w-4 h-4" /> {reportData.analysis_summary?.passed || 0}</span>
                        <span className="text-brand-fail font-extrabold text-sm flex items-center gap-1"><XCircle className="w-4 h-4" /> {reportData.analysis_summary?.failed || 0}</span>
                      </div>
                    </div>
                    <PieChart passed={reportData.analysis_summary?.passed || 0} failed={reportData.analysis_summary?.failed || 0} />
                  </div>
                </div>

                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div className="bg-slate-50 p-3 rounded-xl border border-slate-100">
                    <div className="text-xs font-bold text-slate-400 mb-1 uppercase tracking-wide">Tester</div>
                    <div className="font-bold text-sm text-slate-700">{reportData.metadata?.tester || 'N/A'}</div>
                  </div>
                  <div className="bg-slate-50 p-3 rounded-xl border border-slate-100">
                    <div className="text-xs font-bold text-slate-400 mb-1 uppercase tracking-wide">Stage</div>
                    <div className="font-bold text-sm text-slate-700">{reportData.metadata?.dr_stage || 'N/A'}</div>
                  </div>
                  <div className="bg-slate-50 p-3 rounded-xl border border-slate-100">
                    <div className="text-xs font-bold text-slate-400 mb-1 uppercase tracking-wide">DBC</div>
                    <div className="font-bold text-sm text-slate-700 truncate" title={reportData.metadata?.dbc_file}>{reportData.metadata?.dbc_file || 'N/A'}</div>
                  </div>
                  <div className="bg-blue-50 p-3 rounded-xl border border-blue-100">
                    <div className="text-xs font-bold text-brand-accent/80 mb-1 uppercase tracking-wide">AI Analyzed</div>
                    <div className="font-extrabold text-sm text-brand-accent">{reportData.analysis_summary?.ai_analyzed || 0} Cases</div>
                  </div>
                </div>
              </div>

              {/* Test Cases List */}
              <div className="glass-panel rounded-2xl flex flex-col overflow-hidden shadow-sm border border-slate-200" style={{ height: 'calc(100vh - 360px)' }}>
                <div className="p-4 border-b border-slate-200 flex justify-between items-center bg-white">
                  <h3 className="font-heading font-extrabold text-lg text-slate-800">Test Cases</h3>
                  <div className="flex bg-slate-100 rounded-lg p-1 border border-slate-200 shadow-inner">
                    <button onClick={() => setActiveFilter("all")} className={`px-4 py-1.5 text-xs font-bold rounded-md transition-all ${activeFilter === 'all' ? 'bg-white text-slate-800 shadow' : 'text-slate-500 hover:text-slate-700'}`}>All</button>
                    <button onClick={() => setActiveFilter("pass")} className={`px-4 py-1.5 text-xs font-bold rounded-md transition-all ${activeFilter === 'pass' ? 'bg-white text-brand-pass shadow' : 'text-slate-500 hover:text-slate-700'}`}>Passed</button>
                    <button onClick={() => setActiveFilter("fail")} className={`px-4 py-1.5 text-xs font-bold rounded-md transition-all ${activeFilter === 'fail' ? 'bg-white text-brand-fail shadow' : 'text-slate-500 hover:text-slate-700'}`}>Failed</button>
                  </div>
                </div>
                
                <div className="overflow-y-auto custom-scrollbar flex-1 p-3 space-y-2 bg-slate-50/30">
                  {filteredTestCases.map((tc, idx) => (
                    <div 
                      key={idx} 
                      onClick={() => setSelectedTc(tc)}
                      className={`p-4 rounded-xl border-2 transition-all cursor-pointer group flex items-start gap-4
                        ${selectedTc?.tc_id === tc.tc_id 
                          ? 'bg-blue-50/50 border-brand-accent shadow-md' 
                          : 'bg-white border-transparent hover:border-slate-200 shadow-sm'}`}
                    >
                      <div className={`mt-1 flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center font-bold ${tc.verdict === 'pass' ? 'bg-green-100 text-brand-pass' : 'bg-red-100 text-brand-fail'}`}>
                        {tc.verdict === 'pass' ? <Check className="w-4 h-4 stroke-[3]" /> : <X className="w-4 h-4 stroke-[3]" />}
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex justify-between items-start mb-1">
                          <h4 className="font-mono text-sm text-slate-800 font-extrabold truncate pr-4">{tc.tc_id}</h4>
                          <span className={`text-[10px] uppercase font-extrabold px-2 py-0.5 rounded-md ${tc.verdict === 'pass' ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}>
                            {tc.verdict}
                          </span>
                        </div>
                        <p className="text-sm text-slate-500 font-semibold truncate">{tc.name}</p>
                      </div>
                      <ChevronRight className={`w-5 h-5 mt-2 transition-transform ${selectedTc?.tc_id === tc.tc_id ? 'text-brand-accent translate-x-1' : 'text-slate-300 group-hover:text-slate-500'}`} />
                    </div>
                  ))}
                  {filteredTestCases.length === 0 && (
                    <div className="text-center p-12 text-slate-400 text-sm font-bold">No test cases match this filter.</div>
                  )}
                </div>
              </div>
            </div>

            {/* Right Column: Detailed Diagnosis & Waveform */}
            <div className="lg:col-span-6 h-[calc(100vh-120px)] animate-slide-up" style={{ animationDelay: '0.1s' }}>
              {selectedTc ? (
                <div className="glass-panel rounded-2xl h-full flex flex-col overflow-hidden border border-slate-200 shadow-xl">
                  
                  {/* Header */}
                  <div className={`p-6 flex items-center gap-4 border-b ${selectedTc.verdict === 'pass' ? 'bg-gradient-to-r from-emerald-50 to-white border-emerald-100' : 'bg-gradient-to-r from-rose-50 to-white border-rose-100'}`}>
                    <div className={`w-12 h-12 rounded-xl flex items-center justify-center shadow-sm ${selectedTc.verdict === 'pass' ? 'bg-brand-pass text-white' : 'bg-brand-fail text-white'}`}>
                      {selectedTc.verdict === 'pass' ? <ShieldCheck className="w-6 h-6" /> : <AlertTriangle className="w-6 h-6" />}
                    </div>
                    <div>
                      <h3 className="font-heading font-extrabold text-xl text-slate-800">{selectedTc.tc_id}</h3>
                      <p className="text-sm font-bold text-slate-500">{selectedTc.name}</p>
                    </div>
                  </div>

                  <div className="flex-1 overflow-y-auto custom-scrollbar p-6 space-y-8 bg-slate-50">
                    
                    {/* AI Diagnosis Panel */}
                    {selectedTc.verdict === 'fail' && selectedTc.ai_analysis && (
                      <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-sm relative overflow-hidden">
                        <div className="absolute top-0 left-0 w-1.5 h-full bg-brand-accent"></div>
                        <div className="flex items-center gap-3 mb-6">
                          <div className="bg-blue-50 p-2 rounded-xl border border-blue-100">
                            <Bot className="w-5 h-5 text-brand-accent" />
                          </div>
                          <h4 className="font-heading font-extrabold text-lg text-slate-800">NeuroNest AI Diagnosis</h4>
                          {selectedTc.ai_analysis.severity && (
                            <span className={`ml-auto text-xs font-extrabold px-3 py-1 rounded-full uppercase shadow-sm
                              ${selectedTc.ai_analysis.severity.includes('CRITICAL') ? 'bg-red-100 text-red-700 border border-red-200' : 
                                selectedTc.ai_analysis.severity.includes('HIGH') ? 'bg-orange-100 text-orange-700 border border-orange-200' : 
                                'bg-yellow-100 text-yellow-700 border border-yellow-200'}`}>
                              {selectedTc.ai_analysis.severity}
                            </span>
                          )}
                        </div>

                        <div className="space-y-6">
                          <div>
                            <h5 className="text-xs font-extrabold text-slate-400 uppercase tracking-widest mb-2 flex items-center gap-1.5">
                              <Search className="w-3.5 h-3.5" /> Root Cause
                            </h5>
                            <p className="text-sm font-semibold text-slate-700 leading-relaxed">
                              {selectedTc.ai_analysis.root_cause || "No root cause provided."}
                            </p>
                          </div>

                          <div>
                            <h5 className="text-xs font-extrabold text-slate-400 uppercase tracking-widest mb-2 flex items-center gap-1.5">
                              <BookOpen className="w-3.5 h-3.5" /> ISO Reference
                            </h5>
                            <p className="text-sm text-indigo-700 font-bold bg-indigo-50 p-3 rounded-xl border border-indigo-100 leading-relaxed font-mono">
                              {selectedTc.ai_analysis.iso_reference || "N/A"}
                            </p>
                          </div>

                          <div>
                            <h5 className="text-xs font-extrabold text-slate-400 uppercase tracking-widest mb-2 flex items-center gap-1.5">
                              <Wrench className="w-3.5 h-3.5" /> Recommended Fix
                            </h5>
                            <div className="text-sm font-semibold text-slate-700 leading-relaxed whitespace-pre-wrap bg-slate-50 p-4 rounded-xl border border-slate-200">
                              {selectedTc.ai_analysis.recommended_fix || "No fix recommended."}
                            </div>
                          </div>
                        </div>
                      </div>
                    )}

                    {selectedTc.verdict === 'pass' && (
                      <div className="bg-white border-2 border-green-100 rounded-2xl p-10 text-center shadow-sm">
                        <div className="bg-green-50 w-20 h-20 rounded-full flex items-center justify-center mx-auto mb-4 border border-green-100">
                          <CheckCircle2 className="w-10 h-10 text-brand-pass" />
                        </div>
                        <h3 className="text-xl font-extrabold text-slate-800 mb-2">Test Passed Successfully</h3>
                        <p className="text-sm text-slate-500 font-semibold max-w-sm mx-auto leading-relaxed">To optimize database performance per our 90/10 AI rule, the heavy measurement tables for this passed test case have been compressed and archived.</p>
                      </div>
                    )}

                    {/* Waveform Images */}
                    {selectedTc.images && selectedTc.images.length > 0 && (
                      <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-sm">
                        <h4 className="font-heading font-extrabold text-slate-800 mb-4 flex items-center gap-2">
                          <Activity className="w-5 h-5 text-brand-accent" />
                          Waveform Analysis Trace
                        </h4>
                        <div className="space-y-6">
                          {selectedTc.images.map((img, i) => (
                            <div key={i} className="group relative rounded-xl overflow-hidden border border-slate-200 bg-slate-50 shadow-sm hover:shadow-md transition-shadow">
                              <img 
                                src={`${STATIC_BASE}${img.image_path}`} 
                                alt={`Waveform ${i}`} 
                                className="w-full h-auto object-contain max-h-80 transition-transform duration-500 group-hover:scale-[1.02] p-2 cursor-zoom-in"
                                onClick={() => setZoomedImage(`${STATIC_BASE}${img.image_path}`)}
                                onError={(e) => { e.target.style.display = 'none'; e.target.nextSibling.style.display = 'flex'; }}
                              />
                              <div className="hidden absolute inset-0 flex-col items-center justify-center text-slate-400 bg-slate-50">
                                <ImageOff className="w-8 h-8 mb-2 opacity-50" />
                                <span className="text-sm font-bold">Trace image not available</span>
                              </div>
                              <div className="absolute bottom-3 right-3 z-20 text-[10px] text-slate-600 font-extrabold font-mono bg-white/90 px-2 py-1 rounded-md shadow-sm border border-slate-200 backdrop-blur">
                                {img.width}x{img.height}
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                  </div>
                </div>
              ) : (
                <div className="glass-panel rounded-2xl h-full flex flex-col items-center justify-center text-center p-12 border border-slate-200 shadow-sm text-slate-500">
                  <div className="w-20 h-20 bg-slate-100 rounded-full flex items-center justify-center mb-6 shadow-inner">
                    <MousePointerClick className="w-10 h-10 text-slate-400" />
                  </div>
                  <h3 className="text-xl font-extrabold text-slate-800 mb-2">Select a Test Case</h3>
                  <p className="max-w-xs font-semibold leading-relaxed">Click on any test case from the list on the left to view detailed AI analysis and oscilloscope waveform traces.</p>
                </div>
              )}
            </div>
          </>
        )}
        {/* Image Zoom Modal */}
        {zoomedImage && (
          <div 
            className="fixed inset-0 z-[100] flex items-center justify-center bg-slate-900/90 backdrop-blur-sm p-8 animate-fade-in cursor-zoom-out"
            onClick={() => setZoomedImage(null)}
          >
            <div className="relative max-w-7xl max-h-full">
              <img 
                src={zoomedImage} 
                alt="Zoomed Waveform" 
                className="w-auto h-auto max-w-full max-h-[90vh] object-contain rounded-xl shadow-2xl border border-white/20"
                onClick={(e) => e.stopPropagation()} 
              />
              <button 
                className="absolute -top-4 -right-4 w-10 h-10 bg-white rounded-full flex items-center justify-center shadow-xl text-slate-800 hover:text-rose-600 hover:scale-110 transition-all cursor-pointer"
                onClick={(e) => { e.stopPropagation(); setZoomedImage(null); }}
              >
                <X className="w-5 h-5" />
              </button>
            </div>
          </div>
        )}

        {/* Interactive Automotive AI Copilot Chatbot */}
        <ChatbotCopilot apiBase={API_BASE} activeReport={reportData} />
      </main>
    </div>
  );
}

export default App;
