import React, { useState, useEffect } from 'react';
import { Eye, ChevronLeft, ChevronRight, Mail, User, Briefcase, MapPin, Loader2 } from 'lucide-react';
import api from '../services/api';

export default function EmailPreview({ campaignId, subjectTemplate, bodyTemplate, signatureId, recipients }) {
  const [currentIndex, setCurrentIndex] = useState(0);
  const [previewData, setPreviewData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const currentRecipient = recipients[currentIndex];

  useEffect(() => {
    if (currentRecipient && subjectTemplate && bodyTemplate && campaignId) {
      const timer = setTimeout(() => {
        fetchPreview();
      }, 500);
      return () => clearTimeout(timer);
    }
  }, [currentIndex, subjectTemplate, bodyTemplate, signatureId, currentRecipient, campaignId]);

  const fetchPreview = async () => {
    if (!currentRecipient?.recruiter_id) {
      // If we don't have a recruiter_id (e.g. manually added), we can't fully preview server-side.
      // We'd fallback to basic client-side replace or just show an error.
      setPreviewData({
        subject: subjectTemplate.replace(/\{\{([^}]+)\}\}/g, '...'),
        body: bodyTemplate.replace(/\{\{([^}]+)\}\}/g, '...') + (signatureId ? '<br/><br/>[Signature]' : ''),
        recipient_email: currentRecipient.email,
        recipient_name: currentRecipient.name || 'Unknown'
      });
      return;
    }

    try {
      setLoading(true);
      setError(null);
      const res = await api.post(`/campaigns/${campaignId}/preview`, {
        recruiter_id: currentRecipient.recruiter_id,
        subject_template: subjectTemplate,
        body_template: bodyTemplate,
        signature_id: signatureId
      });
      setPreviewData(res.data);
    } catch (e) {
      console.error("Failed to fetch preview:", e);
      setError("Failed to generate preview for this recipient.");
    } finally {
      setLoading(false);
    }
  };

  const handlePrev = () => setCurrentIndex(prev => Math.max(0, prev - 1));
  const handleNext = () => setCurrentIndex(prev => Math.min(recipients.length - 1, prev + 1));

  if (!recipients || recipients.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-[var(--text-muted)] space-y-4 p-8">
        <Eye className="w-12 h-12 opacity-20" />
        <p className="text-sm">Add recipients to preview emails.</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full bg-[var(--card-bg)] border border-[var(--card-border)] rounded-xl overflow-hidden">
      {/* HEADER */}
      <div className="p-3 border-b border-[var(--card-border)] bg-[var(--bg-surface)] flex justify-between items-center">
        <span className="font-medium text-sm flex items-center gap-2 text-[var(--text-primary)]">
          <Eye className="w-4 h-4 text-[var(--accent)]" /> Live Preview
        </span>
        
        <div className="flex items-center gap-4">
          <div className="text-xs text-[var(--text-secondary)]">
            Recipient {currentIndex + 1} of {recipients.length}
          </div>
          <div className="flex gap-1">
            <button 
              onClick={handlePrev} 
              disabled={currentIndex === 0}
              className="p-1 rounded bg-[var(--card-bg)] border border-[var(--border)] text-[var(--text-primary)] disabled:opacity-30"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>
            <button 
              onClick={handleNext} 
              disabled={currentIndex === recipients.length - 1}
              className="p-1 rounded bg-[var(--card-bg)] border border-[var(--border)] text-[var(--text-primary)] disabled:opacity-30"
            >
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>

      {/* PREVIEW CONTAINER */}
      <div className="flex-1 overflow-y-auto p-0 flex flex-col relative">
        {loading && (
          <div className="absolute inset-0 bg-[var(--card-bg)]/50 backdrop-blur-[1px] flex items-center justify-center z-10">
            <Loader2 className="w-8 h-8 animate-spin text-[var(--accent)]" />
          </div>
        )}
        
        {error ? (
          <div className="p-8 text-center text-red-400 text-sm">{error}</div>
        ) : previewData ? (
          <div className="flex flex-col h-full">
            {/* Email Header */}
            <div className="border-b border-[var(--border)] p-4 bg-[var(--bg-surface)] space-y-2">
              <div className="flex gap-4 items-baseline">
                <span className="text-xs text-[var(--text-muted)] w-12 text-right">To:</span>
                <span className="text-sm font-medium text-[var(--text-primary)]">
                  {previewData.recipient_name} &lt;{previewData.recipient_email}&gt;
                </span>
              </div>
              <div className="flex gap-4 items-baseline">
                <span className="text-xs text-[var(--text-muted)] w-12 text-right">Subject:</span>
                <span className="text-sm font-semibold text-[var(--text-primary)]">{previewData.subject}</span>
              </div>
            </div>
            
            {/* Recipient Context Card */}
            {currentRecipient.company_name && (
              <div className="mx-4 mt-4 p-3 bg-blue-500/10 border border-blue-500/20 rounded-lg flex items-center gap-4">
                <div className="text-blue-400"><Briefcase className="w-4 h-4" /></div>
                <div>
                  <div className="text-xs text-blue-400 font-medium">Context</div>
                  <div className="text-xs text-blue-400/80">Company: {currentRecipient.company_name}</div>
                </div>
              </div>
            )}
            
            {/* Email Body */}
            <div className="flex-1 p-6 bg-white dark:bg-[#1e1e1e] text-black dark:text-[#d4d4d4] m-4 rounded-lg border border-[var(--border)] shadow-sm">
              <div 
                className="prose dark:prose-invert max-w-none text-sm font-sans"
                style={{ fontFamily: 'Inter, sans-serif' }}
                dangerouslySetInnerHTML={{ __html: previewData.body }} 
              />
            </div>
          </div>
        ) : (
           <div className="p-8 text-center text-[var(--text-muted)] text-sm">Generating preview...</div>
        )}
      </div>
    </div>
  );
}
