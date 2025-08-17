import React, { useState } from 'react';
import { buildCompanyHierarchy, getCompanyTypeLabel, getStatusLabel, formatDate } from '../utils/companyUtils';
import './CompanyTreeView.css';

const CompanyTreeView = ({ companies, onCompanyAction }) => {
    const [expandedCompanies, setExpandedCompanies] = useState(new Set());



    const hierarchy = buildCompanyHierarchy(companies);

    const toggleCompany = (companyId) => {
        const newExpanded = new Set(expandedCompanies);
        if (newExpanded.has(companyId)) {
            newExpanded.delete(companyId);
        } else {
            newExpanded.add(companyId);
        }
        setExpandedCompanies(newExpanded);
    };

    // 유틸 함수들을 import로 대체

    const CompanyNode = ({ company, retailers = [], level = 0 }) => {
        const isExpanded = expandedCompanies.has(company.id);
        const hasRetailers = retailers.length > 0;
        const hasChildren = (company.children && company.children.length > 0) || hasRetailers;
        const showExpandIcon = hasChildren;

        return (
            <div className={`company-tree-node level-${level}`}>
                <div 
                    className={`company-tree-header ${showExpandIcon ? 'expandable' : ''}`}
                    onClick={() => showExpandIcon && toggleCompany(company.id)}
                >
                    <div className="company-tree-info">
                        {showExpandIcon && (
                            <span className={`expand-icon ${isExpanded ? 'expanded' : ''}`}>
                                ▶
                            </span>
                        )}
                        <div className="company-main-info">
                            <span className="company-name">{company.name}</span>
                            <span className="company-code">{company.code}</span>
                            <span className={`company-type-badge ${company.type}`}>
                                {getCompanyTypeLabel(company.type)}
                            </span>
                            <span className={`status-badge ${company.status ? 'active' : 'inactive'}`}>
                                {getStatusLabel(company.status)}
                            </span>
                        </div>
                        <div className="company-meta">
                            <span className="created-date">{formatDate(company.created_at)}</span>
                            {hasChildren && (
                                <span className="children-count">
                                    {company.type === 'headquarters' && `협력사: ${company.children?.length || 0}개`}
                                    {company.type === 'agency' && `판매점: ${retailers.length}개`}
                                </span>
                            )}
                        </div>
                    </div>
                    
                    <div className="company-tree-actions">
                        <button 
                            className="action-btn view"
                            onClick={(e) => {
                                e.stopPropagation();
                                onCompanyAction('view', company.id);
                            }}
                        >
                            보기
                        </button>
                        <button 
                            className="action-btn edit"
                            onClick={(e) => {
                                e.stopPropagation();
                                onCompanyAction('edit', company.id);
                            }}
                        >
                            수정
                        </button>
                        <button 
                            className="action-btn delete"
                            onClick={(e) => {
                                e.stopPropagation();
                                onCompanyAction('delete', company.id);
                            }}
                        >
                            삭제
                        </button>
                    </div>
                </div>

                {isExpanded && hasChildren && (
                    <div className="company-tree-content">
                        {/* 협력사들 (본사의 자식들) */}
                        {company.children && company.children.map(child => (
                            <CompanyNode 
                                key={child.id} 
                                company={child} 
                                retailers={child.retailers || []}
                                level={level + 1} 
                            />
                        ))}
                        
                        {/* 판매점들 (협력사의 자식들) */}
                        {retailers.map(retailer => (
                            <CompanyNode 
                                key={retailer.id} 
                                company={retailer} 
                                level={level + 1} 
                            />
                        ))}
                    </div>
                )}
            </div>
        );
    };

    return (
        <div className="company-tree-view">
            {/* 본사들 */}
            {hierarchy.headquarters.map(headquarters => (
                <CompanyNode 
                    key={headquarters.id} 
                    company={headquarters} 
                    level={0} 
                />
            ))}
            
            {/* 미배정 회사들 */}
            {hierarchy.unassigned.length > 0 && (
                <div className="unassigned-section">
                    <h3>미배정 회사</h3>
                    {hierarchy.unassigned.map(company => (
                        <CompanyNode 
                            key={company.id} 
                            company={company} 
                            level={0} 
                        />
                    ))}
                </div>
            )}
        </div>
    );
};

export default CompanyTreeView;
