import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { get, post } from '../services/api';
import './UserListPage.css';

const UserListPage = () => {
    const [users, setUsers] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const navigate = useNavigate();

    console.log('[UserListPage] 컴포넌트 렌더링');

    useEffect(() => {
        fetchUsers();
    }, []);

    const fetchUsers = async () => {
        console.log('[UserListPage] 사용자 목록 조회 시작');
        setLoading(true);
        setError(null);

        try {
            const response = await get('companies/users/');
            console.log('[UserListPage] 사용자 목록 응답:', response);

            if (response.success) {
                setUsers(response.data.results || []);
                console.log('[UserListPage] 사용자 목록 설정 완료:', response.data.results?.length);
            } else {
                setError(response.error || '사용자 목록을 불러오는데 실패했습니다.');
                console.error('[UserListPage] 사용자 목록 조회 실패:', response.error);
            }
        } catch (error) {
            setError('네트워크 오류가 발생했습니다.');
            console.error('[UserListPage] 사용자 목록 조회 중 오류:', error);
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
        console.log('[UserListPage] 사용자 승인:', userId);
        
        try {
            const response = await post(`companies/users/${userId}/approval/`, { action: 'approve' });
            console.log('[UserListPage] 사용자 승인 응답:', response);

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
        console.log('[UserListPage] 사용자 거부:', userId);
        
        if (!window.confirm('정말로 이 사용자를 거부하시겠습니까?')) {
            return;
        }
        
        try {
            const response = await post(`companies/users/${userId}/approval/`, { action: 'reject' });
            console.log('[UserListPage] 사용자 거부 응답:', response);

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
        console.log('[UserListPage] 새 사용자 등록 버튼 클릭');
        navigate('/users/create');
    };

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
                <h1>👥 사용자 목록</h1>
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
                                <td>{getRoleDisplay(user.role)}</td>
                                <td>
                                    <span className={`status-badge ${user.status}`}>
                                        {getStatusDisplay(user.status)}
                                    </span>
                                </td>
                                <td>{user.last_login ? new Date(user.last_login).toLocaleDateString() : '-'}</td>
                                <td>
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
                                    <button className="action-btn edit">수정</button>
                                    <button className="action-btn delete">삭제</button>
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