/**
 * TalentOps Deterministic Mock API Service
 *
 * Generates stable demo datasets that progress smoothly with the calendar date
 * and time-of-day. Rapid polling (e.g. 5-second intervals) returns completely stable
 * identical numbers instead of jumping erratically.
 */

/**
 * Deterministic Value Generator
 * @param {number} min - Minimum value (inclusive)
 * @param {number} max - Maximum value (inclusive)
 * @param {number} seedOffset - Optional seed offset to distinguish different metrics
 * @param {Date} [now] - Optional reference date
 * @returns {number} Deterministic integer within [min, max]
 */
export function dv(min, max, seedOffset = 0, now = new Date()) {
  const y = now.getFullYear();
  const m = now.getMonth() + 1;
  const d = now.getDate();
  const minutes = now.getHours() * 60 + now.getMinutes();

  // Seed changes smoothly every 15 minutes, remaining stable during fast refreshes
  const timeBlock = Math.floor(minutes / 15);
  const seed = Math.abs(
    (y * 10000 + m * 100 + d + seedOffset * 31337 + timeBlock * 101) % 2147483647
  );
  
  // Sine pseudo-random normalized generator
  const x = Math.sin(seed) * 10000;
  const norm = x - Math.floor(x);
  return Math.floor(norm * (max - min + 1)) + min;
}

/**
 * Deterministic ISO timestamp helper
 * Generates an ISO string roughly `hoursAgo` in the past from now.
 */
export function deterministicTimestamp(hoursAgo = 2, now = new Date()) {
  const target = new Date(now.getTime() - hoursAgo * 3600 * 1000);
  return target.toISOString();
}

/**
 * Get Deterministic Dashboard KPIs
 */
export function getMockKPIs() {
  return {
    total_recruiters: dv(46200, 47100, 1),
    active_recruiters: dv(41000, 42500, 2),
    verified_deliverable: dv(34800, 35900, 3),
    companies_covered: dv(8400, 8900, 4),
    staged_records: dv(12, 28, 5),
    ingested_today: dv(180, 260, 6),
    data_quality_index: dv(91, 95, 7),
  };
}

/**
 * Get Deterministic Page Visits & Traffic
 */
export function getMockVisits() {
  const total = dv(14200, 15400, 10);
  const today = dv(480, 620, 11);
  const yesterday = dv(450, 590, 12);

  return {
    total_visits: total,
    today,
    yesterday,
    top_pages: [
      { page: '/recruiters', visits: dv(1400, 1600, 13) },
      { page: '/search', visits: dv(1100, 1300, 14) },
      { page: '/companies', visits: dv(850, 980, 15) },
      { page: '/directory', visits: dv(620, 740, 16) },
      { page: '/analytics', visits: dv(410, 520, 17) },
    ],
  };
}

/**
 * Get Deterministic Ingestion Pipeline Metrics
 */
export function getMockIngestionMetrics() {
  const rawObs = dv(540, 680, 20);
  const useful = dv(210, 260, 21);
  const staging = dv(8, 22, 22);
  const enriched = dv(54, 72, 23);
  const newCreated = dv(32, 48, 24);

  return {
    metrics_today: {
      raw_observations_received: rawObs,
      useful_discoveries: useful,
      staging_records: staging,
      validated_records: useful,
      new_people_created: newCreated,
      existing_people_enriched: enriched,
      fields_added: dv(180, 240, 25),
      fields_corrected: dv(12, 24, 26),
      duplicates_ignored: dv(20, 35, 27),
      rejected_low_confidence: dv(6, 14, 28),
      companies_discovered: dv(15, 25, 29),
      jobs_discovered: dv(45, 65, 30),
      staffing_signals: dv(38, 55, 31),
      master_db_inserts: newCreated,
      master_db_updates: enriched,
    },
    timestamps: {
      last_scraper_observation: deterministicTimestamp(0.08),
      last_screenshot: deterministicTimestamp(0.12),
      last_staging_write: deterministicTimestamp(0.25),
      last_enrichment: deterministicTimestamp(0.4),
      last_new_record: deterministicTimestamp(1.2),
      last_master_db_update: deterministicTimestamp(0.4),
    },
    pipeline_state: staging > 0 ? 'PROCESSING' : 'RECEIVING_DATA',
    status_detail: staging > 0 ? 'Batch processing staging buffer' : 'Receiving edge telemetry',
    recent_enrichment_diffs: [
      {
        event_id: 'DIFF-001',
        timestamp: '14:22:10',
        candidate_name: 'Sarah Jenkins',
        company_name: 'Apex Systems',
        decision: 'ENRICHED',
        fields_added: ['phone', 'linkedin_url'],
        capture_id: 'CAP-9012',
        db_status: 'COMMITTED',
      },
      {
        event_id: 'DIFF-002',
        timestamp: '14:18:45',
        candidate_name: 'David Miller',
        company_name: 'Insight Global',
        decision: 'NEW_DISCOVERY',
        fields_added: ['email', 'title', 'location'],
        capture_id: 'CAP-9011',
        db_status: 'COMMITTED',
      },
      {
        event_id: 'DIFF-003',
        timestamp: '14:05:32',
        candidate_name: 'Elena Rostova',
        company_name: 'Robert Half',
        decision: 'ENRICHED',
        fields_added: ['seniority_level'],
        capture_id: 'CAP-9009',
        db_status: 'COMMITTED',
      },
    ],
  };
}

/**
 * Deterministic Mock Recruiters Dataset
 */
export function getMockRecruiters() {
  return [
    {
      recruiter_id: 101,
      recruiter_name: 'Marcus Vance',
      specialization: 'Cloud Infrastructure & DevOps',
      seniority_level: 'Lead',
      is_deliverable: true,
      completeness_score: 94,
      last_active_at: deterministicTimestamp(2),
      company_name: 'Apex Systems',
      company_domain: 'apexsystems.com',
      email: 'mvance@apexsystems.com',
      email_status: 'verified',
      email_confidence: 98,
      state: 'TX',
      city: 'Austin',
      is_active: true,
      quality_score: 96,
      timezone: 'America/Chicago',
      timezone_code: 'CT',
    },
    {
      recruiter_id: 102,
      recruiter_name: 'Danielle Brooks',
      specialization: 'Full Stack & Distributed Systems',
      seniority_level: 'Senior',
      is_deliverable: true,
      completeness_score: 88,
      last_active_at: deterministicTimestamp(5),
      company_name: 'Insight Global',
      company_domain: 'insightglobal.com',
      email: 'dbrooks@insightglobal.com',
      email_status: 'verified',
      email_confidence: 95,
      state: 'NC',
      city: 'Raleigh',
      is_active: true,
      quality_score: 92,
      timezone: 'America/New_York',
      timezone_code: 'ET',
    },
    {
      recruiter_id: 103,
      recruiter_name: 'Alexandria Sterling',
      specialization: 'Executive Leadership & AI/ML',
      seniority_level: 'Executive',
      is_deliverable: true,
      completeness_score: 96,
      last_active_at: deterministicTimestamp(1),
      company_name: 'Robert Half',
      company_domain: 'roberthalf.com',
      email: 'asterling@roberthalf.com',
      email_status: 'verified',
      email_confidence: 99,
      state: 'CA',
      city: 'San Francisco',
      is_active: true,
      quality_score: 98,
      timezone: 'America/Los_Angeles',
      timezone_code: 'PT',
    },
    {
      recruiter_id: 104,
      recruiter_name: 'Liam O\'Connor',
      specialization: 'Cybersecurity & Governance',
      seniority_level: 'Specialist',
      is_deliverable: false,
      completeness_score: 62,
      last_active_at: deterministicTimestamp(28),
      company_name: 'TEKsystems',
      company_domain: 'teksystems.com',
      email: 'loconnor@teksystems.com',
      email_status: 'needs_monitoring',
      email_confidence: 65,
      state: 'IL',
      city: 'Chicago',
      is_active: true,
      quality_score: 70,
      timezone: 'America/Chicago',
      timezone_code: 'CT',
    },
    {
      recruiter_id: 105,
      recruiter_name: 'Priya Patel',
      specialization: 'Data Engineering & Analytics',
      seniority_level: 'Senior',
      is_deliverable: true,
      completeness_score: 91,
      last_active_at: deterministicTimestamp(9),
      company_name: 'CyberCoders',
      company_domain: 'cybercoders.com',
      email: 'ppatel@cybercoders.com',
      email_status: 'likely_valid',
      email_confidence: 88,
      state: 'NY',
      city: 'New York',
      is_active: true,
      quality_score: 90,
      timezone: 'America/New_York',
      timezone_code: 'ET',
    },
  ];
}
