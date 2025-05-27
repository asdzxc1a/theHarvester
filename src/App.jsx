import React from 'react';
import { Routes, Route, Link, Navigate } from 'react-router-dom';
import Login from './components/Login';
import Register from './components/Register';
import Dashboard from './components/Dashboard'; // Import Dashboard
import './App.css';

function App() {
    // Basic check for token to simulate protected route behavior
    const isAuthenticated = () => !!localStorage.getItem('accessToken');

    return (
        <div className="App">
            <nav>
                <ul>
                    <li><Link to="/login">Login</Link></li>
                    <li><Link to="/register">Register</Link></li>
                    {isAuthenticated() && <li><Link to="/dashboard">Dashboard</Link></li>}
                </ul>
            </nav>
            <Routes>
                <Route path="/login" element={<Login />} />
                <Route path="/register" element={<Register />} />
                <Route 
                    path="/dashboard" 
                    element={isAuthenticated() ? <Dashboard /> : <Navigate to="/login" replace />} 
                />
                {/* Default route: redirect to login or dashboard based on auth */}
                <Route 
                    path="/" 
                    element={isAuthenticated() ? <Navigate to="/dashboard" replace /> : <Navigate to="/login" replace />} 
                />
            </Routes>
        </div>
    );
}

export default App;
