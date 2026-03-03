import React, { useEffect, useState } from 'react';
import { BrowserRouter, Routes, Route, useNavigate, useLocation, Navigate } from 'react-router-dom';
import Sidebar from './components/layout/Sidebar';
import TopBar from './components/layout/TopBar';
import ChatHistory from './components/layout/ChatHistory';
import LoginScreen from './components/auth/LoginScreen';
import { useAuthStore } from './stores/authStore';
import { supabase } from './lib/supabaseClient';
import { setAccessToken } from './api/tradeclawApi';
import ComputerPanel from './components/panels/ComputerPanel';
import ChatView from './views/ChatView';
import TradeView from './views/TradeView';
import MonitorView from './views/MonitorView';
import BacktestView from './views/BacktestView';
import UniverseView from './views/UniverseView';
import RiskView from './views/RiskView';
import HistoryView from './views/HistoryView';
import { DEMO_SESSIONS } from './demoSessions';

function ProtectedRoute({ children }) {
  const { user } = useAuthStore();
  if (!user) return <Navigate to="/login" replace />;
  return children;
}

function AppShell() {
  const navigate = useNavigate();
  const location = useLocation();
  const [historyOpen, setHistoryOpen] = useState(false);
  const [sessions] = useState(DEMO_SESSIONS);
  const [activeSessionId, setActiveSessionId] = useState(null);
   const { setUser } = useAuthStore();

  const handleNavigate = (path) => {
    if (path === '/chat') {
      setHistoryOpen(true);
      return;
    }
    navigate(path || '/');
  };

  const handleEmailLogin = async ({ email, password, mode }) => {
    if (!supabase) {
      throw new Error('Supabase not configured. Set VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY.');
    }
    if (mode === 'signup') {
      const { data, error } = await supabase.auth.signUp({ email, password });
      if (error) throw error;
      if (data.session) {
        setUser(data.user);
        setAccessToken(data.session.access_token);
        navigate('/');
      }
      return;
    }
    const { data, error } = await supabase.auth.signInWithPassword({ email, password });
    if (error) throw error;
    if (data.session) {
      setUser(data.user);
      setAccessToken(data.session.access_token);
      navigate('/');
    }
  };

  const handleGoogleOAuth = async () => {
    if (!supabase) return;
    await supabase.auth.signInWithOAuth({ provider: 'google' });
  };

  useEffect(() => {
    if (!supabase) return;
    let cancelled = false;
    supabase.auth.getSession().then(({ data }) => {
      if (cancelled) return;
      const session = data?.session;
      if (session?.user) {
        setUser(session.user);
        setAccessToken(session.access_token);
      }
    });
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div className="app-shell flex h-screen bg-[var(--bg-base)] text-[var(--text-primary)] overflow-hidden">
      <Sidebar
        currentRoute={location.pathname}
        onNavigate={handleNavigate}
        onNewChat={() => navigate('/')}
        onExportSession={() => {}}
        onOpenSettings={() => {}}
      />
      <ChatHistory
        isOpen={historyOpen}
        onClose={() => setHistoryOpen(false)}
        sessions={sessions}
        activeSessionId={activeSessionId}
        onSelectSession={(s) => {
          setActiveSessionId(s.id);
          setHistoryOpen(false);
          navigate('/');
        }}
      />
      <main className="main-content flex-1 flex flex-col min-w-0">
        <TopBar isSessionActive={false} onStarsClick={() => {}} onAvatarClick={() => {}} />
        <div className="flex-1 overflow-auto">
          <Routes>
            <Route
              path="/login"
              element={(
                <LoginScreen
                  onEmailLogin={handleEmailLogin}
                  onGoogleOAuth={handleGoogleOAuth}
                />
              )}
            />

            <Route
              path="/"
              element={(
                <ProtectedRoute>
                  <ChatView />
                </ProtectedRoute>
              )}
            />
            <Route
              path="/search"
              element={(
                <ProtectedRoute>
                  <ChatView />
                </ProtectedRoute>
              )}
            />
            <Route
              path="/trade"
              element={(
                <ProtectedRoute>
                  <TradeView />
                </ProtectedRoute>
              )}
            />
            <Route
              path="/monitor"
              element={(
                <ProtectedRoute>
                  <MonitorView />
                </ProtectedRoute>
              )}
            />
            <Route
              path="/backtest"
              element={(
                <ProtectedRoute>
                  <BacktestView />
                </ProtectedRoute>
              )}
            />
            <Route
              path="/universe"
              element={(
                <ProtectedRoute>
                  <UniverseView />
                </ProtectedRoute>
              )}
            />
            <Route
              path="/risk"
              element={(
                <ProtectedRoute>
                  <RiskView />
                </ProtectedRoute>
              )}
            />
            <Route
              path="/history"
              element={(
                <ProtectedRoute>
                  <HistoryView />
                </ProtectedRoute>
              )}
            />
          </Routes>
        </div>
      </main>
      <ComputerPanel />
    </div>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AppShell />
    </BrowserRouter>
  );
}
