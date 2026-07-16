import React, { useState, useEffect, useRef } from 'react';
import { Send, ArrowLeft, Plus, Mail, ShieldAlert, FileText, BarChart3, HelpCircle, CheckCircle2 } from 'lucide-react';
import toast from 'react-hot-toast';
import api from '../services/api';

import RecipientValidator from '../components/RecipientValidator';
import BridgeStatus from '../components/BridgeStatus';
import PersonalizationToolbar from '../components/PersonalizationToolbar';
import CampaignProgress from '../components/CampaignProgress';
import CampaignLogs from '../components/CampaignLogs';

export default function Campaigns() {
  const [view, setView] = useState('list'); // 'list' | 'compose'
  const [campaigns, setCampaigns] = useState([]);
  
  // Compose State
  const [activeCampaignId, setActiveCampaignId] = useState(null);
  const [campaignName, setCampaignName] = useState('New Campaign');
  const [fromEmail, setFromEmail] = useState('abhishek.jadon@technovion.com');
  const [subject, setSubject] = useState('');
  const [body, setBody] = useState('');
  const [cc, setCc] = useState('');
  const [bcc, setBcc] = useState('');
  const [validatedRecipients, setValidatedRecipients] = useState(null);
  const [bridgeHealthy, setBridgeHealthy] = useState(false);
  const [campaignStatus, setCampaignStatus] = useState('draft'); // draft, active, paused, completed, failed
  
  // Ref for textarea to insert variables
  const bodyRef = useRef(null);

  // Load campaigns
  useEffect(() => {
    if (view === 'list') {
      fetchCampaigns();
    }
  }, [view]);

  const fetchCampaigns = async () => {
    try {
      // Assuming a GET /campaigns endpoint exists
      const res = await api.get('/campaigns');
      setCampaigns(res.data.items || []);
    } catch (e) {
      console.error("Failed to load campaigns", e);
    }
  };

  const handleStartCampaign = async () => {
    if (!bridgeHealthy) {
      toast.error("Outlook Bridge is offline or unhealthy. Cannot start.");
      return;
    }
    
    if (!validatedRecipients || validatedRecipients.valid_count === 0) {
      toast.error("Please add and validate recipients first.");
      return;
    }
    
    if (!subject.trim() || !body.trim()) {
      toast.error("Subject and body are required.");
      return;
    }

    try {
      let currentCampaignId = activeCampaignId;
      
      // If we don't have a campaign yet, create one
      if (!currentCampaignId) {
        const createRes = await api.post('/campaigns', {
          name: campaignName,
          from_email: fromEmail,
          status: 'draft'
        });
        currentCampaignId = createRes.data.campaign_id;
        setActiveCampaignId(currentCampaignId);
        
        // Add template step
        const stepRes = await api.post(`/campaigns/${currentCampaignId}/steps`, {
          step_number: 1,
          subject: subject,
          body: body,
          delay_days: 0
        });
        
        // Enroll recipients (the valid ones)
        const validEmails = validatedRecipients.recipients.filter(r => r.status === 'valid').map(r => r.email);
        if (validEmails.length > 0) {
          await api.post(`/campaigns/${currentCampaignId}/enroll-emails`, {
            emails: validEmails
          });
        }
        
        toast.success("Campaign created. Starting engine...");
      }
      
      // Start the campaign
      await api.post(`/campaigns/${currentCampaignId}/start`);
      setCampaignStatus('active');
      toast.success("Campaign started successfully.");
    } catch (e) {
      toast.error(api.getErrorMessage(e) || "Failed to start campaign");
    }
  };

  const handleInsertVariable = (tag) => {
    const textarea = bodyRef.current;
    if (!textarea) return;
    
    const startPos = textarea.selectionStart;
    const endPos = textarea.selectionEnd;
    
    setBody(body.substring(0, startPos) + tag + body.substring(endPos));
    
    // Set focus back after state updates
    setTimeout(() => {
      textarea.focus();
      textarea.setSelectionRange(startPos + tag.length, startPos + tag.length);
    }, 0);
  };

  // --------------------------------------------------------
  // LIST VIEW
  // --------------------------------------------------------
  if (view === 'list') {
    return (
      <div className="page-container page-enter h-[calc(100vh-65px)] flex flex-col">
        <div className="flex justify-between items-center mb-6">
          <h1 className="page-title flex items-center gap-2"><Mail className="w-6 h-6 text-[var(--accent)]" /> Campaign Engine</h1>
          <button 
            onClick={() => {
              setActiveCampaignId(null);
              setCampaignStatus('draft');
              setValidatedRecipients(null);
              setSubject('');
              setBody('');
              setView('compose');
            }} 
            className="btn-primary flex items-center gap-2"
          >
            <Plus className="w-4 h-4" /> New Campaign
          </button>
        </div>

        <div className="flex-1 bg-[var(--panel-bg)] border border-[var(--card-border)] rounded-xl overflow-hidden">
          {campaigns.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full text-[var(--text-muted)]">
              <Mail className="w-12 h-12 mb-4 opacity-20" />
              <p>No campaigns found.</p>
              <p className="text-sm">Create a new campaign to start sending bulk emails.</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead className="bg-[var(--card-bg)] border-b border-[var(--card-border)] text-[var(--text-muted)] font-medium">
                  <tr>
                    <th className="px-6 py-4">Campaign Name</th>
                    <th className="px-6 py-4">Status</th>
                    <th className="px-6 py-4">Created</th>
                    <th className="px-6 py-4 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[var(--card-border)]">
                  {campaigns.map(c => (
                    <tr key={c.campaign_id} className="hover:bg-[var(--card-bg)]/50 transition-colors">
                      <td className="px-6 py-4 font-medium">{c.name}</td>
                      <td className="px-6 py-4">
                        <span className={`px-2 py-1 rounded-full text-xs ${
                          c.status === 'active' ? 'bg-green-500/20 text-green-400' :
                          c.status === 'paused' ? 'bg-yellow-500/20 text-yellow-400' :
                          'bg-[var(--card-border)] text-[var(--text-muted)]'
                        }`}>
                          {c.status.toUpperCase()}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-[var(--text-muted)]">{new Date(c.created_at).toLocaleDateString()}</td>
                      <td className="px-6 py-4 text-right">
                        <button 
                          onClick={() => {
                            setActiveCampaignId(c.campaign_id);
                            setCampaignName(c.name);
                            setCampaignStatus(c.status);
                            setView('compose');
                          }}
                          className="text-[var(--accent)] hover:underline"
                        >
                          View & Manage
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    );
  }

  // --------------------------------------------------------
  // COMPOSE / DETAIL VIEW
  // --------------------------------------------------------
  return (
    <div className="page-container page-enter h-[calc(100vh-65px)] flex flex-col">
      <div className="flex justify-between items-center mb-4">
        <div className="flex items-center gap-4">
          <button onClick={() => setView('list')} className="text-[var(--text-muted)] hover:text-white transition-colors">
            <ArrowLeft className="w-5 h-5" />
          </button>
          {activeCampaignId && campaignStatus !== 'draft' ? (
            <h1 className="page-title m-0">{campaignName}</h1>
          ) : (
            <input 
              type="text" 
              value={campaignName}
              onChange={(e) => setCampaignName(e.target.value)}
              className="page-title m-0 bg-transparent border-b border-transparent hover:border-[var(--card-border)] focus:border-[var(--accent)] outline-none"
            />
          )}
        </div>
        
        <div className="flex gap-3 items-center">
          <BridgeStatus onStatusChange={setBridgeHealthy} />
          
          {(campaignStatus === 'draft' || campaignStatus === 'paused') && (
            <button 
              onClick={handleStartCampaign}
              className={`btn-primary flex items-center gap-2 ${(!bridgeHealthy || (validatedRecipients?.valid_count || 0) === 0) ? 'opacity-50 cursor-not-allowed' : ''}`}
              disabled={!bridgeHealthy}
            >
              <Send className="w-4 h-4" /> 
              {campaignStatus === 'paused' ? 'Resume Campaign' : 'Start Engine'}
            </button>
          )}
        </div>
      </div>

      <div className="flex-1 grid grid-cols-12 gap-6 min-h-0 pb-6">
        {/* LEFT PANEL: Input Intelligence */}
        <div className="col-span-3 flex flex-col h-full">
          <RecipientValidator onValidated={setValidatedRecipients} />
        </div>

        {/* CENTER & RIGHT PANELS */}
        <div className="col-span-9 flex flex-col h-full gap-6 overflow-y-auto pr-2 custom-scrollbar">
          
          {/* Progress Dashboard (Only show if campaign is active/paused/completed) */}
          {activeCampaignId && (
            <div className="w-full">
              <CampaignProgress campaignId={activeCampaignId} onStatusChange={setCampaignStatus} />
            </div>
          )}

          <div className="grid grid-cols-3 gap-6 flex-1 min-h-[500px]">
            {/* Compose Area */}
            <div className="col-span-2 bg-[var(--panel-bg)] border border-[var(--card-border)] rounded-xl flex flex-col overflow-hidden">
              <div className="px-4 py-3 border-b border-[var(--card-border)] bg-[var(--card-bg)] flex justify-between items-center">
                <span className="font-medium text-sm flex items-center gap-2">
                  <FileText className="w-4 h-4 text-[var(--accent)]" /> Email Composer
                </span>
                {campaignStatus !== 'draft' && (
                  <span className="text-xs bg-yellow-500/20 text-yellow-500 px-2 py-1 rounded flex items-center gap-1">
                    <ShieldAlert className="w-3 h-3" /> Read-only while active
                  </span>
                )}
              </div>
              
              <div className="flex-1 p-4 flex flex-col gap-3 overflow-y-auto">
                <div className="flex items-center gap-3">
                  <label className="text-[var(--text-muted)] text-sm w-12 text-right">From:</label>
                  <select 
                    className="flex-1 bg-[var(--card-bg)] border border-[var(--card-border)] rounded-lg px-3 py-1.5 text-sm outline-none focus:border-[var(--accent)]"
                    value={fromEmail}
                    onChange={(e) => setFromEmail(e.target.value)}
                    disabled={campaignStatus !== 'draft'}
                  >
                    <option value="abhishek.jadon@technovion.com">abhishek.jadon@technovion.com (Outlook Default)</option>
                  </select>
                </div>
                <div className="flex items-center gap-3">
                  <label className="text-[var(--text-muted)] text-sm w-12 text-right">Cc:</label>
                  <input type="text" className="flex-1 bg-[var(--card-bg)] border border-[var(--card-border)] rounded-lg px-3 py-1.5 text-sm outline-none focus:border-[var(--accent)]" value={cc} onChange={(e)=>setCc(e.target.value)} disabled={campaignStatus !== 'draft'} placeholder="Optional" />
                </div>
                <div className="flex items-center gap-3">
                  <label className="text-[var(--text-muted)] text-sm w-12 text-right">Bcc:</label>
                  <input type="text" className="flex-1 bg-[var(--card-bg)] border border-[var(--card-border)] rounded-lg px-3 py-1.5 text-sm outline-none focus:border-[var(--accent)]" value={bcc} onChange={(e)=>setBcc(e.target.value)} disabled={campaignStatus !== 'draft'} placeholder="Optional" />
                </div>
                <div className="flex items-center gap-3">
                  <label className="text-[var(--text-muted)] text-sm w-12 text-right font-medium text-white">Subject:</label>
                  <input 
                    type="text" 
                    className="flex-1 bg-[var(--card-bg)] border border-[var(--card-border)] rounded-lg px-3 py-2 text-sm outline-none focus:border-[var(--accent)] font-medium" 
                    value={subject} 
                    onChange={(e)=>setSubject(e.target.value)} 
                    disabled={campaignStatus !== 'draft'} 
                    placeholder="Enter email subject..." 
                  />
                </div>
                
                <div className="mt-2 flex-1 flex flex-col">
                  {campaignStatus === 'draft' && (
                    <PersonalizationToolbar onInsert={handleInsertVariable} />
                  )}
                  <textarea 
                    ref={bodyRef}
                    className="flex-1 w-full bg-[var(--card-bg)] border border-[var(--card-border)] rounded-lg p-4 text-sm resize-none outline-none focus:border-[var(--accent)]"
                    placeholder="Write your email body here... Use variables from the toolbar above to personalize for each recipient."
                    value={body}
                    onChange={(e) => setBody(e.target.value)}
                    disabled={campaignStatus !== 'draft'}
                  />
                  <div className="text-xs text-[var(--text-muted)] mt-2 italic flex justify-end">
                    Your native Outlook signature will be automatically attached by the bridge.
                  </div>
                </div>
              </div>
            </div>

            {/* AI Assistant & Logs */}
            <div className="col-span-1 flex flex-col gap-6">
              {/* AI Assistant Panel */}
              <div className="bg-[var(--panel-bg)] border border-purple-500/30 rounded-xl overflow-hidden shadow-[0_0_15px_rgba(168,85,247,0.1)]">
                <div className="px-4 py-3 bg-purple-500/10 border-b border-purple-500/20 flex items-center gap-2 text-purple-400 font-medium text-sm">
                  <HelpCircle className="w-4 h-4" /> AI Campaign Assistant
                </div>
                <div className="p-4 flex flex-col gap-3 text-sm">
                  {subject.length > 50 && (
                    <div className="flex items-start gap-2 text-yellow-500">
                      <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
                      <span>Subject is longer than 50 characters, which may lower open rates on mobile.</span>
                    </div>
                  )}
                  {body.toLowerCase().includes('free') || body.toLowerCase().includes('guarantee') ? (
                    <div className="flex items-start gap-2 text-red-400">
                      <ShieldAlert className="w-4 h-4 shrink-0 mt-0.5" />
                      <span>Found potential spam trigger words ("free", "guarantee"). Consider rewording to improve deliverability.</span>
                    </div>
                  ) : null}
                  {(validatedRecipients?.valid_count || 0) > 0 ? (
                    <div className="flex items-start gap-2 text-green-400">
                      <CheckCircle2 className="w-4 h-4 shrink-0 mt-0.5" />
                      <span>{validatedRecipients.valid_count} valid recipients detected. Rate limiting (15-60s) will be automatically applied to protect sender reputation.</span>
                    </div>
                  ) : (
                    <div className="flex items-start gap-2 text-[var(--text-muted)]">
                      <BarChart3 className="w-4 h-4 shrink-0 mt-0.5" />
                      <span>Add recipients and write your email to get proactive suggestions.</span>
                    </div>
                  )}
                </div>
              </div>

              {/* Historical Logs */}
              {activeCampaignId && (
                <div className="flex-1">
                  <CampaignLogs campaignId={activeCampaignId} />
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
