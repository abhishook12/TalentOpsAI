import React from 'react';
import { Laptop, Globe, FileSpreadsheet, UserCheck, Sparkles, UploadCloud } from 'lucide-react';
import { classifyCandidateSource, SOURCE_TYPES } from '../../utils/sourceProvenance';

/**
 * SourceProvenanceBadge — High-contrast, clean visual pill indicating candidate origin.
 * Clearly differentiates:
 * - Desktop Scout captures
 * - Web Harvester extractions
 * - Bulk Uploads / Spreadsheets
 * - Manual entries
 */
export default function SourceProvenanceBadge({
  source,
  size = 'sm',
  showIcon = true,
  detailed = false,
  className = '',
  style = {},
}) {
  const info = classifyCandidateSource(source);

  const getIcon = () => {
    const iconSize = size === 'xs' ? 'w-2.5 h-2.5' : size === 'lg' ? 'w-4 h-4' : 'w-3 h-3';
    switch (info.type) {
      case SOURCE_TYPES.SCOUT:
        return <Laptop className={iconSize} />;
      case SOURCE_TYPES.WEB_HARVESTER:
        return <Globe className={iconSize} />;
      case SOURCE_TYPES.BULK_UPLOAD:
        return <FileSpreadsheet className={iconSize} />;
      case SOURCE_TYPES.MANUAL:
      default:
        return <UserCheck className={iconSize} />;
    }
  };

  const displayText = detailed ? info.label : info.shortLabel;

  // Monochrome black & white high-contrast styling adhering to design rules
  const baseStyle = {
    display: 'inline-flex',
    alignItems: 'center',
    gap: size === 'xs' ? 3 : 5,
    borderRadius: 9999,
    fontSize: size === 'xs' ? 9.5 : size === 'lg' ? 12 : 11,
    fontWeight: 650,
    letterSpacing: '0.02em',
    whiteSpace: 'nowrap',
    transition: 'all 0.15s ease',
    ...style,
  };

  const sizeClasses = size === 'xs'
    ? 'px-1.5 py-0.5'
    : size === 'lg'
    ? 'px-3 py-1'
    : 'px-2 py-0.5';

  return (
    <span
      className={`border ${sizeClasses} ${info.badgeClass} ${className}`}
      style={baseStyle}
      title={info.description}
    >
      {showIcon && getIcon()}
      <span>{displayText}</span>
    </span>
  );
}
