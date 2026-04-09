import React, { useState, useEffect } from 'react';
import * as api from './api';

function Login({ onLoginSuccess }) {
  const [isRegister, setIsRegister] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [successMsg, setSuccessMsg] = useState('');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const hash = window.location.hash;
    if (hash && hash.includes('access_token')) {
      const params = new URLSearchParams(hash.substring(1));
      const token = params.get('access_token');
      if (token) {
        localStorage.setItem('token', token);
        window.location.hash = ''; // clear hash
        onLoginSuccess();
      }
    }
  }, [onLoginSuccess]);

  const handleGoogleLogin = async () => {
    try {
      const res = await api.getGoogleAuthUrl();
      window.location.href = res.data.url;
    } catch (err) {
      setError('Failed to initiate Google login');
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setSuccessMsg('');
    setLoading(true);

    try {
      if (isRegister) {
        await api.register(email, password);
        const res = await api.login(email, password);
        localStorage.setItem('token', res.data.access_token);
        onLoginSuccess();
      } else {
        const res = await api.login(email, password);
        localStorage.setItem('token', res.data.access_token);
        onLoginSuccess();
      }
    } catch (err) {
      let errorMsg = err.response?.data?.detail || err.message || 'An error occurred';
      if (typeof errorMsg === 'string') {
        if (errorMsg.toLowerCase().includes('email not confirmed')) {
          errorMsg = 'Please check your email inbox and click the confirmation link to verify your account before logging in.';
        } else if (errorMsg.toLowerCase().includes('rate limit')) {
          errorMsg = 'You have tried to register too many times recently. Please wait a while or disable email confirmations in your Supabase dashboard.';
        }
      }
      setError(errorMsg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-container">
      <form className="login-card" onSubmit={handleSubmit}>
        <h2 className="login-title">
          {isRegister ? 'Create Account' : 'Welcome Back'}
        </h2>
        <p className="login-subtitle">
          {isRegister ? 'Join the autonomous execution platform' : 'Access your intelligent agent'}
        </p>

        <div style={{ marginBottom: '1.5rem' }}>
          <button type="button" className="login-btn-google" onClick={handleGoogleLogin}>
            <svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor"><path d="M12.545,10.239v3.821h5.445c-0.712,2.315-2.647,3.972-5.445,3.972c-3.332,0-6.033-2.701-6.033-6.032s2.701-6.032,6.033-6.032c1.498,0,2.866,0.549,3.921,1.453l2.814-2.814C17.503,2.988,15.139,2,12.545,2C7.021,2,2.543,6.477,2.543,12s4.478,10,10.002,10c8.396,0,10.249-7.85,9.426-11.748L12.545,10.239z"/></svg>
            Continue with Google
          </button>
          <div className="login-divider">Or</div>
        </div>
        
        {successMsg && (
          <div style={{ background: 'rgba(16, 185, 129, 0.1)', color: 'var(--success)', padding: '0.875rem', borderRadius: '12px', marginBottom: '1.25rem', fontSize: '0.9rem', border: '1px solid rgba(16, 185, 129, 0.2)' }}>
            {successMsg}
          </div>
        )}

        {error && (
          <div style={{ background: 'rgba(239, 68, 68, 0.1)', color: 'var(--danger)', padding: '0.875rem', borderRadius: '12px', marginBottom: '1.25rem', fontSize: '0.9rem', border: '1px solid rgba(239, 68, 68, 0.2)' }}>
            {error}
          </div>
        )}

        <div className="login-input-group">
          <input 
            type="email" 
            className="login-input" 
            value={email} 
            onChange={e => setEmail(e.target.value)} 
            required 
            placeholder="Email address"
          />
        </div>
        
        <div className="login-input-group">
          <input 
            type="password" 
            className="login-input" 
            value={password} 
            onChange={e => setPassword(e.target.value)} 
            required
            placeholder="Password"
            minLength={isRegister ? 6 : undefined}
          />
          {isRegister && (
            <small style={{ display: 'block', marginTop: '0.5rem', color: 'rgba(255,255,255,0.4)', fontSize: '11px', marginLeft: '0.5rem' }}>
              Password must be at least 6 characters.
            </small>
          )}
        </div>

        <button type="submit" className="login-btn-primary" disabled={loading}>
          {loading ? 'Processing...' : (isRegister ? 'Create Account' : 'Sign In')}
        </button>

        <p style={{ textAlign: 'center', marginTop: '1.5rem', fontSize: '0.9rem', color: 'var(--text-muted)' }}>
          {isRegister ? 'Already have an account?' : "Don't have an account?"}
          <button 
            type="button" 
            className="login-toggle-link" 
            style={{ marginLeft: '0.5rem' }} 
            onClick={() => setIsRegister(!isRegister)}
          >
            {isRegister ? 'Sign In' : 'Register'}
          </button>
        </p>
      </form>
    </div>
  );
}

export default Login;
