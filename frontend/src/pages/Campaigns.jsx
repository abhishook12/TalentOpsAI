import React, { useState, useEffect } from 'react';
import { 
  Send, ArrowLeft, Plus, Mail, Activity, AlertCircle, FileText, 
  CheckCircle2, Loader2, ChevronRight, Play, Eye
} from 'lucide-react';
import toast from 'react-hot-toast';
import api from '../services/api';

import RecipientValidator from '../components/RecipientValidator';
import BridgeStatus from '../components/BridgeStatus';
import RichTextComposer from '../components/RichTextComposer';
import SignatureManager from '../components/SignatureManager';
import EmailPreview from '../components/EmailPreview';
import CampaignProgress from '../components/CampaignProgress';
import CampaignLogs from '../components/CampaignLogs';

const STEPS = {
  RECIPIENTS: 1,
  COMPOSE: 2,
  PREVIEW: 3,
  SEND: 4
};

export default function Campaigns() {
  const [view, setView] = useState('list'); // 'list' | 'wizard'
  const [campaigns, setCampaigns] = useState([]);
  const [loading, setLoading] = useState(false);
  
  // Wizard State
  const [currentStep, setCurrentStep] = useState(STEPS.RECIPIENTS);
  const [activeCampaignId, setActiveCampaignId] = useState(null);
  const [campaignName, setCampaignName] = useState('New Campaign');
  
  // Compose State
  const [fromEmail, setFromEmail] = useState('abhishek.jadon@technovion.com');
  const [subject, setSubject] = useState('');
  const [body, setBody] = useState('');
  const [signatureId, setSignatureId] = useState(null);
  
  // Recipient State
  const [validatedRecipients, setValidatedRecipients] = useState({ recipients: [], valid_count: 0 });
  
  // Pre-flight State
  const [preflightData, setPreflightData] = useState(null);
  const [isValidating, setIsValidating] = useState(false);
  const [bridgeHealthy, setBridgeHealthy] = useState(false);

  useEffect(() => {
    if (view === 'wizard' && activeCampaignId && currentStep !== STEPS.SEND) {
      const timer = setTimeout(() => {
        saveDraft();
      }, 5000); // Save every 5s if changed (simplified)
      return () => clearTimeout(timer);
    }
  }, [subject, body, signatureId, view]);

  // Load campaigns
  useEffect(() => {
    if (view === 'list') {
      fetchCampaigns();
    }
  }, [view]);

  const fetchCampaigns = async () => {
    try {
      setLoading(true);
      const res = await api.get('/campaigns');
      setCampaigns(Array.isArray(res.data) ? res.data : res.data.items || []);
    } catch (e) {
      console.error("Failed to load campaigns", e);
      toast.error("Failed to load campaigns");
    } finally {
      setLoading(false);
    }
  };

  const startNewCampaign = () => {
    setActiveCampaignId(null);
    setCampaignName('New Campaign');
    setSubject('');
    setBody('');
    setSignatureId(null);
    setValidatedRecipients({ recipients: [], valid_count: 0 });
    setCurrentStep(STEPS.RECIPIENTS);
    setView('wizard');
  };

  const saveDraft = async () => {
    try {
      if (activeCampaignId) {
        // Update existing campaign
        await api.put(`/campaigns/${activeCampaignId}`, {
          name: campaignName,
          from_email: fromEmail,
          signature_id: signatureId
        });
        
        // Update or create template step
        // For simplicity we assume step 1 exists if campaign exists, or backend handles it
        // Actually we need to make sure we create a step if it doesn't exist
        return activeCampaignId;
      } else {
        // Create new campaign shell
        const res = await api.post('/campaigns', {
          name: campaignName,
          from_email: fromEmail,
          status: 'draft',
          signature_id: signatureId
        });
        setActiveCampaignId(res.data.campaign_id);
        return res.data.campaign_id;
      }
    } catch (e) {
      console.error("Draft save failed", e);
      return null;
    }
  };

  const runPreflight = async (currentId) => {
    let cid = currentId || activeCampaignId;
    if (!cid) cid = await saveDraft();
    
    setIsValidating(true);
    try {
      // First save the template so preview/preflight works
      if (cid) {
        try {
          await api.post(`/campaigns/${cid}/steps`, {
            step_order: 1, // backend uses step_order
            subject: subject || 'No Subject',
            body: body || 'No Body',
            delay_days: 0
          });
        } catch (e) {
          console.error("Error saving step", e);
        }
      }

      const res = await api.post(`/campaigns/${cid}/validate-before-send`);
      setPreflightData(res.data);
    } catch (e) {
      console.error("Preflight failed", e);
      toast.error("Validation failed");
    } finally {
      setIsValidating(false);
    }
  };

  const handleNextStep = async () => {
    if (currentStep === STEPS.RECIPIENTS) {
      if (validatedRecipients.valid_count === 0) {
        toast.error("Please add at least one valid recipient.");
        return;
      }
      setCurrentStep(STEPS.COMPOSE);
    } 
    else if (currentStep === STEPS.COMPOSE) {
      if (!subject.trim() || !body.trim()) {
        toast.error("Subject and body are required.");
        return;
      }
      const cid = await saveDraft();
      
      // Need to enroll recipients before preview so we have recruiters attached
      if (cid && validatedRecipients.valid_count > 0) {
        const validEmails = validatedRecipients.recipients.filter(r => r.status === 'valid').map(r => r.email);
        try {
          await api.post(`/campaigns/${cid}/enroll-emails`, {
            emails: validEmails
          });
        } catch (e) {
          console.error("Failed to enroll", e);
        }
      }
      
      setCurrentStep(STEPS.PREVIEW);
      runPreflight(cid);
    }
    else if (currentStep === STEPS.PREVIEW) {
      if (!preflightData?.ready) {
        toast.error("Cannot proceed. Please fix validation errors.");
        return;
      }
      startCampaign();
    }
  };

  const startCampaign = async () => {
    try {
      await api.post(`/campaigns/${activeCampaignId}/start`);
      setCurrentStep(STEPS.SEND);
      toast.success("Campaign engine started successfully!");
    } catch (e) {
      toast.error(api.getErrorMessage(e) || "Failed to start campaign");
    }
  };

  const renderList = () => (
    <div className="h-full flex flex-col">
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-2xl font-semibold text-[var(--text-primary)]">Campaigns</h1>
          <p className="text-sm text-[var(--text-secondary)] mt-1">Manage outbound email campaigns</p>
        </div>
        <div className="flex items-center gap-4">
          <BridgeStatus onStatusChange={setBridgeHealthy} />
          <button 
            onClick={startNewCampaign}
            className="bg-[var(--accent)] text-white px-4 py-2 rounded-lg text-sm font-medium flex items-center gap-2 hover:bg-[var(--accent)]/90 transition-colors"
          >
            <Plus size={16} /> New Campaign
          </button>
        </div>
      </div>

      <div className="bg-[var(--card-bg)] border border-[var(--card-border)] rounded-xl flex-1 overflow-hidden">
        {loading ? (
          <div className="h-full flex justify-center items-center">
            <Loader2 className="w-8 h-8 animate-spin text-[var(--accent)]" />
          </div>
        ) : campaigns.length === 0 ? (
          <div className="h-full flex flex-col justify-center items-center text-[var(--text-muted)] space-y-4">
            <Activity className="w-12 h-12 opacity-20" />
            <p>No campaigns found.</p>
            <button onClick={startNewCampaign} className="text-[var(--accent)] hover:underline text-sm font-medium">Create your first campaign</button>
          </div>
        ) : (
          <table className="w-full text-left text-sm">
            <thead className="bg-[var(--bg-surface)] border-b border-[var(--card-border)] text-[var(--text-secondary)]">
              <tr>
                <th className="px-6 py-4 font-medium">Campaign Name</th>
                <th className="px-6 py-4 font-medium">Status</th>
                <th className="px-6 py-4 font-medium">Created</th>
                <th className="px-6 py-4 font-medium">Speed</th>
                <th className="px-6 py-4 font-medium text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[var(--card-border)]">
              {campaigns.map(c => (
                <tr key={c.campaign_id} className="hover:bg-[var(--bg-surface)] transition-colors">
                  <td className="px-6 py-4">
                    <div className="font-medium text-[var(--text-primary)]">{c.name}</div>
                    <div className="text-xs text-[var(--text-muted)] mt-1">ID: {c.campaign_id}</div>
                  </td>
                  <td className="px-6 py-4">
                    <span className={`inline-flex items-center px-2 py-1 rounded-md text-xs font-medium border ${
                      c.status === 'active' ? 'bg-green-500/10 text-green-400 border-green-500/20' :
                      c.status === 'paused' ? 'bg-yellow-500/10 text-yellow-400 border-yellow-500/20' :
                      c.status === 'completed' ? 'bg-blue-500/10 text-blue-400 border-blue-500/20' :
                      'bg-[var(--bg-surface)] text-[var(--text-secondary)] border-[var(--border)]'
                    }`}>
                      {c.status.charAt(0).toUpperCase() + c.status.slice(1)}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-[var(--text-secondary)]">
                    {new Date(c.created_at).toLocaleDateString()}
                  </td>
                  <td className="px-6 py-4 text-[var(--text-secondary)]">
                    {c.rate_per_minute || 4} / min
                  </td>
                  <td className="px-6 py-4 text-right">
                    <button 
                      onClick={() => {
                        setActiveCampaignId(c.campaign_id);
                        setCampaignName(c.name);
                        setCurrentStep(STEPS.SEND); // Jump to progress view for existing
                        setView('wizard');
                      }}
                      className="text-[var(--accent)] hover:text-white transition-colors"
                    >
                      View & Manage
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );

  const renderWizard = () => (
    <div className="h-full flex flex-col">
      {/* Wizard Header */}
      <div className="flex justify-between items-center mb-6">
        <div className="flex items-center gap-4">
          <button 
            onClick={() => setView('list')}
            className="p-2 hover:bg-[var(--bg-surface)] rounded-lg text-[var(--text-secondary)] transition-colors"
          >
            <ArrowLeft size={20} />
          </button>
          <div>
            <div className="flex items-center gap-3">
              <input 
                type="text" 
                value={campaignName}
                onChange={e => setCampaignName(e.target.value)}
                className="bg-transparent text-2xl font-semibold text-[var(--text-primary)] border-none focus:outline-none focus:ring-1 focus:ring-[var(--accent)] rounded px-1 -ml-1"
              />
              <span className="text-xs bg-[var(--bg-surface)] px-2 py-1 rounded text-[var(--text-muted)] border border-[var(--border)]">
                Draft
              </span>
            </div>
            <p className="text-sm text-[var(--text-secondary)] mt-1 flex items-center gap-2">
              <Mail className="w-4 h-4" /> Sending via Outlook Bridge
            </p>
          </div>
        </div>
        
        {/* Step Indicator */}
        <div className="flex items-center gap-2">
          {[
            { id: STEPS.RECIPIENTS, label: 'Recipients' },
            { id: STEPS.COMPOSE, label: 'Compose' },
            { id: STEPS.PREVIEW, label: 'Preview' },
            { id: STEPS.SEND, label: 'Send' }
          ].map((step, idx) => (
            <React.Fragment key={step.id}>
              <div className={`flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-medium border ${
                currentStep === step.id 
                  ? 'bg-[var(--accent)]/10 text-[var(--accent)] border-[var(--accent)]/30' 
                  : currentStep > step.id 
                    ? 'bg-[var(--bg-surface)] text-[var(--text-primary)] border-[var(--border)]'
                    : 'bg-transparent text-[var(--text-muted)] border-transparent'
              }`}>
                <div className={`w-5 h-5 rounded-full flex items-center justify-center text-[10px] ${
                  currentStep === step.id ? 'bg-[var(--accent)] text-white' : 
                  currentStep > step.id ? 'bg-[var(--text-primary)] text-[var(--card-bg)]' : 
                  'bg-[var(--border)] text-[var(--text-muted)]'
                }`}>
                  {currentStep > step.id ? <CheckCircle2 size={12} /> : step.id}
                </div>
                {step.label}
              </div>
              {idx < 3 && <div className="w-4 h-[1px] bg-[var(--border)]" />}
            </React.Fragment>
          ))}
        </div>
      </div>

      {/* Main Content Area */}
      <div className="flex-1 overflow-hidden min-h-0 flex gap-6">
        
        {currentStep === STEPS.RECIPIENTS && (
          <div className="flex-1 h-full">
            <RecipientValidator 
              onValidated={setValidatedRecipients} 
              initialRecipients={validatedRecipients.recipients}
            />
          </div>
        )}

        {currentStep === STEPS.COMPOSE && (
          <>
            {/* Left Side: Editor */}
            <div className="flex-[2] h-full flex flex-col gap-4">
              <div className="bg-[var(--card-bg)] border border-[var(--card-border)] rounded-xl p-4 flex flex-col gap-3">
                <div className="flex gap-4">
                  <div className="flex-1">
                    <label className="block text-xs text-[var(--text-secondary)] mb-1">Subject</label>
                    <input 
                      type="text" 
                      value={subject}
                      onChange={e => setSubject(e.target.value)}
                      placeholder="Enter subject... (Tip: type {{FirstName}} to personalize)"
                      className="w-full bg-[var(--bg-surface)] border border-[var(--border)] rounded-lg px-3 py-2 text-sm text-[var(--text-primary)] focus:border-[var(--accent)] outline-none"
                    />
                  </div>
                </div>
              </div>
              
              <div className="flex-1 min-h-0">
                <RichTextComposer 
                  content={body}
                  onChange={setBody}
                  placeholder="Draft your message here..."
                  signature={''} // Will be handled by preview visually, but we could render it here if we fetch it
                />
              </div>
            </div>
            
            {/* Right Side: Sidebar */}
            <div className="flex-1 flex flex-col gap-4 overflow-y-auto pr-2">
              <div className="bg-[var(--card-bg)] border border-[var(--card-border)] rounded-xl p-4">
                <h3 className="text-sm font-medium text-[var(--text-primary)] mb-3 flex items-center gap-2">
                  <Activity className="w-4 h-4 text-[var(--accent)]" /> Campaign Settings
                </h3>
                
                <div className="space-y-4">
                  <div>
                    <label className="block text-xs text-[var(--text-secondary)] mb-1">From Email</label>
                    <input 
                      type="text" 
                      value={fromEmail}
                      disabled
                      className="w-full bg-[var(--bg-surface)] border border-[var(--border)] rounded-lg px-3 py-2 text-sm text-[var(--text-muted)] cursor-not-allowed opacity-70"
                    />
                  </div>
                  
                </div>
              </div>
              
              <SignatureManager 
                selectedSignatureId={signatureId}
                onSelectSignature={setSignatureId}
              />
            </div>
          </>
        )}

        {currentStep === STEPS.PREVIEW && (
          <>
            <div className="flex-[2] h-full">
              <EmailPreview 
                campaignId={activeCampaignId}
                subjectTemplate={subject}
                bodyTemplate={body}
                signatureId={signatureId}
                recipients={validatedRecipients.recipients.filter(r => r.status === 'valid')}
              />
            </div>
            
            <div className="flex-1 h-full flex flex-col gap-4">
              <div className="bg-[var(--card-bg)] border border-[var(--card-border)] rounded-xl p-4 h-full flex flex-col">
                <h3 className="text-sm font-medium text-[var(--text-primary)] mb-4 flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 text-[var(--accent)]" /> Pre-Flight Validation
                </h3>
                
                {isValidating ? (
                  <div className="flex-1 flex flex-col items-center justify-center text-[var(--text-muted)] space-y-3">
                    <Loader2 className="w-6 h-6 animate-spin text-[var(--accent)]" />
                    <span className="text-sm">Running pre-flight checks...</span>
                  </div>
                ) : preflightData ? (
                  <div className="flex-1 space-y-4">
                    <ValidationItem 
                      label="Outlook Bridge Online" 
                      success={preflightData.bridge_healthy} 
                      error={preflightData.bridge_error} 
                    />
                    <ValidationItem 
                      label="Recipients Enrolled" 
                      success={preflightData.has_recipients} 
                      info={`${validatedRecipients.valid_count} valid recipients ready`}
                    />
                    <ValidationItem 
                      label="Templates Saved" 
                      success={preflightData.has_template} 
                    />
                    
                    <div className="mt-8 pt-4 border-t border-[var(--border)]">
                      <div className="bg-blue-500/10 border border-blue-500/20 rounded-lg p-3 text-sm text-blue-400 mb-4">
                        Estimated sending time: <strong>~{Math.ceil(validatedRecipients.valid_count / ratePerMinute)} minutes</strong>
                      </div>
                      
                      <BridgeStatus onStatusChange={setBridgeHealthy} />
                    </div>
                  </div>
                ) : null}
              </div>
            </div>
          </>
        )}

        {currentStep === STEPS.SEND && activeCampaignId && (
          <div className="w-full h-full flex flex-col gap-6 overflow-y-auto pb-6">
            <CampaignProgress campaignId={activeCampaignId} />
            {/* The CampaignProgress component inside has a live activity feed now, or we can use CampaignLogs */}
            <div className="bg-[var(--card-bg)] border border-[var(--card-border)] rounded-xl p-4 min-h-[300px]">
               <h3 className="text-sm font-medium text-[var(--text-primary)] mb-4 flex items-center gap-2">
                  <FileText className="w-4 h-4 text-[var(--text-secondary)]" /> Detailed Delivery Logs
                </h3>
               <CampaignLogs campaignId={activeCampaignId} />
            </div>
          </div>
        )}
        
      </div>

      {/* Footer Navigation */}
      {currentStep !== STEPS.SEND && (
        <div className="mt-6 pt-4 border-t border-[var(--card-border)] flex justify-between items-center">
          <button
            onClick={() => setCurrentStep(prev => prev - 1)}
            disabled={currentStep === STEPS.RECIPIENTS}
            className="px-4 py-2 text-sm font-medium text-[var(--text-secondary)] hover:text-white disabled:opacity-30 transition-colors"
          >
            Back
          </button>
          
          <button
            onClick={handleNextStep}
            className={`px-6 py-2 rounded-lg text-sm font-medium flex items-center gap-2 transition-colors ${
               currentStep === STEPS.PREVIEW && preflightData?.ready
                ? 'bg-green-600 hover:bg-green-500 text-white shadow-lg shadow-green-500/20'
                : 'bg-[var(--accent)] hover:bg-[var(--accent)]/90 text-white'
            }`}
          >
            {currentStep === STEPS.PREVIEW ? (
              <><Play size={16} /> Launch Campaign</>
            ) : (
              <>Continue <ChevronRight size={16} /></>
            )}
          </button>
        </div>
      )}
    </div>
  );

  return (
    <div className="h-full bg-[var(--bg-page)] text-[var(--text-primary)] p-6">
      {view === 'list' ? renderList() : renderWizard()}
    </div>
  );
}

function ValidationItem({ label, success, error, info }) {
  return (
    <div className="flex items-start gap-3 p-3 bg-[var(--bg-surface)] rounded-lg border border-[var(--border)]">
      <div className="mt-0.5">
        {success ? (
          <CheckCircle2 className="w-4 h-4 text-green-400" />
        ) : (
          <AlertCircle className="w-4 h-4 text-red-400" />
        )}
      </div>
      <div>
        <div className="text-sm font-medium text-[var(--text-primary)]">{label}</div>
        {info && <div className="text-xs text-[var(--text-muted)] mt-1">{info}</div>}
        {error && <div className="text-xs text-red-400 mt-1">{error}</div>}
      </div>
    </div>
  );
}
