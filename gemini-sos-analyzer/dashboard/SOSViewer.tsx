import React, { useState, useMemo } from 'react';
import {
  useReactTable,
  getCoreRowModel,
  flexRender,
  createColumnHelper,
} from '@tanstack/react-table';
import Editor from '@monaco-editor/react';

// Import the pre-generated JSON data
import diagnosticData from './diagnostic_data.json';

interface LogFile {
  name: string;
  content: string;
  error_count: number;
  recent_errors: string[];
}

interface SOSData {
  summary: { hostname?: string; os?: string };
  analysis?: {
    root_cause: string;
    likely_causes: string[];
    remediation: string[];
    evidence: { line: string; file: string }[];
  };
  resources: {
    memory: any[];
    disk: any[];
    load_avg?: string;
    threads?: { pid: string; cmd: string; threads: number }[];
  };
  cluster: { nodes: string[]; raw_status: string };
  logs: LogFile[];
  version?: number;
}

const columnHelper = createColumnHelper<any>();

const SOSViewer: React.FC = () => {
  const [data] = useState<SOSData>(diagnosticData as any);
  const [selectedLog, setSelectedLog] = useState<LogFile | null>(data.logs[0] || null);

  if (!data) return <div>Loading diagnostic data...</div>;

  // Dynamic Logic: Determine what's important
  const loadValues = data.resources.load_avg?.split(',').map(v => parseFloat(v.trim())) || [];
  const isHighLoad = loadValues.some(v => v > 10); // Simple threshold
  const hasThreadStorm = data.resources.threads?.some(t => t.threads > 200);

  return (
    <div style={{ padding: '20px', fontFamily: 'sans-serif', maxWidth: '1200px', margin: '0 auto' }}>
      <header style={{ borderBottom: '2px solid #333', marginBottom: '20px', paddingBottom: '10px' }}>
        <h1 style={{ margin: 0 }}>SOS Diagnostic Report: {data.summary.hostname}</h1>
        <p style={{ color: '#666' }}>OS: {data.summary.os} | Analysis Generated: {new Date().toLocaleDateString()}</p>
        
        {/* Only show Load if it's actually high */}
        {isHighLoad && (
          <div style={{ marginTop: '10px', padding: '10px', background: '#fff5f5', border: '1px solid #feb2b2', borderRadius: '4px' }}>
            <span style={{ fontWeight: 'bold', color: '#c53030' }}>CRITICAL: High System Load Average: {data.resources.load_avg}</span>
          </div>
        )}
      </header>

      {/* PRIMARY ANALYSIS SECTION (Always first if present) */}
      {data.analysis && (
        <section style={{ marginBottom: '30px', display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>
          <div style={{ background: '#fffcf0', border: '1px solid #faf089', padding: '20px', borderRadius: '8px' }}>
            <h2 style={{ marginTop: 0, color: '#b7791f' }}>Root Cause Analysis</h2>
            <p style={{ lineHeight: '1.6', fontWeight: '500' }}>{data.analysis.root_cause}</p>
            
            {data.analysis.likely_causes && (
              <div style={{ marginTop: '15px' }}>
                <h4 style={{ margin: '0 0 5px 0', color: '#744210' }}>Likely Factors:</h4>
                <ul style={{ margin: 0, paddingLeft: '20px', fontSize: '0.9rem' }}>
                  {data.analysis.likely_causes.map((cause, i) => (
                    <li key={i}>{cause}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
          <div style={{ background: '#f0fff4', border: '1px solid #9ae6b4', padding: '20px', borderRadius: '8px' }}>
            <h2 style={{ marginTop: 0, color: '#2f855a' }}>Required Actions</h2>
            <ul style={{ paddingLeft: '20px', lineHeight: '1.8' }}>
              {data.analysis.remediation.map((step, i) => (
                <li key={i} style={{ fontWeight: 'bold' }}>{step}</li>
              ))}
            </ul>
          </div>
        </section>
      )}

      {/* SECONDARY EVIDENCE SECTION */}
      {data.analysis?.evidence && (
        <section style={{ marginBottom: '40px' }}>
          <h3 style={{ color: '#2b6cb0' }}>Supporting Evidence</h3>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(350px, 1fr))', gap: '15px' }}>
            {data.analysis.evidence.map((item: any, i: number) => (
              <div key={i} style={{ background: '#f7fafc', border: '1px solid #e2e8f0', padding: '12px', borderRadius: '6px' }}>
                <div style={{ fontSize: '0.75rem', color: '#718096', fontWeight: 'bold', marginBottom: '5px' }}>FILE: {item.file}</div>
                <code style={{ fontSize: '0.85rem', color: '#2d3748', display: 'block', whiteSpace: 'pre-wrap' }}>{item.line}</code>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* OPTIONAL RESOURCE TABLES (Only if relevant) */}
      {(hasThreadStorm || isHighLoad) && (
        <section style={{ marginBottom: '30px', borderTop: '1px solid #eee', paddingTop: '20px' }}>
          <h3>Resource Monitoring (Contextual)</h3>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>
            {data.resources.threads && data.resources.threads.length > 0 && (
              <div style={{ border: '1px solid #e2e8f0', padding: '15px', borderRadius: '8px' }}>
                <h4 style={{ marginTop: 0 }}>Top Threads</h4>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem' }}>
                  <thead>
                    <tr style={{ borderBottom: '2px solid #edf2f7' }}>
                      <th style={{ textAlign: 'left' }}>PID</th>
                      <th style={{ textAlign: 'left' }}>Count</th>
                      <th style={{ textAlign: 'left' }}>Command</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.resources.threads.map((t, i) => (
                      <tr key={i} style={{ borderBottom: '1px solid #edf2f7' }}>
                        <td>{t.pid}</td>
                        <td style={{ fontWeight: 'bold' }}>{t.threads}</td>
                        <td style={{ color: '#4a5568' }}>{t.cmd}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
            {data.cluster.raw_status && (
              <div style={{ border: '1px solid #e2e8f0', padding: '15px', borderRadius: '8px' }}>
                <h4 style={{ marginTop: 0 }}>Cluster Status</h4>
                <pre style={{ fontSize: '0.75rem', height: '150px', overflow: 'auto' }}>{data.cluster.raw_status}</pre>
              </div>
            )}
          </div>
        </section>
      )}

      <section style={{ marginTop: '40px' }}>
        <h2>Log Viewer (monaco-editor)</h2>
        <div style={{ display: 'flex', gap: '10px', marginBottom: '10px' }}>
          {data.logs.map(log => (
            <button 
              key={log.name} 
              onClick={() => setSelectedLog(log)}
              style={{ padding: '5px 10px', background: selectedLog?.name === log.name ? '#007bff' : '#eee', color: selectedLog?.name === log.name ? 'white' : 'black', border: 'none', cursor: 'pointer' }}
            >
              {log.name} ({log.error_count} errors)
            </button>
          ))}
        </div>
        {selectedLog && (
          <div style={{ border: '1px solid #ddd' }}>
            <Editor
              height="500px"
              defaultLanguage="log"
              value={selectedLog.content}
              theme="vs-dark"
              options={{ readOnly: true, minimap: { enabled: true } }}
            />
          </div>
        )}
      </section>

      {data.version && (
        <footer style={{ marginTop: '50px', fontSize: '0.7rem', color: '#999', textAlign: 'center' }}>
          Data Version ID: {data.version} (If info seems stale, please Force-Reload with Ctrl+F5)
        </footer>
      )}
    </div>
  );
};

export default SOSViewer;
