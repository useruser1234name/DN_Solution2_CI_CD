# companies/views.py
import logging
from django.db import models
from django.shortcuts import render
from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

from .models import Company, CompanyUser, CompanyMessage
from .serializers import (
    CompanySerializer, CompanyUserSerializer, CompanyMessageSerializer,
    CompanyBulkDeleteSerializer, CompanyStatusToggleSerializer
)

def model_test_ui(request):
    """모델 테스트를 위한 UI 페이지 뷰"""
    if request.method == 'POST':
        form_type = request.POST.get('form_type')
        try:
            if form_type == 'create_company':
                name = request.POST.get('name')
                company_type = request.POST.get('type')
                parent_id = request.POST.get('parent_company')
                parent_company = Company.objects.get(id=parent_id) if parent_id else None
                Company.objects.create(name=name, type=company_type, parent_company=parent_company)
            elif form_type == 'create_user':
                company_id = request.POST.get('company')
                username = request.POST.get('username')
                password = request.POST.get('password')
                role = request.POST.get('role')
                company = Company.objects.get(id=company_id)
                CompanyUser.objects.create(company=company, username=username, password=password, role=role)
        except Exception as e:
            logger.error(f"모델 테스트 UI 오류: {e}")

    companies = Company.objects.all().order_by('name')
    users = CompanyUser.objects.all().order_by('username')
    return render(request, 'companies/model_test.html', {'companies': companies, 'users': users})

logger = logging.getLogger('companies')


class CompanyViewSet(viewsets.ModelViewSet):
    """
    `Company` 모델에 대한 CRUD(Create, Retrieve, Update, Delete) 작업을 제공하는 ViewSet입니다.
    업체 관리와 관련된 추가적인 기능(일괄 삭제, 상태 토글, 사용자 목록 조회)을 포함합니다.
    
    **주요 책임:**
    1.  업체 데이터의 API 노출 및 관리.
    2.  사용자 역할에 따른 업체 목록 필터링 및 접근 제어.
    3.  업체 생성, 수정, 삭제 시 비즈니스 로직 및 유효성 검증 연동.
    4.  각 작업에 대한 상세 로깅.
    """
    
    queryset = Company.objects.all()
    serializer_class = CompanySerializer
    permission_classes = [IsAuthenticated] # 인증된 사용자만 접근 허용
    
    # 필터링, 검색, 정렬 설정: DRF의 내장 기능을 활용하여 API의 유연성을 높입니다.
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['type', 'status', 'visible'] # 특정 필드로 필터링 가능
    search_fields = ['name', 'default_courier'] # 이름 또는 택배사로 검색 가능
    ordering_fields = ['name', 'created_at', 'updated_at'] # 특정 필드로 정렬 가능
    ordering = ['-created_at'] # 기본 정렬 기준 (업체명 오름차순)
    
    def get_queryset(self):
        """
        현재 요청을 보낸 사용자의 권한에 따라 조회 가능한 업체(Company) 목록을 필터링하여 반환합니다.
        이는 객체 레벨 권한 제어의 핵심 로직입니다.
        
        **흐름:**
        1.  슈퍼유저는 모든 업체를 조회할 수 있습니다.
        2.  본사(headquarters) 소속 사용자는 모든 업체를 조회할 수 있습니다.
        3.  협력사(agency) 소속 사용자는 자신의 업체와 자신이 상위 업체인 판매점(retail)을 조회할 수 있습니다.
        4.  판매점(retail) 소속 사용자는 자신의 업체만 조회할 수 있습니다.
        5.  그 외 소속이 없거나 권한이 없는 사용자는 빈 쿼리셋을 반환합니다.
        """
        user = self.request.user
        logger.info(f"[CompanyViewSet.get_queryset] 업체 목록 조회 요청 시작 - 사용자: {user.username}")

        # 1. 슈퍼유저는 모든 업체 조회 가능
        if user.is_superuser:
            logger.info(f"[CompanyViewSet.get_queryset] 슈퍼유저({user.username}) - 모든 업체 조회 권한 부여.")
            queryset = Company.objects.all()
        else:
            try:
                # 2. CompanyUser 모델을 통해 사용자의 소속 업체 정보 조회
                # Django User와 CompanyUser 간의 명시적인 1:1 관계가 없으므로 username으로 조회
                company_user = CompanyUser.objects.get(username=user.username)
                current_company = company_user.company # 로그인한 사용자가 속한 업체
                logger.info(f"[CompanyViewSet.get_queryset] 일반 사용자({user.username}) - 소속 업체: {current_company.name} ({current_company.type})")
                
                # 3. 소속 업체의 유형에 따라 쿼리셋 필터링
                if current_company.type == 'headquarters':
                    # 본사 관리자는 모든 업체 조회 가능
                    logger.info(f"[CompanyViewSet.get_queryset] 본사 관리자({user.username}) - 모든 업체 조회 권한 부여.")
                    queryset = Company.objects.all()
                elif current_company.type == 'agency':
                    # 협력사 관리자는 자신의 업체와 하위 판매점 목록 조회
                    # Q 객체를 사용하여 OR 조건으로 필터링합니다.
                    logger.info(f"[CompanyViewSet.get_queryset] 협력사 관리자({user.username}) - 자신의 업체 및 하위 판매점 조회 권한 부여.")
                    queryset = Company.objects.filter(models.Q(id=current_company.id) | models.Q(parent_company=current_company))
                elif current_company.type == 'retail':
                    # 판매점 직원은 자신의 업체 정보만 조회
                    logger.info(f"[CompanyViewSet.get_queryset] 판매점 직원({user.username}) - 자신의 업체만 조회 권한 부여.")
                    queryset = Company.objects.filter(id=current_company.id)
                else:
                    # 정의되지 않은 유형의 업체는 빈 쿼리셋 반환
                    logger.warning(f"[CompanyViewSet.get_queryset] 알 수 없는 업체 유형({current_company.type})의 사용자({user.username}) - 빈 쿼리셋 반환.")
                    queryset = Company.objects.none()
            except CompanyUser.DoesNotExist:
                # CompanyUser에 매핑되지 않은 Django User는 빈 쿼리셋 반환
                logger.warning(f"[CompanyViewSet.get_queryset] CompanyUser에 매핑되지 않은 사용자({user.username}) - 빈 쿼리셋 반환.")
                queryset = Company.objects.none()
            except Exception as e:
                # 예상치 못한 오류 발생 시 로깅
                logger.error(f"[CompanyViewSet.get_queryset] 쿼리셋 생성 중 예상치 못한 오류 발생 - 사용자: {user.username}, 오류: {str(e)}", exc_info=True)
                queryset = Company.objects.none() # 안전하게 빈 쿼리셋 반환

        # N+1 쿼리 문제 방지를 위해 관련 사용자 및 하위 업체 정보를 미리 로드합니다.
        return queryset.prefetch_related('users', 'child_companies')

    def create(self, request, *args, **kwargs):
        """
        새로운 업체를 생성합니다.
        본사 계정의 판매점 직접 생성 금지 정책을 포함합니다.
        """
        user = self.request.user
        logger.info(f"[CompanyViewSet.create] 업체 생성 요청 시작 - 사용자: {user.username}, 요청 데이터: {request.data}")
        
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True) # 유효성 검증 실패 시 400 Bad Request 자동 반환
            
            # --- 비즈니스 규칙 강화: 본사 계정의 판매점 직접 생성 금지 ---
            # 슈퍼유저 또는 본사 소속 사용자가 판매점 생성을 시도하는 경우를 검증합니다.
            is_headquarters_user = user.is_superuser or \
                                   (hasattr(user, 'companyuser') and user.companyuser.company.type == 'headquarters')
            
            if is_headquarters_user and serializer.validated_data.get('type') == 'retail':
                logger.warning(f"[CompanyViewSet.create] 본사 계정({user.username})이 판매점 직접 생성을 시도했습니다. 요청 데이터: {request.data}")
                return Response(
                    {"error": "본사 계정은 판매점을 직접 생성할 수 없습니다. 협력사를 통해 생성해주세요."},
                    status=status.HTTP_403_FORBIDDEN # 403 Forbidden: 권한 없음
                )

            # --- 협력사 관리자가 판매점을 생성하는 경우, parent_company 자동 할당 ---
            # 이 로직은 협력사 사용자가 자신의 하위에 판매점을 쉽게 생성할 수 있도록 돕습니다.
            if hasattr(user, 'companyuser') and user.companyuser.company.type == 'agency':
                if serializer.validated_data.get('type') == 'retail':
                    # 요청 데이터에 parent_company가 없거나 잘못된 경우 자동 할당
                    if not serializer.validated_data.get('parent_company'):
                        serializer.validated_data['parent_company'] = user.companyuser.company
                        logger.info(f"[CompanyViewSet.create] 협력사({user.companyuser.company.name})가 판매점 생성 시 상위 업체 자동 할당.")
                    elif serializer.validated_data['parent_company'] != user.companyuser.company:
                        # 협력사가 다른 상위 업체를 지정하려 할 경우 경고 및 오류
                        logger.warning(f"[CompanyViewSet.create] 협력사({user.companyuser.company.name})가 판매점 생성 시 다른 상위 업체({serializer.validated_data['parent_company'].name}) 지정 시도.")
                        return Response(
                            {"error": "협력사는 자신의 하위에만 판매점을 생성할 수 있습니다."},
                            status=status.HTTP_400_BAD_REQUEST
                        )

            with transaction.atomic(): # 데이터 일관성을 위한 트랜잭션 시작
                company = serializer.save() # 시리얼라이저의 create 메서드 호출
            
            logger.info(f"[CompanyViewSet.create] 업체 생성 성공. Name: '{company.name}', Type: '{company.type}', ID: {company.id}")
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        
        except serializers.ValidationError as e:
            # 시리얼라이저 유효성 검증 오류는 이미 is_valid(raise_exception=True)에서 처리되지만,
            # 명시적인 로깅을 위해 추가합니다.
            logger.warning(f"[CompanyViewSet.create] 업체 생성 요청 유효성 검증 실패: {e.detail} - 사용자: {user.username}, 데이터: {request.data}")
            raise # DRF가 자동으로 400 응답을 생성하도록 다시 발생시킵니다.
        except Exception as e:
            # 예상치 못한 서버 내부 오류 처리
            logger.error(f"[CompanyViewSet.create] 업체 생성 중 예상치 못한 오류 발생 - 사용자: {user.username}, 데이터: {request.data}, 오류: {str(e)}", exc_info=True)
            return Response(
                {"error": "업체 생성 중 서버 내부 오류가 발생했습니다. 관리자에게 문의해주세요."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def update(self, request, *args, **kwargs):
        """
        기존 업체의 정보를 수정합니다.
        부분 업데이트(PATCH)와 전체 업데이트(PUT)를 모두 지원합니다.
        """
        instance = self.get_object() # URL에서 pk를 통해 대상 객체를 가져옵니다.
        user = self.request.user
        logger.info(f"[CompanyViewSet.update] 업체 정보 수정 요청 시작 - 사용자: {user.username}, 대상 업체: '{instance.name}' (ID: {instance.id}), 요청 데이터: {request.data}")
        
        try:
            # partial=True는 PATCH 요청 시 부분 업데이트를 허용합니다.
            serializer = self.get_serializer(instance, data=request.data, partial=kwargs.get('partial', False))
            serializer.is_valid(raise_exception=True) # 유효성 검증 실패 시 400 Bad Request 자동 반환
            
            with transaction.atomic(): # 데이터 일관성을 위한 트랜잭션 시작
                company = serializer.save() # 시리얼라이저의 update 메서드 호출
            
            logger.info(f"[CompanyViewSet.update] 업체 정보 수정 성공. Name: '{company.name}' (ID: {company.id})")
            return Response(serializer.data)
        
        except serializers.ValidationError as e:
            logger.warning(f"[CompanyViewSet.update] 업체 정보 수정 요청 유효성 검증 실패: {e.detail} - 사용자: {user.username}, 대상: {instance.name}, 데이터: {request.data}")
            raise
        except Exception as e:
            logger.error(f"[CompanyViewSet.update] 업체 정보 수정 중 예상치 못한 오류 발생 - 사용자: {user.username}, 대상: {instance.name}, 오류: {str(e)}", exc_info=True)
            return Response(
                {"error": "업체 정보 수정 중 서버 내부 오류가 발생했습니다. 관리자에게 문의해주세요."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def destroy(self, request, *args, **kwargs):
        """
        특정 업체를 삭제합니다.
        연관된 사용자(CompanyUser)가 있는 업체는 삭제를 허용하지 않습니다.
        """
        instance = self.get_object() # URL에서 pk를 통해 대상 객체를 가져옵니다.
        user = self.request.user
        logger.info(f"[CompanyViewSet.destroy] 업체 삭제 요청 시작 - 사용자: {user.username}, 대상 업체: '{instance.name}' (ID: {instance.id})")
        
        try:
            # 1. 연관된 사용자(CompanyUser)가 있는지 확인
            users_count = instance.users.count()
            if users_count > 0:
                logger.warning(f"[CompanyViewSet.destroy] 사용자가 있는 업체 삭제 시도 거부. 업체: '{instance.name}' (ID: {instance.id}), 사용자 수: {users_count}")
                return Response(
                    {"error": f"이 업체에는 {users_count}명의 사용자가 있습니다. 먼저 모든 사용자를 삭제해야 합니다."},
                    status=status.HTTP_400_BAD_REQUEST # 400 Bad Request: 잘못된 요청
                )
            
            # 2. 연관된 메시지(CompanyMessage)가 있는지 확인 (선택 사항, 비즈니스 규칙에 따라)
            # messages_count = instance.messages.count()
            # if messages_count > 0:
            #     logger.warning(f"[CompanyViewSet.destroy] 메시지가 있는 업체 삭제 시도 거부. 업체: '{instance.name}' (ID: {instance.id}), 메시지 수: {messages_count}")
            #     return Response(
            #         {"error": f"이 업체에는 {messages_count}개의 메시지가 있습니다. 먼저 모든 메시지를 삭제해야 합니다."},
            #         status=status.HTTP_400_BAD_REQUEST
            #     )

            with transaction.atomic(): # 데이터 일관성을 위한 트랜잭션 시작
                instance.delete() # 모델의 delete 메서드 호출
            
            logger.info(f"[CompanyViewSet.destroy] 업체 삭제 성공. Name: '{instance.name}' (ID: {instance.id})")
            return Response(status=status.HTTP_204_NO_CONTENT) # 204 No Content: 성공적으로 삭제되었으나 반환할 내용 없음
        
        except Exception as e:
            logger.error(f"[CompanyViewSet.destroy] 업체 삭제 중 예상치 못한 오류 발생 - 사용자: {user.username}, 대상: {instance.name}, 오류: {str(e)}", exc_info=True)
            return Response(
                {"error": "업체 삭제 중 서버 내부 오류가 발생했습니다. 관리자에게 문의해주세요."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['post'])
    def bulk_delete(self, request):
        """
        여러 업체를 동시에 삭제합니다.
        요청 본문에 `company_ids` 리스트를 포함해야 합니다.
        """
        user = self.request.user
        logger.info(f"[CompanyViewSet.bulk_delete] 업체 일괄 삭제 요청 시작 - 사용자: {user.username}, 요청 데이터: {request.data}")
        
        serializer = CompanyBulkDeleteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True) # 유효성 검증 실패 시 400 Bad Request 자동 반환
        
        company_ids_to_delete = serializer.validated_data['company_ids']
        
        deleted_companies_info = []
        failed_companies_info = []

        try:
            with transaction.atomic(): # 데이터 일관성을 위한 트랜잭션 시작
                # 삭제 대상 업체들을 미리 조회하여 반복문 내에서 쿼리 발생 최소화
                companies_to_process = Company.objects.filter(id__in=company_ids_to_delete)
                
                for company in companies_to_process:
                    try:
                        # 연관된 사용자(CompanyUser)가 있는지 확인
                        if company.users.exists():
                            logger.warning(f"[CompanyViewSet.bulk_delete] 일괄 삭제 중 업체('{company.name}', ID: {company.id})에 사용자가 있어 삭제 건너뜀.")
                            failed_companies_info.append({
                                'id': str(company.id),
                                'name': company.name,
                                'reason': '연관된 사용자가 존재합니다.'
                            })
                            continue
                        
                        company.delete() # 개별 업체 삭제 (모델의 delete 메서드 호출)
                        logger.info(f"[CompanyViewSet.bulk_delete] 업체('{company.name}', ID: {company.id}) 성공적으로 삭제됨.")
                        deleted_companies_info.append({
                            'id': str(company.id),
                            'name': company.name
                        })
                    
                    except Exception as e:
                        # 개별 업체 삭제 중 발생한 예상치 못한 오류
                        logger.error(f"[CompanyViewSet.bulk_delete] 일괄 삭제 중 개별 업체('{company.name}', ID: {company.id}) 삭제 실패: {str(e)}", exc_info=True)
                        failed_companies_info.append({
                            'id': str(company.id),
                            'name': company.name,
                            'reason': f'삭제 중 오류 발생: {str(e)}'
                        })
                
            logger.info(f"[CompanyViewSet.bulk_delete] 업체 일괄 삭제 완료 - 성공: {len(deleted_companies_info)}개, 실패: {len(failed_companies_info)}개.")
            
            return Response({
                'message': f'{len(deleted_companies_info)}개 업체가 성공적으로 삭제되었습니다.',
                'deleted': deleted_companies_info,
                'failed': failed_companies_info
            }, status=status.HTTP_200_OK)
        
        except Exception as e:
            # 트랜잭션 전체에서 발생한 예상치 못한 오류
            logger.critical(f"[CompanyViewSet.bulk_delete] 업체 일괄 삭제 중 치명적인 오류 발생 - 사용자: {user.username}, 요청 데이터: {request.data}, 오류: {str(e)}", exc_info=True)
            return Response(
                {"error": "업체 일괄 삭제 중 서버 내부 오류가 발생했습니다. 관리자에게 문의해주세요."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'])
    def toggle_status(self, request, pk=None):
        """
        특정 업체의 운영 상태(status)를 토글(True <-> False)합니다.
        """
        company_instance = self.get_object() # URL에서 pk를 통해 대상 객체를 가져옵니다.
        user = self.request.user
        logger.info(f"[CompanyViewSet.toggle_status] 업체 상태 전환 요청 시작 - 사용자: {user.username}, 대상 업체: '{company_instance.name}' (ID: {company_instance.id}), 현재 상태: {company_instance.status}")
        
        try:
            # 모델의 toggle_status 메서드를 호출하여 상태 변경 및 저장, 로깅을 일임합니다.
            success = company_instance.toggle_status()
            
            if success:
                current_status_text = "운영중" if company_instance.status else "중단"
                logger.info(f"[CompanyViewSet.toggle_status] 업체 상태 전환 성공. 업체: '{company_instance.name}' (ID: {company_instance.id}), 새 상태: {current_status_text}")
                
                return Response({
                    'message': f'{company_instance.name}의 운영 상태가 {current_status_text}으로 변경되었습니다.',
                    'company_id': str(company_instance.id),
                    'new_status': company_instance.status
                }, status=status.HTTP_200_OK)
            else:
                # toggle_status 메서드 내부에서 오류가 발생하여 False를 반환한 경우
                logger.error(f"[CompanyViewSet.toggle_status] 업체 상태 전환 실패 (모델 내부 오류). 업체: '{company_instance.name}' (ID: {company_instance.id})")
                return Response(
                    {"error": "업체 상태 전환 중 오류가 발생했습니다."},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        
        except Exception as e:
            # 예상치 못한 서버 내부 오류 처리
            logger.error(f"[CompanyViewSet.toggle_status] 업체 상태 전환 중 예상치 못한 오류 발생 - 사용자: {user.username}, 대상: {company_instance.name}, 오류: {str(e)}", exc_info=True)
            return Response(
                {"error": "업체 상태 전환 중 서버 내부 오류가 발생했습니다. 관리자에게 문의해주세요."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['get'])
    def users(self, request, pk=None):
        """
        특정 업체의 사용자 목록을 조회합니다.
        협력사(agency)의 경우, 자신에게 직접 속한 사용자와 하위 판매점(retail)에 속한 사용자들을 모두 반환합니다.
        """
        company_instance = self.get_object() # URL에서 pk를 통해 대상 객체를 가져옵니다.
        user = self.request.user
        logger.info(f"[CompanyViewSet.users] 업체 사용자 목록 조회 요청 시작 - 사용자: {user.username}, 대상 업체: '{company_instance.name}' (ID: {company_instance.id})")
        
        try:
            # 1. 대상 업체에 직접 속한 사용자들을 가져옵니다.
            users_queryset = company_instance.users.all()
            
            # 2. 대상 업체가 협력사(agency)인 경우, 하위 판매점의 사용자들도 포함합니다.
            if company_instance.type == 'agency':
                logger.info(f"[CompanyViewSet.users] 협력사({company_instance.name})의 하위 판매점 사용자 포함 조회.")
                retail_companies = company_instance.child_companies.filter(type='retail')
                for retail_company in retail_companies:
                    users_queryset |= retail_company.users.all() # QuerySet 합집합 연산
            
            # 3. 최종 사용자 목록을 정렬하고 직렬화합니다.
            users_queryset = users_queryset.order_by('-created_at')
            serializer = CompanyUserSerializer(users_queryset, many=True)
            
            logger.info(f"[CompanyViewSet.users] 업체 사용자 목록 조회 성공. 업체: '{company_instance.name}', 사용자 수: {users_queryset.count()}")
            return Response({
                'company_id': str(company_instance.id),
                'company_name': company_instance.name,
                'users': serializer.data
            })
        
        except Exception as e:
            logger.error(f"[CompanyViewSet.users] 업체 사용자 목록 조회 중 예상치 못한 오류 발생 - 사용자: {user.username}, 대상: {company_instance.name}, 오류: {str(e)}", exc_info=True)
            return Response(
                {"error": "사용자 목록 조회 중 서버 내부 오류가 발생했습니다. 관리자에게 문의해주세요."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class CompanyUserViewSet(viewsets.ModelViewSet):
    """
    `CompanyUser` 모델에 대한 CRUD 작업을 제공하는 ViewSet입니다.
    업체별 사용자 계정의 생성, 조회, 수정, 삭제를 관리합니다.
    
    **주요 책임:**
    1.  업체 사용자 데이터의 API 노출 및 관리.
    2.  사용자 생성 시 비밀번호 처리 및 소속 업체 유효성 검증.
    3.  각 작업에 대한 상세 로깅.
    """
    
    queryset = CompanyUser.objects.all()
    serializer_class = CompanyUserSerializer
    permission_classes = [IsAuthenticated] # 인증된 사용자만 접근 허용
    
    # 필터링, 검색, 정렬 설정
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['company', 'role'] # 소속 업체 또는 역할로 필터링 가능
    search_fields = ['username', 'company__name'] # 사용자명 또는 소속 업체명으로 검색 가능
    ordering_fields = ['username', 'created_at', 'last_login'] # 특정 필드로 정렬 가능
    ordering = ['-created_at'] # 기본 정렬 기준 (사용자명 오름차순)
    
    def get_queryset(self):
        """
        `CompanyUser` 목록을 조회합니다.
        N+1 쿼리 문제 방지를 위해 `company` 정보를 미리 로드합니다.
        """
        queryset = super().get_queryset()
        queryset = queryset.select_related('company') # `company` 필드를 미리 로드
        
        user = self.request.user
        logger.info(f"[CompanyUserViewSet.get_queryset] 업체 사용자 목록 조회 요청 시작 - 사용자: {user.username}")
        return queryset
    
    def create(self, request, *args, **kwargs):
        """
        새로운 업체 사용자를 생성합니다.
        """
        user = self.request.user
        logger.info(f"[CompanyUserViewSet.create] 업체 사용자 생성 요청 시작 - 관리자: {user.username}, 요청 데이터: {request.data}")
        
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True) # 유효성 검증 실패 시 400 Bad Request 자동 반환
            
            with transaction.atomic(): # 데이터 일관성을 위한 트랜잭션 시작
                company_user = serializer.save() # 시리얼라이저의 create 메서드 호출
            
            logger.info(f"[CompanyUserViewSet.create] 업체 사용자 생성 성공. Username: '{company_user.username}', Company: '{company_user.company.name}', ID: {company_user.id}")
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        
        except serializers.ValidationError as e:
            logger.warning(f"[CompanyUserViewSet.create] 업체 사용자 생성 요청 유효성 검증 실패: {e.detail} - 관리자: {user.username}, 데이터: {request.data}")
            raise
        except Exception as e:
            logger.error(f"[CompanyUserViewSet.create] 업체 사용자 생성 중 예상치 못한 오류 발생 - 관리자: {user.username}, 데이터: {request.data}, 오류: {str(e)}", exc_info=True)
            return Response(
                {"error": "사용자 생성 중 서버 내부 오류가 발생했습니다. 관리자에게 문의해주세요."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def destroy(self, request, *args, **kwargs):
        """
        특정 업체 사용자를 삭제합니다.
        """
        instance = self.get_object() # URL에서 pk를 통해 대상 객체를 가져옵니다.
        user = self.request.user
        logger.info(f"[CompanyUserViewSet.destroy] 업체 사용자 삭제 요청 시작 - 사용자: {user.username}, 대상 사용자: '{instance.username}' (ID: {instance.id})")
        
        try:
            username_to_log = instance.username
            company_name_to_log = instance.company.name

            with transaction.atomic(): # 데이터 일관성을 위한 트랜잭션 시작
                instance.delete() # 모델의 delete 메서드 호출
            
            logger.info(f"[CompanyUserViewSet.destroy] 업체 사용자 삭제 성공. Username: '{username_to_log}', Company: '{company_name_to_log}', ID: {instance.id}")
            return Response(status=status.HTTP_204_NO_CONTENT)
        
        except Exception as e:
            logger.error(f"[CompanyUserViewSet.destroy] 업체 사용자 삭제 중 예상치 못한 오류 발생 - 사용자: {user.username}, 대상: {instance.username}, 오류: {str(e)}", exc_info=True)
            return Response(
                {"error": "사용자 삭제 중 서버 내부 오류가 발생했습니다. 관리자에게 문의해주세요."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class CompanyMessageViewSet(viewsets.ModelViewSet):
    """
    `CompanyMessage` 모델에 대한 CRUD 작업을 제공하는 ViewSet입니다.
    업체에 발송되는 메시지의 생성, 조회, 수정, 삭제를 관리합니다.
    
    **주요 책임:**
    1.  업체 메시지 데이터의 API 노출 및 관리.
    2.  메시지 발송 시 발송자 자동 설정 및 일괄/개별 발송 로직 처리.
    3.  각 작업에 대한 상세 로깅.
    """
    
    queryset = CompanyMessage.objects.all()
    serializer_class = CompanyMessageSerializer
    permission_classes = [IsAuthenticated] # 인증된 사용자만 접근 허용
    
    # 필터링, 검색, 정렬 설정
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['is_bulk', 'company', 'sent_by'] # 일괄 발송 여부, 업체, 발송자로 필터링 가능
    search_fields = ['message', 'company__name'] # 메시지 내용 또는 업체명으로 검색 가능
    ordering_fields = ['sent_at'] # 발송 일시로 정렬 가능
    ordering = ['-sent_at'] # 기본 정렬 기준 (발송 일시 오름차순)
    
    def get_queryset(self):
        """
        `CompanyMessage` 목록을 조회합니다.
        N+1 쿼리 문제 방지를 위해 `company` 및 `sent_by` 정보를 미리 로드합니다.
        """
        queryset = super().get_queryset()
        queryset = queryset.select_related('company', 'sent_by') # `company`와 `sent_by` 필드를 미리 로드
        
        user = self.request.user
        logger.info(f"[CompanyMessageViewSet.get_queryset] 업체 메시지 목록 조회 요청 시작 - 사용자: {user.username}")
        return queryset
    
    def create(self, request, *args, **kwargs):
        """
        새로운 업체 메시지를 생성하고 발송합니다.
        발송자(`sent_by`)는 현재 요청을 보낸 사용자로 자동 설정됩니다.
        """
        user = self.request.user
        logger.info(f"[CompanyMessageViewSet.create] 업체 메시지 발송 요청 시작 - 발송자: {user.username}, 요청 데이터: {request.data}")
        
        try:
            # 요청 데이터 복사 및 발송자 정보 자동 설정
            mutable_data = request.data.copy()
            mutable_data['sent_by'] = user.id # 현재 로그인한 사용자의 ID를 발송자로 설정
            
            serializer = self.get_serializer(data=mutable_data)
            serializer.is_valid(raise_exception=True) # 유효성 검증 실패 시 400 Bad Request 자동 반환
            
            with transaction.atomic(): # 데이터 일관성을 위한 트랜잭션 시작
                message = serializer.save() # 시리얼라이저의 create 메서드 호출
            
            message_type = "일괄" if message.is_bulk else "개별"
            target_info = "전체 업체" if message.is_bulk else message.company.name
            
            logger.info(f"[CompanyMessageViewSet.create] 업체 메시지 발송 성공. 유형: {message_type}, 대상: {target_info}, 메시지: '{message.message[:50]}...', ID: {message.id}")
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        
        except serializers.ValidationError as e:
            logger.warning(f"[CompanyMessageViewSet.create] 업체 메시지 발송 요청 유효성 검증 실패: {e.detail} - 발송자: {user.username}, 데이터: {request.data}")
            raise
        except Exception as e:
            logger.error(f"[CompanyMessageViewSet.create] 업체 메시지 발송 중 예상치 못한 오류 발생 - 발송자: {user.username}, 데이터: {request.data}, 오류: {str(e)}", exc_info=True)
            return Response(
                {"error": "메시지 발송 중 서버 내부 오류가 발생했습니다. 관리자에게 문의해주세요."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['post'])
    def send_bulk_message(self, request):
        """
        전체 활성화된 업체에 일괄 메시지를 발송합니다.
        요청 본문에 `message` 내용을 포함해야 합니다.
        """
        user = self.request.user
        logger.info(f"[CompanyMessageViewSet.send_bulk_message] 일괄 메시지 발송 요청 시작 - 발송자: {user.username}, 요청 데이터: {request.data}")
        
        try:
            # 일괄 발송 플래그 설정 및 발송자 정보 자동 설정
            mutable_data = request.data.copy()
            mutable_data['is_bulk'] = True
            mutable_data['sent_by'] = user.id
            mutable_data.pop('company', None)  # 일괄 발송 시 `company` 필드는 필요 없으므로 제거
            
            serializer = self.get_serializer(data=mutable_data)
            serializer.is_valid(raise_exception=True) # 유효성 검증 실패 시 400 Bad Request 자동 반환
            
            with transaction.atomic(): # 데이터 일관성을 위한 트랜잭션 시작
                message = serializer.save() # 시리얼라이저의 create 메서드 호출
            
            # 활성화된 업체 수 조회 (실제 메시지 발송 대상 수)
            active_companies_count = Company.objects.filter(status=True).count()
            
            logger.info(f"[CompanyMessageViewSet.send_bulk_message] 일괄 메시지 발송 완료. 메시지: '{message.message[:50]}...', 대상 업체 수: {active_companies_count}개, ID: {message.id}")
            
            return Response({
                'message': f'전체 {active_companies_count}개 업체에 메시지가 성공적으로 발송되었습니다.',
                'message_id': str(message.id),
                'target_count': active_companies_count
            }, status=status.HTTP_201_CREATED)
        
        except serializers.ValidationError as e:
            logger.warning(f"[CompanyMessageViewSet.send_bulk_message] 일괄 메시지 발송 요청 유효성 검증 실패: {e.detail} - 발송자: {user.username}, 데이터: {request.data}")
            raise
        except Exception as e:
            logger.error(f"[CompanyMessageViewSet.send_bulk_message] 일괄 메시지 발송 중 예상치 못한 오류 발생 - 발송자: {user.username}, 데이터: {request.data}, 오류: {str(e)}", exc_info=True)
            return Response(
                {"error": "일괄 메시지 발송 중 서버 내부 오류가 발생했습니다. 관리자에게 문의해주세요."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )