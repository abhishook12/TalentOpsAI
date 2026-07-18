const API_URL = 'https://talentopsai-1.onrender.com';

async function runTests() {
    console.log('--- Phase 3: Pre-Flight Checklist Logic QA ---');
    
    // 1. Create a campaign
    const res1 = await fetch(`${API_URL}/campaigns`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            name: 'Phase 3 QA Campaign',
            status: 'draft'
        })
    });
    const campaign = await res1.json();
    const cid = campaign.campaign_id;
    console.log(`Created campaign ${cid}`);
    
    // 2. Pre-flight check (No template, no recipients)
    console.log('\n[Test 3.1] Checking empty campaign...');
    const res2 = await fetch(`${API_URL}/campaigns/${cid}/validate-before-send`, { method: 'POST' });
    const preflight1 = await res2.json();
    console.log(preflight1);
    if (!preflight1.has_template && !preflight1.has_recipients && !preflight1.ready) {
        console.log('✅ Empty campaign validation correct.');
    } else {
        console.error('❌ Failed empty campaign validation.');
    }
    
    // 3. Add template and recipients
    console.log('\n[Test 3.2] Adding templates and recipients...');
    await fetch(`${API_URL}/campaigns/${cid}/templates`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            name: 'Subject Test',
            subject: 'Subject Test',
            body: 'Body test'
        })
    });
    
    await fetch(`${API_URL}/campaigns/${cid}/enroll-emails`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            emails: ['test1@example.com']
        })
    });
    
    // 4. Pre-flight check (Has template, has recipients)
    const res3 = await fetch(`${API_URL}/campaigns/${cid}/validate-before-send`, { method: 'POST' });
    const preflight2 = await res3.json();
    console.log(preflight2);
    if (preflight2.has_template && preflight2.has_recipients) {
        console.log('✅ Template and recipient flags correctly detected.');
    } else {
        console.error('❌ Failed template/recipient detection.');
    }
    
    if (preflight2.bridge_healthy) {
        console.log('✅ Outlook Bridge is ONLINE.');
    } else {
        console.log('⚠️ Outlook Bridge is OFFLINE. (Expected if not running locally)');
    }
    
    if (preflight2.ready === preflight2.bridge_healthy) {
         console.log('✅ Ready state strictly matches Bridge state when templates and recipients exist.');
    } else {
         console.error('❌ Ready state logic failure.');
    }
    
    console.log('\n✅ Phase 3 complete.');
}

runTests();
