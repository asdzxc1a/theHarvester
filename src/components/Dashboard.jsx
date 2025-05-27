import React from 'react';

function Dashboard() {
    const handleLogout = () => {
        localStorage.removeItem('accessToken');
        // Typically, you would redirect to login here.
        // For now, just log and alert.
        alert('Logged out! Token removed. Please refresh to see login/register (if routes were protected).');
        console.log('User logged out, token removed.');
    };

    return (
        <div>
            <h2>Dashboard</h2>
            <p>Welcome! You are logged in.</p>
            <button onClick={handleLogout}>Logout</button>
        </div>
    );
}

export default Dashboard;
