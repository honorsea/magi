import React, { useEffect, useRef, useState } from 'react';
import { useSimStore } from '../store/simulationStore';
import { api } from '../api/client';
import { Send, Bot, User, Wrench, ChevronDown, ChevronRight, Zap, RefreshCw } from 'lucide-react';

// ── Types ─────────────────────────────────────────────────────────────────────

interface Message {
  id: string;
  role: 'user' | 'agent' | 'tool' | 'system';
  content: string;
  simId: string;
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
      background: 'hsl(262,60%,97%)', border: '1px solid hsl(262,60%,88%)',
      fontSize: '12px', fontFamily: 'var(--font-mono)'
    }}>
      <button onClick={() => setOpen(v => !v)}
        style={{ background: 'none', border: 'none', cursor: 'pointer', padding: 0, width: '100%',
          display: 'flex', alignItems: 'center', gap: '6px', color: 'hsl(262,70%,40%)' }}>
        <Wrench size={12} />
        <strong>{name}</strong>
        {args && <span style={{ color: 'hsl(262,40%,60%)', fontWeight: 400 }}>
          ({Object.entries(args).map(([k,v]) => `${k}=${JSON.stringify(v)}`).join(', ')})
        </span>}
        <span style={{ marginLeft: 'auto', opacity: 0.5 }}>
          {open ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
        </span>
      </button>
      {open && result && (
        <pre style={{ margin: '8px 0 0 0', padding: '8px', background: 'hsl(262,60%,94%)',
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
        background: isUser ? 'var(--accent-blue)' : 'hsl(262,70%,50%)',
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
  const { sessions, fetchSessions, ws, activeSessionId, setActiveSession } = useSimStore();
  const [messages, setMessages] = useState<Message[]>([]);
  const [messagesBySim, setMessagesBySim] = useState<Record<string, Message[]>>({});
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

  const appendMessage = (simId: string, partial: Omit<Message, 'id' | 'timestamp' | 'simId'>) => {
    const nextMessage: Message = {
      ...partial,
      simId,
      id: `${Date.now()}-${Math.random()}`,
      timestamp: Date.now()
    };
    setMessagesBySim(prev => {
      const next = [...(prev[simId] || []), nextMessage];
      return { ...prev, [simId]: next };
    });
  };

  useEffect(() => {
    if (!selectedSim || activeSessionId === selectedSim) return;
    setActiveSession(selectedSim);
  }, [selectedSim, activeSessionId, setActiveSession]);

  useEffect(() => {
    // Subscribe to events from active simulation websocket and gate by sim id.
    if (!ws || !selectedSim) return;
    const cleanup = ws.onMessage((msg: any) => {
      const eventSimId = msg?.sim_id ?? msg?.data?.sim_id ?? activeSessionId ?? selectedSim;
      if (!eventSimId || eventSimId !== selectedSim) return;

      if (msg.type === 'agent_thinking' || msg.type === 'thinking') {
        appendMessage(eventSimId, { role: 'agent', content: msg.data.text, simTime: msg.data.sim_time_s });
      } else if (msg.type === 'tool_call') {
        appendMessage(eventSimId, { role: 'tool', content: '', toolName: msg.data.name, toolArgs: msg.data.args });
      } else if (msg.type === 'tool_result') {
        // Attach result to last tool message
        setMessagesBySim(prev => {
          const simMessages = prev[eventSimId] || [];
          const last = [...simMessages].reverse().find(m => m.role === 'tool' && m.toolName === msg.data.name && !m.toolResult);
          if (!last) return prev;
          return {
            ...prev,
            [eventSimId]: simMessages.map(m => m.id === last.id ? { ...m, toolResult: msg.data.result } : m)
          };
        });
      } else if (msg.type === 'agent_response' || msg.type === 'response') {
        appendMessage(eventSimId, { role: 'agent', content: msg.data.text, simTime: msg.data.sim_time_s });
      } else if (msg.type === 'agent_error') {
        appendMessage(eventSimId, { role: 'system', content: `⚠ Agent error: ${msg.data.error}` });
      }
    });
    return () => { cleanup(); };
  }, [ws, selectedSim, activeSessionId]);

  useEffect(() => {
    setMessages(selectedSim ? (messagesBySim[selectedSim] || []) : []);
  }, [selectedSim, messagesBySim]);

  useEffect(() => {
    if (!selectedSim) {
      setMessages([]);
      return;
    }
    const loadTrace = async () => {
      try {
        const data = await api.agent.getTrace(selectedSim);
        const restored: Message[] = [];
        for (const trace of data.traces || []) {
          for (const entry of trace.entries || []) {
            if (entry.user_message) {
              restored.push({
                id: `${selectedSim}-trace-u-${trace.cycle_num}-${restored.length}`,
                role: 'user',
                content: entry.user_message,
                simId: selectedSim,
                timestamp: Math.floor((trace.recorded_at || 0) * 1000),
                simTime: entry.sim_time_s ?? trace.sim_time_s
              });
            }
            if (entry.agent_text) {
              restored.push({
                id: `${selectedSim}-trace-a-${trace.cycle_num}-${restored.length}`,
                role: 'agent',
                content: entry.agent_text,
                simId: selectedSim,
                timestamp: Math.floor((trace.recorded_at || 0) * 1000),
                simTime: entry.sim_time_s ?? trace.sim_time_s
              });
            }
          }
        }
        setMessagesBySim(prev => ({ ...prev, [selectedSim]: restored }));
      } catch (err: any) {
        setMessagesBySim(prev => ({
          ...prev,
          [selectedSim]: [...(prev[selectedSim] || []), {
            id: `${selectedSim}-trace-error-${Date.now()}`,
            role: 'system',
            content: `⚠ Failed to load trace history: ${err.message}`,
            simId: selectedSim,
            timestamp: Date.now()
          }]
        }));
      }
    };
    loadTrace();
  }, [selectedSim]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

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

    appendMessage(selectedSim, { role: 'user', content: text.trim() });
    setInput('');

    try {
      await api.agent.sendMessage(selectedSim, text.trim());
      appendMessage(selectedSim, { role: 'system', content: 'Message delivered to agent. Response will appear when the next monitoring cycle runs.' });
    } catch (err: any) {
      appendMessage(selectedSim, { role: 'system', content: `⚠ Failed to send: ${err.message}` });
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
          <div style={{ padding: '12px 16px', borderRadius: '8px', background: 'hsl(38,100%,96%)',
            border: '1px solid hsl(38,80%,80%)', color: 'hsl(38,80%,30%)',
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
