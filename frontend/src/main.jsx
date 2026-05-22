import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.jsx'
import './index.css'
import "@fontsource/inter"
import axios from 'axios'

document.documentElement.setAttribute('data-theme', 'dark')
localStorage.setItem('theme', 'dark')
axios.defaults.withCredentials = true
ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)   