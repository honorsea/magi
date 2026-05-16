import React, { useEffect, useState } from 'react';
import { api } from '../api/client';
import { FileText, FileSpreadsheet, Image as ImageIcon, FileJson, Trash2, Download, Search, RefreshCw, X, AlertCircle } from 'lucide-react';

interface FileEntry {
  name: string;
  path: string;
  size_bytes: number;
  modified_at: number;
  type: string;
}

const formatSize = (bytes: number) => {
  if (bytes < 1024) return bytes + ' B';
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
  return (bytes / (1024 * 1024)).toFixed(2) + ' MB';
};

const formatDate = (ts: number) => {
  return new Date(ts * 1000).toLocaleString();
};

const FileIcon: React.FC<{ type: string; size?: number }> = ({ type, size = 16 }) => {
  switch (type) {
    case 'csv': return <FileSpreadsheet size={size} color="hsl(142,65%,45%)" />;
    case 'png':
    case 'jpg': return <ImageIcon size={size} color="hsl(35,80%,50%)" />;
    case 'json': return <FileJson size={size} color="hsl(262,70%,55%)" />;
    default: return <FileText size={size} color="var(--text-secondary)" />;
  }
};

export const OutputsPage: React.FC = () => {
  const [files, setFiles] = useState<FileEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [previewFile, setPreviewFile] = useState<string | null>(null);
  const [previewContent, setPreviewContent] = useState<{ content: string; truncated: boolean } | null>(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [malformed, setMalformed] = useState<string | null>(null);
  const [responseMeta, setResponseMeta] = useState<any>(null);

  const fetchFiles = async () => {
    setLoading(true);
    setError(null);
    setMalformed(null);
    try {
      const data = await api.outputs.list();
      if (!data || !Array.isArray(data.files)) {
        setMalformed('Expected response shape: { files: FileEntry[], meta?: object }.');
        setFiles([]);
      } else {
        setFiles(data.files);
      }
      setResponseMeta(data?.meta ?? null);
    } catch (err: any) {
      setError(err.message);
    }
    setLoading(false);
  };

  useEffect(() => {
    fetchFiles();
  }, []);

  const handleDelete = async (path: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!confirm('Are you sure you want to delete this file?')) return;
    try {
      await api.outputs.delete(path);
      if (previewFile === path) {
        setPreviewFile(null);
        setPreviewContent(null);
      }
      fetchFiles();
    } catch (err: any) {
      alert(`Delete failed: ${err.message}`);
    }
  };

  const handlePreview = async (file: FileEntry) => {
    if (file.type === 'png' || file.type === 'jpg') {
      setPreviewFile(file.path);
      setPreviewContent({ content: 'image', truncated: false });
      return;
    }
    
    setPreviewFile(file.path);
    setPreviewContent(null);
    setPreviewLoading(true);
    try {
      const res = await api.outputs.preview(file.path);
      setPreviewContent({ content: res.content, truncated: res.truncated });
    } catch (err: any) {
      setPreviewContent({ content: `Error loading preview: ${err.message}`, truncated: false });
    }
    setPreviewLoading(false);
  };

  const filtered = files.filter(f => f.name.toLowerCase().includes(search.toLowerCase()));

  return (
    <div style={{ display: 'flex', height: '100%', gap: '16px' }}>
      {/* File List */}
      <div style={{ flex: previewFile ? '0 0 50%' : 1, display: 'flex', flexDirection: 'column', gap: '16px', transition: 'flex 0.2s ease-out' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <h2 style={{ margin: 0 }}>Outputs & Artifacts</h2>
            <p style={{ margin: '2px 0 0 0', fontSize: '13px', color: 'var(--text-secondary)' }}>
              Browse generated logs, traces, KPIs, and graphs
            </p>
          </div>
          <div style={{ display: 'flex', gap: '10px' }}>
            <div style={{ position: 'relative' }}>
              <Search size={14} style={{ position: 'absolute', left: '10px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-secondary)' }} />
              <input 
                type="text" placeholder="Search files…" value={search} onChange={e => setSearch(e.target.value)}
                style={{ paddingLeft: '30px', padding: '8px 10px 8px 30px', borderRadius: '6px', border: '1px solid var(--border)', background: 'var(--bg-secondary)', fontSize: '13px', width: '200px' }}
              />
            </div>
            <button onClick={fetchFiles} disabled={loading}
              style={{ padding: '8px', background: 'var(--bg-tertiary)', border: 'none', borderRadius: '6px', cursor: 'pointer', color: 'var(--text-secondary)' }}>
              <RefreshCw size={15} className={loading ? 'spinning' : ''} />
            </button>
          </div>
        </div>

        {error ? (
          <div style={{ padding: '16px', background: 'hsl(0,60%,97%)', border: '1px solid hsl(0,60%,85%)', borderRadius: '8px', color: 'var(--accent-red)', display: 'flex', gap: '8px' }}>
            <AlertCircle size={18} /> Failed to load files: {error}
          </div>
        ) : loading && files.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '40px', color: 'var(--text-secondary)' }}>Loading files…</div>
        ) : malformed ? (
          <div style={{ padding: '16px', background: 'hsl(35,100%,96%)', border: '1px solid hsl(35,70%,80%)', borderRadius: '8px', color: 'hsl(35,80%,28%)' }}>
            <AlertCircle size={18} style={{ verticalAlign: 'middle', marginRight: '8px' }} />
            Malformed API payload: {malformed}
          </div>
        ) : filtered.length === 0 ? (
          <div className="card" style={{ padding: '40px', textAlign: 'center', color: 'var(--text-secondary)' }}>
            <FileText size={48} style={{ opacity: 0.2, marginBottom: '16px' }} />
            <div>No files found matching "{search}"</div>
            <div style={{ marginTop: '12px', fontSize: '12px', textAlign: 'left', display: 'inline-block' }}>
              <div><strong>Configured outputs root:</strong> <code>{responseMeta?.outputs_root ?? 'unknown'}</code></div>
              <div><strong>API metadata:</strong> <code>{JSON.stringify(responseMeta ?? { note: 'No metadata provided' })}</code></div>
            </div>
          </div>
        ) : (
          <div className="card" style={{ flex: 1, overflowY: 'auto', padding: 0 }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px' }}>
              <thead>
                <tr style={{ background: 'var(--bg-tertiary)', borderBottom: '1px solid var(--border)', textAlign: 'left', color: 'var(--text-secondary)' }}>
                  <th style={{ padding: '12px 16px', fontWeight: 500 }}>Name</th>
                  <th style={{ padding: '12px 16px', fontWeight: 500, width: '120px' }}>Date</th>
                  <th style={{ padding: '12px 16px', fontWeight: 500, width: '80px', textAlign: 'right' }}>Size</th>
                  <th style={{ padding: '12px 16px', fontWeight: 500, width: '100px', textAlign: 'right' }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map(f => (
                  <tr key={f.path} 
                    onClick={() => handlePreview(f)}
                    style={{ 
                      borderBottom: '1px solid var(--border)', 
                      background: previewFile === f.path ? 'var(--bg-tertiary)' : 'transparent',
                      cursor: 'pointer' 
                    }}
                    onMouseOver={e => e.currentTarget.style.background = 'var(--bg-tertiary)'}
                    onMouseOut={e => e.currentTarget.style.background = previewFile === f.path ? 'var(--bg-tertiary)' : 'transparent'}
                  >
                    <td style={{ padding: '12px 16px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <FileIcon type={f.type} />
                        <span style={{ fontWeight: 500, color: 'var(--text-primary)' }}>{f.name}</span>
                      </div>
                    </td>
                    <td style={{ padding: '12px 16px', color: 'var(--text-secondary)' }}>{formatDate(f.modified_at)}</td>
                    <td style={{ padding: '12px 16px', color: 'var(--text-secondary)', textAlign: 'right' }}>{formatSize(f.size_bytes)}</td>
                    <td style={{ padding: '12px 16px', textAlign: 'right' }}>
                      <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px' }}>
                        <a href={api.outputs.downloadUrl(f.path)} target="_blank" rel="noreferrer" 
                           onClick={e => e.stopPropagation()}
                           style={{ color: 'var(--text-secondary)', padding: '4px', display: 'flex', alignItems: 'center' }} title="Download">
                          <Download size={14} />
                        </a>
                        <button onClick={(e) => handleDelete(f.path, e)}
                          style={{ background: 'none', border: 'none', color: 'var(--accent-red)', cursor: 'pointer', padding: '4px', display: 'flex', alignItems: 'center', opacity: 0.7 }} title="Delete">
                          <Trash2 size={14} />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Preview Panel */}
      {previewFile && (
        <div className="card" style={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0 }}>
          <div style={{ padding: '12px 16px', borderBottom: '1px solid var(--border)', display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: 'var(--bg-tertiary)' }}>
            <h3 style={{ margin: 0, fontSize: '14px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
              Preview: {previewFile.split(/[/\\]/).pop()}
            </h3>
            <div style={{ display: 'flex', gap: '8px' }}>
              <a href={api.outputs.downloadUrl(previewFile)} target="_blank" rel="noreferrer" 
                style={{ background: 'var(--bg-secondary)', border: '1px solid var(--border)', padding: '4px 8px', borderRadius: '4px', color: 'var(--text-secondary)', fontSize: '12px', textDecoration: 'none', display: 'flex', alignItems: 'center', gap: '4px' }}>
                <Download size={12} /> Download
              </a>
              <button onClick={() => setPreviewFile(null)} style={{ background: 'none', border: 'none', color: 'var(--text-secondary)', cursor: 'pointer', padding: '4px' }}>
                <X size={16} />
              </button>
            </div>
          </div>
          
          <div style={{ flex: 1, overflow: 'auto', padding: '16px', background: 'var(--bg-secondary)' }}>
            {previewLoading ? (
              <div style={{ color: 'var(--text-secondary)' }}>Loading preview…</div>
            ) : previewContent?.content === 'image' ? (
              <div style={{ width: '100%', height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <img src={api.outputs.downloadUrl(previewFile)} alt="Preview" style={{ maxWidth: '100%', maxHeight: '100%', objectFit: 'contain' }} />
              </div>
            ) : previewContent ? (
              <div style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
                {previewContent.truncated && (
                  <div style={{ background: 'hsl(38,100%,96%)', color: 'hsl(38,80%,40%)', padding: '8px 12px', fontSize: '12px', borderRadius: '4px', marginBottom: '12px', flexShrink: 0 }}>
                    File is large. Showing preview of the first 5000 characters. Download to see full content.
                  </div>
                )}
                <pre style={{ 
                  margin: 0, padding: '16px', background: 'white', border: '1px solid var(--border)', 
                  borderRadius: '6px', fontSize: '12px', fontFamily: 'var(--font-mono)', 
                  whiteSpace: 'pre-wrap', wordBreak: 'break-all', overflowY: 'auto', flex: 1
                }}>
                  {previewContent.content}
                </pre>
              </div>
            ) : null}
          </div>
        </div>
      )}
    </div>
  );
};
