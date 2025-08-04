import React, { useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './contexts/AuthContext';
import ProtectedRoute from './components/ProtectedRoute';
import LoginPage from './pages/LoginPage';
import MainLayout from './pages/MainLayout';
import DashboardPage from './pages/DashboardPage';
import CompanyListPage from './pages/CompanyListPage';
import CompanyCreatePage from './pages/CompanyCreatePage';
import UserListPage from './pages/UserListPage';
import UserCreatePage from './pages/UserCreatePage';
import PolicyListPage from './pages/PolicyListPage';
import { testConnection } from './services/api';
import './App.css';

console.log('[App] 애플리케이션 시작');

const App = () => {
  console.log('[App] 컴포넌트 렌더링');

  useEffect(() => {
    // API 연결 테스트
    const testAPI = async () => {
      console.log('[App] API 연결 테스트 시작');
      const result = await testConnection();
      if (result.success) {
        console.log('[App] API 연결 성공');
      } else {
        console.error('[App] API 연결 실패:', result.error);
      }
    };

    testAPI();
  }, []);

  return (
    <AuthProvider>
      <Router>
        <div className="App">
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route path="/" element={<Navigate to="/dashboard" replace />} />
            
            {/* 대시보드 */}
            <Route
              path="/dashboard"
              element={
                <ProtectedRoute>
                  <MainLayout>
                    <DashboardPage />
                  </MainLayout>
                </ProtectedRoute>
              }
            />
            
            {/* 업체 관리 */}
            <Route
              path="/companies"
              element={
                <ProtectedRoute>
                  <MainLayout>
                    <CompanyListPage />
                  </MainLayout>
                </ProtectedRoute>
              }
            />
            
            <Route
              path="/companies/create"
              element={
                <ProtectedRoute>
                  <MainLayout>
                    <CompanyCreatePage />
                  </MainLayout>
                </ProtectedRoute>
              }
            />
            
            {/* 사용자 관리 */}
            <Route
              path="/users"
              element={
                <ProtectedRoute>
                  <MainLayout>
                    <UserListPage />
                  </MainLayout>
                </ProtectedRoute>
              }
            />
            
            <Route
              path="/users/create"
              element={
                <ProtectedRoute>
                  <MainLayout>
                    <UserCreatePage />
                  </MainLayout>
                </ProtectedRoute>
              }
            />
            
            {/* 정책 관리 */}
            <Route
              path="/policies"
              element={
                <ProtectedRoute>
                  <MainLayout>
                    <PolicyListPage />
                  </MainLayout>
                </ProtectedRoute>
              }
            />
            
            <Route
              path="/policies/create"
              element={
                <ProtectedRoute>
                  <MainLayout>
                    <PolicyListPage />
                  </MainLayout>
                </ProtectedRoute>
              }
            />
            
            {/* 주문 관리 */}
            <Route
              path="/orders"
              element={
                <ProtectedRoute>
                  <MainLayout>
                    <div className="page-placeholder">
                      <h1>📦 주문 목록</h1>
                      <p>주문 목록 페이지가 준비 중입니다.</p>
                    </div>
                  </MainLayout>
                </ProtectedRoute>
              }
            />
            
            {/* 재고 관리 */}
            <Route
              path="/inventory"
              element={
                <ProtectedRoute>
                  <MainLayout>
                    <div className="page-placeholder">
                      <h1>📦 재고 목록</h1>
                      <p>재고 목록 페이지가 준비 중입니다.</p>
                    </div>
                  </MainLayout>
                </ProtectedRoute>
              }
            />
            
            {/* 메시지 관리 */}
            <Route
              path="/messages"
              element={
                <ProtectedRoute>
                  <MainLayout>
                    <div className="page-placeholder">
                      <h1>💬 메시지 목록</h1>
                      <p>메시지 목록 페이지가 준비 중입니다.</p>
                    </div>
                  </MainLayout>
                </ProtectedRoute>
              }
            />
            
            {/* 시스템 설정 */}
            <Route
              path="/settings"
              element={
                <ProtectedRoute>
                  <MainLayout>
                    <div className="page-placeholder">
                      <h1>⚙️ 시스템 설정</h1>
                      <p>시스템 설정 페이지가 준비 중입니다.</p>
                    </div>
                  </MainLayout>
                </ProtectedRoute>
              }
            />
            
            {/* 로그 보기 */}
            <Route
              path="/logs"
              element={
                <ProtectedRoute>
                  <MainLayout>
                    <div className="page-placeholder">
                      <h1>📝 로그 보기</h1>
                      <p>로그 보기 페이지가 준비 중입니다.</p>
                    </div>
                  </MainLayout>
                </ProtectedRoute>
              }
            />
            
            {/* 기본 리다이렉트 */}
            <Route path="*" element={<Navigate to="/dashboard" replace />} />
          </Routes>
        </div>
      </Router>
    </AuthProvider>
  );
};

export default App;
