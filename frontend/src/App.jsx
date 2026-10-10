import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Upload, FileText, Settings, Activity, Image as ImageIcon, Download, Send, CheckCircle, Database, Shield, Server, Play, CircleDot, CheckCircle2 } from 'lucide-react';

const API_URL = 'http://localhost:8000';

function App() {
  const [documents, setDocuments] = useState([]);
  const [images, setImages] = useState([]);
  const [chatHistory, setChatHistory] = useState([]);
  const [query, setQuery] = useState('');
  
  // Real-time loading states tracking actual backend SSE
  const [loading, setLoading] = useState(false);
  const [loadingStage, setLoadingStage] = useState(null); 
  // e.g. { stage: 'working'|'almost_done'|'completed', message: '...' }

  const [agentActivity, setAgentActivity] = useState([
    { task: 'System Initialized', status: 'done' }
  ]);
  const [sysStatus, setSysStatus] = useState({ status: 'unknown', mode: 'unknown', offline_ready: false });
  const [auditStats, setAuditStats] = useState({ external_calls: 0, local_calls: 0, cloud_uploads: 0 });
  const [selectedModel, setSelectedModel] = useState(null);

  useEffect(() => {
    fetchStatus();
    fetchDocuments();
    fetchAuditStats();
    
    const interval = setInterval(fetchAuditStats, 5000);
    return () => clearInterval(interval);
  }, []);

  const fetchStatus = async () => {
    try {
      const res = await axios.get(`${API_URL}/health`);
      setSysStatus(res.data);
    } catch (e) {
      console.error(e);
      setSysStatus({ status: 'offline', mode: 'disconnected', offline_ready: false });
    }
  };

  const fetchDocuments = async () => {
    try {
      const res = await axios.get(`${API_URL}/documents`);
      setDocuments(res.data.documents || []);
      setImages(res.data.images || []);
    } catch (e) {
      console.error(e);
    }
  };

  const fetchAuditStats = async () => {
    try {
      const res = await axios.get(`${API_URL}/audit/logs`);
      setAuditStats(res.data.stats);
    } catch (e) {
      console.error(e);
    }
  };

  const [uploadProgress, setUploadProgress] = useState(null);
  // uploadProgress: null | { steps: [{label, status}] }

  const handleFileUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    const isPdf = file.name.toLowerCase().endsWith('.pdf');

    const steps = [
      { label: '📄 Uploading document', status: 'running' },
      { label: '🔍 Extracting text', status: 'pending' },
      { label: '🧩 Chunking & indexing', status: 'pending' },
    ];
    if (isPdf) steps.push({ label: '🧠 Analysing document', status: 'pending' });
    setUploadProgress({ steps });

    const setStep = (idx, status) => {
      setUploadProgress(prev => {
        const updated = [...prev.steps];
        updated[idx] = { ...updated[idx], status };
        return { steps: updated };
      });
    };

    const formData = new FormData();
    formData.append('file', file);

    try {
      // Step 0 done immediately — upload starting
      await new Promise(r => setTimeout(r, 300));
      setStep(0, 'done');
      setStep(1, 'running');

      const res = await axios.post(`${API_URL}/upload`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });

      setStep(1, 'done');
      setStep(2, 'running');
      await new Promise(r => setTimeout(r, 200));
      setStep(2, 'done');
      if (isPdf) setStep(3, 'running');

      fetchDocuments();

      // Show analysis result in chat if available
      const summary = res.data?.analysis_summary;
      if (summary) {
        if (isPdf) {
          await new Promise(r => setTimeout(r, 400));
          setStep(3, 'done');
        }

        const findings = (summary.key_findings || []).map(f => `  • ${f}`).join('\n') || '  None recorded.';
        const risks    = [...(summary.risks || []), ...(summary.problems || [])].map(r => `  • ${r}`).join('\n') || '  None recorded.';
        const recs     = (summary.recommendations || []).map(r => `  • ${r}`).join('\n') || '  None recorded.';

        const analysisMsg = {
          role: 'ai',
          content:
            `✅ **${file.name}** processed successfully!\n\n` +
            `**Purpose:** ${summary.purpose}\n\n` +
            `**Key Findings (${(summary.key_findings || []).length}):**\n${findings}\n\n` +
            `**Risks / Problems (${(summary.risks || []).length + (summary.problems || []).length}):**\n${risks}\n\n` +
            `**Recommendations (${(summary.recommendations || []).length}):**\n${recs}\n\n` +
            `**Conclusion:** ${summary.conclusion || 'N/A'}\n\n` +
            `_You can now ask questions about this document._`
        };
        setChatHistory(prev => [...prev, analysisMsg]);
      } else if (isPdf) {
        setStep(3, 'done');
      }

      setAgentActivity(prev => [...prev.filter(a => a.status !== 'running'), { task: `Uploaded ${file.name}`, status: 'done' }]);
    } catch (err) {
      console.error(err);
      setUploadProgress(null);
      setAgentActivity(prev => [...prev, { task: `Failed to upload ${file.name}`, status: 'error' }]);
    } finally {
      setTimeout(() => setUploadProgress(null), 2000);
    }
  };

  const handleSend = async (explicitQuery = null) => {
    const rawText = typeof explicitQuery === 'string' ? explicitQuery : query;
    if (!rawText.trim()) return;
    
    const userMsg = { role: 'user', content: rawText };
    setChatHistory(prev => [...prev, userMsg]);
    if (typeof explicitQuery !== 'string') setQuery('');
    
    setLoading(true);
    setLoadingStage({ stage: 'working', message: 'Initiating request...' });
    
    const docsContext = documents.length > 0 ? ` (Focus on documents: ${documents.join(', ')})` : '';
    const textToSend = rawText + docsContext;
    
    try {
      const response = await fetch(`${API_URL}/agent/run`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: textToSend, history: chatHistory })
      });

      const reader = response.body.getReader();
      const decoder = new TextDecoder('utf-8');
      
      let finalData = null;

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        
        const chunk = decoder.decode(value, { stream: true });
        const lines = chunk.split('\n');
        
        for (const line of lines) {
          if (line.trim() === '') continue;
          
          try {
            const data = JSON.parse(line);
            if (data.type === 'stage') {
              // Real-time backend status stream! No fake timers.
              setLoadingStage({ stage: data.stage, message: data.message });
            } else if (data.type === 'result') {
              finalData = data.data;
            }
          } catch (err) {
            console.error('Error parsing SSE line:', err);
          }
        }
      }

      if (finalData) {
        setSelectedModel(finalData.routing);
        
        const log = finalData.execution_log || [];
        const steps = log.map(p => ({ task: p.task, status: p.status }));
        setAgentActivity(prev => [...prev.filter(a => a.status !== 'running'), ...steps]);
        
        setChatHistory(prev => [...prev, { 
          role: 'ai', 
          content: finalData.response_text,
          file: finalData.file
        }]);
      }
      
      // Add a 1.2s delay so the "Completed" status is actually readable by the user
      await new Promise(resolve => setTimeout(resolve, 1200));

    } catch (e) {
      console.error(e);
      setChatHistory(prev => [...prev, { role: 'ai', content: 'Error communicating with local AI.' }]);
    } finally {
      setLoading(false);
      setLoadingStage(null);
      fetchAuditStats();
    }
  };

  const handleGenerateReport = (type) => {
    let q = '';
    if (type === 'word') q = `Analyze the current documents and prepare a DOCX approval note.`;
    if (type === 'excel') q = `Extract all readings from the current documents and create an XLSX spreadsheet.`;
    if (type === 'ppt') q = `Create a PPTX presentation summarizing the current documents.`;
    handleSend(q);
  };

  // Helper to render the live stage icon and color
  const renderLoadingStage = () => {
    if (!loadingStage) return null;
    
    let color = 'text-slate-400';
    let dotColor = 'bg-slate-400';
    let Icon = CircleDot;
    let label = 'Working';

    if (loadingStage.stage === 'working') {
      color = 'text-red-400';
      dotColor = 'bg-red-500';
      label = 'Working on it';
    } else if (loadingStage.stage === 'almost_done') {
      color = 'text-yellow-400';
      dotColor = 'bg-yellow-500';
      label = 'Almost done';
    } else if (loadingStage.stage === 'completed') {
      color = 'text-green-400';
      dotColor = 'bg-green-500';
      label = 'Completed';
    }

    return (
      <div className="flex justify-start">
        <div className="bg-dark-800 border border-slate-700 rounded-lg p-4 flex flex-col space-y-2 min-w-[250px]">
          <div className={`flex items-center space-x-2 font-semibold ${color}`}>
            <div className={`w-3 h-3 rounded-full ${dotColor} animate-pulse`}></div>
            <span>{label}</span>
          </div>
          <span className="text-sm text-slate-300">{loadingStage.message}</span>
        </div>
      </div>
    );
  };

  return (
    <div className="flex flex-col h-screen bg-dark-900 text-slate-200 overflow-hidden font-sans">
      {/* Header */}
      <header className="flex items-center justify-between px-6 py-4 bg-dark-800 border-b border-slate-700 shadow-sm z-10">
        <div className="flex items-center space-x-3">
          <Database className="w-6 h-6 text-brand-500" />
          <h1 className="text-xl font-bold tracking-tight">KaizenAI Sovereign Workbench</h1>
        </div>
        <div className="flex items-center space-x-4 text-sm font-medium">
          <div className="flex items-center px-3 py-1 bg-dark-900 rounded-full border border-slate-700">
            <div className={`w-2 h-2 rounded-full mr-2 ${sysStatus.status === 'ok' ? 'bg-green-500' : 'bg-red-500'}`}></div>
            <span>{sysStatus.status === 'ok' ? 'LOCAL MODE' : 'OFFLINE'}</span>
          </div>
          <div className="flex items-center px-3 py-1 bg-dark-900 rounded-full border border-slate-700 text-brand-400">
            <Shield className="w-4 h-4 mr-1" />
            <span>EXTERNAL CALLS: {auditStats.external_calls}</span>
          </div>
        </div>
      </header>

      {/* Main Layout */}
      <div className="flex flex-1 overflow-hidden">
        
        {/* Left Sidebar - Documents & Dashboard */}
        <div className="w-64 bg-dark-800 border-r border-slate-700 flex flex-col">
          <div className="p-4 border-b border-slate-700">
            <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-400 mb-4">Documents</h2>
            <label className="flex items-center justify-center w-full px-4 py-2 bg-brand-500 hover:bg-brand-600 text-white rounded-md cursor-pointer transition-colors text-sm font-medium">
              <Upload className="w-4 h-4 mr-2" />
              Upload File
              <input type="file" className="hidden" onChange={handleFileUpload} accept=".pdf,.jpg,.jpeg,.png" />
            </label>

            {/* Upload Progress Steps */}
            {uploadProgress && (
              <div className="mt-3 space-y-1">
                {uploadProgress.steps.map((step, i) => (
                  <div key={i} className="flex items-center space-x-2 text-xs">
                    {step.status === 'done'    && <span className="text-green-400">✓</span>}
                    {step.status === 'running' && <span className="text-yellow-400 animate-pulse">⏳</span>}
                    {step.status === 'pending' && <span className="text-slate-500">○</span>}
                    <span className={
                      step.status === 'done'    ? 'text-green-400' :
                      step.status === 'running' ? 'text-yellow-300 font-medium' :
                      'text-slate-500'
                    }>{step.label}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
          <div className="flex-1 overflow-y-auto p-4">
            <div className="space-y-4">
              <div>
                <h3 className="text-xs font-semibold text-slate-500 mb-2">PDF DOCUMENTS</h3>
                {documents.length === 0 ? <p className="text-xs text-slate-500 italic">No documents</p> : null}
                <ul className="space-y-2">
                  {documents.map((doc, i) => (
                    <li key={i} className="flex items-center text-sm text-slate-300">
                      <FileText className="w-4 h-4 mr-2 text-slate-400" />
                      <span className="truncate">{doc}</span>
                    </li>
                  ))}
                </ul>
              </div>
              
              <div>
                <h3 className="text-xs font-semibold text-slate-500 mb-2 mt-4">IMAGES</h3>
                {images.length === 0 ? <p className="text-xs text-slate-500 italic">No images</p> : null}
                <ul className="space-y-2">
                  {images.map((img, i) => (
                    <li key={i} className="flex items-center text-sm text-slate-300">
                      <ImageIcon className="w-4 h-4 mr-2 text-slate-400" />
                      <span className="truncate">{img}</span>
                    </li>
                  ))}
                </ul>
              </div>
              
              <div className="pt-4 mt-4 border-t border-slate-700">
                <h3 className="text-xs font-semibold text-slate-500 mb-2">NETWORK AUDIT</h3>
                <div className="text-xs space-y-1 text-slate-400">
                  <p>Local API Calls: <span className="text-slate-200">{auditStats.local_calls}</span></p>
                  <p>Cloud Uploads: <span className="text-slate-200">{auditStats.cloud_uploads}</span></p>
                  <p>External AI: <span className="text-brand-400 font-bold">{auditStats.external_calls}</span></p>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Center - AI Workspace */}
        <div className="flex-1 flex flex-col bg-dark-900 relative">
          
          {selectedModel && (
             <div className="absolute top-0 w-full bg-dark-800/80 backdrop-blur-sm border-b border-slate-700 p-2 flex justify-center z-10 shadow-sm">
                <div className="flex items-center space-x-6 text-xs text-slate-300">
                   <div className="flex items-center"><Server className="w-3 h-3 mr-1 text-brand-500"/> ROUTER SELECTION</div>
                   <div><span className="text-slate-500">TASK:</span> {selectedModel.task_type.toUpperCase()}</div>
                   <div><span className="text-slate-500">MODEL:</span> {selectedModel.selected_role} ({selectedModel.model_name})</div>
                   <div><span className="text-slate-500">REASON:</span> {selectedModel.reason}</div>
                </div>
             </div>
          )}
          
          <div className={`flex-1 overflow-y-auto p-6 space-y-6 ${selectedModel ? 'pt-14' : ''}`}>
            {chatHistory.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-full text-slate-500 space-y-4">
                <Database className="w-16 h-16 opacity-20" />
                <h2 className="text-xl font-medium text-slate-400">Secure Industrial AI</h2>
                <p className="text-sm max-w-md text-center">Upload confidential documents and images to begin analysis. All data remains strictly on-premise.</p>
              </div>
            ) : (
              chatHistory.map((msg, i) => (
                <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                  <div className={`max-w-[80%] rounded-lg p-4 shadow-sm ${
                    msg.role === 'user' ? 'bg-brand-900 text-brand-50 border border-brand-500/30' : 'bg-dark-800 border border-slate-700'
                  }`}>
                    <p className="whitespace-pre-wrap text-sm leading-relaxed">{msg.content}</p>
                    
                    {msg.file && (
                      <div className="mt-4 p-4 bg-dark-900 border border-slate-700 rounded-md">
                        <p className="text-xs font-bold text-slate-400 mb-2 uppercase tracking-wide">Generated Deliverable</p>
                        <div className="flex items-center space-x-3 mb-3">
                          <FileText className="w-6 h-6 text-brand-500" />
                          <div>
                            <p className="text-sm font-semibold text-slate-200">{msg.file.filename}</p>
                            <p className="text-xs text-green-500 flex items-center">
                              <CheckCircle className="w-3 h-3 mr-1" /> Verified
                            </p>
                          </div>
                        </div>
                        <div className="flex space-x-2 mt-2">
                           <a href={`${API_URL}/api/files/${msg.file.filename}`} target="_blank" rel="noreferrer" className="text-xs bg-dark-800 hover:bg-dark-700 border border-slate-600 px-3 py-1.5 rounded transition-colors text-slate-300">Open</a>
                           <a href={`${API_URL}/api/files/${msg.file.filename}`} download className="text-xs bg-brand-600 hover:bg-brand-500 text-white px-3 py-1.5 rounded transition-colors flex items-center"><Download className="w-3 h-3 mr-1"/> Download</a>
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              ))
            )}
            
            {/* The Real-Time Status Stream Component */}
            {loading && renderLoadingStage()}

          </div>
          
          <div className="p-4 bg-dark-800 border-t border-slate-700">
            <div className="flex items-center space-x-2">
              <input
                type="text"
                className="flex-1 bg-dark-900 border border-slate-600 rounded-md px-4 py-3 text-sm focus:outline-none focus:border-brand-500 focus:ring-1 focus:ring-brand-500 transition-all placeholder-slate-500"
                placeholder="Ask a question about the documents or analyze an image..."
                value={query}
                onChange={e => setQuery(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && handleSend()}
              />
              <button 
                onClick={handleSend}
                disabled={loading}
                className="bg-brand-500 hover:bg-brand-600 text-white p-3 rounded-md transition-colors disabled:opacity-50"
              >
                <Send className="w-5 h-5" />
              </button>
            </div>
            <div className="mt-3 flex justify-end space-x-3">
              <button onClick={() => handleGenerateReport('word')} className="text-xs flex items-center px-3 py-1.5 bg-dark-900 hover:bg-dark-700 border border-slate-700 rounded text-slate-300 transition-colors">
                <FileText className="w-3 h-3 mr-1.5" />
                DOCX
              </button>
              <button onClick={() => handleGenerateReport('excel')} className="text-xs flex items-center px-3 py-1.5 bg-dark-900 hover:bg-dark-700 border border-slate-700 rounded text-slate-300 transition-colors">
                <Database className="w-3 h-3 mr-1.5" />
                XLSX
              </button>
              <button onClick={() => handleGenerateReport('ppt')} className="text-xs flex items-center px-3 py-1.5 bg-dark-900 hover:bg-dark-700 border border-slate-700 rounded text-slate-300 transition-colors">
                <ImageIcon className="w-3 h-3 mr-1.5" />
                PPTX
              </button>
            </div>
          </div>
        </div>

        {/* Right Sidebar - Agent Activity */}
        <div className="w-72 bg-dark-800 border-l border-slate-700 flex flex-col">
          <div className="p-4 border-b border-slate-700 flex items-center">
            <Activity className="w-4 h-4 mr-2 text-brand-500" />
            <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-400">Agent Activity</h2>
          </div>
          <div className="flex-1 overflow-y-auto p-4">
            <ul className="space-y-4 relative before:absolute before:inset-0 before:ml-5 before:-translate-x-px md:before:mx-auto md:before:translate-x-0 before:h-full before:w-0.5 before:bg-gradient-to-b before:from-transparent before:via-slate-700 before:to-transparent">
              {agentActivity.map((activity, i) => (
                <li key={i} className="relative flex items-center justify-between">
                  <div className="flex items-center space-x-3 z-10 w-full bg-dark-800 pl-2 py-1">
                    {activity.status === 'done' && <CheckCircle className="w-4 h-4 text-green-500 flex-shrink-0" />}
                    {activity.status === 'running' && <div className="w-4 h-4 rounded-full border-2 border-brand-500 border-t-transparent animate-spin flex-shrink-0"></div>}
                    {activity.status === 'error' && <div className="w-4 h-4 rounded-full bg-red-500 flex-shrink-0"></div>}
                    <span className={`text-xs ${activity.status === 'done' ? 'text-slate-300' : 'text-slate-200'}`}>
                      {activity.task}
                    </span>
                  </div>
                </li>
              ))}
            </ul>
          </div>
        </div>
        
      </div>
    </div>
  );
}

export default App;
