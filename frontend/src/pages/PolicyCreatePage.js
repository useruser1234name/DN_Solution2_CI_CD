import React from 'react';
import { useNavigate } from 'react-router-dom';
import { PageHeader } from 'antd';
import PolicyCreateForm from '../components/PolicyCreateForm';
import './PolicyCreatePage.css';

const PolicyCreatePage = () => {
  const navigate = useNavigate();

  const handleSuccess = (policy) => {
    console.log('정책 생성 성공:', policy);
    // 정책 생성 성공 후 정책 목록 페이지로 이동
    navigate('/policies');
  };

  const handleCancel = () => {
    navigate('/policies');
  };

  return (
    <div className="policy-create-page">
      <PageHeader
        title="새 정책 생성"
        subTitle="새로운 정책을 생성하고 협력사에 노출할 수 있습니다"
        onBack={() => navigate('/policies')}
        className="page-header"
      />
      
      <div className="page-content">
        <PolicyCreateForm
          onSuccess={handleSuccess}
          onCancel={handleCancel}
        />
      </div>
    </div>
  );
};

export default PolicyCreatePage;
