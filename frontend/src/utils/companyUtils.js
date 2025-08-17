/**
 * 업체 관련 유틸리티 함수들
 */

/**
 * 업체 코드를 기반으로 회사 타입을 구분
 * 확장된 패턴 지원: A/H-YYMMDD-01 (본사), B-YYMMDD-01 (협력사/대리점), C-YYMMDD-01 (판매점)
 * @param {string} companyCode - 업체 코드
 * @returns {string} - 회사 타입 (headquarters, agency, retail, dealer, unknown)
 */
export const getCompanyTypeFromCode = (companyCode) => {
    if (!companyCode || typeof companyCode !== 'string') {
        return 'unknown';
    }

    const code = companyCode.toUpperCase();
    
    // 확장된 업체 코드 패턴 기반 타입 구분
    if (code.startsWith('A-') || code.startsWith('H-')) {
        return 'headquarters';  // 본사: A-YYMMDD-01 또는 H-YYMMDD-01
    } else if (code.startsWith('B-')) {
        // 협력사와 대리점 모두 B로 시작하므로 추가 로직이 필요할 수 있음
        // 현재는 협력사로 가정 (필요시 parent_company 정보로 구분)
        return 'agency';        // 협력사/대리점: B-YYMMDD-01
    } else if (code.startsWith('C-')) {
        return 'retail';        // 판매점: C-YYMMDD-01
    }
    
    return 'unknown';
};

/**
 * 회사 타입에 따른 한글 라벨 반환
 * @param {string} companyType - 회사 타입
 * @returns {string} - 한글 라벨
 */
export const getCompanyTypeLabel = (companyType) => {
    const typeMap = {
        'headquarters': '본사',
        'agency': '협력사',
        'dealer': '대리점',
        'retail': '판매점',
        'unknown': '미분류'
    };
    return typeMap[companyType] || companyType;
};

/**
 * 사용자가 정책 생성 권한이 있는지 확인
 * @param {Object} user - 사용자 정보
 * @returns {boolean} - 정책 생성 권한 여부
 */
export const canCreatePolicy = (user) => {
    if (!user || !user.company) {
        return false;
    }

    // 1. company.type이 있는 경우 직접 확인
    if (user.company.type) {
        return user.company.type === 'headquarters';
    }

    // 2. company.code가 있는 경우 패턴으로 확인
    if (user.company.code) {
        const companyType = getCompanyTypeFromCode(user.company.code);
        return companyType === 'headquarters';
    }

    return false;
};

/**
 * 회사 상태 표시용 라벨
 * @param {boolean} status - 회사 상태
 * @returns {string} - 상태 라벨
 */
export const getStatusLabel = (status) => {
    return status ? '운영중' : '중단';
};

/**
 * 회사 계층 구조 빌드
 * @param {Array} companies - 회사 목록
 * @returns {Object} - 계층 구조 객체
 */
export const buildCompanyHierarchy = (companies) => {
    if (!Array.isArray(companies)) {
        return { headquarters: [], agencies: {}, unassigned: [] };
    }

    const hierarchy = {
        headquarters: [],
        agencies: {},
        unassigned: []
    };

    // 1단계: 회사들을 타입별로 분류
    companies.forEach(company => {
        const companyType = company.type || getCompanyTypeFromCode(company.code);
        
        if (companyType === 'headquarters') {
            hierarchy.headquarters.push({
                ...company,
                children: []
            });
        } else if (companyType === 'agency') {
            hierarchy.agencies[company.id] = {
                ...company,
                retailers: []
            };
        } else if (companyType === 'retail') {
            // parent_company ID가 있으면 해당 협력사에 배정
            const parentId = company.parent_company;
            if (parentId && hierarchy.agencies[parentId]) {
                hierarchy.agencies[parentId].retailers.push(company);
            } else {
                hierarchy.unassigned.push(company);
            }
        } else {
            hierarchy.unassigned.push(company);
        }
    });

    // 2단계: 협력사들을 본사에 연결
    if (hierarchy.headquarters.length > 0) {
        hierarchy.headquarters[0].children = Object.values(hierarchy.agencies);
    }

    return hierarchy;
};

/**
 * 날짜 포맷팅
 * @param {string} dateString - 날짜 문자열
 * @returns {string} - 포맷된 날짜
 */
export const formatDate = (dateString) => {
    if (!dateString) return '-';
    return new Date(dateString).toLocaleDateString('ko-KR');
};

/**
 * 업체 코드 패턴이 유효한지 확인
 * @param {string} companyCode - 업체 코드
 * @returns {boolean} - 유효성 여부
 */
export const isValidCompanyCode = (companyCode) => {
    if (!companyCode || typeof companyCode !== 'string') {
        return false;
    }
    
    // A/H-YYMMDD-01, B-YYMMDD-01, C-YYMMDD-01 패턴 확인
    const pattern = /^[AHBC]-\d{6}-\d{2}$/;
    return pattern.test(companyCode);
};

/**
 * 업체 타입과 대리점 구분 (B 코드의 경우 parent_company로 구분 필요)
 * @param {string} companyCode - 업체 코드
 * @param {Object} parentCompany - 상위 회사 정보
 * @returns {string} - 정확한 회사 타입
 */
export const getExactCompanyType = (companyCode, parentCompany) => {
    const baseType = getCompanyTypeFromCode(companyCode);
    
    // B 코드인 경우 상위 회사로 구분
    if (baseType === 'agency' && parentCompany) {
        if (parentCompany.type === 'headquarters') {
            // 본사 직하는 협력사 또는 대리점
            // 여기서는 기본적으로 협력사로 가정하되, 필요시 추가 로직 구현
            return 'agency';
        }
    }
    
    return baseType;
};


