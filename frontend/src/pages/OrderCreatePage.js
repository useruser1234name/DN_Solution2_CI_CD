import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { get, post } from '../services/api';
import { Card, Form, Button, Select, Input, Space, Typography, Divider, message } from 'antd';
import { ShoppingCartOutlined, UserOutlined, MobileOutlined, ShopOutlined, DollarOutlined } from '@ant-design/icons';
import CarrierPlanSelector from '../components/common/CarrierPlanSelector';
import DeviceSelector from '../components/common/DeviceSelector';
import RebateCalculator from '../components/common/RebateCalculator';
import EnhancedOrderForm from '../components/order/EnhancedOrderForm';
import DynamicOrderForm from '../components/order/DynamicOrderForm';
import './OrderCreatePage.css';

const { Title, Text } = Typography;
const { Option } = Select;

const OrderCreatePage = () => {
    const { user } = useAuth();
    const navigate = useNavigate();
    const [form] = Form.useForm();
    const [loading, setLoading] = useState(false);
    const [policies, setPolicies] = useState([]);
    const [selectedPolicy, setSelectedPolicy] = useState(null);
    const [selectedCarrierPlan, setSelectedCarrierPlan] = useState(null);
    const [selectedDevice, setSelectedDevice] = useState(null);
    const [selectedColor, setSelectedColor] = useState(null);
    const [formData, setFormData] = useState({});
    const [rebateData, setRebateData] = useState(null);
    const [errors, setErrors] = useState({});

    useEffect(() => {
        fetchPolicies();
    }, []);

    const fetchPolicies = async () => {
        try {
            console.log('[OrderCreatePage] 정책 목록 가져오기 시작...');
            const response = await get('api/policies/?only_active=1');
            console.log('[OrderCreatePage] 정책 API 응답:', response);
            
            if (response.success && response.data) {
                // API 응답 구조 처리: {success: true, data: {...}, message: null}
                let policiesData = [];
                
                // 이중 래핑 확인: response.data.data가 실제 데이터인 경우
                const actualData = response.data.data || response.data;
                
                if (actualData.results && Array.isArray(actualData.results)) {
                    // 페이지네이션된 응답
                    policiesData = actualData.results;
                } else if (Array.isArray(actualData)) {
                    // 직접 배열 응답
                    policiesData = actualData;
                } else {
                    console.warn('[OrderCreatePage] 예상하지 못한 데이터 구조:', response.data);
                    console.warn('[OrderCreatePage] actualData:', actualData);
                }
                
                console.log('[OrderCreatePage] 파싱된 정책 데이터:', policiesData);
                
                // 정책 데이터 구조 상세 확인
                if (policiesData.length > 0) {
                    const firstPolicy = policiesData[0];
                    console.log('[OrderCreatePage] 첫 번째 정책 상세:', firstPolicy);
                    console.log('[OrderCreatePage] 정책 필드들:', Object.keys(firstPolicy));
                    console.log('[OrderCreatePage] status:', firstPolicy.status);
                    console.log('[OrderCreatePage] expose:', firstPolicy.expose);
                }
                
                // 백엔드에서 only_active=1을 적용하므로 추가 필터 없이 그대로 사용
                setPolicies(policiesData);
            } else {
                console.warn('[OrderCreatePage] 정책 데이터 없음:', response);
            }
        } catch (error) {
            console.error('[OrderCreatePage] 정책 로딩 실패:', error);
        }
    };

    const handlePolicySelect = async (policyId) => {
        const policy = policies.find(p => p.id === policyId);
        setSelectedPolicy(policy);
        form.setFieldsValue({ policy: policyId });
        
        // 정책의 주문서 템플릿 가져오기
        try {
            const response = await get(`api/policies/${policyId}/form-template/`);
            if (response.success && response.data) {
                // 템플릿에 따라 초기 폼 데이터 설정
                const initialData = {};
                if (response.data.fields) {
                    response.data.fields.forEach(field => {
                        initialData[field.name] = field.default_value || '';
                    });
                }
                setFormData(initialData);
            }
        } catch (error) {
            console.error('[OrderCreatePage] 주문서 템플릿 로딩 실패:', error);
        }
    };

    const handleCarrierPlanSelect = (plan) => {
        setSelectedCarrierPlan(plan);
        form.setFieldsValue({ carrier_plan: plan.id });
        updateRebateCalculation();
    };

    const handleDeviceSelect = (device, color) => {
        setSelectedDevice(device);
        setSelectedColor(color);
        form.setFieldsValue({ 
            device_model: device.id,
            device_color: color?.id 
        });
    };

    const updateRebateCalculation = () => {
        if (selectedPolicy && selectedCarrierPlan) {
            // 리베이트 계산 로직은 RebateCalculator 컴포넌트에서 처리
        }
    };

    const handleFormChange = (fieldName, value) => {
        setFormData(prev => ({
            ...prev,
            [fieldName]: value
        }));
        
        // 에러 제거
        if (errors[fieldName]) {
            setErrors(prev => ({
                ...prev,
                [fieldName]: ''
            }));
        }
    };

    const validateForm = () => {
        const newErrors = {};
        
        if (!selectedPolicy) {
            newErrors.policy = '정책을 선택해주세요.';
        }
        
        // 필수 필드 검증
        if (!formData.customer_name) {
            newErrors.customer_name = '고객명을 입력해주세요.';
        }
        
        if (!formData.customer_phone) {
            newErrors.customer_phone = '연락처를 입력해주세요.';
        } else if (!/^010-?\d{4}-?\d{4}$/.test(formData.customer_phone.replace(/-/g, ''))) {
            newErrors.customer_phone = '올바른 전화번호 형식이 아닙니다.';
        }
        
        setErrors(newErrors);
        return Object.keys(newErrors).length === 0;
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        console.log('[OrderCreatePage] 주문 생성 시작');

        if (!validateForm()) {
            console.log('[OrderCreatePage] 유효성 검사 실패');
            return;
        }

        setLoading(true);
        setErrors({});

        try {
            const orderData = {
                policy: selectedPolicy.id,
                form_data: formData,
                status: 'pending'
            };

            const response = await post('api/orders/', orderData);
            console.log('[OrderCreatePage] 주문 생성 응답:', response);

            if (response.success) {
                alert('주문이 성공적으로 생성되었습니다.');
                navigate('/orders');
            } else {
                setErrors({ general: response.error || '주문 생성에 실패했습니다.' });
            }
        } catch (error) {
            console.error('[OrderCreatePage] 주문 생성 실패:', error);
            setErrors({ general: '주문 생성 중 오류가 발생했습니다.' });
        } finally {
            setLoading(false);
        }
    };

    const handleCancel = () => {
        navigate('/orders');
    };

    return (
        <div className="order-create-page">
            <div className="page-header">
                <Title level={2}>
                    <ShoppingCartOutlined /> 새 주문 생성
                </Title>
                <Text type="secondary">
                    정책을 선택하고 주문 정보를 입력하세요.
                </Text>
            </div>

            <Form
                form={form}
                layout="vertical"
                onFinish={handleSubmit}
                className="order-form"
            >
                {/* 1단계: 정책 선택 */}
                <Card 
                    title={<><UserOutlined /> 정책 선택</>}
                    className="form-card"
                    style={{ marginBottom: 24 }}
                >
                    <Form.Item
                        name="policy"
                        label="정책"
                        rules={[{ required: true, message: '정책을 선택해주세요' }]}
                    >
                        <Select
                            placeholder="정책을 선택하세요"
                            onChange={handlePolicySelect}
                            loading={loading}
                            size="large"
                        >
                            {policies.map(policy => (
                                <Option key={policy.id} value={policy.id}>
                                    {policy.title} - {policy.carrier} ({policy.contract_period}개월)
                                </Option>
                            ))}
                        </Select>
                    </Form.Item>

                    {selectedPolicy && (
                        <div className="policy-info">
                            <Title level={4}>{selectedPolicy.title}</Title>
                            <Text type="secondary">{selectedPolicy.description}</Text>
                            <div className="policy-details">
                                <Space>
                                    <Text>통신사: <strong>{selectedPolicy.carrier}</strong></Text>
                                    <Text>계약기간: <strong>{selectedPolicy.contract_period}개월</strong></Text>
                                </Space>
                            </div>
                        </div>
                    )}
                </Card>

                {selectedPolicy && (
                    <>
                        {/* 2단계: 통신사 요금제 선택 */}
                        <Card 
                            title={<><ShopOutlined /> 통신사 요금제 선택</>}
                            className="form-card"
                            style={{ marginBottom: 24 }}
                        >
                            <CarrierPlanSelector
                                carrier={selectedPolicy.carrier}
                                onSelect={handleCarrierPlanSelect}
                                selectedPlan={selectedCarrierPlan}
                            />
                        </Card>

                        {/* 3단계: 기기 선택 */}
                        <Card 
                            title={<><MobileOutlined /> 기기 선택</>}
                            className="form-card"
                            style={{ marginBottom: 24 }}
                        >
                            <DeviceSelector
                                onSelect={handleDeviceSelect}
                                selectedDevice={selectedDevice}
                                selectedColor={selectedColor}
                            />
                        </Card>

                        {/* 4단계: 리베이트 계산 */}
                        {selectedCarrierPlan && (
                            <Card 
                                title={<><DollarOutlined /> 리베이트 계산</>}
                                className="form-card"
                                style={{ marginBottom: 24 }}
                            >
                                <RebateCalculator
                                    policy={selectedPolicy}
                                    carrierPlan={selectedCarrierPlan}
                                    contractPeriod={selectedPolicy.contract_period}
                                    onCalculate={setRebateData}
                                />
                            </Card>
                        )}

                        {/* 5단계: 고객 정보 및 추가 필드 */}
                        <Card 
                            title={<><UserOutlined /> 고객 정보</>}
                            className="form-card"
                            style={{ marginBottom: 24 }}
                        >
                            <EnhancedOrderForm
                                policy={selectedPolicy}
                                formData={formData}
                                onChange={handleFormChange}
                                disabled={loading}
                            />
                        </Card>
                    </>
                )}

                {/* 제출 버튼 */}
                <div className="form-actions">
                    <Space size="large">
                        <Button 
                            size="large"
                            onClick={handleCancel}
                            disabled={loading}
                        >
                            취소
                        </Button>
                        <Button 
                            type="primary"
                            size="large"
                            htmlType="submit"
                            loading={loading}
                            disabled={!selectedPolicy}
                        >
                            주문 생성
                        </Button>
                    </Space>
                </div>
            </Form>
        </div>
    );
};

export default OrderCreatePage;
