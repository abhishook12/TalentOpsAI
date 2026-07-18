const API_URL = 'https://talentopsai-1.onrender.com';

async function runTests() {
    console.log('--- Phase 2: Validation Engine & API Gateway QA ---');
    
    // Test 2.1: Mixed validation (valid, invalid, disposable, duplicate, enriched)
    console.log('\n[Test 2.1] Submitting mixed email list...');
    const mixedEmails = [
        'valid1@example.com',
        'invalid-email-format',
        'valid1@example.com', // Duplicate
        'throwaway@10minutemail.com', // Disposable
        'qa_enrichment@example.com' // Should be enriched
    ];
    
    try {
        const start1 = Date.now();
        const res1 = await fetch(`${API_URL}/campaigns/validate-recipients`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ emails: mixedEmails })
        });
        const data1 = await res1.json();
        const duration1 = Date.now() - start1;
        
        console.log(`Response received in ${duration1}ms`);
        console.log(`Total: ${data1.total}, Valid: ${data1.valid_count}, Invalid: ${data1.invalid_count}, Duplicate: ${data1.duplicate_count}, Disposable: ${data1.disposable_count}`);
        
        let passed2_1 = true;
        if (data1.valid_count !== 2) { console.error('❌ Expected 2 valid'); passed2_1 = false; }
        if (data1.invalid_count !== 1) { console.error('❌ Expected 1 invalid'); passed2_1 = false; }
        if (data1.duplicate_count !== 1) { console.error('❌ Expected 1 duplicate'); passed2_1 = false; }
        if (data1.disposable_count !== 1) { console.error('❌ Expected 1 disposable'); passed2_1 = false; }
        
        const enriched = data1.recipients.find(r => r.email === 'qa_enrichment@example.com');
        if (!enriched) {
            console.error('❌ Enriched recipient not found in output');
            passed2_1 = false;
        } else if (enriched.company_name !== 'QA Testing Inc') {
            console.error(`❌ Enrichment failed. Expected 'QA Testing Inc', got '${enriched.company_name}'`);
            passed2_1 = false;
        } else {
            console.log(`✅ Enrichment verified: ${enriched.recruiter_name} at ${enriched.company_name}`);
        }
        
        if (passed2_1) {
            console.log('✅ Test 2.1 Passed: Validation logic and enrichment correctly segregated emails.');
        }
        
    } catch (e) {
        console.error('❌ Test 2.1 Failed with error:', e.message);
    }
    
    // Test 2.2: Load check (2000 emails)
    console.log('\n[Test 2.2] Load testing with 2000 unique emails...');
    const loadEmails = [];
    for (let i = 0; i < 2000; i++) {
        loadEmails.push(`load_test_${i}@example.com`);
    }
    
    try {
        const start2 = Date.now();
        const res2 = await fetch(`${API_URL}/campaigns/validate-recipients`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ emails: loadEmails })
        });
        const data2 = await res2.json();
        const duration2 = Date.now() - start2;
        
        console.log(`Response received in ${duration2}ms`);
        if (data2.valid_count === 2000) {
            console.log(`✅ Test 2.2 Passed: Successfully processed 2000 emails in ${duration2}ms`);
        } else {
            console.error(`❌ Test 2.2 Failed: Expected 2000 valid, got ${data2.valid_count}`);
        }
    } catch (e) {
        console.error('❌ Test 2.2 Failed with error:', e.message);
    }
    
}

runTests();
