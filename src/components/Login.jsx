import React, { useState } from 'react';
import axios from 'axios'; // Import axios

function Login() {
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [message, setMessage] = useState('');

    const handleSubmit = async (event) => {
        event.preventDefault();
        setMessage(''); // Clear previous messages

        try {
            // Note: The backend login endpoint expects form data, not JSON.
            // We'll use URLSearchParams to construct the form data.
            const params = new URLSearchParams();
            params.append('username', email); // Backend expects 'username' for email
            params.append('password', password);

            const response = await axios.post('/api/v1/auth/login', params, {
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                },
            });

            if (response.data.access_token) {
                localStorage.setItem('accessToken', response.data.access_token);
                setMessage('Login successful! Token stored.');
                console.log('Login successful:', response.data);
                // TODO: Redirect to a dashboard page or update app state
                setEmail('');
                setPassword('');
            } else {
                setMessage('Login failed: No access token received.');
            }
        } catch (error) {
            let errorMessage = 'Login failed. Please try again.';
            if (error.response) {
                // FastAPI often returns error details in error.response.data.detail
                if (error.response.data && error.response.data.detail) {
                     if (Array.isArray(error.response.data.detail)) {
                        errorMessage = error.response.data.detail.map(err => `${err.loc[1]}: ${err.msg}`).join(', ');
                    } else {
                        errorMessage = error.response.data.detail;
                    }
                } else {
                    errorMessage = `Error ${error.response.status}: ${error.response.statusText}`;
                }
            } else if (error.request) {
                errorMessage = 'Login failed. No response from server.';
            }
            setMessage(errorMessage);
            console.error('Login error:', error.response || error.message);
        }
    };

    return (
        <div>
            <h2>Login</h2>
            <form onSubmit={handleSubmit}>
                <div>
                    <label htmlFor="email">Email (Username):</label>
                    <input
                        type="email"
                        id="email"
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                        required
                    />
                </div>
                <div>
                    <label htmlFor="password">Password:</label>
                    <input
                        type="password"
                        id="password"
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        required
                    />
                </div>
                <button type="submit">Login</button>
            </form>
            {message && <p>{message}</p>}
        </div>
    );
}

export default Login;
