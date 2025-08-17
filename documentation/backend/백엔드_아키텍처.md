# 8. 백엔드 API 리모델링 설계

## 🔌 DN_SOLUTION2 백엔드 API 리모델링 설계

### 8.1 리모델링 개요

#### 8.1.1 현재 API 구조 분석
```
현재 구조: Django REST Framework + JWT 인증
장점:
- 권한 기반 접근 제어 구현됨
- JWT 토큰 인증 시스템
- 계층별 데이터 접근 제어

개선 필요 사항:
- 역할별 API 엔드포인트 세분화
- 동적 폼 스키마 API
- 실시간 알림 시스템
- 정책 하달 플로우 API
- 리베이트 3단계 흐름 API
```

#### 8.1.2 리모델링 목표
```
✅ 역할별 권한 기반 API 엔드포인트 체계화
✅ 동적 폼 스키마 생성/관리 API
✅ 정책 하달 5단계 위저드 API
✅ 리베이트 할당/분배/사용 API
✅ 실시간 알림 WebSocket API
✅ 엑셀 생성/다운로드 최적화
✅ API 성능 최적화 및 캐싱
```

### 8.2 역할별 API 권한 매트릭스

#### 8.2.1 본사 (Headquarters) API 권한
```python
# HQ API 권한 매트릭스
HQ_PERMISSIONS = {
    # 정책 관리 (전체 권한)
    'policies': {
        'CREATE': ['/api/policies/', '/api/policies/create-wizard/'],
        'READ': ['/api/policies/', '/api/policies/{id}/', '/api/policies/all/'],
        'UPDATE': ['/api/policies/{id}/', '/api/policies/{id}/deploy/'],
        'DELETE': ['/api/policies/{id}/'],
        'SPECIAL': [
            '/api/policies/group-assign/',
            '/api/policies/form-fields/',
            '/api/policies/rebate-matrix/',
            '/api/policies/deploy/',
        ]
    },
    
    # 주문 관리 (승인 권한)
    'orders': {
        'READ': ['/api/orders/all/', '/api/orders/{id}/', '/api/orders/pending/'],
        'UPDATE': [
            '/api/orders/{id}/approve/', 
            '/api/orders/{id}/reject/',
            '/api/orders/{id}/tracking/',
        ],
        'SPECIAL': ['/api/orders/approval-queue/', '/api/orders/bulk-approve/']
    },
    
    # 조직 관리 (전체 권한)
    'companies': {
        'CREATE': ['/api/companies/', '/api/companies/agencies/'],
        'READ': ['/api/companies/all/', '/api/companies/hierarchy/'],
        'UPDATE': ['/api/companies/{id}/', '/api/companies/{id}/approve/'],
        'DELETE': ['/api/companies/{id}/'],
    },
    
    # 리베이트 관리 (할당 권한)
    'rebates': {
        'CREATE': ['/api/rebates/allocate/', '/api/rebates/allocate/bulk/'],
        'READ': ['/api/rebates/agency-summary/', '/api/rebates/all/'],
        'UPDATE': ['/api/rebates/allocations/{id}/'],
        'DELETE': ['/api/rebates/allocations/{id}/'],
    },
    
    # 정산 관리 (승인 권한)
    'settlements': {
        'READ': ['/api/settlements/hierarchical/', '/api/settlements/summary/'],
        'UPDATE': ['/api/settlements/approve/', '/api/settlements/bulk-approve/'],
        'SPECIAL': ['/api/settlements/excel/hierarchical/']
    },
    
    # 엑셀/리포트 (전사 데이터)
    'exports': {
        'READ': [
            '/api/exports/settlements/detailed/',
            '/api/exports/settlements/hierarchical/',
            '/api/exports/agency-rebates/',
            '/api/exports/policy-distribution/',
        ]
    }
}
```

#### 8.2.2 협력사 (Agency) API 권한
```python
# Agency API 권한 매트릭스
AGENCY_PERMISSIONS = {
    # 정책 관리 (조회 전용)
    'policies': {
        'READ': ['/api/policies/assigned/', '/api/policies/{id}/view/'],
    },
    
    # 주문 관리 (예하 판매점 범위)
    'orders': {
        'READ': ['/api/orders/subordinates/', '/api/orders/{id}/'],
    },
    
    # 조직 관리 (예하 판매점만)
    'companies': {
        'READ': ['/api/companies/retailers/', '/api/companies/subordinates/'],
        'UPDATE': ['/api/companies/retailers/{id}/'],
        'CREATE': ['/api/companies/retailers/'],
    },
    
    # 리베이트 관리 (분배 권한)
    'rebates': {
        'READ': ['/api/rebates/my/', '/api/rebates/retailers/'],
        'CREATE': ['/api/rebates/distribute/', '/api/rebates/distribute/bulk/'],
        'UPDATE': ['/api/rebates/distributions/{id}/'],
    },
    
    # 정산 관리 (예하 범위)
    'settlements': {
        'READ': ['/api/settlements/my/', '/api/settlements/retailers/'],
    },
    
    # 엑셀/리포트 (소속 데이터)
    'exports': {
        'READ': [
            '/api/exports/my-rebates/',
            '/api/exports/retailer-rebates/',
            '/api/exports/retailer-orders/',
        ]
    }
}
```

#### 8.2.3 판매점 (Retail) API 권한
```python
# Retail API 권한 매트릭스
RETAIL_PERMISSIONS = {
    # 정책 관리 (조회 전용)
    'policies': {
        'READ': ['/api/policies/available/', '/api/policies/{id}/view/'],
    },
    
    # 주문 관리 (본인 주문만)
    'orders': {
        'CREATE': ['/api/orders/'],
        'READ': ['/api/orders/my/', '/api/orders/{id}/'],
        'UPDATE': ['/api/orders/my/{id}/'],
    },
    
    # 리베이트 관리 (잔액 조회)
    'rebates': {
        'READ': ['/api/rebates/balance/', '/api/rebates/usage/'],
    },
    
    # 정산 관리 (본인 정산)
    'settlements': {
        'READ': ['/api/settlements/my/'],
    },
    
    # 엑셀/리포트 (개인 데이터)
    'exports': {
        'READ': [
            '/api/exports/my-orders/',
            '/api/exports/my-rebates/',
            '/api/exports/my-settlements/',
        ]
    }
}
```

### 8.3 정책 하달 API 설계

#### 8.3.1 정책 생성 5단계 위저드 API
```python
# views.py - 정책 생성 위저드
class PolicyWizardViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated, IsHeadquarters]
    
    @action(detail=False, methods=['post'])
    def step1_company_selection(self, request):
        """1단계: 협력사 그룹 선택"""
        serializer = CompanyGroupSelectionSerializer(data=request.data)
        if serializer.is_valid():
            selected_agencies = serializer.validated_data['agency_ids']
            
            # 예하 판매점 자동 조회
            subordinate_retailers = Company.objects.filter(
                parent_company_id__in=selected_agencies,
                type='retail'
            )
            
            # 그룹 생성
            group = PolicyGroup.objects.create(
                group_name=serializer.validated_data['group_name'],
                description=serializer.validated_data['description'],
                created_by=request.user.company_user
            )
            
            # 업체 배정
            assignments = []
            all_companies = list(selected_agencies) + list(subordinate_retailers.values_list('id', flat=True))
            for company_id in all_companies:
                assignments.append(PolicyGroupAssignment(
                    policy_group=group,
                    company_id=company_id,
                    assigned_by=request.user.company_user
                ))
            
            PolicyGroupAssignment.objects.bulk_create(assignments)
            
            return Response({
                'group_id': group.id,
                'selected_agencies': len(selected_agencies),
                'subordinate_retailers': subordinate_retailers.count(),
                'total_companies': len(all_companies)
            })
        
        return Response(serializer.errors, status=400)
    
    @action(detail=False, methods=['post'])
    def step2_form_fields(self, request):
        """2단계: 주문서 양식 생성"""
        serializer = PolicyFormFieldsSerializer(data=request.data)
        if serializer.is_valid():
            group_id = serializer.validated_data['group_id']
            fields_data = serializer.validated_data['fields']
            
            # 정책 생성 (임시)
            policy = Policy.objects.create(
                name=f"정책_{group_id}_임시",
                type='individual',
                created_by=request.user.company_user
            )
            
            # 그룹에 정책 연결
            group = PolicyGroup.objects.get(id=group_id)
            group.policy = policy
            group.save()
            
            # 주문서 필드 생성
            form_fields = []
            for field_data in fields_data:
                form_fields.append(PolicyFormField(
                    policy=policy,
                    field_id=field_data['field_id'],
                    is_required=field_data['is_required'],
                    order_index=field_data['order_index'],
                    default_value=field_data.get('default_value', '')
                ))
            
            PolicyFormField.objects.bulk_create(form_fields)
            
            return Response({
                'policy_id': policy.id,
                'form_fields_count': len(form_fields)
            })
        
        return Response(serializer.errors, status=400)
    
    @action(detail=False, methods=['post'])
    def step3_rebate_matrix(self, request):
        """3단계: 리베이트 매트릭스 설정"""
        serializer = PolicyRebateMatrixSerializer(data=request.data)
        if serializer.is_valid():
            policy_id = serializer.validated_data['policy_id']
            rebate_matrix = serializer.validated_data['rebate_matrix']
            
            # 리베이트 매트릭스 생성
            rebates = []
            for matrix_item in rebate_matrix:
                rebates.append(PolicyRebate(
                    policy_id=policy_id,
                    telecom_provider_id=matrix_item['telecom_provider_id'],
                    plan_category=matrix_item['plan_category'],
                    rebate_amount=matrix_item['rebate_amount']
                ))
            
            PolicyRebate.objects.bulk_create(rebates)
            
            return Response({
                'rebate_count': len(rebates)
            })
        
        return Response(serializer.errors, status=400)
    
    @action(detail=False, methods=['post'])
    def step4_contract_terms(self, request):
        """4단계: 계약 조건 설정"""
        serializer = PolicyContractTermsSerializer(data=request.data)
        if serializer.is_valid():
            policy_id = serializer.validated_data['policy_id']
            contract_terms = serializer.validated_data['contract_terms']
            
            # 정책 업데이트
            policy = Policy.objects.get(id=policy_id)
            policy.min_contract_days = contract_terms['min_contract_days']
            policy.penalty_amount = contract_terms['penalty_amount']
            policy.save()
            
            return Response({'success': True})
        
        return Response(serializer.errors, status=400)
    
    @action(detail=False, methods=['post'])
    def step5_deploy(self, request):
        """5단계: 정책 배포"""
        serializer = PolicyDeploySerializer(data=request.data)
        if serializer.is_valid():
            policy_id = serializer.validated_data['policy_id']
            policy_name = serializer.validated_data['policy_name']
            description = serializer.validated_data['description']
            
            # 정책 최종 업데이트
            policy = Policy.objects.get(id=policy_id)
            policy.name = policy_name
            policy.description = description
            policy.is_active = True
            policy.save()
            
            # 배정된 업체들에게 알림 발송
            group = PolicyGroup.objects.get(policy=policy)
            assignments = PolicyGroupAssignment.objects.filter(policy_group=group)
            
            # 실시간 알림
            notification_data = {
                'type': 'policy_assigned',
                'policy_name': policy_name,
                'policy_id': policy.id
            }
            
            for assignment in assignments:
                send_realtime_notification(
                    company_id=assignment.company_id,
                    data=notification_data
                )
            
            return Response({
                'policy_id': policy.id,
                'deployed_companies': assignments.count()
            })
        
        return Response(serializer.errors, status=400)
```

#### 8.3.2 정책 조회 API (협력사/판매점)
```python
class PolicyViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = PolicySerializer
    
    def get_queryset(self):
        user = self.request.user
        company_user = user.company_user
        
        if company_user.company.type == 'headquarters':
            return Policy.objects.all()
        else:
            # 배정받은 정책만 조회
            assigned_policies = PolicyGroupAssignment.objects.filter(
                company=company_user.company
            ).values_list('policy_group__policy', flat=True)
            
            return Policy.objects.filter(
                id__in=assigned_policies,
                is_active=True
            )
    
    @action(detail=True, methods=['get'])
    def form_schema(self, request, pk=None):
        """정책별 주문서 양식 스키마 반환"""
        policy = self.get_object()
        
        # 정책별 폼 필드 조회
        form_fields = PolicyFormField.objects.filter(
            policy=policy
        ).select_related('field').order_by('order_index')
        
        # JSON 스키마 생성
        schema = {
            'policy_id': policy.id,
            'policy_name': policy.name,
            'fields': []
        }
        
        for pf_field in form_fields:
            field_data = {
                'id': pf_field.field.field_name,
                'label': pf_field.field.display_name,
                'type': pf_field.field.field_type,
                'required': pf_field.is_required,
                'order': pf_field.order_index,
                'default_value': pf_field.default_value,
            }
            
            # 필드별 옵션 처리
            if pf_field.field.options:
                field_data['options'] = pf_field.field.options
            
            # 의존성 필드 처리
            if pf_field.field.field_name == 'plan':
                field_data['dependsOn'] = 'telecom_provider'
                field_data['optionsSource'] = '/api/plans/?provider={telecom_provider}'
            
            schema['fields'].append(field_data)
        
        return Response(schema)
    
    @action(detail=True, methods=['get'])
    def rebate_matrix(self, request, pk=None):
        """정책별 리베이트 매트릭스 반환"""
        policy = self.get_object()
        
        rebates = PolicyRebate.objects.filter(policy=policy).select_related('telecom_provider')
        
        matrix = {}
        for rebate in rebates:
            provider = rebate.telecom_provider.code
            category = rebate.plan_category
            
            if provider not in matrix:
                matrix[provider] = {}
            
            matrix[provider][category] = rebate.rebate_amount
        
        return Response({
            'policy_id': policy.id,
            'rebate_matrix': matrix
        })
```

### 8.4 동적 주문서 처리 API

#### 8.4.1 주문 생성 API (판매점)
```python
class OrderViewSet(viewsets.ModelViewSet):
    serializer_class = CustomerOrderSerializer
    
    def get_queryset(self):
        user = self.request.user
        company_user = user.company_user
        
        if company_user.company.type == 'headquarters':
            # 본사: 모든 주문
            return CustomerOrder.objects.all()
        elif company_user.company.type == 'agency':
            # 협력사: 예하 판매점 주문
            subordinate_companies = Company.objects.filter(
                parent_company=company_user.company
            ).values_list('id', flat=True)
            return CustomerOrder.objects.filter(company_id__in=subordinate_companies)
        else:
            # 판매점: 본인 주문만
            return CustomerOrder.objects.filter(company=company_user.company)
    
    def create(self, request):
        """주문 생성 (판매점만 가능)"""
        if request.user.company_user.company.type != 'retail':
            return Response({'error': '판매점만 주문을 생성할 수 있습니다.'}, status=403)
        
        serializer = OrderCreateSerializer(data=request.data)
        if serializer.is_valid():
            # 정책 및 요금제 검증
            policy_id = serializer.validated_data['policy_id']
            plan_id = serializer.validated_data['selected_plan_id']
            
            # 리베이트 금액 자동 계산
            rebate_amount = self.calculate_rebate(policy_id, plan_id)
            
            # 판매점 리베이트 잔액 확인
            company = request.user.company_user.company
            if company.rebate_balance < rebate_amount:
                return Response({'error': '리베이트 잔액이 부족합니다.'}, status=400)
            
            # 주문 생성
            order_data = serializer.validated_data
            order_data['company'] = company
            order_data['rebate_amount'] = rebate_amount
            order_data['created_by'] = request.user.company_user
            order_data['status'] = 'pending'
            
            order = CustomerOrder.objects.create(**order_data)
            
            # 리베이트 차감
            company.rebate_balance -= rebate_amount
            company.save()
            
            # 리베이트 사용 로그 생성
            RebateSettlement.objects.create(
                order=order,
                company=company,
                rebate_amount=rebate_amount,
                settlement_type='rebate',
                settlement_date=timezone.now().date()
            )
            
            # 본사에 승인 요청 알림
            send_realtime_notification(
                company_id=company.parent_company.parent_company_id,  # 본사
                data={
                    'type': 'order_created',
                    'order_id': order.id,
                    'customer_name': order.customer_name,
                    'company_name': company.name
                }
            )
            
            return Response(CustomerOrderSerializer(order).data, status=201)
        
        return Response(serializer.errors, status=400)
    
    def calculate_rebate(self, policy_id, plan_id):
        """리베이트 금액 자동 계산"""
        plan = Plan.objects.get(id=plan_id)
        
        try:
            policy_rebate = PolicyRebate.objects.get(
                policy_id=policy_id,
                telecom_provider=plan.telecom_provider,
                plan_category=plan.category
            )
            return policy_rebate.rebate_amount
        except PolicyRebate.DoesNotExist:
            return 0
    
    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """주문 승인 (본사만 가능)"""
        if request.user.company_user.company.type != 'headquarters':
            return Response({'error': '본사만 주문을 승인할 수 있습니다.'}, status=403)
        
        order = self.get_object()
        order.status = 'approved'
        order.save()
        
        # 주문 상태 로그
        OrderStatusLog.objects.create(
            order=order,
            status_type='progress',
            status_value='approved',
            changed_by=request.user.company_user,
            memo=request.data.get('memo', '')
        )
        
        # 판매점에 승인 알림
        send_realtime_notification(
            company_id=order.company_id,
            data={
                'type': 'order_approved',
                'order_id': order.id,
                'customer_name': order.customer_name
            }
        )
        
        return Response({'status': 'approved'})
    
    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """주문 반려 (본사만 가능)"""
        if request.user.company_user.company.type != 'headquarters':
            return Response({'error': '본사만 주문을 반려할 수 있습니다.'}, status=403)
        
        order = self.get_object()
        order.status = 'rejected'
        order.save()
        
        # 리베이트 환원
        order.company.rebate_balance += order.rebate_amount
        order.company.save()
        
        # 리베이트 사용 로그 취소
        RebateSettlement.objects.filter(order=order).delete()
        
        # 주문 상태 로그
        OrderStatusLog.objects.create(
            order=order,
            status_type='progress',
            status_value='rejected',
            changed_by=request.user.company_user,
            memo=request.data.get('reason', '')
        )
        
        # 판매점에 반려 알림
        send_realtime_notification(
            company_id=order.company_id,
            data={
                'type': 'order_rejected',
                'order_id': order.id,
                'reason': request.data.get('reason', '')
            }
        )
        
        return Response({'status': 'rejected'})
```

### 8.5 리베이트 3단계 흐름 API

#### 8.5.1 리베이트 할당 API (본사)
```python
class RebateAllocationViewSet(viewsets.ModelViewSet):
    serializer_class = RebateAllocationSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        company_user = user.company_user
        
        if company_user.company.type == 'headquarters':
            return RebateAllocation.objects.filter(from_company=company_user.company)
        elif company_user.company.type == 'agency':
            return RebateAllocation.objects.filter(to_company=company_user.company)
        else:
            return RebateAllocation.objects.none()
    
    @action(detail=False, methods=['post'])
    def bulk_allocate(self, request):
        """협력사들에게 리베이트 일괄 할당 (본사만)"""
        if request.user.company_user.company.type != 'headquarters':
            return Response({'error': '본사만 리베이트를 할당할 수 있습니다.'}, status=403)
        
        serializer = BulkRebateAllocationSerializer(data=request.data)
        if serializer.is_valid():
            period_start = serializer.validated_data['period_start']
            period_end = serializer.validated_data['period_end']
            allocations_data = serializer.validated_data['allocations']
            
            allocations = []
            total_amount = 0
            
            for allocation_data in allocations_data:
                allocation = RebateAllocation(
                    from_company=request.user.company_user.company,
                    to_company_id=allocation_data['agency_id'],
                    allocation_amount=allocation_data['amount'],
                    allocation_period_start=period_start,
                    allocation_period_end=period_end,
                    status='approved',
                    allocated_by=request.user.company_user,
                    notes=allocation_data.get('notes', '')
                )
                allocations.append(allocation)
                total_amount += allocation_data['amount']
            
            # 일괄 생성
            RebateAllocation.objects.bulk_create(allocations)
            
            # 협력사 잔액 업데이트
            for allocation_data in allocations_data:
                agency = Company.objects.get(id=allocation_data['agency_id'])
                agency.rebate_balance += allocation_data['amount']
                agency.save()
                
                # 협력사에 할당 알림
                send_realtime_notification(
                    company_id=agency.id,
                    data={
                        'type': 'rebate_allocated',
                        'amount': allocation_data['amount'],
                        'period_start': period_start.isoformat(),
                        'period_end': period_end.isoformat()
                    }
                )
            
            return Response({
                'allocated_count': len(allocations),
                'total_amount': total_amount
            })
        
        return Response(serializer.errors, status=400)
```

#### 8.5.2 리베이트 분배 API (협력사)
```python
class RebateDistributionViewSet(viewsets.ModelViewSet):
    serializer_class = RebateDistributionSerializer
    permission_classes = [IsAuthenticated, IsAgency]
    
    @action(detail=False, methods=['post'])
    def distribute_to_retailers(self, request):
        """예하 판매점들에게 리베이트 분배 (협력사만)"""
        serializer = RetailerRebateDistributionSerializer(data=request.data)
        if serializer.is_valid():
            distributions_data = serializer.validated_data['distributions']
            agency = request.user.company_user.company
            
            total_distribution = sum(d['amount'] for d in distributions_data)
            
            # 협력사 잔액 확인
            if agency.rebate_balance < total_distribution:
                return Response({'error': '리베이트 잔액이 부족합니다.'}, status=400)
            
            distributions = []
            for dist_data in distributions_data:
                distribution = RebateAllocation(
                    from_company=agency,
                    to_company_id=dist_data['retailer_id'],
                    allocation_amount=dist_data['amount'],
                    allocation_period_start=dist_data['period_start'],
                    allocation_period_end=dist_data['period_end'],
                    status='approved',
                    allocated_by=request.user.company_user,
                    notes=dist_data.get('notes', '')
                )
                distributions.append(distribution)
            
            # 일괄 생성
            RebateAllocation.objects.bulk_create(distributions)
            
            # 협력사 잔액 차감
            agency.rebate_balance -= total_distribution
            agency.save()
            
            # 판매점 잔액 증가 및 알림
            for dist_data in distributions_data:
                retailer = Company.objects.get(id=dist_data['retailer_id'])
                retailer.rebate_balance += dist_data['amount']
                retailer.save()
                
                send_realtime_notification(
                    company_id=retailer.id,
                    data={
                        'type': 'rebate_distributed',
                        'amount': dist_data['amount'],
                        'from_agency': agency.name
                    }
                )
            
            return Response({
                'distributed_count': len(distributions),
                'total_amount': total_distribution
            })
        
        return Response(serializer.errors, status=400)
```

### 8.6 실시간 알림 WebSocket API

#### 8.6.1 WebSocket Consumer
```python
# consumers.py
import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async

class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # URL에서 company_id 추출
        self.company_id = self.scope['url_route']['kwargs']['company_id']
        self.room_group_name = f'notifications_{self.company_id}'
        
        # 인증 확인
        user = self.scope.get('user')
        if not user or not user.is_authenticated:
            await self.close()
            return
        
        # 해당 업체에 속한 사용자인지 확인
        if not await self.is_authorized_user(user, self.company_id):
            await self.close()
            return
        
        # 그룹 참여
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
    
    async def disconnect(self, close_code):
        # 그룹 탈퇴
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
    
    async def receive(self, text_data):
        # 클라이언트에서 메시지 수신 시 처리
        try:
            text_data_json = json.loads(text_data)
            message_type = text_data_json.get('type')
            
            if message_type == 'ping':
                await self.send(text_data=json.dumps({
                    'type': 'pong',
                    'timestamp': timezone.now().isoformat()
                }))
        except json.JSONDecodeError:
            pass
    
    async def notification_message(self, event):
        """그룹으로부터 알림 메시지 수신"""
        await self.send(text_data=json.dumps(event['data']))
    
    @database_sync_to_async
    def is_authorized_user(self, user, company_id):
        """사용자가 해당 업체에 속한지 확인"""
        try:
            company_user = user.company_user
            return str(company_user.company_id) == company_id
        except:
            return False

# routing.py
from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/notifications/(?P<company_id>\w+)/$', consumers.NotificationConsumer.as_asgi()),
]
```

#### 8.6.2 알림 발송 유틸리티
```python
# utils/notifications.py
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

def send_realtime_notification(company_id, data):
    """특정 업체에 실시간 알림 발송"""
    channel_layer = get_channel_layer()
    
    async_to_sync(channel_layer.group_send)(
        f'notifications_{company_id}',
        {
            'type': 'notification_message',
            'data': {
                'timestamp': timezone.now().isoformat(),
                **data
            }
        }
    )

def send_bulk_notification(company_ids, data):
    """여러 업체에 일괄 알림 발송"""
    channel_layer = get_channel_layer()
    
    for company_id in company_ids:
        async_to_sync(channel_layer.group_send)(
            f'notifications_{company_id}',
            {
                'type': 'notification_message',
                'data': {
                    'timestamp': timezone.now().isoformat(),
                    **data
                }
            }
        )

# 알림 타입 정의
NOTIFICATION_TYPES = {
    'order_created': {
        'title': '새로운 주문',
        'icon': 'order',
        'priority': 'high'
    },
    'order_approved': {
        'title': '주문 승인',
        'icon': 'check',
        'priority': 'medium'
    },
    'order_rejected': {
        'title': '주문 반려',
        'icon': 'close',
        'priority': 'high'
    },
    'rebate_allocated': {
        'title': '리베이트 할당',
        'icon': 'money',
        'priority': 'medium'
    },
    'rebate_distributed': {
        'title': '리베이트 분배',
        'icon': 'money',
        'priority': 'low'
    },
    'policy_assigned': {
        'title': '정책 배정',
        'icon': 'policy',
        'priority': 'medium'
    },
    'settlement_approved': {
        'title': '정산 승인',
        'icon': 'settlement',
        'priority': 'medium'
    }
}
```

### 8.7 엑셀 생성/다운로드 최적화

#### 8.7.1 비동기 엑셀 생성 API
```python
# views/exports.py
import openpyxl
from django.http import HttpResponse
from django.utils import timezone
from celery import shared_task

class ExcelExportViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['post'])
    def request_excel(self, request):
        """엑셀 생성 요청 (비동기)"""
        serializer = ExcelRequestSerializer(data=request.data)
        if serializer.is_valid():
            export_type = serializer.validated_data['export_type']
            filters = serializer.validated_data['filters']
            user_company = request.user.company_user.company
            
            # 권한 확인
            if not self.check_export_permission(user_company.type, export_type):
                return Response({'error': '권한이 없습니다.'}, status=403)
            
            # 비동기 작업 시작
            task = generate_excel_async.delay(
                export_type=export_type,
                filters=filters,
                company_id=user_company.id,
                company_type=user_company.type,
                user_id=request.user.id
            )
            
            return Response({
                'task_id': task.id,
                'status': 'processing',
                'message': '엑셀 파일을 생성 중입니다.'
            })
        
        return Response(serializer.errors, status=400)
    
    @action(detail=False, methods=['get'])
    def task_status(self, request):
        """엑셀 생성 작업 상태 확인"""
        task_id = request.query_params.get('task_id')
        
        if not task_id:
            return Response({'error': 'task_id가 필요합니다.'}, status=400)
        
        task_result = AsyncResult(task_id)
        
        if task_result.ready():
            if task_result.successful():
                return Response({
                    'status': 'completed',
                    'download_url': task_result.result.get('download_url'),
                    'file_name': task_result.result.get('file_name')
                })
            else:
                return Response({
                    'status': 'failed',
                    'error': str(task_result.result)
                })
        else:
            return Response({
                'status': 'processing',
                'message': '엑셀 파일을 생성 중입니다.'
            })

@shared_task
def generate_excel_async(export_type, filters, company_id, company_type, user_id):
    """비동기 엑셀 생성 작업"""
    try:
        # 데이터 조회 (권한 기반)
        data = get_export_data(export_type, filters, company_id, company_type)
        
        # 엑셀 파일 생성
        file_path = create_excel_file(export_type, data, filters)
        
        # S3 또는 로컬 스토리지에 업로드
        download_url = upload_excel_file(file_path)
        
        # 완료 알림
        send_realtime_notification(
            company_id=company_id,
            data={
                'type': 'excel_ready',
                'export_type': export_type,
                'download_url': download_url
            }
        )
        
        return {
            'download_url': download_url,
            'file_name': f'{export_type}_{timezone.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
        }
        
    except Exception as e:
        # 오류 알림
        send_realtime_notification(
            company_id=company_id,
            data={
                'type': 'excel_failed',
                'export_type': export_type,
                'error': str(e)
            }
        )
        raise e

def get_export_data(export_type, filters, company_id, company_type):
    """역할별 데이터 조회"""
    start_date = filters.get('start_date')
    end_date = filters.get('end_date')
    
    if export_type == 'settlements_detailed':
        if company_type == 'headquarters':
            # 본사: 전체 정산 내역
            return RebateSettlement.objects.filter(
                settlement_date__range=[start_date, end_date]
            ).select_related('company', 'order')
        elif company_type == 'agency':
            # 협력사: 예하 판매점 정산
            subordinates = Company.objects.filter(
                parent_company_id=company_id
            ).values_list('id', flat=True)
            return RebateSettlement.objects.filter(
                company_id__in=subordinates,
                settlement_date__range=[start_date, end_date]
            ).select_related('company', 'order')
        else:
            # 판매점: 본인 정산
            return RebateSettlement.objects.filter(
                company_id=company_id,
                settlement_date__range=[start_date, end_date]
            ).select_related('company', 'order')
    
    elif export_type == 'my_rebates':
        return RebateAllocation.objects.filter(
            to_company_id=company_id,
            allocation_period_start__lte=end_date,
            allocation_period_end__gte=start_date
        ).select_related('from_company')
    
    # 다른 export_type들...

def create_excel_file(export_type, data, filters):
    """엑셀 파일 생성"""
    wb = openpyxl.Workbook()
    ws = wb.active
    
    if export_type == 'settlements_detailed':
        ws.title = '정산 상세 내역'
        
        # 헤더
        headers = ['정산일', '업체명', '주문번호', '고객명', '리베이트 금액', '상품 마진', '총 수익']
        ws.append(headers)
        
        # 데이터
        for settlement in data:
            ws.append([
                settlement.settlement_date.strftime('%Y-%m-%d'),
                settlement.company.name,
                settlement.order.id if settlement.order else '',
                settlement.order.customer_name if settlement.order else '',
                settlement.rebate_amount,
                settlement.product_profit,
                settlement.total_profit
            ])
        
        # 스타일링
        apply_excel_styling(ws)
    
    # 임시 파일로 저장
    file_path = f'/tmp/{export_type}_{timezone.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
    wb.save(file_path)
    
    return file_path

def apply_excel_styling(worksheet):
    """엑셀 스타일링 적용"""
    from openpyxl.styles import Font, PatternFill, Border, Side
    
    # 헤더 스타일
    header_font = Font(bold=True, color='FFFFFF')
    header_fill = PatternFill(start_color='366092', end_color='366092', fill_type='solid')
    
    for cell in worksheet[1]:
        cell.font = header_font
        cell.fill = header_fill
    
    # 테두리
    thin_border = Border(
        left=Side(style='thin'),
        right=Side(style='thin'),
        top=Side(style='thin'),
        bottom=Side(style='thin')
    )
    
    for row in worksheet.iter_rows():
        for cell in row:
            cell.border = thin_border
```

### 8.8 API 성능 최적화

#### 8.8.1 캐싱 전략
```python
# views/optimized.py
from django.core.cache import cache
from django.db.models import Prefetch

class OptimizedPolicyViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = PolicySerializer
    
    def list(self, request):
        """정책 목록 - 캐싱 적용"""
        cache_key = f'policies_{request.user.company_user.company.type}_{request.user.company_user.company_id}'
        
        cached_data = cache.get(cache_key)
        if cached_data:
            return Response(cached_data)
        
        queryset = self.get_queryset()
        
        # N+1 문제 해결
        queryset = queryset.select_related('created_by__company').prefetch_related(
            Prefetch('policy_rebates', queryset=PolicyRebate.objects.select_related('telecom_provider')),
            Prefetch('policy_form_fields', queryset=PolicyFormField.objects.select_related('field'))
        )
        
        serializer = self.get_serializer(queryset, many=True)
        
        # 5분 캐싱
        cache.set(cache_key, serializer.data, 300)
        
        return Response(serializer.data)

class OptimizedOrderViewSet(viewsets.ModelViewSet):
    serializer_class = CustomerOrderSerializer
    
    def get_queryset(self):
        """주문 목록 - 쿼리 최적화"""
        queryset = super().get_queryset()
        
        # 관련 데이터 사전 로딩
        queryset = queryset.select_related(
            'company',
            'policy',
            'selected_plan__telecom_provider',
            'created_by'
        ).prefetch_related(
            'order_status_logs',
            'order_attachments'
        )
        
        return queryset
    
    def list(self, request):
        """주문 목록 - 페이징 적용"""
        queryset = self.get_queryset()
        
        # 필터링
        status = request.query_params.get('status')
        if status:
            queryset = queryset.filter(status=status)
        
        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')
        if date_from and date_to:
            queryset = queryset.filter(
                created_at__date__range=[date_from, date_to]
            )
        
        # 페이징
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

# 캐시 무효화 시그널
from django.db.models.signals import post_save, post_delete

@receiver(post_save, sender=Policy)
def invalidate_policy_cache(sender, instance, **kwargs):
    """정책 변경 시 캐시 무효화"""
    cache.delete_pattern('policies_*')

@receiver(post_save, sender=CustomerOrder)
def invalidate_order_cache(sender, instance, **kwargs):
    """주문 변경 시 관련 캐시 무효화"""
    cache.delete_pattern(f'dashboard_{instance.company_id}')
    cache.delete_pattern(f'orders_{instance.company_id}')
```

### 8.9 API 문서화 및 버전 관리

#### 8.9.1 Swagger 문서화
```python
# settings.py
INSTALLED_APPS = [
    # ...
    'drf_yasg',
]

# urls.py
from drf_yasg import openapi
from drf_yasg.views import get_schema_view

schema_view = get_schema_view(
    openapi.Info(
        title="DN_SOLUTION2 API",
        default_version='v1',
        description="DN_SOLUTION2 시스템 API 문서",
        terms_of_service="https://www.google.com/policies/terms/",
        contact=openapi.Contact(email="admin@dn-solution.com"),
        license=openapi.License(name="BSD License"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)

urlpatterns = [
    # API 문서
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
    path('api/schema/', schema_view.without_ui(cache_timeout=0), name='schema-json'),
]
```

#### 8.9.2 API 버전 관리
```python
# versioning.py
from rest_framework.versioning import URLPathVersioning

class CustomAPIVersioning(URLPathVersioning):
    default_version = 'v1'
    allowed_versions = ['v1', 'v2']
    version_param = 'version'

# settings.py
REST_FRAMEWORK = {
    'DEFAULT_VERSIONING_CLASS': 'myapp.versioning.CustomAPIVersioning',
}

# urls.py
urlpatterns = [
    path('api/v1/', include('myapp.urls.v1')),
    path('api/v2/', include('myapp.urls.v2')),  # 향후 버전
]
```

### 8.10 구현 우선순위

#### 8.10.1 Phase 1: 핵심 API 개선 (4주)
```
✅ 역할별 권한 매트릭스 구현
✅ 정책 하달 5단계 위저드 API
✅ 동적 주문서 처리 API
✅ 기본 캐싱 전략
```

#### 8.10.2 Phase 2: 리베이트 시스템 (4주)
```
✅ 리베이트 3단계 흐름 API
✅ 자동 정산 처리
✅ 잔액 관리 시스템
✅ 리베이트 사용 로깅
```

#### 8.10.3 Phase 3: 실시간 시스템 (3주)
```
✅ WebSocket 알림 시스템
✅ 실시간 대시보드 데이터
✅ 알림 타입별 처리
✅ 연결 관리 최적화
```

#### 8.10.4 Phase 4: 엑셀/리포팅 (3주)
```
✅ 비동기 엑셀 생성
✅ 역할별 데이터 접근
✅ 파일 스토리지 최적화
✅ 대용량 데이터 처리
```

#### 8.10.5 Phase 5: 성능 최적화 (2주)
```
✅ 쿼리 최적화
✅ 캐싱 전략 고도화
✅ API 응답 최적화
✅ 모니터링 시스템
```

이 문서는 DN_Solution2의 백엔드 API 리모델링을 위한 완전한 설계 가이드입니다.