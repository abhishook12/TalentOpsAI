-- ============================================================
-- TalentOps AI — PostgreSQL Database Schema
-- Version: 1.0
-- ============================================================

-- Drop tables if re-running (safe reset)
DROP TABLE IF EXISTS submissions CASCADE;
DROP TABLE IF EXISTS candidates CASCADE;
DROP TABLE IF EXISTS recruiters CASCADE;
DROP TABLE IF EXISTS vendors CASCADE;
DROP TABLE IF EXISTS companies CASCADE;
DROP TABLE IF EXISTS users CASCADE;

-- ============================================================
-- COMPANIES
-- ============================================================
CREATE TABLE companies (
    company_id      SERIAL PRIMARY KEY,
    company_name    VARCHAR(255) NOT NULL,
    industry        VARCHAR(100),
    location        VARCHAR(150),
    website         VARCHAR(255),
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================
-- VENDORS
-- ============================================================
CREATE TABLE vendors (
    vendor_id       SERIAL PRIMARY KEY,
    vendor_name     VARCHAR(255) NOT NULL,
    contact_name    VARCHAR(150),
    email           VARCHAR(150) UNIQUE,
    phone           VARCHAR(30),
    location        VARCHAR(150),
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================
-- RECRUITERS
-- ============================================================
CREATE TABLE recruiters (
    recruiter_id        SERIAL PRIMARY KEY,
    recruiter_name      VARCHAR(150) NOT NULL,
    email               VARCHAR(150) UNIQUE NOT NULL,
    phone               VARCHAR(30),
    linkedin            VARCHAR(255),
    specialization      VARCHAR(150),
    company_id          INT REFERENCES companies(company_id) ON DELETE SET NULL,
    is_active           BOOLEAN DEFAULT TRUE,
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================
-- CANDIDATES
-- ============================================================
CREATE TABLE candidates (
    candidate_id        SERIAL PRIMARY KEY,
    candidate_name      VARCHAR(150) NOT NULL,
    email               VARCHAR(150) UNIQUE NOT NULL,
    phone               VARCHAR(30),
    linkedin            VARCHAR(255),
    visa_status         VARCHAR(50),   -- H1B, GC, USC, OPT, CPT, TN etc.
    skills              TEXT[],        -- array of skill strings
    experience_years    NUMERIC(4,1),
    location            VARCHAR(150),
    rate_per_hour       NUMERIC(8,2),
    availability        VARCHAR(50),   -- immediate, 2 weeks, 1 month
    is_duplicate        BOOLEAN DEFAULT FALSE,
    duplicate_of        INT REFERENCES candidates(candidate_id) ON DELETE SET NULL,
    recruiter_id        INT REFERENCES recruiters(recruiter_id) ON DELETE SET NULL,
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================
-- SUBMISSIONS
-- ============================================================
CREATE TABLE submissions (
    submission_id       SERIAL PRIMARY KEY,
    candidate_id        INT NOT NULL REFERENCES candidates(candidate_id) ON DELETE CASCADE,
    recruiter_id        INT REFERENCES recruiters(recruiter_id) ON DELETE SET NULL,
    company_id          INT REFERENCES companies(company_id) ON DELETE SET NULL,
    vendor_id           INT REFERENCES vendors(vendor_id) ON DELETE SET NULL,
    job_title           VARCHAR(150),
    status              VARCHAR(50) DEFAULT 'submitted',
                        -- submitted, interview, offer, rejected, placed, withdrawn
    submission_date     DATE DEFAULT CURRENT_DATE,
    interview_date      DATE,
    notes               TEXT,
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================
-- USERS (for login/auth later)
-- ============================================================
CREATE TABLE users (
    user_id         SERIAL PRIMARY KEY,
    username        VARCHAR(100) UNIQUE NOT NULL,
    email           VARCHAR(150) UNIQUE NOT NULL,
    password_hash   VARCHAR(255) NOT NULL,
    role            VARCHAR(50) DEFAULT 'analyst', -- admin, analyst, viewer
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================
-- INDEXES for fast querying
-- ============================================================
CREATE INDEX idx_candidates_email       ON candidates(email);
CREATE INDEX idx_candidates_visa        ON candidates(visa_status);
CREATE INDEX idx_candidates_skills      ON candidates USING GIN(skills);
CREATE INDEX idx_recruiters_email       ON recruiters(email);
CREATE INDEX idx_submissions_status     ON submissions(status);
CREATE INDEX idx_submissions_date       ON submissions(submission_date);
CREATE INDEX idx_submissions_candidate  ON submissions(candidate_id);
CREATE INDEX idx_submissions_recruiter  ON submissions(recruiter_id);

-- ============================================================
-- SAMPLE SEED DATA
-- ============================================================

-- Companies
INSERT INTO companies (company_name, industry, location) VALUES
('TechCorp Solutions', 'Information Technology', 'Austin, TX'),
('DataBridge Inc', 'Data & Analytics', 'Chicago, IL'),
('CloudNova Systems', 'Cloud Infrastructure', 'Seattle, WA'),
('FinEdge Partners', 'Financial Services', 'New York, NY'),
('HealthSync Corp', 'Healthcare IT', 'Boston, MA');

-- Vendors
INSERT INTO vendors (vendor_name, contact_name, email, phone, location) VALUES
('StaffBridge LLC', 'Mike Torres', 'mike@staffbridge.com', '312-555-0101', 'Chicago, IL'),
('TalentLink Corp', 'Sarah Kim', 'sarah@talentlink.com', '512-555-0202', 'Austin, TX'),
('PrimeStaff Inc', 'David Patel', 'david@primestaff.com', '206-555-0303', 'Seattle, WA');

-- Recruiters
INSERT INTO recruiters (recruiter_name, email, phone, linkedin, specialization, company_id) VALUES
('James Carter',   'james.carter@techcorp.com',   '512-555-1001', 'linkedin.com/in/jamescarter',   'Java / Backend',        1),
('Priya Sharma',   'priya.sharma@databridge.com',  '312-555-1002', 'linkedin.com/in/priyasharma',   'Data Engineering',      2),
('Kevin Nguyen',   'kevin.nguyen@cloudnova.com',   '206-555-1003', 'linkedin.com/in/kevinnguyen',   'DevOps / Cloud',        3),
('Lisa Hernandez', 'lisa.h@finedge.com',           '212-555-1004', 'linkedin.com/in/lisahernandez', 'Finance Tech',          4),
('Raj Patel',      'raj.patel@healthsync.com',     '617-555-1005', 'linkedin.com/in/rajpatel',      'Healthcare IT',         5);

-- Candidates
INSERT INTO candidates (candidate_name, email, phone, visa_status, skills, experience_years, location, rate_per_hour, availability, recruiter_id) VALUES
('Arjun Mehta',    'arjun.mehta@email.com',    '415-555-2001', 'H1B',  ARRAY['Java','Spring Boot','Microservices','SQL'],  5.0, 'San Jose, CA',    85.00, 'immediate',  1),
('Emily Zhang',    'emily.zhang@email.com',     '312-555-2002', 'GC',   ARRAY['Python','Pandas','SQL','Power BI','ETL'],    3.5, 'Chicago, IL',     75.00, '2 weeks',    2),
('Carlos Rivera',  'carlos.r@email.com',        '512-555-2003', 'USC',  ARRAY['React','Node.js','TypeScript','AWS'],        4.0, 'Austin, TX',      90.00, 'immediate',  1),
('Neha Singh',     'neha.singh@email.com',      '206-555-2004', 'OPT',  ARRAY['Python','Machine Learning','TensorFlow'],    2.0, 'Seattle, WA',     65.00, '1 month',    3),
('David Kim',      'david.kim@email.com',       '212-555-2005', 'GC',   ARRAY['SQL','PostgreSQL','Data Modeling','ETL'],    6.0, 'New York, NY',    95.00, 'immediate',  4),
('Fatima Al-Hassan','fatima.ah@email.com',      '617-555-2006', 'H1B',  ARRAY['Java','Hibernate','Oracle','Spring'],        4.5, 'Boston, MA',      80.00, '2 weeks',    5),
('Ryan Thompson',  'ryan.t@email.com',          '512-555-2007', 'USC',  ARRAY['DevOps','Kubernetes','Docker','Terraform'],  5.5, 'Austin, TX',      100.00,'immediate',  3),
('Aisha Patel',    'aisha.p@email.com',         '415-555-2008', 'OPT',  ARRAY['Python','Django','REST APIs','PostgreSQL'],  1.5, 'San Francisco, CA',60.00, '2 weeks',    2);

-- Submissions
INSERT INTO submissions (candidate_id, recruiter_id, company_id, vendor_id, job_title, status, submission_date) VALUES
(1, 1, 1, 1, 'Senior Java Developer',       'interview',  '2026-04-10'),
(2, 2, 2, 2, 'Data Analyst',                'submitted',  '2026-04-15'),
(3, 1, 3, 2, 'Frontend Engineer',           'offer',      '2026-04-08'),
(4, 3, 3, 3, 'ML Engineer',                 'submitted',  '2026-04-20'),
(5, 4, 4, 1, 'Senior SQL Developer',        'placed',     '2026-03-28'),
(6, 5, 5, 3, 'Java Backend Engineer',       'rejected',   '2026-04-05'),
(7, 3, 3, 2, 'DevOps Engineer',             'interview',  '2026-04-18'),
(8, 2, 2, 1, 'Junior Python Developer',     'submitted',  '2026-04-22');
