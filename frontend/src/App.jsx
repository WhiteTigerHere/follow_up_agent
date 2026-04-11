import React, { useState, useEffect } from 'react';
import * as api from './api';
import './App.css';

function FollowUpCard({ item, onApprove, onClose, onExplain, onReject, onModify, onReschedule }) {
  const [draftText, setDraftText] = useState(item.current_draft || '');
  const [isEditing, setIsEditing] = useState(false);
  const [isRescheduling, setIsRescheduling] = useState(false);
  const [rescheduleTime, setRescheduleTime] = useState(
    item.next_follow_up_at ? new Date(item.next_follow_up_at).toISOString().slice(0, 16) : ''
  );

  const getStageLabel = () => {
    if (['draft_ready', 'awaiting_approval'].includes(item.status)) return 'Action Needed';
    if (item.status === 'sent') return 'Sent';
    if (item.status === 'paused') return 'Paused';
    return 'Waiting';
  };

  const stages = [
    { key: 'created', label: 'Created' },
    { key: 'waiting', label: getStageLabel() },
    { key: 'followed_up_1', label: 'Follow Up 1' },
    { key: 'followed_up_2', label: 'Follow Up 2' },
    { key: 'escalated', label: item.status === 'closed' ? 'Closed' : 'Escalated' }
  ];

  const getStageIndex = (status) => {
    if (status === 'created') return 0;
    if (['waiting', 'draft_ready', 'awaiting_approval', 'sent', 'paused'].includes(status)) return 1;
    if (status === 'followed_up_1') return 2;
    if (status === 'followed_up_2') return 3;
    if (['escalated', 'closed'].includes(status)) return 4;
    return 1;
  };
  const currentIndex = getStageIndex(item.status);

  let timeSinceLastSent = null;
  if (item.last_sent_at) {
    const diffHours = (new Date() - new Date(item.last_sent_at + (item.last_sent_at.endsWith('Z') ? '' : 'Z'))) / (1000 * 60 * 60);
    timeSinceLastSent = diffHours < 1 ? 'less than an hour ago' : `${Math.floor(diffHours)} hours ago`;
  }

  useEffect(() => {
    setDraftText(item.current_draft || '');
  }, [item.current_draft]);

  return (
    <div className="card">
      <div className="card-header">
        <h3 className="card-title">{item.ask_summary}</h3>
        <div>
          <span className={`badge ${item.priority}`}>{item.priority}</span>
          <span className={`badge status-badge ${item.status}`} style={{ marginLeft: '0.5rem', whiteSpace: 'nowrap' }}>{item.status.replace('_', ' ')}</span>
        </div>
      </div>
      <div className="card-body">
        <p><strong>Target:</strong> {item.target_contact}</p>
        <p><strong>Source:</strong> {item.source_type} ({item.source_ref})</p>
        <p><strong>Due:</strong> {new Date(item.due_at).toLocaleString()}</p>
        <p><strong>Attempts:</strong> {item.attempts_count}</p>
        {timeSinceLastSent && <p><strong>Last Sent:</strong> {timeSinceLastSent}</p>}
        {item.next_follow_up_at && <p><strong>Next Follow-up:</strong> {new Date(item.next_follow_up_at).toLocaleString()}</p>}
      </div>

      <div className="progress-container">
        {stages.map((stage, idx) => {
           let markerClass = '';
           if (idx < currentIndex) markerClass = 'completed';
           else if (idx === currentIndex) {
             markerClass = (item.status === 'escalated') ? 'escalated' : 'current';
             if (item.status === 'closed') markerClass = 'completed';
           }
           
           return (
             <div key={idx} className="progress-step">
                <div className={`step-marker ${markerClass}`} />
                <div className={`step-label ${markerClass}`}>{stage.label}</div>
             </div>
           );
        })}
      </div>

      {isRescheduling && (
        <div style={{ marginTop: '1rem', background: 'rgba(0,0,0,0.2)', padding: '1rem', borderRadius: '4px' }}>
          <h4 style={{ marginBottom: '0.5rem' }}>Reschedule Follow-up</h4>
          <input 
            type="datetime-local" 
            className="form-control" 
            value={rescheduleTime} 
            onChange={e => setRescheduleTime(e.target.value)} 
          />
          <div style={{ display: 'flex', gap: '0.5rem', marginTop: '1rem' }}>
            <button className="btn" onClick={() => { onReschedule(item.id, new Date(rescheduleTime).toISOString()); setIsRescheduling(false); }}>Save</button>
            <button className="btn btn-danger" onClick={() => setIsRescheduling(false)}>Cancel</button>
          </div>
        </div>
      )}

      {item.status === 'draft_ready' && (
        <div style={{ marginTop: '1rem', padding: '1rem', background: 'rgba(0,0,0,0.2)', borderRadius: '4px' }}>
          <h4 style={{ marginBottom: '0.5rem', color: 'var(--primary)' }}>Generated Draft</h4>
          {isEditing ? (
            <textarea
              value={draftText}
              onChange={e => setDraftText(e.target.value)}
              style={{ width: '100%', minHeight: '150px', background: 'var(--surface)', color: 'var(--text)', padding: '0.5rem', border: '1px solid var(--border)', fontFamily: 'inherit' }}
            />
          ) : (
            <pre style={{ whiteSpace: 'pre-wrap', fontSize: '13px', lineHeight: '1.5' }}>{item.current_draft || 'No draft text saved.'}</pre>
          )}

          <div style={{ display: 'flex', gap: '0.5rem', marginTop: '1rem', flexWrap: 'wrap' }}>
            {isEditing ? (
              <button className="btn" onClick={() => { onModify(item.id, draftText); setIsEditing(false); }}>Save Edits</button>
            ) : (
              <button className="btn" style={{ background: 'rgba(255,255,255,0.1)' }} onClick={() => setIsEditing(true)}>Edit Draft</button>
            )}
            <button className="btn" style={{ background: 'var(--border)', color: 'white' }} onClick={() => onReject(item.id)}>Reject</button>
            <button className="btn" style={{ background: 'var(--primary)', flexGrow: 1 }} onClick={() => onApprove(item.id)}>Approve</button>
          </div>
        </div>
      )}

      <div className="actions" style={{ marginTop: '1rem' }}>
        {item.status !== 'closed' && item.status !== 'escalated' && (
           <button className="btn" style={{ background: 'rgba(255,255,255,0.05)' }} onClick={() => setIsRescheduling(!isRescheduling)}>Reschedule</button>
        )}
        <button className="btn" style={{ background: 'rgba(255,255,255,0.05)' }} onClick={() => onExplain(item.id)}>Explain</button>
        <button className="btn btn-danger" onClick={() => onClose(item.id)}>Close Task</button>
      </div>
    </div>
  );
}

function CreateForm({ onCreated }) {
  const getLocalISOTime = () => {
    const tzoffset = (new Date()).getTimezoneOffset() * 60000; 
    return (new Date(Date.now() - tzoffset)).toISOString().slice(0, 16);
  };

  const [formData, setFormData] = useState({
    workspace_id: 'ws_1',
    requester_user_id: 'user_1',
    source_type: 'manual',
    source_ref: 'manual_entry_1',
    target_persons: '',
    ask_summary: '',
    due_date_time: getLocalISOTime(),
    urgency: 'medium',
    action_mode: 'approval_required'
  });
  const [isImporting, setIsImporting] = useState(false);
  const [importStatus, setImportStatus] = useState('');

  const handleImport = async () => {
    if (!formData.source_ref) {
      alert("Please enter a Thread ID in the Source Ref field");
      return;
    }
    setIsImporting(true);
    setImportStatus('Importing...');
    try {
      const res = await api.importGmailThread(formData.source_ref);
      setImportStatus(`Success! ${res.data.messages_stored} messages ingested.`);
    } catch (err) {
      setImportStatus(`Import failed: ${err.response?.data?.detail || err.message}`);
    }
    setIsImporting(false);
  };
  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      const payload = { ...formData, target_persons: formData.target_persons.split(',').map(s => s.trim()) };
      // Add timezone 'Z' if missing for simplicity
      payload.due_date_time = new Date(payload.due_date_time).toISOString();
      await api.createFollowUp(payload);
      onCreated();
    } catch (err) {
      alert("Error creating: " + err);
    }
  };

  return (
    <form className="card" onSubmit={handleSubmit}>
      <h2 style={{ marginBottom: '1.5rem' }}>Create Manual Follow-up</h2>
      <div className="form-group">
        <label>Source Type</label>
        <select className="form-control" value={formData.source_type} onChange={e => setFormData({ ...formData, source_type: e.target.value })}>
          <option value="manual">Manual</option>
          <option value="email">Email Thread</option>
          <option value="task">Task / Ticket</option>
          <option value="meeting">Meeting</option>
        </select>
      </div>
      <div className="form-group">
        <label>Source Reference (e.g. Thread ID)</label>
        <div style={{ display: 'flex', gap: '0.5rem' }}>
          <input required type="text" className="form-control" value={formData.source_ref} onChange={e => setFormData({ ...formData, source_ref: e.target.value })} placeholder="Thread ID or Link" />
          {formData.source_type === 'email' && (
            <button type="button" className="btn" style={{ whiteSpace: 'nowrap' }} disabled={isImporting} onClick={handleImport}>
              {isImporting ? '⏳ Importing...' : '📥 Import Thread Context'}
            </button>
          )}
        </div>
        {importStatus && <p style={{ fontSize: '12px', marginTop: '4px', color: importStatus.startsWith('Success') ? 'var(--primary)' : 'var(--danger)' }}>{importStatus}</p>}
      </div>
      <div className="form-group">
        <label>Ask Summary</label>
        <input required type="text" className="form-control" value={formData.ask_summary} onChange={e => setFormData({ ...formData, ask_summary: e.target.value })} placeholder="E.g. Get Q3 Report" />
      </div>
      <div className="form-group">
        <label>Target Email/Slack</label>
        <input required type="text" className="form-control" value={formData.target_persons} onChange={e => setFormData({ ...formData, target_persons: e.target.value })} placeholder="alice@example.com" />
      </div>
      <div className="form-group">
        <label>Due Date & Time</label>
        <input required type="datetime-local" className="form-control" value={formData.due_date_time} onChange={e => setFormData({ ...formData, due_date_time: e.target.value })} />
      </div>
      <div className="form-group">
        <label>Urgency</label>
        <select className="form-control" value={formData.urgency} onChange={e => setFormData({ ...formData, urgency: e.target.value })}>
          <option value="low">Low</option>
          <option value="medium">Medium</option>
          <option value="high">High</option>
          <option value="urgent">Urgent</option>
        </select>
      </div>
      <div className="form-group">
        <label>Action Mode</label>
        <select className="form-control" value={formData.action_mode} onChange={e => setFormData({ ...formData, action_mode: e.target.value })}>
          <option value="approval_required">Mode A: Approval Required (Default)</option>
          <option value="draft_only">Mode B: Draft Only (Assisted)</option>
          <option value="auto_send">Mode C: Auto Send (Automated)</option>
        </select>
        {formData.action_mode === 'auto_send' && <p style={{ fontSize: '12px', color: 'var(--warning)', marginTop: '4px' }}>Note: Must pass domain/keyword validation or will fallback to Mode A.</p>}
      </div>
      <button type="submit" className="btn" style={{ width: '100%' }}>Create Follow-up</button>
    </form>
  )
}

function ExplainModal({ data, onClose }) {
  if (!data) return null;
  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={e => e.stopPropagation()}>
        <h2>Follow-up Explanation</h2>
        <div style={{ marginTop: '1rem', color: 'var(--text-muted)' }}>
          <p><strong>Pending:</strong> {data.what_is_pending}</p>
          <p><strong>Owner:</strong> {data.who_owes_it}</p>
          <p><strong>Reason:</strong> {data.why_triggered}</p>
          <p><strong>Next steps:</strong> {data.what_happens_next}</p>
        </div>

        <h3 style={{ marginTop: '1.5rem' }}>Timeline</h3>
        <div className="timeline">
          {data.timeline.map((evt, idx) => (
            <div key={idx} className="timeline-item">
              <strong>{evt.event_type}</strong> - {new Date(evt.created_at).toLocaleString()}<br />
              <div style={{ marginTop: '0.5rem' }}>
                {evt.payload.reason && (
                  <p style={{ color: 'var(--text-muted)', fontStyle: 'italic', marginBottom: '0.5rem' }}>{evt.payload.reason}</p>
                )}
                {evt.payload.execution_request && (
                  <div style={{ marginTop: '0.5rem', marginBottom: '0.5rem', background: 'rgba(0,0,0,0.3)', padding: '0.5rem', borderRadius: '4px' }}>
                    <p style={{ fontSize: '11px', textTransform: 'uppercase', color: 'var(--primary)', marginBottom: '0.25rem' }}>Execution Request Payload</p>
                    <pre style={{ margin: 0, fontSize: '12px', overflowX: 'auto', color: 'var(--text-muted)' }}>
                      {JSON.stringify(evt.payload.execution_request, null, 2)}
                    </pre>
                  </div>
                )}
                {evt.payload.draft && (
                  <div style={{ background: 'rgba(255,255,255,0.05)', padding: '1rem', borderRadius: '4px', borderLeft: '3px solid var(--primary)', whiteSpace: 'pre-wrap', fontSize: '13px' }}>
                    {evt.payload.draft}
                  </div>
                )}
                {!evt.payload.reason && !evt.payload.draft && !evt.payload.execution_request && (
                  <small>{JSON.stringify(evt.payload)}</small>
                )}
              </div>
            </div>
          ))}
          {data.timeline.length === 0 && <p>No events yet.</p>}
        </div>
        <button className="btn" style={{ marginTop: '2rem', width: '100%' }} onClick={onClose}>Close</button>
      </div>
    </div>
  )
}

import Login from './Login';

function App() {
  const [activeTab, setActiveTab] = useState('pending');
  const [items, setItems] = useState([]);
  const [explainData, setExplainData] = useState(null);
  const [reportData, setReportData] = useState(null);
  const [isAuthenticated, setIsAuthenticated] = useState(!!localStorage.getItem('token'));
  const [myWorkspaces, setMyWorkspaces] = useState([]);
  const [adminWorkspace, setAdminWorkspace] = useState(null);
  const [workspaceMembers, setWorkspaceMembers] = useState([]);
  const [addMemberEmail, setAddMemberEmail] = useState('');
  const [addMemberRole, setAddMemberRole] = useState('user');

  const handleLogout = () => {
    localStorage.removeItem('token');
    setIsAuthenticated(false);
  };

  const loadData = async () => {
    if (!isAuthenticated) return;
    try {
      // Always ensure we have workspace info
      if (myWorkspaces.length === 0) {
        const wsRes = await api.getMyWorkspaces();
        setMyWorkspaces(wsRes.data);
        const adminWs = wsRes.data.find(w => w.user_role === 'admin');
        if (adminWs) {
           setAdminWorkspace(adminWs);
        }
      }

      if (activeTab === 'active') {
        const res = await api.getActive();
        setItems(res.data);
      } else if (activeTab === 'pending') {
        const res = await api.getPending();
        setItems(res.data);
      } else if (activeTab === 'overdue') {
        const res = await api.getOverdue();
        setItems(res.data);
      } else if (activeTab === 'escalations') {
        const res = await api.getReport();
        setReportData(res.data);
      } else if (activeTab === 'admin' && adminWorkspace) {
        const res = await api.getWorkspaceMembers(adminWorkspace.id);
        setWorkspaceMembers(res.data);
      } else {
        setItems([]);
      }
    } catch (err) {
      if (err.response?.status === 401) {
        handleLogout();
      }
      console.error(err);
    }
  };

  useEffect(() => {
    loadData();
    // Auto-refresh interval (for scheduler changes)
    const interval = setInterval(loadData, 5000);
    return () => clearInterval(interval);
  }, [activeTab, isAuthenticated]);

  const handleApprove = async (id) => {
    await api.approveFollowUp(id);
    loadData();
  };

  const handleClose = async (id) => {
    await api.closeFollowUp(id);
    loadData();
  };

  const handleReject = async (id) => {
    await api.rejectFollowUp(id);
    loadData();
  };

  const handleModify = async (id, new_text) => {
    await api.modifyFollowUp(id, new_text);
    loadData();
  };

  const handleExplain = async (id) => {
    const res = await api.explainFollowUp(id);
    setExplainData(res.data);
  };

  const handleReschedule = async (id, new_time) => {
    await api.rescheduleFollowUp(id, new_time);
    loadData();
  };

  const handleAddMember = async (e) => {
    e.preventDefault();
    if (!addMemberEmail) return;
    try {
      await api.addWorkspaceMember(adminWorkspace.id, addMemberEmail, addMemberRole);
      setAddMemberEmail('');
      loadData();
    } catch (err) {
      alert(err.response?.data?.detail || "Failed to add member. They may need to join via code first.");
    }
  };

  const handleRemoveMember = async (userId) => {
    if (!window.confirm("Are you sure you want to remove this member?")) return;
    try {
      await api.removeWorkspaceMember(adminWorkspace.id, userId);
      loadData();
    } catch (err) {
      alert(err.response?.data?.detail || "Failed to remove member.");
    }
  };

  if (!isAuthenticated) {
    return <Login onLoginSuccess={() => setIsAuthenticated(true)} />;
  }

  return (
    <div className="app-container">
      <header style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h1>Follow-Up Agent</h1>
          <p style={{ color: 'var(--text-muted)', marginTop: '0.5rem' }}>Your semantic assistant for zero-chase execution.</p>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '1.5rem' }}>
          {myWorkspaces.length > 0 && (
            <div className="org-badge">
              <div className="org-code-wrapper">
                <div className="org-name">{myWorkspaces[0].name}</div>
                <div className="org-code">{myWorkspaces[0].join_code}</div>
              </div>
              <div className="org-badge-icon">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path>
                  <circle cx="9" cy="7" r="4"></circle>
                  <path d="M23 21v-2a4 4 0 0 0-3-3.87"></path>
                  <path d="M16 3.13a4 4 0 0 1 0 7.75"></path>
                </svg>
              </div>
            </div>
          )}
          <button className="btn btn-danger" onClick={handleLogout}>Logout</button>
        </div>
      </header>

      <div className="tabs">
        <button className={`tab-btn ${activeTab === 'pending' ? 'active' : ''}`} onClick={() => setActiveTab('pending')}>Pending</button>
        <button className={`tab-btn ${activeTab === 'overdue' ? 'active' : ''}`} onClick={() => setActiveTab('overdue')}>Overdue</button>
        <button className={`tab-btn ${activeTab === 'escalations' ? 'active' : ''}`} onClick={() => setActiveTab('escalations')}>Report & Escalations</button>
        <button className={`tab-btn ${activeTab === 'active' ? 'active' : ''}`} onClick={() => setActiveTab('active')}>Active Follow-Ups</button>
        <button className={`tab-btn ${activeTab === 'create' ? 'active' : ''}`} onClick={() => setActiveTab('create')}>+ Create New</button>
        {adminWorkspace && (
          <button className={`tab-btn ${activeTab === 'admin' ? 'active' : ''}`} style={{ borderLeft: '1px solid rgba(255,255,255,0.1)', marginLeft: '0.5rem', paddingLeft: '1.5rem', color: 'var(--primary)' }} onClick={() => setActiveTab('admin')}>Admin Panel</button>
        )}
      </div>

      <main>
        {['active', 'pending', 'overdue'].includes(activeTab) && (
          <div className="grid">
            {items.map(item => (
                <FollowUpCard
                  key={item.id}
                  item={item}
                  onApprove={handleApprove}
                  onClose={handleClose}
                  onExplain={handleExplain}
                  onReject={handleReject}
                  onModify={handleModify}
                  onReschedule={handleReschedule}
                />
            ))}
            {items.length === 0 && <p style={{ color: 'var(--text-muted)' }}>No {activeTab} follow-ups.</p>}
          </div>
        )}

        {activeTab === 'create' && (
          <div style={{ maxWidth: '600px' }}>
            <CreateForm onCreated={() => { setActiveTab('pending'); loadData(); }} />
          </div>
        )}

        {activeTab === 'escalations' && reportData && (
          <div>
            <div className="card" style={{ marginBottom: '2rem', borderLeft: '4px solid var(--warning)' }}>
              <h3>Status Check</h3>
              <p style={{ marginTop: '0.5rem', color: 'var(--text-muted)' }}>{reportData.blocking_you_summary}</p>
            </div>
            <h2>Escalated Items</h2>
            <div className="grid" style={{ marginTop: '1.5rem' }}>
              {reportData.escalations.map(item => (
                <FollowUpCard
                  key={item.id}
                  item={item}
                  onApprove={handleApprove}
                  onClose={handleClose}
                  onExplain={handleExplain}
                  onReject={handleReject}
                  onModify={handleModify}
                />
              ))}
              {reportData.escalations.length === 0 && <p style={{ color: 'var(--text-muted)' }}>No escalations currently.</p>}
            </div>
          </div>
        )}

        {activeTab === 'admin' && adminWorkspace && (
          <div style={{ maxWidth: '800px' }}>
            <h2 style={{ marginBottom: '1.5rem' }}>Workspace Administration: {adminWorkspace.name}</h2>
            
            <div className="card" style={{ marginBottom: '2rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                  <h3 style={{ color: 'var(--primary)' }}>Organization Join Code</h3>
                  <p style={{ color: 'var(--text-muted)', marginTop: '0.5rem', fontSize: '0.9rem' }}>Share this code with your team members so they can join this workspace.</p>
                </div>
                <div style={{ background: 'rgba(255,255,255,0.05)', padding: '0.75rem 1.5rem', borderRadius: '8px', fontSize: '1.5rem', letterSpacing: '2px', fontWeight: 'bold' }}>
                  {adminWorkspace.join_code}
                </div>
              </div>
            </div>

            <div className="card" style={{ marginBottom: '2rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
                <h3>Administrators</h3>
              </div>
              <table style={{ width: '100%', textAlign: 'left', borderCollapse: 'collapse' }}>
                <thead>
                  <tr style={{ borderBottom: '1px solid var(--border)', color: 'var(--text-muted)' }}>
                    <th style={{ padding: '0.5rem 0', width: '50px' }}>#</th>
                    <th style={{ padding: '0.5rem 0' }}>Email Address</th>
                    <th style={{ padding: '0.5rem 0' }}>Joined At</th>
                    <th style={{ padding: '0.5rem 0', textAlign: 'right' }}>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {workspaceMembers.filter(m => m.role === 'admin').map((member, index) => (
                    <tr key={member.user_id} style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                      <td style={{ padding: '0.75rem 0', color: 'var(--text-muted)' }}>{index + 1}</td>
                      <td style={{ padding: '0.75rem 0', fontWeight: '500' }}>{member.email || member.user_id}</td>
                      <td style={{ padding: '0.75rem 0', fontSize: '0.9rem', color: 'var(--text-muted)' }}>{new Date(member.created_at).toLocaleDateString()}</td>
                      <td style={{ padding: '0.75rem 0', textAlign: 'right' }}>
                         <button className="btn btn-danger" style={{ padding: '0.25rem 0.5rem', fontSize: '0.8rem' }} onClick={() => handleRemoveMember(member.user_id)}>Remove</button>
                      </td>
                    </tr>
                  ))}
                  {workspaceMembers.filter(m => m.role === 'admin').length === 0 && (
                    <tr><td colSpan="4" style={{ padding: '1rem 0', textAlign: 'center', color: 'var(--text-muted)' }}>No administrators found.</td></tr>
                  )}
                </tbody>
              </table>
            </div>

            <div className="card" style={{ marginBottom: '2rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
                <h3>Users</h3>
              </div>
              <table style={{ width: '100%', textAlign: 'left', borderCollapse: 'collapse' }}>
                <thead>
                  <tr style={{ borderBottom: '1px solid var(--border)', color: 'var(--text-muted)' }}>
                    <th style={{ padding: '0.5rem 0', width: '50px' }}>#</th>
                    <th style={{ padding: '0.5rem 0' }}>Email Address</th>
                    <th style={{ padding: '0.5rem 0' }}>Joined At</th>
                    <th style={{ padding: '0.5rem 0', textAlign: 'right' }}>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {workspaceMembers.filter(m => m.role === 'user').map((member, index) => (
                    <tr key={member.user_id} style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                      <td style={{ padding: '0.75rem 0', color: 'var(--text-muted)' }}>{index + 1}</td>
                      <td style={{ padding: '0.75rem 0', fontWeight: '500' }}>{member.email || member.user_id}</td>
                      <td style={{ padding: '0.75rem 0', fontSize: '0.9rem', color: 'var(--text-muted)' }}>{new Date(member.created_at).toLocaleDateString()}</td>
                      <td style={{ padding: '0.75rem 0', textAlign: 'right' }}>
                         <button className="btn btn-danger" style={{ padding: '0.25rem 0.5rem', fontSize: '0.8rem' }} onClick={() => handleRemoveMember(member.user_id)}>Remove</button>
                      </td>
                    </tr>
                  ))}
                  {workspaceMembers.filter(m => m.role === 'user').length === 0 && (
                    <tr><td colSpan="4" style={{ padding: '1rem 0', textAlign: 'center', color: 'var(--text-muted)' }}>No regular users found.</td></tr>
                  )}
                </tbody>
              </table>
            </div>

            <div className="card" style={{ marginBottom: '2rem' }}>
              <h3 style={{ marginBottom: '1rem' }}>Add Member or Change Role</h3>
              <form onSubmit={handleAddMember} style={{ display: 'flex', gap: '1rem', alignItems: 'flex-end' }}>
                <div style={{ flex: 1 }}>
                  <label style={{ display: 'block', marginBottom: '0.5rem', fontSize: '0.9rem' }}>Email Address</label>
                  <input type="email" required className="form-control" value={addMemberEmail} onChange={e => setAddMemberEmail(e.target.value)} placeholder="user@example.com" />
                </div>
                <div style={{ width: '150px' }}>
                  <label style={{ display: 'block', marginBottom: '0.5rem', fontSize: '0.9rem' }}>Role</label>
                  <select className="form-control" value={addMemberRole} onChange={e => setAddMemberRole(e.target.value)}>
                    <option value="user">User</option>
                    <option value="admin">Admin</option>
                  </select>
                </div>
                <button type="submit" className="btn">Apply</button>
              </form>
            </div>

            <div className="card" style={{ borderLeft: '4px solid var(--primary)' }}>
              <h3>Organization RAG Pipeline Settings</h3>
              <p style={{ marginTop: '0.5rem', color: 'var(--text-muted)', fontSize: '0.9rem', marginBottom: '1.5rem' }}>
                Upload brand guidelines, tone-of-voice documents, and product context. The Follow-up Agent will use this knowledge for every draft generated in this workspace.
              </p>
              
              <div style={{ display: 'flex', gap: '1rem' }}>
                <button className="btn" style={{ background: 'rgba(255,255,255,0.05)' }} onClick={() => alert('File upload pending')}>Upload Document (PDF/TXT)</button>
                <button className="btn" style={{ background: 'rgba(255,255,255,0.05)' }} onClick={() => alert('Sync pending')}>Sync with Google Drive</button>
              </div>

              <div style={{ marginTop: '1.5rem', background: 'rgba(0,0,0,0.2)', padding: '1rem', borderRadius: '8px' }}>
                <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem', textAlign: 'center' }}>No documents uploaded yet.</p>
              </div>
            </div>
          </div>
        )}
      </main>

      {explainData && (
        <ExplainModal data={explainData} onClose={() => setExplainData(null)} />
      )}
    </div>
  );
}

export default App;
