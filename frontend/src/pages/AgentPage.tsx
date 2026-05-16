import React, { useEffect, useRef, useState } from 'react';
import { useSimStore } from '../store/simulationStore';
import { api } from '../api/client';
import { Send, Bot, User, Wrench, ChevronDown, ChevronRight, Zap, RefreshCw } from 'lucide-react';

// ── Types ─────────────────────────────────────────────────────────────────────

interface Message {
  id: string;
  role: 'user' | 'agent' | 'tool' | 'system';
  content: string;
  toolName?: string;
  toolArgs?: any;
  toolResult?: any;
  timestamp: number;
  simTime?: number;
}

interface Shortcut {
  id: string;
  name: string;
  category: string;
  content: string;
}

// ── Tool Call Card ─────────────────────────────────────────────────────────────

const ToolCallCard: React.FC<{ name: string; args?: any; result?: any }> = ({ name, args, result }) => {
  const [open, setOpen] = useState(false);
  return (
    <div style={{
      margin: '6px 0', padding: '8px 12px', borderRadius: '6px',
      background: 'var(--tool-card-bg)', border: '1px solid var(--tool-card-border)',
      fontSize: '12px', fontFamily: 'var(--font-mono)'
    }}>
      <button onClick={() => setOpen(v => !v)}
        style={{ background: 'none', border: 'none', cursor: 'pointer', padding: 0, width: '100%',
          display: 'flex', alignItems: 'center', gap: '6px', color: 'var(--tool-card-text)' }}>
        <Wrench size={12} />
        <strong>{name}</strong>
        {args && <span style={{ color: 'var(--tool-card-subtle-text)', fontWeight: 400 }}>
          ({Object.entries(args).map(([k,v]) => `${k}=${JSON.stringify(v)}`).join(', ')})
        </span>}
        <span style={{ marginLeft: 'auto', opacity: 0.5 }}>
          {open ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
        </span>
      </button>
      {open && result && (
        <pre style={{ margin: '8px 0 0 0', padding: '8px', background: 'var(--tool-card-pre-bg)',
          borderRadius: '4px', whiteSpace: 'pre-wrap', wordBreak: 'break-all',
          fontSize: '11px', maxHeight: '200px', overflowY: 'auto' }}>
          {JSON.stringify(result, null, 2)}
        </pre>
      )}
    </div>
  );
};

// ── Message Bubble ─────────────────────────────────────────────────────────────

const MessageBubble: React.FC<{ msg: Message }> = ({ msg }) => {
  const isUser = msg.role === 'user';
  const isSystem = msg.role === 'system';

  if (isSystem) {
    return (
      <div style={{ textAlign: 'center', padding: '6px', color: 'var(--text-secondary)', fontSize: '12px', fontStyle: 'italic' }}>
        {msg.content}
      </div>
    );
  }

  if (msg.role === 'tool') {
    return <ToolCallCard name={msg.toolName || 'tool'} args={msg.toolArgs} result={msg.toolResult} />;
  }

  return (
    <div style={{
      display: 'flex', gap: '10px', alignItems: 'flex-start',
      flexDirection: isUser ? 'row-reverse' : 'row',
      marginBottom: '12px'
    }}>
      <div style={{
        width: '32px', height: '32px', borderRadius: '50%', flexShrink: 0,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        background: isUser ? 'var(--accent-blue)' : 'var(--accent-purple)',
        color: 'white'
      }}>
        {isUser ? <User size={16} /> : <Bot size={16} />}
      </div>
      <div style={{
        maxWidth: '80%',
        padding: '10px 14px', borderRadius: isUser ? '12px 4px 12px 12px' : '4px 12px 12px 12px',
        background: isUser ? 'var(--accent-blue)' : 'var(--bg-secondary)',
        color: isUser ? 'white' : 'var(--text-primary)',
        border: isUser ? 'none' : '1px solid var(--border)',
        fontSize: '14px', lineHeight: '1.5',
        whiteSpace: 'pre-wrap', wordBreak: 'break-word'
      }}>
        {msg.content}
        {msg.simTime != null && (
          <div style={{ marginTop: '4px', fontSize: '11px', opacity: 0.6 }}>
            Sim time: {(msg.simTime / 3600).toFixed(2)}h
          </div>
        )}
      </div>
    </div>
  );
};

// ── Agent Page ─────────────────────────────────────────────────────────────────

export const AgentPage: React.FC = () => {
  const { sessions, fetchSessions, ws } = useSimStore();
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [sending, setSending] = useState(false);
  const [shortcuts, setShortcuts] = useState<Shortcut[]>([]);
  const [selectedSim, setSelectedSim] = useState<string>('');
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  const runningSims = sessions.filter(s => s.status === 'running' || s.status === 'paused');

  useEffect(() => {
    fetchSessions();
    loadShortcuts();
  }, []);

  useEffect(() => {
    if (runningSims.length > 0 && !selectedSim) {
      setSelectedSim(runningSims[0].id);
    }
  }, [runningSims]);

  useEffect(() => {
    // Subscribe to agent events via WebSocket
    if (!ws) return;
    const cleanup = ws.onMessage((msg: any) => {
      if (msg.type === 'agent_thinking' || msg.type === 'thinking') {
        appendMessage({ role: 'agent', content: msg.data.text, simTime: msg.data.sim_time_s });
      } else if (msg.type === 'tool_call') {
        appendMessage({ role: 'tool', content: '', toolName: msg.data.name, toolArgs: msg.data.args });
      } else if (msg.type === 'tool_result') {
        // Attach result to last tool message
        setMessages(prev => {
          const last = [...prev].reverse().find(m => m.role === 'tool' && m.toolName === msg.data.name && !m.toolResult);
          if (!last) return prev;
          return prev.map(m => m.id === last.id ? { ...m, toolResult: msg.data.result } : m);
        });
      } else if (msg.type === 'agent_response' || msg.type === 'response') {
        appendMessage({ role: 'agent', content: msg.data.text, simTime: msg.data.sim_time_s });
      } else if (msg.type === 'agent_error') {
        appendMessage({ role: 'system', content: `⚠ Agent error: ${msg.data.error}` });
      }
    });
    return () => { cleanup(); };
  }, [ws]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const appendMessage = (partial: Omit<Message, 'id' | 'timestamp'>) => {
    setMessages(prev => [...prev, {
      ...partial,
      id: `${Date.now()}-${Math.random()}`,
      timestamp: Date.now()
    }]);
  };

  const loadShortcuts = async () => {
    try {
      await api.shortcuts.seedDefaults();
      const data = await api.shortcuts.list();
      setShortcuts(Array.isArray(data) ? data : []);
    } catch { /* ignore */ }
  };

  const sendMessage = async (text: string) => {
    if (!text.trim() || !selectedSim || sending) return;
    setSending(true);

    appendMessage({ role: 'user', content: text.trim() });
    setInput('');

    try {
      await api.agent.sendMessage(selectedSim, text.trim());
      appendMessage({ role: 'system', content: 'Message delivered to agent. Response will appear when the next monitoring cycle runs.' });
    } catch (err: any) {
      appendMessage({ role: 'system', content: `⚠ Failed to send: ${err.message}` });
    }
    setSending(false);
    inputRef.current?.focus();
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage(input);
    }
  };

  const selectedSession = sessions.find(s => s.id === selectedSim);
  const canSend = !!selectedSim && !!selectedSession && (selectedSession.status === 'running' || selectedSession.status === 'paused') && selectedSession.mode === 'magi';

  return (
    <div style={{ display: 'flex', height: '100%', gap: '16px' }}>
      {/* Main chat area */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0 }}>
        {/* Header */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px', flexShrink: 0 }}>
          <div>
            <h2 style={{ margin: 0 }}>Cognitive Agent</h2>
            <p style={{ margin: '2px 0 0 0', fontSize: '13px', color: 'var(--text-secondary)' }}>
              Chat with MAGI Layer 4 — real-time monitoring &amp; intervention
            </p>
          </div>
          <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
            <select
              value={selectedSim}
              onChange={e => setSelectedSim(e.target.value)}
              style={{ padding: '6px 10px', borderRadius: '6px', border: '1px solid var(--border)',
                background: 'var(--bg-secondary)', color: 'var(--text-primary)', fontSize: '13px' }}
            >
              <option value="">— Select Simulation —</option>
              {sessions.map(s => (
                <option key={s.id} value={s.id}>
                  {s.label} ({s.status}) {s.mode !== 'magi' ? '⚠ not MAGI mode' : ''}
                </option>
              ))}
            </select>
            <button onClick={() => { fetchSessions(); }}
              style={{ background: 'var(--bg-tertiary)', border: 'none', padding: '8px', borderRadius: '6px',
                cursor: 'pointer', color: 'var(--text-secondary)' }}>
              <RefreshCw size={15} />
            </button>
          </div>
        </div>

        {/* Not MAGI mode warning */}
        {selectedSession && selectedSession.mode !== 'magi' && (
          <div style={{ padding: '12px 16px', borderRadius: '8px', background: 'var(--status-warning-bg)',
            border: '1px solid var(--status-warning-border)', color: 'var(--status-warning-text)',
            marginBottom: '16px', fontSize: '13px', flexShrink: 0 }}>
            ⚠ This simulation runs in <strong>baseline</strong> mode. The Cognitive Agent is only active in <strong>MAGI</strong> mode.
            Start a new simulation with mode set to "MAGI" to use the agent.
          </div>
        )}

        {/* Messages */}
        <div className="card" style={{ flex: 1, overflowY: 'auto', padding: '16px', minHeight: 0 }}>
          {messages.length === 0 && (
            <div style={{ height: '100%', display: 'flex', flexDirection: 'column', alignItems: 'center',
              justifyContent: 'center', color: 'var(--text-secondary)' }}>
              <Bot size={48} style={{ opacity: 0.15, marginBottom: '16px' }} />
              <p style={{ margin: 0, fontWeight: 500 }}>MAGI Cognitive Agent</p>
              <p style={{ margin: '4px 0 0', fontSize: '13px' }}>
                {canSend ? 'Use the shortcuts or type a message to interact with the agent.' : 'Select a running MAGI simulation to begin.'}
              </p>
            </div>
          )}
          {messages.map(msg => (
            <MessageBubble key={msg.id} msg={msg} />
          ))}
          <div ref={bottomRef} />
        </div>

        {/* Input area */}
        <div style={{ marginTop: '12px', flexShrink: 0 }}>
          <div style={{ display: 'flex', gap: '10px', alignItems: 'flex-end' }}>
            <textarea
              ref={inputRef}
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={canSend ? 'Message the MAGI Agent… (Enter to send, Shift+Enter for newline)' : 'Select a running MAGI simulation first'}
              disabled={!canSend || sending}
              rows={3}
              style={{
                flex: 1, padding: '10px 14px', borderRadius: '8px',
                border: '1px solid var(--border)', background: 'var(--bg-secondary)',
                color: 'var(--text-primary)', fontSize: '14px', resize: 'none',
                fontFamily: 'var(--font-sans)',
                opacity: (!canSend || sending) ? 0.6 : 1
              }}
            />
            <button
              onClick={() => sendMessage(input)}
              disabled={!canSend || !input.trim() || sending}
              style={{
                padding: '10px 16px', background: 'var(--accent-blue)', color: 'white',
                border: 'none', borderRadius: '8px', cursor: 'pointer',
                display: 'flex', alignItems: 'center', gap: '6px',
                opacity: (!canSend || !input.trim() || sending) ? 0.5 : 1,
                height: '42px', whiteSpace: 'nowrap'
              }}
            >
              <Send size={16} /> Send
            </button>
          </div>
        </div>
      </div>

      {/* Shortcuts sidebar */}
      <div style={{ width: '240px', flexShrink: 0, display: 'flex', flexDirection: 'column', gap: '12px' }}>
        <div className="card" style={{ padding: '16px', flex: 1, overflowY: 'auto' }}>
          <h3 style={{ margin: '0 0 14px 0', fontSize: '14px', fontWeight: 600,
            display: 'flex', alignItems: 'center', gap: '6px' }}>
            <Zap size={14} /> Quick Prompts
          </h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
            {shortcuts.map(sc => (
              <button
                key={sc.id}
                onClick={() => sendMessage(sc.content)}
                disabled={!canSend || sending}
                style={{
                  padding: '8px 10px', borderRadius: '6px', border: '1px solid var(--border)',
                  background: 'var(--bg-secondary)', color: 'var(--text-primary)',
                  cursor: canSend ? 'pointer' : 'not-allowed', textAlign: 'left',
                  fontSize: '12px', fontWeight: 500, transition: 'background 0.15s',
                  opacity: (!canSend || sending) ? 0.5 : 1
                }}
                title={sc.content}
              >
                <div style={{ color: 'var(--accent-blue)', fontSize: '10px', marginBottom: '2px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                  {sc.category}
                </div>
                {sc.name}
              </button>
            ))}
            {shortcuts.length === 0 && (
              <div style={{ color: 'var(--text-secondary)', fontSize: '12px', padding: '8px 0' }}>
                No shortcuts yet.
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
