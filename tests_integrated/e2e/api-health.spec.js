// @ts-check
const { test, expect } = require('@playwright/test');

test.describe('API 상태 확인 테스트', () => {
  test('백엔드 API 서버 연결 확인', async ({ request }) => {
    // API 서버 상태 확인
    const response = await request.get('http://localhost:8001/api/health-check/');
    
    // 응답 상태 확인
    expect(response.ok()).toBeTruthy();
    
    // 응답 본문 확인
    const body = await response.json();
    expect(body.status).toBe('ok');
  });

  test('인증 API 엔드포인트 확인', async ({ request }) => {
    // 인증 API 엔드포인트 확인
    const response = await request.get('http://localhost:8001/api/auth/token/');
    
    // 405 Method Not Allowed 응답 예상 (GET 요청이므로)
    // 이는 엔드포인트가 존재하지만 POST 요청만 허용함을 의미
    expect(response.status()).toBe(405);
  });

  test('회사 API 엔드포인트 확인', async ({ request }) => {
    // 회사 API 엔드포인트 확인 (인증 필요)
    const response = await request.get('http://localhost:8001/api/companies/');
    
    // 401 Unauthorized 응답 예상 (인증 필요)
    expect(response.status()).toBe(401);
  });
});