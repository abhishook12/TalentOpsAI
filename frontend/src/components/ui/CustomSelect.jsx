import React, { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ChevronDown } from 'lucide-react';

export default function CustomSelect({ 
  value, 
  onChange, 
  options, 
  placeholder = "Select...", 
  className = "", 
  style = {} 
}) {
  const [isOpen, setIsOpen] = useState(false);
  const containerRef = useRef(null);

  useEffect(() => {
    const handleOutsideClick = (e) => {
      if (containerRef.current && !containerRef.current.contains(e.target)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleOutsideClick);
    return () => document.removeEventListener('mousedown', handleOutsideClick);
  }, []);

  const selectedOption = options.find(opt => opt.value === value) || options[0];

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
          padding: '0', // The wrapper will handle padding usually, or we pass it via class
          background: 'transparent',
          color: selectedOption && selectedOption.value !== '' ? '#fff' : 'var(--text-secondary)',
          fontSize: 'inherit',
          fontFamily: 'inherit',
          width: '100%',
          textAlign: 'left',
          border: 'none',
          cursor: 'pointer',
        }}
      >
        <span className="truncate pr-4">{selectedOption ? selectedOption.label : placeholder}</span>
        <ChevronDown 
          size={16} 
          className="text-[var(--text-muted)] flex-shrink-0 transition-transform duration-200"
          style={{ transform: isOpen ? 'rotate(180deg)' : 'rotate(0deg)' }}
        />
      </button>

      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0, y: -4, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -4, scale: 0.98 }}
            transition={{ duration: 0.15, ease: 'easeOut' }}
            className="absolute z-[100] mt-1 min-w-[160px]"
            style={{
              left: 0,
              background: 'var(--card-bg)',
              border: '1px solid var(--card-border)',
              borderRadius: '8px',
              boxShadow: '0 12px 32px rgba(0,0,0,0.4)',
              overflow: 'hidden',
              padding: '6px'
            }}
          >
            <div className="max-h-60 overflow-y-auto" style={{ scrollbarWidth: 'thin', scrollbarColor: 'var(--card-border) transparent' }}>
              {options.map((opt) => {
                const isActive = opt.value === value;
                return (
                  <button
                    key={opt.value}
                    type="button"
                    onClick={() => {
                      onChange(opt.value);
                      setIsOpen(false);
                    }}
                    className="w-full text-left px-3 py-2 rounded-md transition-colors flex items-center gap-2"
                    style={{
                      fontSize: '13px',
                      color: isActive ? 'var(--accent)' : 'var(--text-primary)',
                      background: isActive ? 'var(--accent-bg)' : 'transparent',
                      cursor: 'pointer',
                      border: 'none',
                      outline: 'none',
                    }}
                    onMouseEnter={(e) => {
                      if (!isActive) {
                        e.currentTarget.style.background = 'var(--main-bg)';
                        e.currentTarget.style.color = '#fff';
                      }
                    }}
                    onMouseLeave={(e) => {
                      if (!isActive) {
                        e.currentTarget.style.background = 'transparent';
                        e.currentTarget.style.color = 'var(--text-primary)';
                      }
                    }}
                  >
                    {opt.label}
                  </button>
                )
              })}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
