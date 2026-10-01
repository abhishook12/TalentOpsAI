/**
 * sourceProvenance.js — Authoritative Candidate Origin & Sourcing Channel Classifier.
 * 
 * Accurately categorizes any candidate's data_source into distinct, user-distinguishable origins:
 * 1. SCOUT: Desktop Scout / Browser Extension autonomous captures.
 * 2. WEB_HARVESTER: Autonomous Web Harvester, Search X-Ray, and Deep Discovery pipelines.
 * 3. BULK_UPLOAD: XLSX, CSV, Roster bulk ingestions, and ETL batch uploads.
 * 4. MANUAL: Manual user entry or explicit record creation.
 */

export const SOURCE_TYPES = {
  SCOUT: 'SCOUT',
  WEB_HARVESTER: 'WEB_HARVESTER',
  BULK_UPLOAD: 'BULK_UPLOAD',
  MANUAL: 'MANUAL',
};

export function classifyCandidateSource(rawSource) {
  if (!rawSource || typeof rawSource !== 'string' || !rawSource.trim()) {
    return {
      type: SOURCE_TYPES.MANUAL,
      label: 'Manual Entry',
      shortLabel: 'Manual Entry',
      tag: 'MANUAL',
      description: 'Directly created or manually entered in the system',
      badgeClass: 'bg-zinc-800/80 text-zinc-300 border-zinc-700/80',
      iconType: 'manual',
      raw: rawSource || 'manual',
    };
  }

  const s = rawSource.trim().toLowerCase();

  // 1. Web Harvester / Web Intelligence Pipelines
  if (
    s.startsWith('web_intelligence') ||
    s.startsWith('web_harvest') ||
    s.includes('harvest') ||
    s.includes('search_xray') ||
    s.includes('email_signature_flywheel') ||
    s.includes('discovery_worker')
  ) {
    let specificLabel = 'Web Harvester';
    if (s.includes('search_xray')) specificLabel = 'Web Harvester (X-Ray)';
    else if (s.includes('signature')) specificLabel = 'Web Harvester (Signature)';
    else if (s.includes('web_harvest')) specificLabel = 'Web Harvester';

    return {
      type: SOURCE_TYPES.WEB_HARVESTER,
      label: specificLabel,
      shortLabel: 'Web Harvester',
      tag: 'WEB HARVEST',
      description: 'Discovered autonomously by the AI Web Harvester engine',
      badgeClass: 'bg-white/10 text-white border-white/20',
      iconType: 'globe',
      raw: rawSource,
    };
  }

  // 2. Scout Desktop / Browser Extension
  if (
    s.includes('scout') ||
    s.includes('extension') ||
    s.includes('visual_capture') ||
    s.includes('chrome_extension') ||
    s.includes('staging_batch')
  ) {
    let specificLabel = 'Desktop Scout';
    if (s.includes('chrome_extension')) specificLabel = 'Scout Extension';
    else if (s.includes('visual_capture')) specificLabel = 'Scout (Visual DOM)';
    else if (s.includes('desktop')) specificLabel = 'Desktop Scout';

    return {
      type: SOURCE_TYPES.SCOUT,
      label: specificLabel,
      shortLabel: 'Desktop Scout',
      tag: 'SCOUT',
      description: 'Captured live by the Desktop Scout background worker',
      badgeClass: 'bg-zinc-100 text-zinc-950 font-bold border-white',
      iconType: 'laptop',
      raw: rawSource,
    };
  }

  // 3. Bulk Uploading / Spreadsheet / Files / Roster Import
  if (
    s.endsWith('.xlsx') ||
    s.endsWith('.csv') ||
    s.endsWith('.json') ||
    s.endsWith('.tsv') ||
    s.endsWith('.txt') ||
    s.includes('.xlsx::') ||
    s.includes('.csv::') ||
    s.includes('bulk_upload') ||
    s.includes('manual_upload') ||
    s.includes('user_roster_upload') ||
    s.includes('enterprise roster') ||
    s.includes('campaign_import') ||
    s.includes('parquet_canonical') ||
    s.includes('postgresql_roster') ||
    s.includes('etl') ||
    s.includes('text_dump') ||
    s.includes('location_workbook') ||
    s.includes('companies_state_workbook')
  ) {
    let cleanFilename = rawSource.trim();
    if (cleanFilename.includes('::')) {
      cleanFilename = cleanFilename.split('::')[0];
    }
    let shortName = 'Bulk Upload';
    if (cleanFilename.toLowerCase().endsWith('.xlsx') || cleanFilename.toLowerCase().endsWith('.csv')) {
      shortName = 'Bulk (Spreadsheet)';
    } else if (s.includes('roster')) {
      shortName = 'Bulk (Roster)';
    } else if (s.includes('campaign')) {
      shortName = 'Bulk (Campaign)';
    }

    return {
      type: SOURCE_TYPES.BULK_UPLOAD,
      label: `Bulk Upload: ${cleanFilename}`,
      shortLabel: shortName,
      tag: 'BULK UPLOAD',
      description: `Imported via bulk file or roster ingestion (${cleanFilename})`,
      badgeClass: 'bg-zinc-800 text-zinc-200 border-zinc-600',
      iconType: 'file',
      raw: rawSource,
    };
  }

  // Fallback to Manual
  return {
    type: SOURCE_TYPES.MANUAL,
    label: rawSource || 'Manual Entry',
    shortLabel: 'Manual Entry',
    tag: 'MANUAL',
    description: 'Manually added or created record',
    badgeClass: 'bg-zinc-800/80 text-zinc-300 border-zinc-700/80',
    iconType: 'manual',
    raw: rawSource,
  };
}
