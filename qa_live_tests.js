const axios = require('axios');
const crypto = require('crypto');

const API_URL = 'https://talentopsai-1.onrender.com';
let token = '';

async function login() {
    const testEmail = `test_${Date.now()}@example.com`;
    const testPass = 'Password123!';
    
    console.log(`Registering ${testEmail}...`);
    try {
        await axios.post(`${API_URL}/auth/register`, {
            email: testEmail,
            password: testPass,
            first_name: 'Live',
            last_name: 'Test'
        });
        
        console.log('Activating...');
        const { execSync } = require('child_process');
        execSync(`python activate_user.py "${testEmail}"`);
        
        console.log('Logging in...');
        const res = await axios.post(`${API_URL}/auth/login`, {
            email: testEmail,
            password: testPass
        }, {
            headers: { 'Content-Type': 'application/json' }
        });
        token = res.data.token; // Note: In my backend, the field is 'token', not 'access_token'
        axios.defaults.headers.common['Authorization'] = `Bearer ${token}`;
        console.log('✅ Logged in successfully.');
    } catch (e) {
        console.error('Login error:', e.response ? e.response.data : e.message);
        process.exit(1);
    }
}

async function runCampaign(name, sender, recipients) {
    console.log(`\n--- Starting Campaign: ${name} ---`);
    const timestampId = crypto.randomBytes(4).toString('hex');
    const subject = `Live Production Test [${timestampId}] - ${name}`;
    
    // 1. Create Campaign
    const campRes = await axios.post(`${API_URL}/campaigns`, {
        name: name,
        from_email: sender,
        status: 'draft',
        is_active: true
    });
    const cid = campRes.data.campaign_id;
    console.log(`✅ Campaign created. ID: ${cid}`);
    
    // 2. Add Template
    await axios.post(`${API_URL}/campaigns/${cid}/templates`, {
        name: 'Template 1',
        subject: subject,
        body: `This is a live production test for ${name}. This email confirms the TalentOps Campaign Engine is fully operational.\nTimestamp: ${Date.now()}`
    });
    console.log('✅ Template added.');
    
    // 3. Enroll Recipients
    await axios.post(`${API_URL}/campaigns/${cid}/enroll-emails`, {
        emails: recipients
    });
    console.log(`✅ Enrolled ${recipients.length} recipients.`);
    
    // 4. Start Campaign
    await axios.post(`${API_URL}/campaigns/${cid}/start`);
    console.log(`✅ Campaign ${cid} started.`);
    
    // 5. Monitor Stream
    return new Promise(async (resolve, reject) => {
        let terminalReached = false;
        let logs = [];
        const timeout = setTimeout(() => {
            if (!terminalReached) {
                console.error(`❌ Timeout waiting for campaign ${cid}`);
                resolve({ success: false, subject: subject });
            }
        }, 120000); // 2 minutes max
        
        try {
            // Using axios GET without parsing as JSON, but fetching SSE is tricky in axios, fetch is better
            const response = await fetch(`${API_URL}/campaigns/${cid}/progress`, {
                headers: { 'Authorization': `Bearer ${token}` }
            });
            const reader = response.body.getReader();
            const decoder = new TextDecoder('utf-8');
            
            while (true) {
                const { value, done } = await reader.read();
                if (done) break;
                
                const chunk = decoder.decode(value, { stream: true });
                const lines = chunk.split('\n');
                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        try {
                            const data = JSON.parse(line.substring(6));
                            console.log(`Stream Update: Status=${data.status}, Sent=${data.sent}/${data.total}`);
                            
                            if (data.new_logs && data.new_logs.length > 0) {
                                data.new_logs.forEach(log => {
                                    console.log(`   -> Log [${log.status}]: ${log.email}`);
                                    logs.push(log);
                                });
                            }
                            
                            if (data.status === 'completed' || data.status === 'failed') {
                                terminalReached = true;
                                clearTimeout(timeout);
                                console.log(`✅ Campaign ${cid} finished with status: ${data.status}`);
                                resolve({ success: data.status === 'completed', subject: subject, logs });
                                return;
                            }
                        } catch (e) {}
                    }
                }
            }
        } catch (e) {
            console.error('Stream error:', e);
            resolve({ success: false, subject: subject });
        }
    });
}

async function runTests() {
    const startOverall = Date.now();
    await login();
    
    const sender = 'abhishek.jadon@technovion.com';
    
    // Test 1
    const t1Start = Date.now();
    const t1 = await runCampaign('Test 1 (Single Recipient)', sender, ['abhishekjadon706@gmail.com']);
    const t1Time = Date.now() - t1Start;
    
    // Test 2
    const t2Start = Date.now();
    const t2 = await runCampaign('Test 2 (Multiple Recipients)', sender, ['abhishekjadon706@gmail.com', 'abhishekjadon824@gmail.com']);
    const t2Time = Date.now() - t2Start;
    
    console.log('\n--- FINAL RESULTS ---');
    console.log(`Test 1 Subject Prefix: ${t1.subject}`);
    console.log(`Test 1 Processing Time: ${t1Time}ms`);
    console.log(`Test 2 Subject Prefix: ${t2.subject}`);
    console.log(`Test 2 Processing Time: ${t2Time}ms`);
    console.log(`Total Elapsed: ${(Date.now() - startOverall)/1000}s`);
    
    // Output subjects to a file for Python verification
    const fs = require('fs');
    fs.writeFileSync('C:/TalentOpsAI/live_test_subjects.txt', `${t1.subject}\n${t2.subject}`);
}

runTests();
