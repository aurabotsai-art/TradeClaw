import React, { useState } from 'react';

function Input({ label, type = 'text', value, onChange, ...props }) {
  return (
    <div className="mb-3">
      <label className="block text-xs font-medium text-tc-muted mb-1">{label}</label>
      <input
        type={type}
        value={value}
        onChange={onChange}
        className="w-full px-3 py-2 text-sm rounded-lg border border-tc-border bg-tc-input text-tc-primary focus:outline-none focus:ring-1 focus:ring-tc-accent"
        {...props}
      />
    </div>
  );
}

function Button({ variant = 'primary', className = '', children, ...props }) {
  const base =
    'inline-flex items-center justify-center rounded-lg px-3 py-2 text-sm font-medium transition-colors';
  const variants = {
    primary: 'bg-tc-accent text-white hover:bg-tc-accent-strong',
    outline:
      'border border-tc-border text-tc-primary bg-transparent hover:bg-tc-raised/60',
  };
  return (
    <button type="button" className={`${base} ${variants[variant]} ${className}`} {...props}>
      {children}
    </button>
  );
}

export default function LoginScreen({ onEmailLogin, onGoogleOAuth }) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [mode, setMode] = useState('login'); // 'login' | 'signup'

  const handleSubmit = async (e) => {
    e?.preventDefault();
    if (!onEmailLogin) return;
    setSubmitting(true);
    try {
      await onEmailLogin({ email, password, mode });
    } finally {
      setSubmitting(false);
    }
  };

  const handleGoogle = async () => {
    if (!onGoogleOAuth) return;
    await onGoogleOAuth();
  };

  return (
    <div className="login-screen flex items-center justify-center h-screen bg-tc-bg">
      <div className="login-card w-[380px] bg-tc-raised border border-tc-border rounded-2xl p-8">
        {/* Logo */}
        <div className="flex items-center gap-3 mb-8">
          <div className="logo-icon text-2xl" aria-hidden="true">
            🦾
          </div>
          <div>
            <div className="font-display font-black text-xl text-tc-primary">TradeClaw</div>
            <div className="text-xs text-tc-muted font-mono">aurabotsai-art</div>
          </div>
        </div>

        <form onSubmit={handleSubmit}>
          {/* Email + Password */}
          <Input
            label="Email"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            autoComplete="email"
          />
          <Input
            label="Password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete="current-password"
          />
          <Button
            variant="primary"
            className="w-full mt-4"
            type="submit"
            disabled={submitting}
          >
            {submitting ? (mode === 'login' ? 'Signing in…' : 'Creating account…') : mode === 'login' ? 'Sign in' : 'Sign up'}
          </Button>
        </form>

        <div className="mt-3 text-xs text-tc-muted text-center">
          {mode === 'login' ? (
            <>
              No account yet?{' '}
              <button
                type="button"
                onClick={() => setMode('signup')}
                className="text-tc-accent hover:underline"
              >
                Create one
              </button>
            </>
          ) : (
            <>
              Already have an account?{' '}
              <button
                type="button"
                onClick={() => setMode('login')}
                className="text-tc-accent hover:underline"
              >
                Sign in
              </button>
            </>
          )}
        </div>

        {/* Google OAuth option */}
        <Button variant="outline" className="w-full mt-3" onClick={handleGoogle}>
          Continue with Google
        </Button>
      </div>
    </div>
  );
}

