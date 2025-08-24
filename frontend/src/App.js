import React, { useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './contexts/AuthContext';
import ProtectedRoute from './components/common/ProtectedRoute';
import LoginPage from './pages/LoginPage';
import SignupChoicePage from './pages/SignupChoicePage';
import AdminSignupPage from './pages/AdminSignupPage';
import StaffSignupPage from './pages/StaffSignupPage';
import MainLayout from './pages/MainLayout';
import DashboardPage from './pages/DashboardPage';
import CompanyListPage from './pages/CompanyListPage';
import CompanyCreatePage from './pages/CompanyCreatePage';
import UserListPage from './pages/UserListPage';
import UserCreatePage from './pages/UserCreatePage';
import PolicyListPage from './pages/PolicyListPage';
import PolicyCreatePage from './pages/PolicyCreatePage';
import PolicyDetailPage from './pages/PolicyDetailPage';
import PolicyEditPage from './pages/PolicyEditPage';
import OrderFormTemplateEditorPage from './pages/OrderFormTemplateEditorPage';
import AgencyRebateAllocationPage from './pages/AgencyRebateAllocationPage';
import OrderListPage from './pages/OrderListPage';
import OrderCreatePage from './pages/OrderCreatePage';
import OrderCreatePageNew from './pages/OrderCreatePageNew';
import OrderDetailPage from './pages/OrderDetailPage';
import SettlementListPage from './pages/SettlementListPage';
import AdminSettingsPage from './pages/AdminSettingsPage';
// import { testConnection } from './services/api'; // 제거: 로그인 전 API 호출 방지
import './App.css';



const App = () => {


  // API 연결 테스트 제거 - 로그인하지 않은 상태에서 인증이 필요한 API를 호출하면 안됨
  // useEffect(() => {
  //   const testAPI = async () => {
  //     console.log('[App] API 연결 테스트 시작');
  //     const result = await testConnection();
  //     if (result.success) {
  //       console.log('[App] API 연결 성공');
  //     } else {
  //       console.error('[App] API 연결 실패:', result.error);
  //     }
  //   };
  //   testAPI();
  // }, []);

  return (
    <AuthProvider>
      <Router>
        <div className="App">
          <Routes>
            {/* 인증 관련 라우트 */}
            <Route path="/login" element={<LoginPage />} />
            <Route path="/signup" element={<SignupChoicePage />} />
            <Route path="/signup/admin" element={<AdminSignupPage />} />
            <Route path="/signup/staff" element={<StaffSignupPage />} />
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
                <ProtectedRoute requiredPermissions={['canViewUserHierarchy']}>
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
                    <PolicyCreatePage />
                  </MainLayout>
                </ProtectedRoute>
              }
            />
            

            <Route
              path="/policies/:id"
              element={
                <ProtectedRoute>
                  <MainLayout>
                    <PolicyDetailPage />
                  </MainLayout>
                </ProtectedRoute>
              }
            />
            
            <Route
              path="/policies/:id/edit"
              element={
                <ProtectedRoute>
                  <MainLayout>
                    <PolicyEditPage />
                  </MainLayout>
                </ProtectedRoute>
              }
            />
            
            <Route
              path="/policies/:id/form-template/edit"
              element={
                <ProtectedRoute>
                  <MainLayout>
                    <OrderFormTemplateEditorPage />
                  </MainLayout>
                </ProtectedRoute>
              }
            />
            
            <Route
              path="/policies/:id/rebate-allocation"
              element={
                <ProtectedRoute>
                  <MainLayout>
                    <AgencyRebateAllocationPage />
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
                    <OrderListPage />
                  </MainLayout>
                </ProtectedRoute>
              }
            />
            
            <Route
              path="/orders/create"
              element={
                <ProtectedRoute>
                  <MainLayout>
                    <OrderCreatePageNew />
                  </MainLayout>
                </ProtectedRoute>
              }
            />
            
            <Route
              path="/orders/create-old"
              element={
                <ProtectedRoute>
                  <MainLayout>
                    <OrderCreatePage />
                  </MainLayout>
                </ProtectedRoute>
              }
            />
            
            <Route
              path="/orders/:id"
              element={
                <ProtectedRoute>
                  <MainLayout>
                    <OrderDetailPage />
                  </MainLayout>
                </ProtectedRoute>
              }
            />
            
            {/* 정산 관리 */}
            <Route
              path="/settlements"
              element={
                <ProtectedRoute>
                  <MainLayout>
                    <SettlementListPage />
                  </MainLayout>
                </ProtectedRoute>
              }
            />
            
            <Route
              path="/settlements/report"
              element={
                <ProtectedRoute>
                  <MainLayout>
                    <div className="page-placeholder">
                      <h1>📊 정산 보고서</h1>
                      <p>정산 보고서 페이지가 준비 중입니다.</p>
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
                    <AdminSettingsPage />
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
