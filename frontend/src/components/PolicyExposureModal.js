import React, { useState, useEffect } from 'react';
import { Modal, Button, Checkbox, message, Spin } from 'antd';
import { get, post } from '../services/api';
import './PolicyExposureModal.css';

const PolicyExposureModal = ({ visible, onClose, policyId, policyTitle }) => {
  const [agencies, setAgencies] = useState([]);
  const [selectedAgencies, setSelectedAgencies] = useState([]);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (visible && policyId) {
      fetchAgencies();
    }
  }, [visible, policyId]);

  const fetchAgencies = async () => {
    setLoading(true);
    try {
      // 협력사 목록 가져오기
      const response = await get('companies/agencies/');
      setAgencies(response.data || []);
      
      // 이미 노출된 협력사 정보 가져오기
      const exposureResponse = await get(`policies/${policyId}/exposure/`);
      setSelectedAgencies(exposureResponse.exposed_agencies || []);
    } catch (error) {
      message.error('협력사 목록을 불러오는데 실패했습니다.');
      console.error('Error fetching agencies:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleAgencyToggle = (agencyId) => {
    setSelectedAgencies(prev => {
      if (prev.includes(agencyId)) {
        return prev.filter(id => id !== agencyId);
      } else {
        return [...prev, agencyId];
      }
    });
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      await post(`policies/${policyId}/exposure/`, {
        agency_ids: selectedAgencies
      });
      message.success('정책 노출 설정이 저장되었습니다.');
      onClose();
    } catch (error) {
      message.error('정책 노출 설정 저장에 실패했습니다.');
      console.error('Error saving exposure:', error);
    } finally {
      setSaving(false);
    }
  };

  return (
    <Modal
      title={`정책 노출 설정 - ${policyTitle}`}
      visible={visible}
      onCancel={onClose}
      width={600}
      footer={[
        <Button key="cancel" onClick={onClose}>
          취소
        </Button>,
        <Button 
          key="save" 
          type="primary" 
          loading={saving}
          onClick={handleSave}
        >
          저장
        </Button>
      ]}
    >
      <div className="exposure-modal-content">
        <p className="exposure-description">
          이 정책을 노출할 협력사를 선택하세요. 
          선택된 협력사만 이 정책을 볼 수 있습니다.
        </p>
        
        {loading ? (
          <div className="loading-container">
            <Spin size="large" />
          </div>
        ) : (
          <div className="agencies-list">
            {agencies.length === 0 ? (
              <p className="no-agencies">등록된 협력사가 없습니다.</p>
            ) : (
              agencies.map(agency => (
                <div key={agency.id} className="agency-item">
                  <Checkbox
                    checked={selectedAgencies.includes(agency.id)}
                    onChange={() => handleAgencyToggle(agency.id)}
                  >
                    <div className="agency-info">
                      <span className="agency-name">{agency.name}</span>
                      <span className="agency-code">({agency.code})</span>
                    </div>
                  </Checkbox>
                </div>
              ))
            )}
          </div>
        )}
      </div>
    </Modal>
  );
};

export default PolicyExposureModal;
