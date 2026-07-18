const axios = require('axios');

const API_URL = 'https://talentopsai-1.onrender.com';
const campaignId = 100;

async function runTests() {
    console.log('--- Phase 4: Campaign Sending Engine QA ---');
    
    // 1. Start Campaign
    console.log(`\n[Test 4.1] Starting Campaign ${campaignId}...`);
    try {
        const res = await axios.post(`${API_URL}/campaigns/${campaignId}/start`);
        console.log('✅ Start API triggered:', res.data);
    } catch (e) {
        console.error('❌ Failed to start campaign:', e.message);
        // It might already be started or completed, we can proceed to listen anyway.
    }
    
    // 2. Connect to Progress Stream
    console.log('\n[Test 4.2] Connecting to Progress Stream via Fetch...');
    
    let terminalReached = false;
    
    const timeout = setTimeout(() => {
        if (!terminalReached) {
            console.error('❌ Test timed out before campaign completed.');
            process.exit(1);
        }
    }, 45000); // Wait up to 45s
    
    try {
        const response = await fetch(`${API_URL}/campaigns/${campaignId}/progress`);
        const reader = response.body.getReader();
        const decoder = new TextDecoder('utf-8');
        
        while (true) {
            const { value, done } = await reader.read();
            if (done) break;
            
            const chunk = decoder.decode(value, { stream: true });
            // SSE chunks come as 'data: {...}\n\n'
            const lines = chunk.split('\n');
            for (const line of lines) {
                if (line.startsWith('data: ')) {
                    try {
                        const jsonStr = line.substring(6);
                        const data = JSON.parse(jsonStr);
                        console.log(`Stream Update: Status=${data.status}, Total=${data.total}, Sent=${data.sent}, Pending=${data.pending}`);
                        
                        if (data.new_logs && data.new_logs.length > 0) {
                            data.new_logs.forEach(log => {
                                console.log(`   -> Log [${log.status}]: ${log.email} (Error: ${log.error || 'None'})`);
                            });
                        }
                        
                        if (data.status === 'completed' || data.status === 'failed') {
                            console.log(`✅ Campaign reached terminal state: ${data.status}`);
                            terminalReached = true;
                            clearTimeout(timeout);
                            
                            if (data.sent === data.total) {
                                console.log('✅ Phase 4 Complete: All recipients successfully processed!');
                            } else {
                                console.log('⚠️ Phase 4 finished, but not all recipients were sent successfully.');
                            }
                            process.exit(0);
                        }
                    } catch (e) {}
                }
            }
        }
    } catch (e) {
        console.error('❌ Stream error:', e.message);
        clearTimeout(timeout);
        process.exit(1);
    }
}

runTests();
