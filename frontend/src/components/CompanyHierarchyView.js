import React, { useState } from 'react';
import './CompanyHierarchyView.css';

const CompanyHierarchyView = ({ users, onUserAction }) => {
    const [expandedCompanies, setExpandedCompanies] = useState(new Set());



    // 계층 구조로 사용자 그룹핑: 본사 → 협력사 → 판매점
    const buildHierarchy = (users) => {
        const hierarchy = {
            headquarters: null,
            agencies: {}
        };

        // 1단계: 모든 사용자를 회사 타입별로 분류
        const usersByCompany = {};
        users.forEach(user => {
            const companyId = user.company_id || 'no-company';
            const companyType = user.company_type || 'unknown';
            const companyName = user.company_name || '미지정';

            if (!usersByCompany[companyId]) {
                usersByCompany[companyId] = {
                    id: companyId,
                    name: companyName,
                    type: companyType,
                    users: [],
                    children: {}
                };
            }
            usersByCompany[companyId].users.push(user);
        });

        // 2단계: 본사 설정
        Object.values(usersByCompany).forEach(company => {
            if (company.type === 'headquarters') {
                hierarchy.headquarters = company;
            }
        });

        // 3단계: 협력사들 설정
        Object.values(usersByCompany).forEach(company => {
            if (company.type === 'agency') {
                hierarchy.agencies[company.id] = {
                    ...company,
                    retailers: {}
                };
            }
        });

        // 4단계: 판매점들을 해당 협력사에 배정 (임시로 모든 협력사에 표시)
        Object.values(usersByCompany).forEach(company => {
            if (company.type === 'retail') {
                // 실제로는 parent_company 정보를 사용해야 하지만, 임시로 첫 번째 협력사에 배정
                const agencyIds = Object.keys(hierarchy.agencies);
                if (agencyIds.length > 0) {
                    const targetAgencyId = agencyIds[0]; // 임시
                    hierarchy.agencies[targetAgencyId].retailers[company.id] = company;
                }
            }
        });

        return hierarchy;
    };

    const hierarchy = buildHierarchy(users);

    const toggleCompany = (companyId) => {
        const newExpanded = new Set(expandedCompanies);
        if (newExpanded.has(companyId)) {
            newExpanded.delete(companyId);
        } else {
            newExpanded.add(companyId);
        }
        setExpandedCompanies(newExpanded);
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

    const getCompanyTypeLabel = (type) => {
        const typeMap = {
            'headquarters': '본사',
            'agency': '협력사',
            'dealer': '대리점',
            'retail': '판매점'
        };
        return typeMap[type] || type;
    };

    const UserRow = ({ user, level = 0 }) => (
        <div className={`user-row level-${level}`}>
            <div className="user-info">
                <span className="user-name">{user.username}</span>
                <span className="user-role">{getRoleDisplay(user.role)}</span>
                <span className={`user-status ${user.status}`}>
                    {getStatusDisplay(user.status)}
                </span>
                {user.last_login && (
                    <span className="last-login">
                        {new Date(user.last_login).toLocaleDateString()}
                    </span>
                )}
            </div>
            <div className="user-actions">
                {user.status === 'pending' && (
                    <>
                        <button 
                            className="action-btn approve"
                            onClick={() => onUserAction('approve', user.id)}
                        >
                            승인
                        </button>
                        <button 
                            className="action-btn reject"
                            onClick={() => onUserAction('reject', user.id)}
                        >
                            거부
                        </button>
                    </>
                )}
                <button 
                    className="action-btn edit"
                    onClick={() => onUserAction('edit', user.id)}
                >
                    수정
                </button>
                <button 
                    className="action-btn delete"
                    onClick={() => onUserAction('delete', user.id)}
                >
                    삭제
                </button>
            </div>
        </div>
    );

    const CompanyNode = ({ company, level = 0 }) => {
        const isExpanded = expandedCompanies.has(company.id);
        const hasUsers = company.users && company.users.length > 0;
        const hasChildren = Object.keys(company.children || {}).length > 0;

        return (
            <div className={`company-node level-${level}`}>
                <div 
                    className={`company-header ${hasUsers || hasChildren ? 'expandable' : ''}`}
                    onClick={() => (hasUsers || hasChildren) && toggleCompany(company.id)}
                >
                    <div className="company-info">
                        {(hasUsers || hasChildren) && (
                            <span className={`expand-icon ${isExpanded ? 'expanded' : ''}`}>
                                ▶
                            </span>
                        )}
                        <span className="company-name">{company.name}</span>
                        <span className="company-type">{getCompanyTypeLabel(company.type)}</span>
                        <span className="user-count">
                            사용자: {company.users.length}명
                        </span>
                    </div>
                </div>

                {isExpanded && (
                    <div className="company-content">
                        {hasUsers && (
                            <div className="users-section">
                                {company.users.map(user => (
                                    <UserRow key={user.id} user={user} level={level + 1} />
                                ))}
                            </div>
                        )}
                        
                        {hasChildren && (
                            <div className="children-section">
                                {Object.values(company.children).map(child => (
                                    <CompanyNode key={child.id} company={child} level={level + 1} />
                                ))}
                            </div>
                        )}
                    </div>
                )}
            </div>
        );
    };

    const HierarchyNode = ({ company, retailers = {}, level = 0 }) => {
        const isExpanded = expandedCompanies.has(company.id);
        const hasUsers = company.users && company.users.length > 0;
        const hasRetailers = Object.keys(retailers).length > 0;
        const showExpandIcon = hasUsers || hasRetailers;

        return (
            <div className={`company-node level-${level}`}>
                <div 
                    className={`company-header ${showExpandIcon ? 'expandable' : ''}`}
                    onClick={() => showExpandIcon && toggleCompany(company.id)}
                >
                    <div className="company-info">
                        {showExpandIcon && (
                            <span className={`expand-icon ${isExpanded ? 'expanded' : ''}`}>
                                ▶
                            </span>
                        )}
                        <span className="company-name">{company.name}</span>
                        <span className="company-type">{getCompanyTypeLabel(company.type)}</span>
                        <span className="user-count">
                            사용자: {company.users.length}명
                            {hasRetailers && ` / 판매점: ${Object.keys(retailers).length}개`}
                        </span>
                    </div>
                </div>

                {isExpanded && (
                    <div className="company-content">
                        {hasUsers && (
                            <div className="users-section">
                                {company.users.map(user => (
                                    <UserRow key={user.id} user={user} level={level + 1} />
                                ))}
                            </div>
                        )}
                        
                        {hasRetailers && (
                            <div className="retailers-section">
                                {Object.values(retailers).map(retailer => (
                                    <HierarchyNode 
                                        key={retailer.id} 
                                        company={retailer} 
                                        level={level + 1} 
                                    />
                                ))}
                            </div>
                        )}
                    </div>
                )}
            </div>
        );
    };

    return (
        <div className="company-hierarchy-view">
            {/* 본사 */}
            {hierarchy.headquarters && (
                <HierarchyNode company={hierarchy.headquarters} level={0} />
            )}
            
            {/* 협력사들과 그 하위 판매점들 */}
            {Object.values(hierarchy.agencies).map(agency => (
                <HierarchyNode 
                    key={agency.id} 
                    company={agency} 
                    retailers={agency.retailers}
                    level={0} 
                />
            ))}
        </div>
    );
};

export default CompanyHierarchyView;
