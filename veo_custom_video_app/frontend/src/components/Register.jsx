import React, { useState } from 'react';
import axios from 'axios'; // Import axios

function Register() {
    const [fullName, setFullName] = useState('');
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [message, setMessage] = useState('');

    const handleSubmit = async (event) => {
        event.preventDefault();
        setMessage(''); // Clear previous messages

        try {
            const response = await axios.post('/api/v1/users/', {
                full_name: fullName, // Ensure key matches backend (full_name)
                email: email,
                password: password,
            });
            setMessage('Registration successful! You can now log in.');
            console.log('Registration successful:', response.data);
            // Optionally, clear form fields
            setFullName('');
            setEmail('');
            setPassword('');
        } catch (error) {
            let errorMessage = 'Registration failed. Please try again.';
            if (error.response && error.response.data && error.response.data.detail) {
                if (Array.isArray(error.response.data.detail)) {
                    // Handle FastAPI validation errors array
                    errorMessage = error.response.data.detail.map(err => `${err.loc[1]}: ${err.msg}`).join(', ');
                } else {
                    // Handle single string error detail
                    errorMessage = error.response.data.detail;
                }
            } else if (error.request) {
                errorMessage = 'Registration failed. No response from server.';
            }
            setMessage(errorMessage);
            console.error('Registration error:', error.response || error.message);
        }
    };

    return (
        <div>
            <h2>Register</h2>
            <form onSubmit={handleSubmit}>
                <div>
                    <label htmlFor="fullName">Full Name:</label>
                    <input
                        type="text"
                        id="fullName"
                        value={fullName}
                        onChange={(e) => setFullName(e.target.value)}
                        required
                    />
                </div>
                <div>
                    <label htmlFor="email">Email:</label>
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
                <button type="submit">Register</button>
            </form>
            {message && <p>{message}</p>}
        </div>
    );
}

export default Register;
