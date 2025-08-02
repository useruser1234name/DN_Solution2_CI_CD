# 슈퍼유저와 CompanyUser 권한 및 연동 문제

## 현상
- Django 관리자(슈퍼유저) 계정으로 로그인해도, 일부 API(예: 업체 목록 조회, 생성, 수정, 삭제 등)에서 403 Forbidden 에러가 발생할 수 있음
- 이는 슈퍼유저가 CompanyUser 테이블에 등록되어 있지 않으면 발생

## 원인
- 대부분의 ViewSet/권한 로직이 CompanyUser에 등록된 사용자만 허용하도록 설계되어 있음
- 슈퍼유저라도 CompanyUser에 등록되어 있지 않으면 일부 API에서 권한 부족(403) 발생

## 해결 방법

### 1. 관리자 페이지에서 슈퍼유저를 CompanyUser로 등록
- Django Admin → 업체 사용자(CompanyUser) → 슈퍼유저 계정(admin, admin2 등) 등록
- 소속 업체, 역할 등 지정
- 가장 빠르고 쉬운 방법

### 2. 코드에서 슈퍼유저 예외 처리 강화
- ViewSet의 get_queryset, create, update, destroy 등에서
  ```python
  user = self.request.user
  if user.is_superuser:
      # 슈퍼유저는 모든 권한 허용
      return super().get_queryset()
  ```
- 각 메서드에서 슈퍼유저면 바로 통과하도록 처리
- 유지보수성과 확장성이 좋음

## 실무 팁
- 개발/운영 환경에서 슈퍼유저 계정은 CompanyUser에도 등록해두는 것이 편리함
- 권한 로직을 리팩토링할 때는 슈퍼유저 예외를 항상 고려할 것
- 문제가 발생하면 로그(로그인, 쿼리셋, 권한 체크 등)를 적극적으로 활용할 것

---

**이 문서는 DN_solution 프로젝트의 슈퍼유저 권한 및 CompanyUser 연동 이슈를 해결하기 위한 가이드입니다.** 