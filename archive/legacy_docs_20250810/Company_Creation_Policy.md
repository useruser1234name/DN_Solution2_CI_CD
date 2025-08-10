# Company 생성 정책 (Company Creation Policy)

## 1. 개요

이 문서는 `DN_solution` 프로젝트 내 `Company` 모델의 생성 정책에 대해 설명합니다. 특히, 각 계층(본사, 협력사)이 어떤 유형의 하위 업체를 생성할 수 있는지에 대한 현재 백엔드 로직과, 향후 적용될 수 있는 비즈니스 규칙 강화 방안을 다룹니다.

## 2. 현재 백엔드 로직 (Current Backend Logic)

현재 `companies/models.py`의 `Company` 모델과 `companies/views.py`의 `CompanyViewSet` `create` 메서드에 구현된 `Company` 생성 정책은 다음과 같습니다.

### 2.1. `Company` 모델의 유효성 검증 (`models.py`의 `clean` 메서드)

`Company` 모델 자체는 데이터의 무결성을 보장하기 위해 다음과 같은 규칙을 강제합니다.

*   **본사 (headquarters):**
    *   상위 업체(`parent_company`)를 가질 수 없습니다.
    *   시스템 내에 오직 하나만 존재해야 합니다.
*   **협력사 (agency):**
    *   반드시 상위 업체로 `headquarters` 타입의 `Company`를 지정해야 합니다.
*   **판매점 (retail):**
    *   반드시 상위 업체로 `agency` 타입의 `Company`를 지정해야 합니다.

이러한 규칙들은 어떤 계층의 사용자가 `Company`를 생성하든 관계없이, 데이터베이스에 저장되기 전에 모델 레벨에서 항상 검증됩니다.

### 2.2. `CompanyViewSet`의 `create` 메서드 (`views.py`)

API를 통한 `Company` 생성 시, `CompanyViewSet`의 `create` 메서드는 다음과 같은 로직을 포함합니다.

*   **본사 계정 (Superuser 또는 `headquarters` 타입 `Company`에 속한 `CompanyUser`):**
    *   **협력사(`agency`) 생성:** 가능합니다. 본사 계정은 `agency` 타입의 업체를 생성할 수 있습니다. 이 경우 `models.py`의 `clean` 메서드에 의해 상위 업체로 본사가 지정되어야 합니다.
    *   **판매점(`retail`) 생성:** **현재 로직상 가능합니다.** 본사 계정이 판매점을 생성할 때, 요청 데이터에 유효한 협력사(`agency`) ID를 `parent_company`로 지정하면 `models.py`의 `clean` 메서드 유효성 검증을 통과하여 판매점 생성이 허용됩니다.
        *   **특징:** 본사가 직접 판매점을 생성하는 경우에도, 판매점은 반드시 협력사 하위에 속해야 한다는 모델의 규칙을 따라야 합니다. 즉, 본사가 임의의 판매점을 생성할 수는 없으며, 반드시 기존의 협력사를 상위 업체로 지정해야 합니다.

*   **협력사 계정 (`agency` 타입 `Company`에 속한 `CompanyUser`):**
    *   **판매점(`retail`) 생성:** 가능합니다. `create` 메서드 내에서 협력사 사용자가 `retail` 타입의 업체를 생성하려고 하면, 해당 협력사(`request.user.companyuser.company`)가 자동으로 `parent_company`로 할당되어 판매점 생성이 허용됩니다.

## 3. 향후 비즈니스 규칙 강화 방안: 본사의 판매점 직접 생성 금지 (Future Policy Enhancement)

현재 백엔드 로직은 본사가 유효한 상위 협력사를 지정하는 경우 판매점 생성을 허용하지만, 비즈니스 요구사항에 따라 **본사가 판매점을 직접 생성하는 것을 명시적으로 금지**할 필요가 있을 수 있습니다.

이러한 정책을 적용하려면 `companies/views.py`의 `CompanyViewSet` 내 `create` 메서드에 추가적인 권한 검증 로직을 구현해야 합니다.

### 3.1. 백엔드 구현 방안

`CompanyViewSet`의 `create` 메서드 내에서, 요청을 보낸 사용자가 본사 계정(`headquarters` 타입)이고 생성하려는 `Company`의 `type`이 `retail`인 경우, 해당 요청을 거부하는 로직을 추가합니다.

```python
# companies/views.py (CompanyViewSet의 create 메서드 내)

# ... (기존 코드)

    def create(self, request, *args, **kwargs):
        user = request.user
        logger.info(f"업체 생성 요청 시작 - 사용자: {user}")
        
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            # --- 추가될 로직 시작 ---
            # 본사 계정이 판매점을 직접 생성하는 것을 금지
            if user.is_superuser or (hasattr(user, 'companyuser') and user.companyuser.company.type == 'headquarters'):
                if serializer.validated_data.get('type') == 'retail':
                    logger.warning(f"본사 계정({user.username})이 판매점 직접 생성을 시도했습니다.")
                    return Response(
                        {"error": "본사 계정은 판매점을 직접 생성할 수 없습니다. 협력사를 통해 생성해주세요."},
                        status=status.HTTP_403_FORBIDDEN # 또는 HTTP_400_BAD_REQUEST
                    )
            # --- 추가될 로직 끝 ---

            # 대리점 관리자가 판매점을 생성하는 경우, parent_company 자동 할당
            if hasattr(user, 'companyuser') and user.companyuser.company.type == 'agency':
                if serializer.validated_data.get('type') == 'retail':
                    serializer.validated_data['parent_company'] = user.companyuser.company

            with transaction.atomic():
                company = serializer.save()
            
            logger.info(f"업체 생성 성공: {company.name} (ID: {company.id})")
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        
        except Exception as e:
            logger.error(f"업체 생성 실패: {str(e)} - 요청 데이터: {request.data}")
            return Response(
                {"error": "업체 생성 중 오류가 발생했습니다."},
                status=status.HTTP_400_BAD_REQUEST
            )
```

### 3.2. 프론트엔드 구현 방안

백엔드 정책 변경에 맞춰 프론트엔드 UI도 업데이트해야 합니다.

*   **본사 계정의 '판매점 생성' UI 요소 비활성화/숨김:**
    *   본사 계정으로 로그인했을 때, '새로운 Company 생성' 폼에서 '업체 유형'을 '판매점'으로 선택하는 옵션을 비활성화하거나, 아예 해당 폼 자체를 숨깁니다.
    *   또는, '판매점 생성' 버튼을 숨기거나 비활성화합니다.
*   **사용자 안내:** 본사 계정이 판매점 생성을 시도할 경우, 백엔드에서 반환하는 오류 메시지를 사용자에게 명확하게 표시하여 정책을 안내합니다.

## 4. 결론

현재 `DN_solution`의 `Company` 생성 로직은 모델 레벨에서 계층적 유효성을 검증하고 있습니다. 본사가 판매점을 직접 생성하는 것을 금지하는 것은 추가적인 비즈니스 규칙으로, `CompanyViewSet`의 `create` 메서드에 로직을 추가하여 강화할 수 있습니다. 이는 백엔드와 프론트엔드 양쪽에서 일관되게 적용되어야 합니다.
