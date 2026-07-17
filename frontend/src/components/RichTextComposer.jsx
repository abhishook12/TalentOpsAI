import React, { useEffect, useCallback } from 'react';
import { useEditor, EditorContent } from '@tiptap/react';
import { StarterKit } from '@tiptap/starter-kit';
import { Link } from '@tiptap/extension-link';
import { Image } from '@tiptap/extension-image';
import { Table } from '@tiptap/extension-table';
import { TableRow } from '@tiptap/extension-table-row';
import { TableCell } from '@tiptap/extension-table-cell';
import { TableHeader } from '@tiptap/extension-table-header';
import { TextAlign } from '@tiptap/extension-text-align';
import { Underline } from '@tiptap/extension-underline';
import { Placeholder } from '@tiptap/extension-placeholder';
import { Highlight } from '@tiptap/extension-highlight';
import { TextStyle } from '@tiptap/extension-text-style';
import { Color } from '@tiptap/extension-color';
import { FontFamily } from '@tiptap/extension-font-family';

import {
  Bold, Italic, Underline as UnderlineIcon, Strikethrough,
  Heading1, Heading2, Heading3, Type,
  List, ListOrdered,
  AlignLeft, AlignCenter, AlignRight, AlignJustify,
  Link as LinkIcon, Image as ImageIcon, Table as TableIcon, Minus,
  Quote, Code,
  Undo, Redo,
  Highlighter, Smile, Braces
} from 'lucide-react';

const variablesList = [
  { label: 'First Name', tag: '{{FirstName}}' },
  { label: 'Last Name', tag: '{{LastName}}' },
  { label: 'Full Name', tag: '{{FullName}}' },
  { label: 'Company', tag: '{{Company}}' },
  { label: 'Title', tag: '{{Title}}' },
  { label: 'Location', tag: '{{Location}}' },
  { label: 'State', tag: '{{State}}' },
  { label: 'Email', tag: '{{Email}}' },
];

const ToolbarButton = ({ onClick, isActive, disabled, children, title }) => (
  <button
    type="button"
    onClick={onClick}
    disabled={disabled}
    title={title}
    style={{
      width: '28px',
      height: '28px',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      borderRadius: '4px',
      border: 'none',
      background: isActive ? 'var(--accent)' : 'transparent',
      color: isActive ? '#fff' : 'var(--text-secondary)',
      cursor: disabled ? 'not-allowed' : 'pointer',
      opacity: disabled ? 0.5 : 1,
      transition: 'all 0.2s',
    }}
    onMouseEnter={(e) => {
      if (!isActive && !disabled) e.currentTarget.style.background = 'rgba(255,255,255,0.1)';
    }}
    onMouseLeave={(e) => {
      if (!isActive && !disabled) e.currentTarget.style.background = 'transparent';
    }}
  >
    {children}
  </button>
);

const ToolbarSeparator = () => (
  <div style={{ width: '1px', height: '20px', background: 'var(--border)', margin: '0 4px' }} />
);

export default function RichTextComposer({
  content = '',
  onChange,
  disabled = false,
  placeholder = 'Write your email...',
  signature = ''
}) {
  const editor = useEditor({
    extensions: [
      StarterKit,
      Underline,
      Highlight.configure({ multicolor: true }),
      TextStyle,
      Color,
      FontFamily,
      Link.configure({ openOnClick: false, HTMLAttributes: { target: '_blank', rel: 'noopener noreferrer' } }),
      Image.configure({ inline: true }),
      Table.configure({ resizable: true }),
      TableRow,
      TableHeader,
      TableCell,
      TextAlign.configure({ types: ['heading', 'paragraph'] }),
      Placeholder.configure({ placeholder }),
    ],
    content,
    editable: !disabled,
    onUpdate: ({ editor }) => {
      if (onChange) {
        onChange(editor.getHTML());
      }
    },
  });

  // Sync external content changes (if not matching current editor content)
  useEffect(() => {
    if (editor && content !== editor.getHTML()) {
      editor.commands.setContent(content, false);
    }
  }, [content, editor]);

  // Sync disabled state
  useEffect(() => {
    if (editor) {
      editor.setEditable(!disabled);
    }
  }, [disabled, editor]);

  const insertVariable = (tag) => {
    if (editor) {
      // Create a spanned element that looks like a chip but is just styled text
      const html = `<span style="background: rgba(14, 165, 233, 0.15); border: 1px solid rgba(14, 165, 233, 0.3); border-radius: 4px; padding: 2px 6px; font-family: monospace; color: var(--accent);">${tag}</span>&nbsp;`;
      editor.chain().focus().insertContent(html).run();
    }
  };

  const addLink = useCallback(() => {
    if (!editor) return;
    const previousUrl = editor.getAttributes('link').href;
    const url = window.prompt('URL', previousUrl);
    
    if (url === null) return;
    if (url === '') {
      editor.chain().focus().extendMarkRange('link').unsetLink().run();
      return;
    }
    editor.chain().focus().extendMarkRange('link').setLink({ href: url }).run();
  }, [editor]);

  const addImage = useCallback(() => {
    if (!editor) return;
    const url = window.prompt('Image URL');
    if (url) {
      editor.chain().focus().setImage({ src: url }).run();
    }
  }, [editor]);

  if (!editor) {
    return null;
  }

  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      borderRadius: '12px',
      border: '1px solid var(--card-border)',
      background: 'var(--card-bg)',
      overflow: 'hidden',
      height: '100%',
      minHeight: '400px'
    }}>
      {/* TOOLBAR */}
      <div style={{
        display: 'flex',
        flexWrap: 'wrap',
        alignItems: 'center',
        padding: '8px',
        gap: '4px',
        borderBottom: '1px solid var(--card-border)',
        background: 'var(--bg-surface)',
        position: 'sticky',
        top: 0,
        zIndex: 10
      }}>
        {/* Group 1: Text Format */}
        <ToolbarButton onClick={() => editor.chain().focus().toggleBold().run()} isActive={editor.isActive('bold')} disabled={disabled} title="Bold">
          <Bold size={16} />
        </ToolbarButton>
        <ToolbarButton onClick={() => editor.chain().focus().toggleItalic().run()} isActive={editor.isActive('italic')} disabled={disabled} title="Italic">
          <Italic size={16} />
        </ToolbarButton>
        <ToolbarButton onClick={() => editor.chain().focus().toggleUnderline().run()} isActive={editor.isActive('underline')} disabled={disabled} title="Underline">
          <UnderlineIcon size={16} />
        </ToolbarButton>
        <ToolbarButton onClick={() => editor.chain().focus().toggleStrike().run()} isActive={editor.isActive('strike')} disabled={disabled} title="Strikethrough">
          <Strikethrough size={16} />
        </ToolbarButton>
        <ToolbarSeparator />

        {/* Group 2: Structure */}
        <ToolbarButton onClick={() => editor.chain().focus().toggleHeading({ level: 1 }).run()} isActive={editor.isActive('heading', { level: 1 })} disabled={disabled} title="Heading 1">
          <Heading1 size={16} />
        </ToolbarButton>
        <ToolbarButton onClick={() => editor.chain().focus().toggleHeading({ level: 2 }).run()} isActive={editor.isActive('heading', { level: 2 })} disabled={disabled} title="Heading 2">
          <Heading2 size={16} />
        </ToolbarButton>
        <ToolbarButton onClick={() => editor.chain().focus().toggleHeading({ level: 3 }).run()} isActive={editor.isActive('heading', { level: 3 })} disabled={disabled} title="Heading 3">
          <Heading3 size={16} />
        </ToolbarButton>
        <ToolbarButton onClick={() => editor.chain().focus().setParagraph().run()} isActive={editor.isActive('paragraph')} disabled={disabled} title="Paragraph">
          <Type size={16} />
        </ToolbarButton>
        <ToolbarSeparator />

        {/* Group 3: Lists */}
        <ToolbarButton onClick={() => editor.chain().focus().toggleBulletList().run()} isActive={editor.isActive('bulletList')} disabled={disabled} title="Bullet List">
          <List size={16} />
        </ToolbarButton>
        <ToolbarButton onClick={() => editor.chain().focus().toggleOrderedList().run()} isActive={editor.isActive('orderedList')} disabled={disabled} title="Ordered List">
          <ListOrdered size={16} />
        </ToolbarButton>
        <ToolbarSeparator />

        {/* Group 4: Alignment */}
        <ToolbarButton onClick={() => editor.chain().focus().setTextAlign('left').run()} isActive={editor.isActive({ textAlign: 'left' })} disabled={disabled} title="Align Left">
          <AlignLeft size={16} />
        </ToolbarButton>
        <ToolbarButton onClick={() => editor.chain().focus().setTextAlign('center').run()} isActive={editor.isActive({ textAlign: 'center' })} disabled={disabled} title="Align Center">
          <AlignCenter size={16} />
        </ToolbarButton>
        <ToolbarButton onClick={() => editor.chain().focus().setTextAlign('right').run()} isActive={editor.isActive({ textAlign: 'right' })} disabled={disabled} title="Align Right">
          <AlignRight size={16} />
        </ToolbarButton>
        <ToolbarSeparator />

        {/* Group 5: Insert */}
        <ToolbarButton onClick={addLink} isActive={editor.isActive('link')} disabled={disabled} title="Insert Link">
          <LinkIcon size={16} />
        </ToolbarButton>
        <ToolbarButton onClick={addImage} isActive={editor.isActive('image')} disabled={disabled} title="Insert Image">
          <ImageIcon size={16} />
        </ToolbarButton>
        <ToolbarButton onClick={() => editor.chain().focus().insertTable({ rows: 3, cols: 3, withHeaderRow: true }).run()} disabled={disabled} title="Insert Table">
          <TableIcon size={16} />
        </ToolbarButton>
        <ToolbarButton onClick={() => editor.chain().focus().setHorizontalRule().run()} disabled={disabled} title="Horizontal Rule">
          <Minus size={16} />
        </ToolbarButton>
        <ToolbarSeparator />

        {/* Group 6: Block */}
        <ToolbarButton onClick={() => editor.chain().focus().toggleBlockquote().run()} isActive={editor.isActive('blockquote')} disabled={disabled} title="Blockquote">
          <Quote size={16} />
        </ToolbarButton>
        <ToolbarButton onClick={() => editor.chain().focus().toggleCodeBlock().run()} isActive={editor.isActive('codeBlock')} disabled={disabled} title="Code Block">
          <Code size={16} />
        </ToolbarButton>
        <ToolbarSeparator />

        {/* Group 7: History */}
        <ToolbarButton onClick={() => editor.chain().focus().undo().run()} disabled={disabled || !editor.can().undo()} title="Undo">
          <Undo size={16} />
        </ToolbarButton>
        <ToolbarButton onClick={() => editor.chain().focus().redo().run()} disabled={disabled || !editor.can().redo()} title="Redo">
          <Redo size={16} />
        </ToolbarButton>
        
        <div style={{ flex: 1 }} />
        
        {/* Variables Dropdown (Custom implementation for inline styles) */}
        <div style={{ position: 'relative' }} className="group">
          <button
            type="button"
            disabled={disabled}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              padding: '6px 12px',
              borderRadius: '6px',
              background: 'var(--accent)',
              color: 'white',
              border: 'none',
              fontSize: '13px',
              fontWeight: 500,
              cursor: disabled ? 'not-allowed' : 'pointer',
              opacity: disabled ? 0.5 : 1
            }}
          >
            <Braces size={14} /> Variables
          </button>
          
          <div className="absolute right-0 top-full mt-1 w-48 bg-[var(--card-bg)] border border-[var(--card-border)] rounded-lg shadow-xl opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all z-50 py-1">
            {variablesList.map((v, i) => (
              <button
                key={i}
                type="button"
                onClick={() => insertVariable(v.tag)}
                disabled={disabled}
                className="w-full text-left px-3 py-2 text-sm text-[var(--text-secondary)] hover:bg-[var(--bg-surface)] hover:text-white transition-colors flex justify-between items-center"
              >
                <span>{v.label}</span>
                <span className="text-xs text-[var(--text-muted)] font-mono">{v.tag}</span>
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* EDITOR AREA */}
      <div style={{ flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column' }}>
        <div style={{ padding: '16px', flex: 1, color: 'var(--text-primary)' }}>
          <EditorContent editor={editor} />
        </div>
        
        {/* SIGNATURE SECTION */}
        {signature && (
          <div style={{
            padding: '16px',
            borderTop: '1px dashed var(--card-border)',
            opacity: 0.6,
            background: 'var(--bg-surface)'
          }}>
            <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginBottom: '8px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              Appended Signature
            </div>
            <div dangerouslySetInnerHTML={{ __html: signature }} style={{ fontSize: '13px', fontFamily: 'var(--mono)' }} />
          </div>
        )}
      </div>

      {/* GLOBAL TIPTAP STYLES */}
      <style dangerouslySetInnerHTML={{ __html: `
        .ProseMirror { outline: none; min-height: 250px; font-family: 'Inter', sans-serif; font-size: 14px; line-height: 1.6; }
        .ProseMirror p { margin: 0.25em 0; }
        .ProseMirror p.is-editor-empty:first-child::before {
          content: attr(data-placeholder);
          float: left;
          color: var(--text-muted);
          pointer-events: none;
          height: 0;
        }
        .ProseMirror h1 { font-size: 1.5em; font-weight: 700; margin: 1em 0 0.5em; }
        .ProseMirror h2 { font-size: 1.25em; font-weight: 700; margin: 1em 0 0.5em; }
        .ProseMirror h3 { font-size: 1.1em; font-weight: 600; margin: 1em 0 0.5em; }
        .ProseMirror blockquote { border-left: 3px solid var(--accent); padding-left: 12px; margin-left: 0; color: var(--text-secondary); }
        .ProseMirror code { background: rgba(255,255,255,0.06); padding: 2px 6px; border-radius: 4px; font-family: monospace; font-size: 0.9em; }
        .ProseMirror pre { background: rgba(0,0,0,0.3); padding: 12px; border-radius: 8px; overflow-x: auto; font-family: monospace; }
        .ProseMirror pre code { background: none; padding: 0; color: inherit; }
        .ProseMirror table { border-collapse: collapse; width: 100%; margin: 1em 0; }
        .ProseMirror td, .ProseMirror th { border: 1px solid var(--card-border); padding: 8px 12px; position: relative; }
        .ProseMirror th { background: rgba(255,255,255,0.04); font-weight: 600; text-align: left; }
        .ProseMirror img { max-width: 100%; border-radius: 8px; margin: 1em 0; }
        .ProseMirror a { color: var(--accent); text-decoration: underline; cursor: pointer; }
        .ProseMirror ul { padding-left: 24px; list-style-type: disc; margin: 0.5em 0; }
        .ProseMirror ol { padding-left: 24px; list-style-type: decimal; margin: 0.5em 0; }
        .ProseMirror li > p { margin: 0; }
      `}} />
    </div>
  );
}
