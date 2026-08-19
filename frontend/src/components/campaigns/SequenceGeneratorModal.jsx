import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Zap, Sparkles, X, Check, Copy, ArrowRight, Clock, RefreshCw } from 'lucide-react';
import toast from 'react-hot-toast';
import api from '../../services/api';

export default function SequenceGeneratorModal({ isOpen, onClose, onApplyTouch }) {
  const [targetRole, setTargetRole] = useState('Senior Full-Stack Engineer');
  const [companyName, setCompanyName] = useState('TalentOps');
  const [industry, setIndustry] = useState('Enterprise SaaS');
  const [seniority, setSeniority] = useState('Senior');
  const [valueProps, setValueProps] = useState('impactful greenfield architecture, competitive equity, remote-first culture');
  const [tone, setTone] = useState('Professional');
  const [loading, setLoading] = useState(false);
  const [sequence, setSequence] = useState(null);
  const [selectedTouch, setSelectedTouch] = useState(0);

  if (!isOpen) return null;

  const handleGenerate = async () => {
    setLoading(true);
    try {
      const res = await api.post('/campaigns/generate-sequence', {
        target_role: targetRole,
        company_name: companyName,
        industry,
        seniority,
        value_props: valueProps,
        tone
      });
      if (res.data && res.data.touches) {
        setSequence(res.data);
        setSelectedTouch(0);
        toast.success('3-Touch Outreach Sequence Synthesized!');
      }
    } catch (err) {
      toast.error('Failed to generate sequence: ' + (err.response?.data?.detail || err.message));
    } finally {
      setLoading(false);
    }
  };

  const copyToClipboard = (text, label) => {
    navigator.clipboard.writeText(text);
    toast.success(`${label} copied to clipboard!`);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm">
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        exit={{ opacity: 0, scale: 0.95 }}
        className="bg-slate-900 border border-slate-700 w-full max-w-4xl rounded-2xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh]"
      >
        {/* Modal Header */}
        <div className="px-6 py-4 border-b border-slate-800 flex items-center justify-between bg-slate-950/60">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-cyan-500 to-indigo-600 flex items-center justify-center shadow-lg shadow-cyan-500/20">
              <Sparkles className="w-5 h-5 text-white" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-white flex items-center gap-2">
                AI Multi-Touch Sequence Generator
                <span className="text-[10px] font-semibold tracking-wider uppercase px-2 py-0.5 rounded-full bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">
                  3-Touch Cadence
                </span>
              </h2>
              <p className="text-xs text-slate-400">Synthesizes high-converting, personalized cold recruiting email sequences.</p>
            </div>
          </div>
          <button onClick={onClose} className="p-2 text-slate-400 hover:text-white rounded-lg hover:bg-slate-800 transition">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Content */}
        <div className="p-6 overflow-y-auto grid grid-cols-1 md:grid-cols-12 gap-6 flex-1">
          {/* Controls Column */}
          <div className="md:col-span-5 space-y-4">
            <div>
              <label className="text-xs font-semibold text-slate-300 mb-1 block">Target Candidate Role</label>
              <input
                type="text"
                value={targetRole}
                onChange={(e) => setTargetRole(e.target.value)}
                placeholder="e.g. Lead React Architect, VP of Sales"
                className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-cyan-500"
              />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-xs font-semibold text-slate-300 mb-1 block">Hiring Company</label>
                <input
                  type="text"
                  value={companyName}
                  onChange={(e) => setCompanyName(e.target.value)}
                  placeholder="e.g. Acme Corp"
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-cyan-500"
                />
              </div>
              <div>
                <label className="text-xs font-semibold text-slate-300 mb-1 block">Seniority</label>
                <select
                  value={seniority}
                  onChange={(e) => setSeniority(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-cyan-500"
                >
                  <option value="Senior">Senior</option>
                  <option value="Lead / Staff">Lead / Staff</option>
                  <option value="Director / VP">Director / VP</option>
                  <option value="Executive / C-Suite">Executive / C-Suite</option>
                </select>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-xs font-semibold text-slate-300 mb-1 block">Industry</label>
                <input
                  type="text"
                  value={industry}
                  onChange={(e) => setIndustry(e.target.value)}
                  placeholder="e.g. HealthTech, AI SaaS"
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-cyan-500"
                />
              </div>
              <div>
                <label className="text-xs font-semibold text-slate-300 mb-1 block">Outreach Tone</label>
                <select
                  value={tone}
                  onChange={(e) => setTone(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-cyan-500"
                >
                  <option value="Professional">Professional</option>
                  <option value="Casual">Casual & Direct</option>
                  <option value="Executive">Executive / Brief</option>
                </select>
              </div>
            </div>

            <div>
              <label className="text-xs font-semibold text-slate-300 mb-1 block">Key Value Propositions</label>
              <textarea
                rows={2}
                value={valueProps}
                onChange={(e) => setValueProps(e.target.value)}
                placeholder="What makes this opportunity compelling?"
                className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-cyan-500 resize-none"
              />
            </div>

            <button
              onClick={handleGenerate}
              disabled={loading}
              className="w-full py-2.5 px-4 bg-gradient-to-r from-cyan-500 to-indigo-600 hover:from-cyan-400 hover:to-indigo-500 text-white text-xs font-semibold rounded-lg flex items-center justify-center gap-2 shadow-lg shadow-cyan-500/20 disabled:opacity-50 transition"
            >
              {loading ? (
                <>
                  <RefreshCw className="w-4 h-4 animate-spin" />
                  Synthesizing Cadence...
                </>
              ) : (
                <>
                  <Zap className="w-4 h-4" />
                  Generate 3-Touch Sequence
                </>
              )}
            </button>
          </div>

          {/* Sequence Preview Column */}
          <div className="md:col-span-7 bg-slate-950/80 border border-slate-800 rounded-xl p-4 flex flex-col">
            {sequence ? (
              <div className="flex flex-col h-full">
                {/* Step Selector Tabs */}
                <div className="flex items-center gap-2 border-b border-slate-800 pb-3 mb-3">
                  {sequence.touches.map((touch, idx) => (
                    <button
                      key={idx}
                      onClick={() => setSelectedTouch(idx)}
                      className={`flex-1 py-1.5 px-2 rounded-lg text-xs font-medium border flex items-center justify-center gap-1.5 transition ${
                        selectedTouch === idx
                          ? 'bg-cyan-500/10 border-cyan-500/30 text-cyan-400 shadow-sm'
                          : 'bg-slate-900 border-slate-800 text-slate-400 hover:text-white'
                      }`}
                    >
                      <Clock className="w-3 h-3" />
                      Day {touch.day_delay}: {touch.touch_type}
                    </button>
                  ))}
                </div>

                {/* Active Touch Display */}
                {sequence.touches[selectedTouch] && (
                  <div className="flex-1 flex flex-col justify-between space-y-3">
                    <div>
                      <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-1">Subject Line</div>
                      <div className="bg-slate-900 border border-slate-800 rounded-lg p-2.5 text-xs text-white font-medium flex items-center justify-between">
                        <span>{sequence.touches[selectedTouch].subject}</span>
                        <button
                          onClick={() => copyToClipboard(sequence.touches[selectedTouch].subject, 'Subject')}
                          className="p-1 text-slate-400 hover:text-white rounded transition"
                          title="Copy Subject"
                        >
                          <Copy className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </div>

                    <div className="flex-1">
                      <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-1">Email Body</div>
                      <div className="bg-slate-900 border border-slate-800 rounded-lg p-3 text-xs text-slate-200 whitespace-pre-line font-mono max-h-[190px] overflow-y-auto leading-relaxed">
                        {sequence.touches[selectedTouch].body}
                      </div>
                    </div>

                    {/* Action Bar */}
                    <div className="flex items-center justify-between pt-2 border-t border-slate-800">
                      <button
                        onClick={() => copyToClipboard(sequence.touches[selectedTouch].body, 'Email body')}
                        className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs rounded-lg flex items-center gap-1.5 transition"
                      >
                        <Copy className="w-3.5 h-3.5" />
                        Copy Touch {selectedTouch + 1}
                      </button>
                      {onApplyTouch && (
                        <button
                          onClick={() => {
                            onApplyTouch(sequence.touches[selectedTouch]);
                            onClose();
                            toast.success(`Touch ${selectedTouch + 1} applied to campaign composer!`);
                          }}
                          className="px-3.5 py-1.5 bg-cyan-600 hover:bg-cyan-500 text-white text-xs font-semibold rounded-lg flex items-center gap-1.5 shadow-md shadow-cyan-600/20 transition"
                        >
                          <Check className="w-3.5 h-3.5" />
                          Apply to Composer
                        </button>
                      )}
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <div className="flex-1 flex flex-col items-center justify-center text-center p-6 text-slate-500">
                <Sparkles className="w-10 h-10 text-slate-600 mb-3" />
                <div className="text-sm font-semibold text-slate-300">No Sequence Synthesized Yet</div>
                <p className="text-xs text-slate-500 max-w-xs mt-1">
                  Configure your target role and value props on the left, then click Generate to create a 3-touch outreach sequence.
                </p>
              </div>
            )}
          </div>
        </div>
      </motion.div>
    </div>
  );
}
