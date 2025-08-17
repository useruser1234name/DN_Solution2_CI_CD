import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { get, post } from '../services/api';
import { getCompanyTypeLabel } from '../utils/companyUtils';
import './UserListPage.css';

const UserListPage = () => {
    const [users, setUsers] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    // 계층구조만 사용하므로 viewMode 제거
    const navigate = useNavigate();



    useEffect(() => {
        fetchUsers();
    }, []);

    const fetchUsers = async () => {

        setLoading(true);
        setError(null);

        try {
            const response = await get('api/companies/users/');
            if (response.success) {
                setUsers(response.data.results || []);
            } else {
                setError(response.error || '사용자 목록을 불러오는데 실패했습니다.');

            }
        } catch (error) {
            setError('네트워크 오류가 발생했습니다.');

        } finally {
            setLoading(false);
        }
    };

    const getRoleDisplay = (role) => {
        const roleMap = {
            'admin': '관리자',
            'staff': '직원',
            'user': '사용자'
        };
        return roleMap[role] || role;
    };

    const getStatusDisplay = (status) => {
        const statusMap = {
            'approved': '승인됨',
            'pending': '대기 중',
            'rejected': '거부됨'
        };
        return statusMap[status] || status;
    };

    const handleApproveUser = async (userId) => {
        
        try {
            const response = await post(`companies/users/${userId}/approval/`, { action: 'approve' });


            if (response.success) {
                alert('사용자가 승인되었습니다.');
                fetchUsers(); // 목록 새로고침
            } else {
                alert(response.error || '사용자 승인에 실패했습니다.');
                console.error('[UserListPage] 사용자 승인 실패:', response.error);
            }
        } catch (error) {
            alert('네트워크 오류가 발생했습니다.');
            console.error('[UserListPage] 사용자 승인 중 오류:', error);
        }
    };

    const handleRejectUser = async (userId) => {
        
        if (!window.confirm('정말로 이 사용자를 거부하시겠습니까?')) {
            return;
        }
        
        try {
            const response = await post(`companies/users/${userId}/approval/`, { action: 'reject' });


            if (response.success) {
                alert('사용자가 거부되었습니다.');
                fetchUsers(); // 목록 새로고침
            } else {
                alert(response.error || '사용자 거부에 실패했습니다.');
                console.error('[UserListPage] 사용자 거부 실패:', response.error);
            }
        } catch (error) {
            alert('네트워크 오류가 발생했습니다.');
            console.error('[UserListPage] 사용자 거부 중 오류:', error);
        }
    };

    const handleAddUser = () => {
        navigate('/users/create');
    };

    const handleEditUser = (userId) => {

        navigate(`/users/${userId}/edit`);
    };

    const handleDeleteUser = async (userId) => {
        
        if (!window.confirm('정말로 이 사용자를 삭제하시겠습니까? 이 작업은 되돌릴 수 없습니다.')) {
            return;
        }
        
        try {
            const response = await post(`companies/users/${userId}/delete/`);


            if (response.success) {
                alert('사용자가 삭제되었습니다.');
                fetchUsers(); // 목록 새로고침
            } else {
                alert(response.error || '사용자 삭제에 실패했습니다.');
                console.error('[UserListPage] 사용자 삭제 실패:', response.error);
            }
        } catch (error) {
            alert('네트워크 오류가 발생했습니다.');

        }
    };

    // getCompanyTypeLabel은 utils에서 import

    if (loading) {
        return (
            <div className="user-list-page">
                <div className="page-header">
                    <h1>👥 사용자 목록</h1>
                </div>
                <div className="loading">로딩 중...</div>
            </div>
        );
    }

    if (error) {
        return (
            <div className="user-list-page">
                <div className="page-header">
                    <h1>👥 사용자 목록</h1>
                </div>
                <div className="error">{error}</div>
            </div>
        );
    }

    return (
        <div className="user-list-page">
            <div className="page-header">
                <div className="header-content">
                    <h1>👥 사용자 목록</h1>
                    <p>조직별 계층 구조로 사용자를 관리합니다.</p>
                </div>
                <button className="add-btn" onClick={handleAddUser}>
                    ➕ 새 사용자 등록
                </button>
            </div>

            <div className="user-stats">
                <div className="stat-card">
                    <span className="stat-number">{users.length}</span>
                    <span className="stat-label">총 사용자 수</span>
                </div>
                <div className="stat-card">
                    <span className="stat-number">{users.filter(u => u.status === 'approved').length}</span>
                    <span className="stat-label">승인된 사용자</span>
                </div>
                <div className="stat-card">
                    <span className="stat-number">{users.filter(u => u.status === 'pending').length}</span>
                    <span className="stat-label">대기 중인 사용자</span>
                </div>
            </div>

            <div className="user-table">
                <table>
                    <thead>
                        <tr>
                            <th>사용자명</th>
                            <th>회사</th>
                            <th>회사타입</th>
                            <th>역할</th>
                            <th>상태</th>
                            <th>마지막 로그인</th>
                            <th>작업</th>
                        </tr>
                    </thead>
                    <tbody>
                        {users.map((user) => (
                            <tr key={user.id}>
                                <td>{user.username}</td>
                                <td>{user.company_name}</td>
                                <td>
                                    <span className={`company-type-badge ${user.company_type}`}>
                                        {getCompanyTypeLabel(user.company_type)}
                                    </span>
                                </td>
                                <td>
                                    <span className={`role-badge ${user.role}`}>
                                        {getRoleDisplay(user.role)}
                                    </span>
                                </td>
                                <td>
                                    <span className={`status-badge ${user.status}`}>
                                        {getStatusDisplay(user.status)}
                                    </span>
                                </td>
                                <td>{user.last_login ? new Date(user.last_login).toLocaleDateString() : '-'}</td>
                                <td>
                                    <div className="user-actions">
                                        {user.status === 'pending' && (
                                            <>
                                                <button 
                                                    className="action-btn approve"
                                                    onClick={() => handleApproveUser(user.id)}
                                                >
                                                    승인
                                                </button>
                                                <button 
                                                    className="action-btn reject"
                                                    onClick={() => handleRejectUser(user.id)}
                                                >
                                                    거부
                                                </button>
                                            </>
                                        )}
                                        <button 
                                            className="action-btn edit"
                                            onClick={() => handleEditUser(user.id)}
                                        >
                                            수정
                                        </button>
                                        <button 
                                            className="action-btn delete"
                                            onClick={() => handleDeleteUser(user.id)}
                                        >
                                            삭제
                                        </button>
                                    </div>
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </div>
    );
};

export default UserListPage; 