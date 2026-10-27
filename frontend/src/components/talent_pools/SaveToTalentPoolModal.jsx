import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { FolderPlus, Users, X, Plus, Check, Loader2, Sparkles } from 'lucide-react';
import toast from 'react-hot-toast';
import api from '../../services/api';

export default function SaveToTalentPoolModal({ isOpen, onClose, recruiterIds = [], onSaved }) {
  const [pools, setPools] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedPoolId, setSelectedPoolId] = useState('');
  const [isCreatingNew, setIsCreatingNew] = useState(false);
  const [newPoolName, setNewPoolName] = useState('');
  const [newPoolTargetRole, setNewPoolTargetRole] = useState('');
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (isOpen) {
      loadPools();
    }
  }, [isOpen]);

  const loadPools = async () => {
    setLoading(true);
    try {
      const res = await api.get('/talent-pools');
      setPools(res.data || []);
      if (res.data && res.data.length > 0) {
        setSelectedPoolId(res.data[0].id);
      } else {
        setIsCreatingNew(true);
      }
    } catch (err) {
      toast.error('Failed to load talent pools');
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  const handleSave = async () => {
    if (recruiterIds.length === 0) {
      toast.error('No candidates selected');
      return;
    }

    setSaving(true);
    try {
      let targetPoolId = selectedPoolId;

      // If creating a new pool first
      if (isCreatingNew) {
        if (!newPoolName.trim()) {
          toast.error('Please enter a name for the talent pool');
          setSaving(false);
          return;
        }
        const createRes = await api.post('/talent-pools', {
          name: newPoolName.trim(),
          target_role: newPoolTargetRole.trim(),
          tags: ['Sourced']
        });
        targetPoolId = createRes.data.id;
      }

      const res = await api.post(`/talent-pools/${targetPoolId}/add-recruiters`, {
        recruiter_ids: recruiterIds
      });

      toast.success(`Saved ${res.data.added_count} candidates to Talent Pool!`);
      if (onSaved) onSaved(targetPoolId);
      onClose();
    } catch (err) {
      toast.error('Failed to save to talent pool: ' + (err.response?.data?.detail || err.message));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm">
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        exit={{ opacity: 0, scale: 0.95 }}
        className="bg-[#121212] border border-white/15 w-full max-w-md rounded-2xl shadow-2xl overflow-hidden flex flex-col"
      >
        {/* Header */}
        <div className="px-6 py-4 border-b border-white/10 flex items-center justify-between bg-black/60">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-[#e41937] to-[#fe063f] flex items-center justify-center shadow-lg shadow-[#e41937]/20">
              <FolderPlus className="w-5 h-5 text-white" />
            </div>
            <div>
              <h2 className="text-base font-bold text-white flex items-center gap-2">
                Save to Talent Pool
                <span className="text-[10px] font-semibold uppercase px-2 py-0.5 rounded-full bg-white/5 text-[#e41937] border border-white/15">
                  {recruiterIds.length} Selected
                </span>
              </h2>
              <p className="text-xs text-zinc-400">Organize candidates into custom lists for future outreach.</p>
            </div>
          </div>
          <button onClick={onClose} className="p-1.5 text-zinc-400 hover:text-white rounded-lg hover:bg-[#18181b] transition">
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-4">
          {loading ? (
            <div className="py-8 flex flex-col items-center justify-center text-zinc-400">
              <Loader2 className="w-6 h-6 animate-spin mb-2 text-[#e41937]" />
              <span className="text-xs">Loading talent pools...</span>
            </div>
          ) : (
            <>
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-zinc-300">Target Talent Pool</span>
                <button
                  type="button"
                  onClick={() => setIsCreatingNew(!isCreatingNew)}
                  className="text-xs text-[#e41937] hover:text-zinc-300 font-medium flex items-center gap-1 transition"
                >
                  {isCreatingNew ? 'Choose Existing Pool' : '+ Create New Pool'}
                </button>
              </div>

              {!isCreatingNew ? (
                <div className="space-y-2 max-h-48 overflow-y-auto pr-1">
                  {pools.length > 0 ? (
                    pools.map((p) => (
                      <div
                        key={p.id}
                        onClick={() => setSelectedPoolId(p.id)}
                        className={`p-3 rounded-xl border cursor-pointer flex items-center justify-between transition ${
                          selectedPoolId === p.id
                            ? 'bg-white/5 border-white/30 text-white'
                            : 'bg-black border-white/10 text-zinc-300 hover:border-white/15'
                        }`}
                      >
                        <div className="flex items-center gap-2.5">
                          <Users className="w-4 h-4 text-[#e41937]" />
                          <div>
                            <div className="text-xs font-semibold">{p.name}</div>
                            {p.target_role && <div className="text-[10px] text-zinc-500">{p.target_role}</div>}
                          </div>
                        </div>
                        <div className="text-[10px] font-semibold px-2 py-0.5 rounded bg-[#18181b] text-zinc-400">
                          {p.total_members} candidates
                        </div>
                      </div>
                    ))
                  ) : (
                    <div className="text-center py-4 text-xs text-zinc-500">
                      No talent pools yet. Create one below.
                    </div>
                  )}
                </div>
              ) : (
                <div className="space-y-3 bg-black border border-white/10 rounded-xl p-3.5">
                  <div>
                    <label className="text-[11px] font-semibold text-zinc-300 mb-1 block">Pool Name</label>
                    <input
                      type="text"
                      value={newPoolName}
                      onChange={(e) => setNewPoolName(e.target.value)}
                      placeholder="e.g. Q3 Healthcare Specialists"
                      className="w-full bg-[#121212] border border-white/15 rounded-lg px-3 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-white/20"
                    />
                  </div>
                  <div>
                    <label className="text-[11px] font-semibold text-zinc-300 mb-1 block">Target Role / Specialization (Optional)</label>
                    <input
                      type="text"
                      value={newPoolTargetRole}
                      onChange={(e) => setNewPoolTargetRole(e.target.value)}
                      placeholder="e.g. Senior Informaticist"
                      className="w-full bg-[#121212] border border-white/15 rounded-lg px-3 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-white/20"
                    />
                  </div>
                </div>
              )}
            </>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-white/10 bg-black/40 flex items-center justify-end gap-2">
          <button
            onClick={onClose}
            className="px-3 py-2 text-xs font-medium text-zinc-400 hover:text-white rounded-lg transition"
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            disabled={saving || (isCreatingNew && !newPoolName.trim()) || (!isCreatingNew && !selectedPoolId)}
            className="px-4 py-2 bg-gradient-to-r from-[#e41937] to-[#fe063f] hover:from-[#e41937] hover:to-[#fe063f] text-white text-xs font-semibold rounded-lg flex items-center gap-1.5 shadow-md shadow-[#e41937]/20 disabled:opacity-50 transition"
          >
            {saving ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Check className="w-3.5 h-3.5" />}
            Save Candidates
          </button>
        </div>
      </motion.div>
    </div>
  );
}
