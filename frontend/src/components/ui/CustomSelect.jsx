import { useState, useRef, useEffect, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ChevronDown, Search, X } from 'lucide-react';

export default function CustomSelect({ 
  value, 
  onChange, 
  options = [], 
  placeholder = "Select...", 
  className = "", 
  style = {},
  searchable = false,
  searchPlaceholder = "Search..."
}) {
  const [isOpen, setIsOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const containerRef = useRef(null);
  const searchInputRef = useRef(null);

  useEffect(() => {
    const handleOutsideClick = (e) => {
      if (containerRef.current && !containerRef.current.contains(e.target)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleOutsideClick);
    return () => document.removeEventListener('mousedown', handleOutsideClick);
  }, []);

  useEffect(() => {
    if (isOpen && (searchable || options.length > 8)) {
      setTimeout(() => {
        if (searchInputRef.current) searchInputRef.current.focus();
      }, 50);
    } else {
      setSearchQuery("");
    }
  }, [isOpen, searchable, options.length]);

  const selectedOption = useMemo(() => {
    return options.find(opt => String(opt.value).toLowerCase() === String(value || '').toLowerCase()) || 
      (value ? { value, label: value } : options[0]);
  }, [options, value]);

  const filteredOptions = useMemo(() => {
    if (!searchQuery.trim()) return options;
    const q = searchQuery.toLowerCase().trim();
    return options.filter(opt => 
      (opt.label || '').toLowerCase().includes(q) || 
      (opt.value || '').toLowerCase().includes(q)
    );
  }, [options, searchQuery]);

  const showCustomOption = useMemo(() => {
    if (!searchQuery.trim()) return false;
    const q = searchQuery.toLowerCase().trim();
    return !options.some(opt => (opt.label || '').toLowerCase() === q || (opt.value || '').toLowerCase() === q);
  }, [options, searchQuery]);

  const isSearchActive = searchable || options.length > 8;

  return (
    <div 
      ref={containerRef} 
      className={`relative inline-block ${className}`}
      style={style}
    >
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className="w-full flex items-center justify-between outline-none"
        style={{
          height: '100%',
          padding: '0 12px',
          background: 'var(--panel-bg, #000000)',
          border: '1px solid var(--card-border, rgba(255, 255, 255, 0.12))',
          borderRadius: '8px',
          color: selectedOption && selectedOption.value !== '' ? '#ffffff' : 'var(--text-secondary, #f4f4f5)',
          fontSize: '13px',
          fontFamily: 'var(--font)',
          width: '100%',
          textAlign: 'left',
          cursor: 'pointer',
          transition: 'border-color 0.2s ease, background 0.2s ease'
        }}
      >
        <span className="truncate pr-2 font-medium">
          {selectedOption ? selectedOption.label : placeholder}
        </span>
        <ChevronDown 
          size={15} 
          className="text-[#a1a1aa] flex-shrink-0 transition-transform duration-200"
          style={{ transform: isOpen ? 'rotate(180deg)' : 'rotate(0deg)' }}
        />
      </button>

      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0, y: -4, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -4, scale: 0.98 }}
            transition={{ type: "spring", stiffness: 450, damping: 32 }}
            className="absolute z-[100] mt-1"
            style={{
              left: 0,
              minWidth: '220px',
              maxWidth: '340px',
              width: 'max-content',
              background: '#09090b',
              border: '1px solid rgba(255, 255, 255, 0.15)',
              borderRadius: '8px',
              boxShadow: '0 16px 40px rgba(0, 0, 0, 0.75)',
              overflow: 'hidden',
              padding: '6px'
            }}
          >
            {isSearchActive && (
              <div style={{ padding: '4px 4px 8px 4px', borderBottom: '1px solid rgba(255, 255, 255, 0.08)', marginBottom: '4px' }}>
                <div style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  background: '#121214',
                  borderRadius: '6px',
                  padding: '6px 10px',
                  border: '1px solid rgba(255, 255, 255, 0.12)'
                }}>
                  <Search size={14} style={{ color: '#a1a1aa', flexShrink: 0 }} />
                  <input
                    ref={searchInputRef}
                    type="text"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    placeholder={searchPlaceholder}
                    style={{
                      background: 'transparent',
                      border: 'none',
                      outline: 'none',
                      color: '#ffffff',
                      fontSize: '12.5px',
                      width: '100%',
                      fontFamily: 'var(--font)'
                    }}
                  />
                  {searchQuery && (
                    <button
                      type="button"
                      onClick={() => setSearchQuery("")}
                      style={{ background: 'none', border: 'none', color: '#a1a1aa', cursor: 'pointer', padding: 0, display: 'flex' }}
                    >
                      <X size={13} />
                    </button>
                  )}
                </div>
              </div>
            )}

            <div className="max-h-64 overflow-y-auto" style={{ scrollbarWidth: 'thin', scrollbarColor: 'rgba(255,255,255,0.2) transparent' }}>
              {showCustomOption && (
                <button
                  type="button"
                  onClick={() => {
                    onChange(searchQuery.trim());
                    setIsOpen(false);
                  }}
                  className="w-full text-left px-3 py-2 rounded-md transition-colors flex items-center gap-2 mb-1"
                  style={{
                    fontSize: '12.5px',
                    color: '#10b981',
                    background: 'rgba(16, 185, 129, 0.1)',
                    border: '1px dashed rgba(16, 185, 129, 0.35)',
                    cursor: 'pointer'
                  }}
                >
                  <span>Filter by "{searchQuery.trim()}"</span>
                </button>
              )}

              {filteredOptions.length === 0 && !showCustomOption && (
                <div style={{ padding: '12px 14px', textAlign: 'center', color: '#a1a1aa', fontSize: '12px' }}>
                  No matches found
                </div>
              )}

              {filteredOptions.map((opt) => {
                const isActive = String(opt.value).toLowerCase() === String(value || '').toLowerCase();
                return (
                  <button
                    key={opt.value}
                    type="button"
                    onClick={() => {
                      onChange(opt.value);
                      setIsOpen(false);
                    }}
                    className="w-full text-left px-3 py-2 rounded-md transition-colors flex items-center justify-between gap-2"
                    style={{
                      fontSize: '13px',
                      color: isActive ? '#ffffff' : '#f4f4f5',
                      background: isActive ? 'rgba(228, 25, 55, 0.2)' : 'transparent',
                      fontWeight: isActive ? 600 : 400,
                      cursor: 'pointer',
                      border: 'none',
                      outline: 'none',
                    }}
                    onMouseEnter={(e) => {
                      if (!isActive) {
                        e.currentTarget.style.background = 'rgba(255, 255, 255, 0.08)';
                        e.currentTarget.style.color = '#ffffff';
                      }
                    }}
                    onMouseLeave={(e) => {
                      if (!isActive) {
                        e.currentTarget.style.background = 'transparent';
                        e.currentTarget.style.color = '#f4f4f5';
                      }
                    }}
                  >
                    <span className="truncate">{opt.label}</span>
                    {isActive && (
                      <span style={{ fontSize: '11px', color: '#fe063f', fontWeight: 700 }}>✓</span>
                    )}
                  </button>
                );
              })}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
