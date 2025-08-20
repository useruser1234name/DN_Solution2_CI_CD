@csrf_exempt
def policy_api_detail(request, policy_id):
    """정책 상세 조회 API (AJAX용)"""
    if request.method == 'GET':
        try:
            policy = get_object_or_404(Policy, id=policy_id)
            
            # 정책 시리얼라이저로 변환
            serializer = PolicySerializer(policy)
            
            return JsonResponse({
                'success': True,
                'data': serializer.data
            })
        
        except Policy.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': '정책을 찾을 수 없습니다.'
            }, status=404)
        except Exception as e:
            logger.error(f"정책 상세 조회 실패: {str(e)}")
            return JsonResponse({
                'success': False,
                'message': '정책 정보를 불러오는 중 오류가 발생했습니다.'
            }, status=500)
    
    return JsonResponse({'success': False, 'message': '잘못된 요청입니다.'}, status=405)


@csrf_exempt
def policy_api_update(request, policy_id):
    """정책 수정 API (AJAX용)"""
    if request.method in ['PUT', 'PATCH']:
        try:
            policy = get_object_or_404(Policy, id=policy_id)
            
            # 권한 확인: 본사만 정책 수정 가능
            if not request.user.is_superuser:
                try:
                    from companies.models import CompanyUser
                    company_user = CompanyUser.objects.get(django_user=request.user)
                    if company_user.company.type != 'headquarters':
                        return JsonResponse({
                            'success': False,
                            'message': '본사 관리자만 정책을 수정할 수 있습니다.'
                        }, status=403)
                except CompanyUser.DoesNotExist:
                    return JsonResponse({
                        'success': False,
                        'message': '업체 정보를 찾을 수 없습니다.'
                    }, status=400)
            
            # JSON 데이터 파싱
            import json
            data = json.loads(request.body)
            
            # 기본 필드 업데이트
            policy.title = data.get('title', policy.title)
            policy.description = data.get('description', policy.description)
            policy.carrier = data.get('carrier', policy.carrier)
            policy.rebate_agency = data.get('rebate_agency', policy.rebate_agency)
            policy.rebate_retail = data.get('rebate_retail', policy.rebate_retail)
            policy.expose = data.get('expose', policy.expose)
            policy.premium_market_expose = data.get('premium_market_expose', policy.premium_market_expose)
            policy.is_active = data.get('is_active', policy.is_active)
            
            policy.save()
            
            logger.info(f"정책 수정 완료: {policy.title} (사용자: {request.user.username})")
            
            # 수정된 정책 데이터 반환
            serializer = PolicySerializer(policy)
            
            return JsonResponse({
                'success': True,
                'message': '정책이 성공적으로 수정되었습니다.',
                'data': serializer.data
            })
            
        except Policy.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': '정책을 찾을 수 없습니다.'
            }, status=404)
        except json.JSONDecodeError:
            return JsonResponse({
                'success': False,
                'message': '잘못된 JSON 형식입니다.'
            }, status=400)
        except Exception as e:
            logger.error(f"정책 수정 실패: {str(e)}")
            return JsonResponse({
                'success': False,
                'message': '정책 수정 중 오류가 발생했습니다.'
            }, status=500)
    
    return JsonResponse({'success': False, 'message': '잘못된 요청입니다.'}, status=405)


# Commission Matrix API
class PolicyCommissionMatrixView(APIView):
    """정책별 수수료 매트릭스 API (기존 RebateMatrix → CommissionMatrix)"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request, policy_id):
        """정책의 수수료 매트릭스 조회"""
        try:
            from .models import CommissionMatrix
            
            logger.info(f"수수료 매트릭스 조회 요청 - 정책 ID: {policy_id}")
            policy = get_object_or_404(Policy, id=policy_id)
            logger.info(f"정책 찾음: {policy.title}")
            
            # 해당 정책의 수수료 매트릭스 조회
            matrix_queryset = CommissionMatrix.objects.filter(policy=policy).order_by('plan_range', 'contract_period')
            logger.info(f"수수료 매트릭스 개수: {matrix_queryset.count()}")
            
            if not matrix_queryset.exists():
                # 매트릭스가 없으면 빈 매트릭스 반환
                logger.info("수수료 매트릭스가 없음, 빈 매트릭스 반환")
                return Response({
                    'success': True,
                    'data': {
                        'policy_id': str(policy.id),
                        'policy_title': policy.title,
                        'matrix': []
                    }
                })
            
            # 매트릭스 데이터 직렬화
            matrix_data = []
            for matrix_item in matrix_queryset:
                matrix_data.append({
                    'id': str(matrix_item.id),
                    'plan_range': matrix_item.plan_range,
                    'plan_range_display': matrix_item.get_plan_range_display(),
                    'contract_period': matrix_item.contract_period,
                    'commission_amount': float(matrix_item.commission_amount),
                    'carrier': matrix_item.carrier,
                    'row': list(dict(CommissionMatrix.PLAN_RANGE_CHOICES).keys()).index(matrix_item.plan_range),
                    'col': 0 if matrix_item.contract_period == 12 else (1 if matrix_item.contract_period == 24 else 2)
                })
            
            logger.info(f"수수료 매트릭스 직렬화 완료: {len(matrix_data)}개 항목")
            return Response({
                'success': True,
                'data': {
                    'policy_id': str(policy.id),
                    'policy_title': policy.title,
                    'matrix': matrix_data
                }
            })
            
        except Exception as e:
            logger.error(f"수수료 매트릭스 조회 오류: {str(e)}")
            return Response({
                'success': False,
                'message': '수수료 매트릭스를 불러오는 중 오류가 발생했습니다.'
            }, status=500)
    
    def post(self, request, policy_id):
        """수수료 매트릭스 생성/수정"""
        return self._save_matrix(request, policy_id)
    
    def put(self, request, policy_id):
        """수수료 매트릭스 수정 (POST와 동일)"""
        return self._save_matrix(request, policy_id)
    
    def _save_matrix(self, request, policy_id):
        """수수료 매트릭스 저장 공통 로직"""
        try:
            from .models import CommissionMatrix
            
            policy = get_object_or_404(Policy, id=policy_id)
            data = request.data
            
            # 기존 매트릭스 삭제 후 새로 생성
            CommissionMatrix.objects.filter(policy=policy).delete()
            
            # 새 매트릭스 생성
            matrix_data = data.get('matrix', [])
            created_count = 0
            
            for item in matrix_data:
                # plan_range 값 처리
                plan_range_raw = item.get('plan_range', 11000)
                if isinstance(plan_range_raw, str):
                    plan_range_value = int(plan_range_raw.replace('K', '')) * 1000
                else:
                    plan_range_value = int(plan_range_raw)
                
                commission_amount = item.get('commission_amount', 0)
                contract_period = item.get('contract_period', 12)
                
                # 0이 아닌 수수료만 저장
                if commission_amount > 0:
                    CommissionMatrix.objects.create(
                        policy=policy,
                        carrier=policy.carrier,
                        plan_range=plan_range_value,
                        contract_period=contract_period,
                        commission_amount=commission_amount
                    )
                    created_count += 1
            
            logger.info(f"수수료 매트릭스 저장 완료: 정책 {policy.title}, {created_count}개 항목")
            
            return Response({
                'success': True,
                'message': f'수수료 매트릭스가 저장되었습니다. ({created_count}개 항목)',
                'data': {
                    'policy_id': str(policy.id),
                    'matrix_count': created_count
                }
            })
            
        except Exception as e:
            logger.error(f"수수료 매트릭스 저장 오류: {str(e)}")
            return Response({
                'success': False,
                'message': '수수료 매트릭스 저장 중 오류가 발생했습니다.'
            }, status=500)


# Commission Grade API
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def policy_commission_grades(request, policy_id):
    """정책별 수수료 그레이드 조회 API"""
    try:
        policy = get_object_or_404(Policy, id=policy_id)
        
        # 수수료 그레이드 반환
        commission_grades = policy.commission_grades or []
        
        return Response({
            'success': True,
            'data': {
                'policy_id': str(policy.id),
                'policy_title': policy.title,
                'grade_period_type': policy.grade_period_type,
                'grade_period_type_display': policy.get_grade_period_type_display(),
                'commission_grades': commission_grades,
                'grade_summary': policy.get_grade_summary()
            }
        })
        
    except Exception as e:
        logger.error(f"수수료 그레이드 조회 오류: {str(e)}")
        return Response({
            'success': False,
            'message': '수수료 그레이드를 불러오는 중 오류가 발생했습니다.'
        }, status=500)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def calculate_grade_bonus(request):
    """그레이드 보너스 계산 API"""
    try:
        data = request.data
        policy_id = data.get('policy_id')
        company_id = data.get('company_id')
        order_count = data.get('order_count', 0)
        
        if not all([policy_id, company_id]):
            return Response({
                'success': False,
                'message': '필수 파라미터가 누락되었습니다.'
            }, status=400)
        
        policy = get_object_or_404(Policy, id=policy_id)
        company = get_object_or_404(Company, id=company_id)
        
        # 적용 가능한 그레이드 찾기
        applicable_grade = policy.get_applicable_grade(order_count)
        
        if applicable_grade:
            bonus_per_order = float(applicable_grade['bonus_per_order'])
            total_bonus = order_count * bonus_per_order
            
            return Response({
                'success': True,
                'data': {
                    'policy_id': str(policy.id),
                    'company_id': str(company.id),
                    'order_count': order_count,
                    'applicable_grade': applicable_grade,
                    'bonus_per_order': bonus_per_order,
                    'total_bonus': total_bonus,
                    'grade_period_type': policy.grade_period_type
                }
            })
        else:
            return Response({
                'success': True,
                'data': {
                    'policy_id': str(policy.id),
                    'company_id': str(company.id),
                    'order_count': order_count,
                    'applicable_grade': None,
                    'bonus_per_order': 0,
                    'total_bonus': 0,
                    'grade_period_type': policy.grade_period_type,
                    'message': '적용 가능한 그레이드가 없습니다.'
                }
            })
        
    except Exception as e:
        logger.error(f"그레이드 보너스 계산 오류: {str(e)}")
        return Response({
            'success': False,
            'message': '그레이드 보너스 계산 중 오류가 발생했습니다.'
        }, status=500)