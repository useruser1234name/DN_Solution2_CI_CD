# orders/serializers.py
import logging
import re
from rest_framework import serializers
from django.contrib.auth.models import User
from companies.models import Company
from policies.models import Policy
from .models import Order, OrderMemo, Invoice, OrderRequest

logger = logging.getLogger('orders')


class OrderSerializer(serializers.ModelSerializer):
    """
    주문서 관리를 위한 시리얼라이저
    주문서의 CRUD 작업과 상태 관리 기능 제공
    """
    
    # 읽기 전용 필드들
    id = serializers.UUIDField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True, format='%Y-%m-%d %H:%M:%S')
    updated_at = serializers.DateTimeField(read_only=True, format='%Y-%m-%d %H:%M:%S')
    
    # 관계 필드들
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    # 연관 객체 정보
    policy_title = serializers.CharField(source='policy.title', read_only=True)
    company_name = serializers.CharField(source='company.name', read_only=True)
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)
    
    # 통계 및 추가 정보
    memo_count = serializers.SerializerMethodField()
    has_invoice = serializers.SerializerMethodField()
    invoice_info = serializers.SerializerMethodField()
    status_history = serializers.SerializerMethodField()
    
    # 프론트엔드에서 전송하는 form_data 처리
    form_data = serializers.DictField(write_only=True, required=False)

    # 접수 메타(읽기 전용)
    acceptance_number = serializers.CharField(source='order_number', read_only=True)
    acceptance_date = serializers.DateTimeField(source='received_date', read_only=True, format='%Y-%m-%d %H:%M:%S')
    activation_phone = serializers.CharField(read_only=True)
    retailer_name = serializers.CharField(read_only=True)
    reference_url = serializers.CharField(read_only=True)
    
    class Meta:
        model = Order
        fields = [
            'id', 'customer_name', 'customer_phone', 'customer_email',
            'customer_address', 'status', 'status_display', 'policy', 'policy_title', 
            'company', 'company_name', 'created_by', 'created_by_username',
            'total_amount', 'rebate_amount', 'notes', 'form_data',
            'memo_count', 'has_invoice', 'invoice_info', 'status_history',
            # TelecomOrder 통합 필드들
            'order_number', 'carrier', 'subscription_type', 'customer_type',
            'received_date', 'activation_date', 'order_data', 'first_id',
            'created_at', 'updated_at'
        ]
        # 추가 필드 확장
        fields += [
            'reference_url', 'retailer_name', 'previous_carrier', 'activation_phone',
            'plan_name', 'contract_period_selected',
            'device_model', 'device_serial', 'imei', 'imei2', 'eid', 'usim_serial',
            'payment_method', 'bank_name', 'account_holder', 'account_number_masked',
            'card_brand', 'card_number_masked', 'card_exp_mmyy',
            'acceptance_number', 'acceptance_date'
        ]
        extra_kwargs = {
            'customer_name': {
                'required': False,  # form_data에서 추출하므로 선택적
                'allow_blank': False,
                'max_length': 100,
                'help_text': '신청 고객의 성명을 입력하세요'
            },
            'customer_phone': {
                'required': False,  # form_data에서 추출하므로 선택적
                'allow_blank': False,
                'help_text': '휴대폰 번호를 입력하세요 (예: 010-1234-5678)'
            },
            'customer_address': {
                'required': False,  # form_data에서 추출하므로 선택적
                'allow_blank': False,
                'help_text': '배송 주소를 입력하세요'
            },
            'company': {
                'required': False,  # 현재 사용자의 회사에서 자동 설정
                'help_text': '주문을 처리할 업체를 선택하세요'
            },
            'total_amount': {
                'required': False,  # 자동 계산
                'help_text': '총 금액 (자동 계산)'
            },
            'rebate_amount': {
                'required': False,  # 자동 계산
                'help_text': '리베이트 금액 (자동 계산)'
            },
            'policy': {
                'help_text': '적용할 정책 ID (필수)'
            },
            'subscription_type': {
                'required': False,
                'help_text': '가입 유형(MNP/device_change/new)'
            },
            'plan_name': {
                'required': False,
                'help_text': '요금상품명'
            },
            'contract_period_selected': {
                'required': False,
                'help_text': '약정기간(12|24|36)'
            },
            'previous_carrier': {
                'required': False,
                'help_text': '이전 통신사(선택)'
            },
            'device_model': {'required': False},
            'device_serial': {'required': False},
            'imei': {'required': False},
            'imei2': {'required': False},
            'eid': {'required': False},
            'usim_serial': {'required': False},
            'payment_method': {'required': False},
            'bank_name': {'required': False},
            'account_holder': {'required': False},
            'account_number_masked': {'required': False},
            'card_brand': {'required': False},
            'card_number_masked': {'required': False},
            'card_exp_mmyy': {'required': False},
        }
    
    def get_memo_count(self, obj):
        """연관된 메모 수 반환"""
        try:
            return obj.memos.count()
        except Exception as e:
            logger.warning(f"주문 메모 수 조회 중 오류: {str(e)} - 주문: {obj.customer_name}")
            return 0
    
    def get_has_invoice(self, obj):
        """송장 존재 여부 반환"""
        try:
            return hasattr(obj, 'invoice') and obj.invoice is not None
        except Exception as e:
            logger.warning(f"송장 존재 여부 확인 중 오류: {str(e)} - 주문: {obj.customer_name}")
            return False
    
    def get_invoice_info(self, obj):
        """송장 정보 반환"""
        try:
            if hasattr(obj, 'invoice') and obj.invoice:
                return {
                    'courier': obj.invoice.courier,
                    'courier_display': obj.invoice.get_courier_display(),
                    'invoice_number': obj.invoice.invoice_number,
                    'sent_at': obj.invoice.sent_at.strftime('%Y-%m-%d %H:%M:%S') if obj.invoice.sent_at else None,
                    'is_delivered': obj.invoice.is_delivered(),
                    'delivery_status': obj.invoice.get_delivery_status()
                }
            return None
        except Exception as e:
            logger.warning(f"송장 정보 조회 중 오류: {str(e)} - 주문: {obj.customer_name}")
            return None
    
    def get_status_history(self, obj):
        """상태 변경 이력 반환 (최근 5개)"""
        try:
            recent_history = obj.history.all()[:5]
            return [
                {
                    'from_status': history.from_status,
                    'from_status_display': history.get_from_status_display(),
                    'to_status': history.to_status,
                    'to_status_display': history.get_to_status_display(),
                    'changed_by': history.changed_by.username if history.changed_by else 'System',
                    'reason': history.reason,
                    'changed_at': history.changed_at.strftime('%Y-%m-%d %H:%M:%S'),
                }
                for history in recent_history
            ]
        except Exception as e:
            logger.warning(f"상태 이력 조회 중 오류: {str(e)} - 주문: {obj.customer_name}")
            return []
    
    def validate_customer_name(self, value):
        """고객명 검증"""
        if not value or not value.strip():
            raise serializers.ValidationError("고객명은 필수 입력 사항입니다.")
        
        # 특수문자 제한 (한글, 영문, 숫자, 공백만 허용)
        if not re.match(r'^[가-힣a-zA-Z0-9\s]+$', value.strip()):
            raise serializers.ValidationError("고객명은 한글, 영문, 숫자, 공백만 입력 가능합니다.")
        
        return value.strip()
    
    def validate_customer_phone(self, value):
        """연락처 검증"""
        if not value or not value.strip():
            raise serializers.ValidationError("연락처는 필수 입력 사항입니다.")
        
        # 휴대폰 번호 정규식 검증
        phone_pattern = r'^01([0|1|6|7|8|9])-?([0-9]{3,4})-?([0-9]{4})$'
        cleaned_phone = value.strip().replace('-', '').replace(' ', '')
        
        if not re.match(r'^01([0|1|6|7|8|9])([0-9]{7,8})$', cleaned_phone):
            raise serializers.ValidationError("올바른 휴대폰 번호를 입력하세요. (예: 010-1234-5678)")
        
        # 표준 형식으로 변환 (010-1234-5678)
        if len(cleaned_phone) == 11:
            return f"{cleaned_phone[:3]}-{cleaned_phone[3:7]}-{cleaned_phone[7:]}"
        elif len(cleaned_phone) == 10:
            return f"{cleaned_phone[:3]}-{cleaned_phone[3:6]}-{cleaned_phone[6:]}"
        
        return value
    
    def validate_customer_email(self, value):
        """이메일 검증"""
        if value and value.strip():
            # 이메일 형식 재검증
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not re.match(email_pattern, value.strip()):
                raise serializers.ValidationError("올바른 이메일 주소를 입력하세요.")
            return value.strip()
        return value
    
    def validate_customer_address(self, value):
        """배송 주소 검증"""
        if not value or not value.strip():
            raise serializers.ValidationError("배송 주소는 필수 입력 사항입니다.")
        
        return value.strip()
    
    def validate_company(self, value):
        """업체 검증"""
        if not value.status:
            logger.warning(f"비활성 업체로 주문 생성 시도: {value.name}")
            raise serializers.ValidationError("운영 중단된 업체로는 주문을 생성할 수 없습니다.")
        
        return value
    
    def validate(self, data):
        """전체 데이터 검증"""
        # form_data에서 고객 정보 추출
        form_data = data.pop('form_data', {})
        
        if form_data:
            # form_data에서 고객 정보 추출
            data['customer_name'] = form_data.get('customer_name', '')
            data['customer_phone'] = form_data.get('customer_phone', '')
            data['customer_email'] = form_data.get('customer_email', '')
            data['customer_address'] = form_data.get('customer_address', '')
            data['notes'] = form_data.get('memo', '')  # memo -> notes로 매핑
            # 고객 유형/가입 유형/이전 통신사
            data['customer_type'] = form_data.get('customer_type', data.get('customer_type'))
            sub_type = form_data.get('subscription_type') or form_data.get('join_type') or data.get('subscription_type')
            if sub_type:
                sub_map = {'mnp': 'MNP', 'MNP': 'MNP', 'device_change': 'device_change', 'new': 'new'}
                data['subscription_type'] = sub_map.get(sub_type, sub_type)
            data['previous_carrier'] = form_data.get('previous_carrier', data.get('previous_carrier', ''))

            # 요금/약정/단말 식별자
            data['plan_name'] = form_data.get('plan_name', form_data.get('plan')) or data.get('plan_name', '')
            cp = (form_data.get('contract_period') or form_data.get('contract_period_selected') or '').strip()
            if cp in ['12', '24', '36']:
                data['contract_period_selected'] = cp
            data['device_model'] = form_data.get('device_model', data.get('device_model', ''))
            data['device_serial'] = form_data.get('device_serial', data.get('device_serial', ''))
            data['imei'] = form_data.get('imei', data.get('imei', ''))
            data['imei2'] = form_data.get('imei2', data.get('imei2', ''))
            data['eid'] = form_data.get('eid', data.get('eid', ''))
            data['usim_serial'] = form_data.get('usim_serial', data.get('usim_serial', ''))

            # 납부/결제 - 평문은 order_data로 보관, 마스킹은 서버가 처리
            data['payment_method'] = (form_data.get('payment_method') or '').lower()
            data['bank_name'] = form_data.get('bank_name', data.get('bank_name', ''))
            data['account_holder'] = form_data.get('account_holder', data.get('account_holder', ''))
            # 평문 민감정보는 order_data에만 남긴다(최종승인 시 해시/마스킹 처리)
            order_payload = data.get('order_data') or {}
            for key in ['rrn', 'resident_registration_number', 'account_number', 'card_number', 'card_cvc']:
                if form_data.get(key):
                    order_payload[key] = form_data.get(key)
            data['order_data'] = order_payload
        
        # 필수 필드 검증
        required_base = ['customer_name', 'customer_phone', 'customer_address', 'customer_type']
        for f in required_base:
            if not data.get(f):
                raise serializers.ValidationError({f: '필수 입력 사항입니다.'})

        # 정책/통신사
        if not data.get('policy'):
            raise serializers.ValidationError({'policy': '정책 선택은 필수입니다.'})
        # 가입/요금/약정/단말 핵심
        required_detail = ['subscription_type', 'plan_name', 'contract_period_selected', 'device_model', 'device_serial', 'imei']
        for f in required_detail:
            if not data.get(f):
                raise serializers.ValidationError({f: '필수 입력 사항입니다.'})
        
        # 결제 방식에 따른 필수 항목
        pm = (data.get('payment_method') or '').lower()
        if pm == 'card':
            payload = data.get('order_data') or {}
            for key in ['card_number', 'card_exp_mmyy', 'card_cvc']:
                if not (payload.get(key) or data.get(key)):
                    raise serializers.ValidationError({key: '카드 결제 시 필수 입력입니다.'})
        elif pm == 'account':
            payload = data.get('order_data') or {}
            if not (payload.get('account_number')):
                raise serializers.ValidationError({'account_number': '계좌 이체 시 계좌번호는 필수입니다.'})

        # 정책과 업체 매칭 확인
        policy = data.get('policy')
        company = data.get('company')
        
        if policy and company:
            policy_assignment = policy.assignments.filter(company=company).exists()
            if not policy_assignment:
                logger.warning(f"정책과 업체가 매칭되지 않는 주문 생성 시도: {policy.title} - {company.name}")
                # 경고만 하고 에러는 발생시키지 않음 (비즈니스 로직에 따라 조정 가능)
        
        return data
    
    def create(self, validated_data):
        """주문서 생성"""
        try:
            # 현재 사용자의 회사 정보 설정
            request = self.context.get('request')
            if request and request.user:
                # company가 없으면 현재 사용자의 회사로 설정
                if not validated_data.get('company'):
                    try:
                        from companies.models import CompanyUser
                        company_user = CompanyUser.objects.get(django_user=request.user)
                        validated_data['company'] = company_user.company
                    except CompanyUser.DoesNotExist:
                        logger.warning(f"사용자 {request.user.username}의 회사 정보를 찾을 수 없습니다.")
                
                # created_by 설정
                validated_data['created_by'] = request.user
            
            order = Order.objects.create(**validated_data)
            logger.info(f"주문서 생성 성공: {order.customer_name} - 정책: {order.policy.title}")
            return order
        except Exception as e:
            logger.error(f"주문서 생성 실패: {str(e)} - 데이터: {validated_data}")
            raise serializers.ValidationError("주문서 생성 중 오류가 발생했습니다.")
    
    def update(self, instance, validated_data):
        """주문서 정보 수정"""
        try:
            old_customer_name = instance.customer_name
            old_status = instance.status
            
            for attr, value in validated_data.items():
                setattr(instance, attr, value)
            
            instance.save()
            
            # 상태 변경 시 추가 로깅
            if 'status' in validated_data and old_status != instance.status:
                logger.info(f"주문 상태 변경: {instance.customer_name} - {old_status} → {instance.status}")
            else:
                logger.info(f"주문서 정보 수정 성공: {old_customer_name} -> {instance.customer_name}")
            
            return instance
        
        except Exception as e:
            logger.error(f"주문서 정보 수정 실패: {str(e)} - 주문: {instance.customer_name}")
            raise serializers.ValidationError("주문서 정보 수정 중 오류가 발생했습니다.")


class OrderMemoSerializer(serializers.ModelSerializer):
    """
    주문 메모 관리를 위한 시리얼라이저
    주문 처리 과정의 메모와 기록 관리 기능 제공
    """
    
    # 읽기 전용 필드들
    id = serializers.UUIDField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True, format='%Y-%m-%d %H:%M:%S')
    
    # 연관 객체 정보
    order_customer_name = serializers.CharField(source='order.customer_name', read_only=True)
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)
    
    class Meta:
        model = OrderMemo
        fields = [
            'id', 'order', 'order_customer_name', 'memo',
            'created_by', 'created_by_username', 'created_at'
        ]
        extra_kwargs = {
            'order': {
                'required': True,
                'help_text': '메모를 추가할 주문서를 선택하세요'
            },
            'memo': {
                'required': True,
                'allow_blank': False,
                'max_length': 2000,
                'help_text': '주문 처리 관련 메모를 입력하세요'
            }
        }
    
    def validate_memo(self, value):
        """메모 내용 검증"""
        if not value or not value.strip():
            raise serializers.ValidationError("메모 내용은 필수 입력 사항입니다.")
        
        if len(value.strip()) > 2000:
            raise serializers.ValidationError("메모는 2000자를 초과할 수 없습니다.")
        
        return value.strip()
    
    def create(self, validated_data):
        """주문 메모 생성"""
        try:
            memo = OrderMemo.objects.create(**validated_data)
            logger.info(f"주문 메모 생성 성공: {memo.order.customer_name}")
            return memo
        except Exception as e:
            logger.error(f"주문 메모 생성 실패: {str(e)} - 데이터: {validated_data}")
            raise serializers.ValidationError("메모 생성 중 오류가 발생했습니다.")


class InvoiceSerializer(serializers.ModelSerializer):
    """
    송장 정보 관리를 위한 시리얼라이저
    배송 처리 및 송장 추적 기능 제공
    """
    
    # 읽기 전용 필드들
    id = serializers.UUIDField(read_only=True)
    sent_at = serializers.DateTimeField(read_only=True, format='%Y-%m-%d %H:%M:%S')
    delivered_at = serializers.DateTimeField(read_only=True, format='%Y-%m-%d %H:%M:%S')
    
    # 관계 필드들
    courier_display = serializers.CharField(source='get_courier_display', read_only=True)
    order_customer_name = serializers.CharField(source='order.customer_name', read_only=True)
    
    # 계산된 필드들
    is_delivered = serializers.SerializerMethodField()
    delivery_status = serializers.SerializerMethodField()
    delivery_duration = serializers.SerializerMethodField()
    
    class Meta:
        model = Invoice
        fields = [
            'id', 'order', 'order_customer_name', 'courier', 'courier_display',
            'invoice_number', 'recipient_name', 'recipient_phone',
            'sent_at', 'delivered_at', 'is_delivered', 'delivery_status',
            'delivery_duration'
        ]
        extra_kwargs = {
            'order': {
                'required': True,
                'help_text': '송장을 등록할 주문서를 선택하세요'
            },
            'invoice_number': {
                'required': True,
                'allow_blank': False,
                'max_length': 100,
                'help_text': '택배사 송장 추적 번호를 입력하세요'
            }
        }
    
    def get_is_delivered(self, obj):
        """배송 완료 여부 반환"""
        try:
            return obj.is_delivered()
        except Exception as e:
            logger.warning(f"배송 완료 여부 확인 중 오류: {str(e)}")
            return False
    
    def get_delivery_status(self, obj):
        """배송 상태 텍스트 반환"""
        try:
            return obj.get_delivery_status()
        except Exception as e:
            logger.warning(f"배송 상태 조회 중 오류: {str(e)}")
            return "알 수 없음"
    
    def get_delivery_duration(self, obj):
        """배송 소요 시간 반환 (일 단위)"""
        try:
            if obj.is_delivered():
                duration = obj.delivered_at - obj.sent_at
                return duration.days
            return None
        except Exception as e:
            logger.warning(f"배송 소요 시간 계산 중 오류: {str(e)}")
            return None
    
    def validate_invoice_number(self, value):
        """송장 번호 검증"""
        if not value or not value.strip():
            raise serializers.ValidationError("송장 번호는 필수 입력 사항입니다.")
        
        # 송장 번호 형식 검증 (숫자와 하이픈만 허용)
        cleaned_number = value.strip().replace('-', '').replace(' ', '')
        if not cleaned_number.isdigit():
            raise serializers.ValidationError("송장 번호는 숫자만 입력 가능합니다.")
        
        return value.strip()
    
    def validate_order(self, value):
        """주문서 검증"""
        # 이미 송장이 등록된 주문인지 확인
        if hasattr(value, 'invoice') and value.invoice and self.instance != value.invoice:
            logger.warning(f"이미 송장이 등록된 주문에 송장 재등록 시도: {value.customer_name}")
            raise serializers.ValidationError("이미 송장이 등록된 주문입니다.")
        
        # 완료되지 않은 주문에 송장 등록 시 경고
        if value.status not in ['processing', 'completed']:
            logger.warning(f"미완료 주문에 송장 등록: {value.customer_name} (상태: {value.status})")
        
        return value
    
    def validate(self, data):
        """전체 데이터 검증"""
        courier = data.get('courier')
        invoice_number = data.get('invoice_number')
        
        if courier and invoice_number:
            # 동일 택배사에서 중복 송장번호 검사
            queryset = Invoice.objects.filter(courier=courier, invoice_number=invoice_number)
            if self.instance:
                queryset = queryset.exclude(id=self.instance.id)
            
            if queryset.exists():
                logger.warning(f"중복 송장 번호 등록 시도: {courier} - {invoice_number}")
                raise serializers.ValidationError({
                    'invoice_number': '동일한 택배사에서 중복된 송장 번호가 존재합니다.'
                })
        
        return data
    
    def create(self, validated_data):
        """송장 생성"""
        try:
            invoice = Invoice.objects.create(**validated_data)
            logger.info(f"송장 생성 성공: {invoice.order.customer_name} - {invoice.courier} ({invoice.invoice_number})")
            return invoice
        except Exception as e:
            logger.error(f"송장 생성 실패: {str(e)} - 데이터: {validated_data}")
            raise serializers.ValidationError("송장 생성 중 오류가 발생했습니다.")
    
    def update(self, instance, validated_data):
        """송장 정보 수정"""
        try:
            old_invoice_number = instance.invoice_number
            
            for attr, value in validated_data.items():
                setattr(instance, attr, value)
            
            instance.save()
            
            logger.info(f"송장 정보 수정 성공: {instance.order.customer_name} - {old_invoice_number} -> {instance.invoice_number}")
            return instance
        
        except Exception as e:
            logger.error(f"송장 정보 수정 실패: {str(e)} - 송장: {instance.invoice_number}")
            raise serializers.ValidationError("송장 정보 수정 중 오류가 발생했습니다.")


class OrderStatusUpdateSerializer(serializers.Serializer):
    """
    주문 상태 업데이트를 위한 시리얼라이저
    주문 상태를 안전하게 변경하는 기능
    """
    
    order_id = serializers.UUIDField(
        required=True,
        help_text="상태를 변경할 주문 ID"
    )
    
    new_status = serializers.ChoiceField(
        choices=Order.STATUS_CHOICES,
        required=True,
        help_text="변경할 새로운 상태"
    )
    
    memo = serializers.CharField(
        max_length=500,
        required=False,
        allow_blank=True,
        help_text="상태 변경 사유 (선택사항)"
    )
    
    def validate_order_id(self, value):
        """주문 ID 검증"""
        try:
            order = Order.objects.get(id=value)
            return value
        except Order.DoesNotExist:
            logger.warning(f"존재하지 않는 주문 ID로 상태 변경 시도: {value}")
            raise serializers.ValidationError("해당 주문을 찾을 수 없습니다.")


class OrderBulkStatusUpdateSerializer(serializers.Serializer):
    """
    주문 일괄 상태 업데이트를 위한 시리얼라이저
    여러 주문의 상태를 동시에 변경하는 기능
    """
    
    order_ids = serializers.ListField(
        child=serializers.UUIDField(),
        min_length=1,
        help_text="상태를 변경할 주문 ID 목록"
    )
    
    new_status = serializers.ChoiceField(
        choices=Order.STATUS_CHOICES,
        required=True,
        help_text="변경할 새로운 상태"
    )
    
    def validate_order_ids(self, value):
        """주문 ID 목록 검증"""
        if not value:
            raise serializers.ValidationError("상태를 변경할 주문을 선택해주세요.")
        
        # 존재하는 주문 ID인지 확인
        existing_orders = Order.objects.filter(id__in=value)
        existing_ids = set(str(order.id) for order in existing_orders)
        provided_ids = set(str(id) for id in value)
        
        if len(existing_ids) != len(provided_ids):
            invalid_ids = provided_ids - existing_ids
            logger.warning(f"존재하지 않는 주문 ID로 일괄 상태 변경 시도: {invalid_ids}")
            raise serializers.ValidationError("일부 주문 ID가 존재하지 않습니다.")
        
        return value


class OrderBulkDeleteSerializer(serializers.Serializer):
    """
    주문 일괄 삭제를 위한 시리얼라이저
    여러 주문을 선택하여 동시에 삭제하는 기능
    """
    
    order_ids = serializers.ListField(
        child=serializers.UUIDField(),
        min_length=1,
        help_text="삭제할 주문 ID 목록"
    )
    
    force_delete = serializers.BooleanField(
        default=False,
        help_text="완료된 주문도 강제로 삭제할지 여부"
    )
    
    def validate_order_ids(self, value):
        """주문 ID 목록 검증"""
        if not value:
            raise serializers.ValidationError("삭제할 주문을 선택해주세요.")
        
        # 존재하는 주문 ID인지 확인
        existing_orders = Order.objects.filter(id__in=value)
        existing_ids = set(str(order.id) for order in existing_orders)
        provided_ids = set(str(id) for id in value)
        
        if existing_ids != provided_ids:
            invalid_ids = provided_ids - existing_ids
            logger.warning(f"존재하지 않는 주문 ID로 삭제 시도: {invalid_ids}")
            raise serializers.ValidationError("일부 주문 ID가 존재하지 않습니다.")
        
        return value