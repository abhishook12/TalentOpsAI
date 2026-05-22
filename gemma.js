require('dotenv').config();
const express = require('express');
const { GoogleGenerativeAI } = require('@google/generative-ai');

const app = express();
app.use(express.json());

// Paste your key from https://aistudio.google.com/apikey between the quotes:
const API_KEY = process.env.GOOGLE_API_KEY || 'YOUR_API_KEY_HERE';

if (!API_KEY || API_KEY === 'YOUR_API_KEY_HERE') {
  console.error('Missing API key. Set GOOGLE_API_KEY in .env or replace YOUR_API_KEY_HERE in gemma.js');
  process.exit(1);
}

const genAI = new GoogleGenerativeAI(API_KEY);
app.post('/api/gemma', async (req, res) => {
  try {
    const { text } = req.body;
    // gemini-1.5-flash retired; gemini-flash-latest is the current flash alias
    const model = genAI.getGenerativeModel({ model: 'gemini-flash-latest' });
    const result = await model.generateContent(text);
    res.json({ reply: result.response.text() });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

app.listen(3001, () => {
  console.log('Gemma running on port 3001');
});
