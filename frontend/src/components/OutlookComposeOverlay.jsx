import { useState } from 'react';

export function OutlookComposeOverlay({ recipients, onClose, onSend }) {
  const [fromEmail, setFromEmail] = useState('abhishek.jadon@technovion.com');
  const [toStr, setToStr] = useState(recipients.map(r => `${r.recruiter_name || ''} <${r.email || ''}>`.trim()).join('; '));
  const [editingTo, setEditingTo] = useState(false);
  const [cc, setCc] = useState('');
  const [bcc, setBcc] = useState('');
  const [subject, setSubject] = useState('');
  const [body, setBody] = useState('');

  const parseToChips = (str) => {
    return str.split(';').map(s => s.trim()).filter(Boolean).map(s => {
      const match = s.match(/(.*)<(.*)>/);
      if (match) return { name: match[1].trim() || match[2].trim(), email: match[2].trim() };
      return { name: s, email: s };
    });
  };

  const handleSend = () => {
    if (onSend) {
      // The bridge currently expects recipients as an array of {recruiter_name, email}
      const finalRecipients = parseToChips(toStr).map(c => ({ recruiter_name: c.name, email: c.email }));
      onSend({ recipients: finalRecipients, from: fromEmail, cc, bcc, subject, body, signature: '' });
    }
  };

  return (
    <div style={{
      position: 'fixed',
      top: 0, left: 0, right: 0, bottom: 0,
      backgroundColor: 'rgba(0, 0, 0, 0.75)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      zIndex: 99999
    }}>
      <div style={{
        width: '900px',
        height: '650px',
        backgroundColor: '#202020',
        display: 'flex',
        flexDirection: 'row',
        boxShadow: '0 12px 32px rgba(0, 0, 0, 0.6)',
        border: '1px solid #444',
        borderRadius: '6px',
        overflow: 'hidden',
        position: 'relative'
      }}>
        {/* Close Button at top right */}
        <button 
          onClick={onClose}
          style={{
            position: 'absolute', top: '8px', right: '12px', background: 'none', border: 'none', color: '#999', fontSize: '20px', cursor: 'pointer', zIndex: 10
          }}
        >
          &times;
        </button>

        {/* Left Sidebar (Send Button) */}
        <div style={{
          width: '80px',
          padding: '16px 12px',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
        }}>
          <button 
            onClick={handleSend}
            style={{ 
              width: '100%',
              aspectRatio: '1',
              backgroundColor: '#333333',
              color: 'var(--text-primary)',
              border: '1px solid #555',
              borderRadius: '4px',
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '6px',
              cursor: 'pointer',
              transition: 'background 0.2s',
            }}
            onMouseOver={e => e.currentTarget.style.backgroundColor = '#444'}
            onMouseOut={e => e.currentTarget.style.backgroundColor = '#333'}
          >
            <i className="ti ti-send" style={{ fontSize: '20px' }}></i>
            <span style={{ fontSize: '12px', fontWeight: 500 }}>Send</span>
          </button>
        </div>

        {/* Right Main Area */}
        <div style={{
          flex: 1,
          display: 'flex',
          flexDirection: 'column',
          padding: '16px 24px 16px 0',
          position: 'relative'
        }}>
          
          {/* Form Rows */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
            
            {/* From */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '16px', minHeight: '36px' }}>
              <button style={{
                backgroundColor: '#333', color: '#ccc', border: '1px solid #444', borderRadius: '4px',
                padding: '4px 8px', fontSize: '13px', width: '70px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', cursor: 'pointer'
              }}>
                From <i className="ti ti-chevron-down" style={{ fontSize: '10px' }}></i>
              </button>
              <input 
                value={fromEmail} onChange={e => setFromEmail(e.target.value)}
                style={{ flex: 1, background: 'transparent', border: 'none', color: '#ccc', fontSize: '13px', outline: 'none', padding: 0 }}
              />
            </div>

            {/* To */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '16px', borderBottom: '1px solid #444', minHeight: '36px', paddingBottom: '4px' }}>
              <button style={{
                backgroundColor: '#333', color: '#ccc', border: '1px solid #444', borderRadius: '4px',
                padding: '4px 8px', fontSize: '13px', width: '70px', textAlign: 'center', cursor: 'pointer'
              }}>
                To
              </button>
              <div 
                onClick={() => setEditingTo(true)}
                style={{ flex: 1, color: '#ccc', fontSize: '13px', display: 'flex', gap: '6px', flexWrap: 'wrap', cursor: editingTo ? 'text' : 'pointer', minHeight: '20px' }}
              >
                {editingTo ? (
                  <input 
                    autoFocus
                    value={toStr} onChange={e => setToStr(e.target.value)} onBlur={() => setEditingTo(false)}
                    style={{ flex: 1, background: 'transparent', border: 'none', color: '#ccc', fontSize: '13px', outline: 'none', padding: 0 }}
                  />
                ) : (
                  parseToChips(toStr).map((chip, idx) => (
                    <span key={idx} title={chip.email} style={{
                      backgroundColor: '#333', padding: '2px 8px', borderRadius: '12px', fontSize: '12px', color: '#e0e0e0', border: '1px solid #444'
                    }}>
                      {chip.name}
                    </span>
                  ))
                )}
              </div>
            </div>

            {/* Cc */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '16px', borderBottom: '1px solid #444', minHeight: '36px', paddingBottom: '4px', paddingTop: '4px' }}>
              <button style={{
                backgroundColor: '#333', color: '#ccc', border: '1px solid #444', borderRadius: '4px',
                padding: '4px 8px', fontSize: '13px', width: '70px', textAlign: 'center'
              }}>
                Cc
              </button>
              <input 
                value={cc} onChange={e => setCc(e.target.value)}
                style={{ flex: 1, background: 'transparent', border: 'none', color: '#ccc', fontSize: '13px', outline: 'none', padding: 0 }}
              />
            </div>

            {/* Bcc */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '16px', borderBottom: '1px solid #444', minHeight: '36px', paddingBottom: '4px', paddingTop: '4px' }}>
              <button style={{
                backgroundColor: '#333', color: '#ccc', border: '1px solid #444', borderRadius: '4px',
                padding: '4px 8px', fontSize: '13px', width: '70px', textAlign: 'center'
              }}>
                Bcc
              </button>
              <input 
                value={bcc} onChange={e => setBcc(e.target.value)}
                style={{ flex: 1, background: 'transparent', border: 'none', color: '#ccc', fontSize: '13px', outline: 'none', padding: 0 }}
              />
            </div>

            {/* Subject */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '16px', borderBottom: '1px solid #444', minHeight: '36px', paddingBottom: '4px', paddingTop: '4px' }}>
              <span style={{ color: '#aaa', fontSize: '13px', width: '70px', paddingLeft: '8px' }}>
                Subject
              </span>
              <input 
                value={subject} onChange={e => setSubject(e.target.value)}
                style={{ flex: 1, background: 'transparent', border: 'none', color: '#ccc', fontSize: '13px', outline: 'none', padding: 0 }}
              />
            </div>

          </div>

          {/* Body Area */}
          <div style={{ flex: 1, display: 'flex', flexDirection: 'column', paddingTop: '16px' }}>
            <textarea 
              value={body} onChange={e => setBody(e.target.value)}
              style={{ 
                flex: 1, width: '100%', background: 'transparent', border: 'none', color: '#ccc', fontSize: '14px', 
                outline: 'none', resize: 'none', fontFamily: 'inherit' 
              }}
            />
            {/* Note about Signature */}
            <div style={{ paddingTop: '20px', borderTop: '1px dashed #444', marginTop: 'auto', paddingBottom: '20px' }}>
              <span style={{ color: '#888', fontSize: '12px', fontStyle: 'italic' }}>
                (Your native Outlook signature will be automatically attached when sent)
              </span>
            </div>
          </div>
          
        </div>
      </div>
    </div>
  );
}
